"""
LearnerOS Tutor Router
- Stateful subsection tutor chat using LangGraph
- Context = subsection/section content + top matched active insights (if authenticated)
"""

from __future__ import annotations

from typing import TypedDict
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from openai import OpenAI
from langgraph.graph import StateGraph, END

from app.auth import get_optional_user, CurrentUser
from app.config import settings
from app.database import read_query, write_query
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/api", tags=["tutor"])

_llm_client: OpenAI | None = None
_embedding_client: OpenAI | None = None
_graph = None


class TutorState(TypedDict, total=False):
    student_id: str
    section_id: str
    subsection_id: str
    user_message: str
    subsection_context: str
    matched_insights: list[dict]
    history: list[dict]
    assistant_response: str


class GlobalTutorState(TypedDict, total=False):
    student_id: str
    user_message: str
    matched_insights: list[dict]
    history: list[dict]
    assistant_response: str


class TutorChatPayload(BaseModel):
    subsection_id: str
    message: str
    session_id: str | None = None


class TutorChatResponse(BaseModel):
    session_id: str
    response: str
    matched_insights: list[dict]


class GlobalTutorChatPayload(BaseModel):
    message: str
    session_id: str | None = None


class GlobalTutorChatResponse(BaseModel):
    session_id: str
    response: str
    matched_insights: list[dict]


class TutorHistoryMessage(BaseModel):
    role: str
    content: str


class TutorSessionHistoryResponse(BaseModel):
    session_id: str | None = None
    messages: list[TutorHistoryMessage] = []



def _get_llm_client() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        if not settings.FIREWORKS_API_KEY:
            raise HTTPException(status_code=500, detail="FIREWORKS_API_KEY not configured")
        _llm_client = OpenAI(api_key=settings.FIREWORKS_API_KEY, base_url=settings.FIREWORKS_BASE_URL)
    return _llm_client


def _get_embedding_client() -> OpenAI:
    global _embedding_client
    if _embedding_client is None:
        api_key = settings.FIREWORKS_API_KEY_EMBEDDINGS or settings.FIREWORKS_API_KEY
        if not api_key:
            raise HTTPException(status_code=500, detail="FIREWORKS_API_KEY_EMBEDDINGS (or FIREWORKS_API_KEY) not configured")
        _embedding_client = OpenAI(api_key=api_key, base_url=settings.FIREWORKS_BASE_URL)
    return _embedding_client


def _embed_query(text: str) -> list[float]:
    client = _get_embedding_client()
    resp = client.embeddings.create(
        model=settings.FIREWORKS_EMBEDDING_MODEL,
        input=text.strip(),
    )
    vec = resp.data[0].embedding if resp.data else None
    if not vec:
        return []
    return [float(v) for v in vec]


def _fetch_subsection_context(section_id: str, subsection_id: str) -> str:
    rows = read_query(
        """
        MATCH (sec:Section {id: $section_id})-[:CONTAINS]->(ss:Subsection)
        RETURN sec.title AS section_title,
               ss.id AS id,
               ss.title AS title,
               ss.content_text AS content,
               ss.order AS ord
        ORDER BY ss.order
        """,
        section_id=section_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Section content not found")

    target = next((r for r in rows if r.get("id") == subsection_id), None)
    if not target:
        raise HTTPException(status_code=400, detail="subsection_id not found in section")

    section_title = rows[0].get("section_title") or section_id
    target_title = target.get("title") or subsection_id
    target_body = target.get("content") or ""

    # Keep full section available but bounded.
    chunks: list[str] = []
    for r in rows:
        title = r.get("title") or r.get("id")
        body = (r.get("content") or "")[:1200]
        chunks.append(f"### {title}\n{body}")

    return (
        f"SECTION: {section_title}\n"
        f"CURRENT SUBSECTION: {target_title} ({subsection_id})\n\n"
        f"FOCUS SUBSECTION CONTENT:\n{target_body}\n\n"
        f"SECTION CONTEXT:\n" + "\n\n".join(chunks)
    )


def _search_top_insights(student_id: str, query: str, k: int = 4) -> list[dict]:
    emb = _embed_query(query)
    if not emb:
        return []
    try:
        rows = read_query(
            """
            CALL db.index.vector.queryNodes('insight_embedding_index', $n, $embedding)
            YIELD node, score
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(node)
            WHERE node.is_active = true
            OPTIONAL MATCH (node)-[:ABOUT_CONCEPT]->(c:Concept)
            OPTIONAL MATCH (node)-[:ABOUT_SOURCE]->(src)
            RETURN node.id AS id,
                   node.type AS type,
                   node.category AS category,
                   node.content AS content,
                   c.id AS concept_id,
                   c.name AS concept_name,
                   src.id AS source_id,
                   src.title AS source_title,
                   score AS similarity
            ORDER BY score DESC
            LIMIT $k
            """,
            student_id=student_id,
            embedding=emb,
            n=max(20, k * 4),
            k=k,
        )
    except Exception:
        rows = read_query(
            """
            MATCH (s:Student {id: $student_id})-[:HAS_INSIGHT]->(i:Insight {is_active: true})
            WHERE i.embedding IS NOT NULL
            WITH i, vector.similarity.cosine(i.embedding, $embedding) AS score
            OPTIONAL MATCH (i)-[:ABOUT_CONCEPT]->(c:Concept)
            OPTIONAL MATCH (i)-[:ABOUT_SOURCE]->(src)
            RETURN i.id AS id,
                   i.type AS type,
                   i.category AS category,
                   i.content AS content,
                   c.id AS concept_id,
                   c.name AS concept_name,
                   src.id AS source_id,
                   src.title AS source_title,
                   score AS similarity
            ORDER BY score DESC
            LIMIT $k
            """,
            student_id=student_id,
            embedding=emb,
            k=k,
        )
    return [r for r in rows if (r.get("similarity") or 0.0) >= 0.35]


def _load_conversation_history(student_id: str, session_id: str, limit: int = 12) -> list[dict]:
    rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_TUTOR_SESSION]->(sess:TutorSession {id: $session_id})
              -[:HAS_MESSAGE]->(m:TutorMessage)
        RETURN m.role AS role, m.content AS content
        ORDER BY m.created_at ASC
        LIMIT $limit
        """,
        student_id=student_id,
        session_id=session_id,
        limit=limit,
    )
    return [
        {"role": r.get("role"), "content": r.get("content")}
        for r in rows
        if r.get("role") in ("user", "assistant") and r.get("content")
    ]


def _load_latest_global_session_id(student_id: str) -> str | None:
    rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_TUTOR_SESSION]->(sess:TutorSession)
        WHERE sess.mode = 'global'
        RETURN sess.id AS id
        ORDER BY coalesce(sess.updated_at, sess.created_at) DESC
        LIMIT 1
        """,
        student_id=student_id,
    )
    return rows[0].get("id") if rows else None


def _load_latest_subsection_session_id(student_id: str, section_id: str, subsection_id: str) -> str | None:
    rows = read_query(
        """
        MATCH (s:Student {id: $student_id})-[:HAS_TUTOR_SESSION]->(sess:TutorSession)
        WHERE sess.section_id = $section_id AND sess.subsection_id = $subsection_id
        RETURN sess.id AS id
        ORDER BY coalesce(sess.updated_at, sess.created_at) DESC
        LIMIT 1
        """,
        student_id=student_id,
        section_id=section_id,
        subsection_id=subsection_id,
    )
    return rows[0].get("id") if rows else None


def _persist_conversation_turn(
    student_id: str,
    session_id: str,
    section_id: str,
    subsection_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    write_query(
        """
        MATCH (s:Student {id: $student_id})
        MERGE (s)-[:HAS_TUTOR_SESSION]->(sess:TutorSession {id: $session_id})
          ON CREATE SET
            sess.section_id = $section_id,
            sess.subsection_id = $subsection_id,
            sess.created_at = datetime()
        SET
          sess.section_id = $section_id,
          sess.subsection_id = $subsection_id,
          sess.updated_at = datetime()

        CREATE (u:TutorMessage {
          id: $user_msg_id,
          role: 'user',
          content: $user_message,
          created_at: datetime()
        })
        CREATE (a:TutorMessage {
          id: $assistant_msg_id,
          role: 'assistant',
          content: $assistant_message,
          created_at: datetime()
        })

        CREATE (sess)-[:HAS_MESSAGE]->(u)
        CREATE (sess)-[:HAS_MESSAGE]->(a)
        """,
        student_id=student_id,
        session_id=session_id,
        section_id=section_id,
        subsection_id=subsection_id,
        user_msg_id=f"tutor_msg:{uuid.uuid4().hex}",
        assistant_msg_id=f"tutor_msg:{uuid.uuid4().hex}",
        user_message=user_message,
        assistant_message=assistant_message,
    )


def _persist_global_conversation_turn(
    student_id: str,
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    write_query(
        """
        MATCH (s:Student {id: $student_id})
        MERGE (s)-[:HAS_TUTOR_SESSION]->(sess:TutorSession {id: $session_id})
          ON CREATE SET
            sess.mode = 'global',
            sess.created_at = datetime()
        SET
          sess.mode = 'global',
          sess.updated_at = datetime()

        CREATE (u:TutorMessage {
          id: $user_msg_id,
          role: 'user',
          content: $user_message,
          created_at: datetime()
        })
        CREATE (a:TutorMessage {
          id: $assistant_msg_id,
          role: 'assistant',
          content: $assistant_message,
          created_at: datetime()
        })

        CREATE (sess)-[:HAS_MESSAGE]->(u)
        CREATE (sess)-[:HAS_MESSAGE]->(a)
        """,
        student_id=student_id,
        session_id=session_id,
        user_msg_id=f"tutor_msg:{uuid.uuid4().hex}",
        assistant_msg_id=f"tutor_msg:{uuid.uuid4().hex}",
        user_message=user_message,
        assistant_message=assistant_message,
    )


def _node_retrieve_context(state: TutorState) -> TutorState:
    context = _fetch_subsection_context(state["section_id"], state["subsection_id"])
    insights = []
    student_id = state.get("student_id")
    if student_id:
        insights = _search_top_insights(student_id, state["user_message"], k=4)
    return {
        "subsection_context": context,
        "matched_insights": insights,
    }


def _node_respond(state: TutorState) -> TutorState:
    client = _get_llm_client()

    history = list(state.get("history", []))
    user_message = state.get("user_message", "")
    history.append({"role": "user", "content": user_message})

    insight_lines = []
    for ins in state.get("matched_insights", []):
        concept = ins.get("concept_name") or ins.get("concept_id") or "General"
        src = ins.get("source_title") or ins.get("source_id") or "Unknown"
        insight_lines.append(
            f"- [{ins.get('type')}/{ins.get('category')}] concept={concept}, source={src}, note={ins.get('content')}"
        )

    system_prompt = (
        "You are the student's LearnerOS subsection tutor. "
        "Teach based on section/subsection curriculum context. "
        "Use matched insights as personalized hints, not absolute truth. "
        "If uncertain, ask one clarifying question. "
        "Keep answers crisp, concrete, and educational. "
        "Use markdown formatting when it improves clarity (headings, bullets, short tables, emphasis)."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Keep short conversation memory.
    for m in history[-8:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})

    messages.append(
        {
            "role": "user",
            "content": (
                "SUBSECTION + SECTION CONTEXT:\n"
                f"{state.get('subsection_context', '')}\n\n"
                "TOP MATCHED ACTIVE INSIGHTS (semantic):\n"
                f"{chr(10).join(insight_lines) if insight_lines else '(none)'}\n\n"
                "Respond to the student's latest message now."
            ),
        }
    )

    resp = client.chat.completions.create(
        model=settings.FIREWORKS_MODEL,
        messages=messages,
        temperature=0.3,
        timeout=60,
    )
    content = resp.choices[0].message.content or ""
    if isinstance(content, list):
        content = "".join(
            p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
        )
    answer = str(content).strip()

    history.append({"role": "assistant", "content": answer})
    return {
        "assistant_response": answer,
        "history": history,
    }


def _node_retrieve_global_context(state: GlobalTutorState) -> GlobalTutorState:
    insights = []
    student_id = state.get("student_id")
    if student_id:
        insights = _search_top_insights(student_id, state["user_message"], k=5)
    return {"matched_insights": insights}


def _node_respond_global(state: GlobalTutorState) -> GlobalTutorState:
    client = _get_llm_client()

    history = list(state.get("history", []))
    user_message = state.get("user_message", "")
    history.append({"role": "user", "content": user_message})

    insight_lines = []
    for ins in state.get("matched_insights", []):
        concept = ins.get("concept_name") or ins.get("concept_id") or "General"
        src = ins.get("source_title") or ins.get("source_id") or "Unknown"
        insight_lines.append(
            f"- [{ins.get('type')}/{ins.get('category')}] concept={concept}, source={src}, note={ins.get('content')}"
        )

    system_prompt = (
        "You are the student's main LearnerOS tutor. "
        "You are textbook-agnostic and can explain concepts generally. "
        "If matched active insights are provided, use them as personalization hints only when relevant. "
        "Do not force unrelated insights into the answer. "
        "If the user asks a very domain-specific question without enough context, ask one clarifying question. "
        "Use markdown formatting when it improves clarity (headings, bullets, short tables, emphasis)."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in history[-8:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})

    messages.append(
        {
            "role": "user",
            "content": (
                "TOP MATCHED ACTIVE INSIGHTS (semantic):\n"
                f"{chr(10).join(insight_lines) if insight_lines else '(none)'}\n\n"
                "Respond to the student's latest message now."
            ),
        }
    )

    resp = client.chat.completions.create(
        model=settings.FIREWORKS_MODEL,
        messages=messages,
        temperature=0.3,
        timeout=60,
    )
    content = resp.choices[0].message.content or ""
    if isinstance(content, list):
        content = "".join(
            p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
        )
    answer = str(content).strip()

    history.append({"role": "assistant", "content": answer})
    return {
        "assistant_response": answer,
        "history": history,
    }


def _get_graph():
    global _graph
    if _graph is not None:
        return _graph

    workflow = StateGraph(TutorState)
    workflow.add_node("retrieve_context", _node_retrieve_context)
    workflow.add_node("respond", _node_respond)
    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "respond")
    workflow.add_edge("respond", END)

    _graph = workflow.compile()
    return _graph


_global_graph = None


def _get_global_graph():
    global _global_graph
    if _global_graph is not None:
        return _global_graph

    workflow = StateGraph(GlobalTutorState)
    workflow.add_node("retrieve_global_context", _node_retrieve_global_context)
    workflow.add_node("respond_global", _node_respond_global)
    workflow.set_entry_point("retrieve_global_context")
    workflow.add_edge("retrieve_global_context", "respond_global")
    workflow.add_edge("respond_global", END)

    _global_graph = workflow.compile()
    return _global_graph


@router.post("/sections/{section_id:path}/tutor/chat", response_model=TutorChatResponse)
async def tutor_chat(
    section_id: str,
    body: TutorChatPayload,
    request: Request,
    user: CurrentUser | None = Depends(get_optional_user),
):
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")
    enforce_rate_limit(
        request,
        scope="tutor_subsection_chat",
        limit=30,
        window_seconds=60,
        user_key=user.student_id if user else None,
    )

    session_id = body.session_id or f"tutor:{uuid.uuid4().hex}"
    history = _load_conversation_history(user.student_id, session_id, limit=12) if user else []

    graph = _get_graph()
    result = graph.invoke(
        {
            "student_id": user.student_id if user else "",
            "section_id": section_id,
            "subsection_id": body.subsection_id,
            "user_message": msg,
            "history": history,
        },
    )

    answer = result.get("assistant_response", "")
    if user and answer:
        _persist_conversation_turn(
            student_id=user.student_id,
            session_id=session_id,
            section_id=section_id,
            subsection_id=body.subsection_id,
            user_message=msg,
            assistant_message=answer,
        )

    return {
        "session_id": session_id,
        "response": answer,
        "matched_insights": result.get("matched_insights", []),
    }


@router.get("/sections/{section_id:path}/tutor/session/latest", response_model=TutorSessionHistoryResponse)
async def latest_subsection_tutor_session(
    section_id: str,
    subsection_id: str,
    user: CurrentUser | None = Depends(get_optional_user),
):
    if not user:
        return {"session_id": None, "messages": []}
    sess_id = _load_latest_subsection_session_id(user.student_id, section_id, subsection_id)
    if not sess_id:
        return {"session_id": None, "messages": []}
    messages = _load_conversation_history(user.student_id, sess_id, limit=40)
    return {"session_id": sess_id, "messages": messages}


@router.post("/tutor/chat", response_model=GlobalTutorChatResponse)
async def global_tutor_chat(
    body: GlobalTutorChatPayload,
    request: Request,
    user: CurrentUser | None = Depends(get_optional_user),
):
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")
    enforce_rate_limit(
        request,
        scope="tutor_global_chat",
        limit=30,
        window_seconds=60,
        user_key=user.student_id if user else None,
    )

    session_id = body.session_id or f"global_tutor:{uuid.uuid4().hex}"
    history = _load_conversation_history(user.student_id, session_id, limit=12) if user else []

    graph = _get_global_graph()
    result = graph.invoke(
        {
            "student_id": user.student_id if user else "",
            "user_message": msg,
            "history": history,
        }
    )

    answer = result.get("assistant_response", "")
    if user and answer:
        _persist_global_conversation_turn(
            student_id=user.student_id,
            session_id=session_id,
            user_message=msg,
            assistant_message=answer,
        )

    return {
        "session_id": session_id,
        "response": answer,
        "matched_insights": result.get("matched_insights", []),
    }


@router.get("/tutor/session/latest", response_model=TutorSessionHistoryResponse)
async def latest_global_tutor_session(user: CurrentUser | None = Depends(get_optional_user)):
    if not user:
        return {"session_id": None, "messages": []}
    sess_id = _load_latest_global_session_id(user.student_id)
    if not sess_id:
        return {"session_id": None, "messages": []}
    messages = _load_conversation_history(user.student_id, sess_id, limit=40)
    return {"session_id": sess_id, "messages": messages}
