"""
Pydantic models for the Common Textbook JSON Format.

These models define the structure every chapter must conform to before
being ingested into the Neo4j knowledge graph. They serve as both
validation and documentation of the ingestion contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class ContentType(str, Enum):
    """Type of content within a subsection."""

    EXPLANATION = "explanation"
    DERIVATION = "derivation"
    LAW = "law"
    DEFINITION = "definition"
    THEOREM = "theorem"
    EXPERIMENT = "experiment"
    APPLICATION = "application"


class Difficulty(str, Enum):
    """Exercise difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ExerciseType(str, Enum):
    """Types of exercises."""

    CONCEPTUAL = "conceptual"
    NUMERICAL = "numerical"
    DERIVATION = "derivation"
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"


class PrerequisiteType(str, Enum):
    """Whether a prerequisite references a specific section or an abstract concept."""

    SECTION = "section"
    CONCEPT = "concept"


# =============================================================================
# Nested Content Models
# =============================================================================


class Diagram(BaseModel):
    """A diagram/figure referenced within a subsection."""

    label: str = Field(..., description="Display label, e.g. 'Fig 7.1'")
    description: str = Field(..., description="Alt-text / description of the diagram")
    image_url: Optional[str] = Field(None, description="URL or path to the image asset")


class Table(BaseModel):
    """A table referenced within a subsection."""

    label: Optional[str] = Field(None, description="Display label, e.g. 'Table 1.1'")
    caption: Optional[str] = Field(None, description="Table caption / title")
    headers: list[str] = Field(default_factory=list, description="Column header labels")
    rows: list[list[str]] = Field(default_factory=list, description="Table data rows")


class WorkedExample(BaseModel):
    """A worked-out example within a subsection."""

    label: str = Field(..., description="Display label, e.g. 'Example 7.1'")
    problem: str = Field(..., description="Problem statement (supports LaTeX)")
    solution: Optional[str] = Field(None, description="Worked solution (supports LaTeX)")


class Subsection(BaseModel):
    """
    An atomic teaching unit within a section.
    The tutor teaches one subsection at a time.
    """

    order: int = Field(..., ge=1, description="Position within the parent section (1-indexed)")
    title: str = Field(..., description="Subsection title")
    content_text: str = Field("", description="Full content text for LLM teaching context")
    content_type: ContentType = Field(
        ContentType.EXPLANATION,
        description="Type of content",
    )
    worked_examples: list[WorkedExample] = Field(
        default_factory=list,
        description="Worked examples within this subsection",
    )
    diagrams: list[Diagram] = Field(
        default_factory=list,
        description="Diagrams/figures within this subsection",
    )
    tables: list[Table] = Field(
        default_factory=list,
        description="Tables within this subsection",
    )


class Prerequisite(BaseModel):
    """
    A prerequisite reference. Can point to either a specific section
    (using full hierarchical ID) or an abstract concept.
    """

    type: PrerequisiteType = Field(..., description="Whether this is a section or concept reference")
    ref: str = Field(
        ...,
        description=(
            "Full ID of the prerequisite. "
            "For sections: 'ncert:physics:11:6:2'. "
            "For concepts: 'concept:vectors'."
        ),
    )


class Section(BaseModel):
    """A numbered section within a chapter (e.g., 7.3)."""

    number: str = Field(..., description="Section number string, e.g. '7.3'")
    title: str = Field(..., description="Section title")
    content_text: Optional[str] = Field(
        None,
        description="Full section text (if not split into subsections)",
    )
    subsections: list[Subsection] = Field(
        default_factory=list,
        description="Ordered list of subsections (atomic teaching units)",
    )
    prerequisites: list[Prerequisite] = Field(
        default_factory=list,
        description="Prerequisite sections or concepts",
    )


# =============================================================================
# Exercise Models
# =============================================================================


class ExerciseItem(BaseModel):
    """An individual end-of-chapter problem."""

    number: int = Field(..., ge=1, description="Exercise number")
    problem: str = Field(..., description="Problem statement (supports LaTeX)")
    solution: Optional[str] = Field(None, description="Official solution (supports LaTeX)")
    difficulty: Optional[Difficulty] = Field(None, description="Difficulty level")
    exercise_type: Optional[ExerciseType] = Field(None, description="Problem type")
    tests_concepts: list[str] = Field(
        default_factory=list,
        description="IDs of concepts or sections this exercise tests",
    )


class ExerciseSet(BaseModel):
    """End-of-chapter exercise collection."""

    title: str = Field("Exercises", description="Title of the exercise set")
    items: list[ExerciseItem] = Field(
        default_factory=list,
        description="List of exercises",
    )


# =============================================================================
# Top-Level Models
# =============================================================================


class Chapter(BaseModel):
    """A chapter within a textbook."""

    number: int = Field(..., ge=1, description="Chapter number")
    title: str = Field(..., description="Chapter title")
    summary: Optional[str] = Field(None, description="Brief chapter summary")
    sections: list[Section] = Field(..., min_length=1, description="Ordered list of sections")
    exercises: Optional[ExerciseSet] = Field(None, description="End-of-chapter exercises")


class TextbookChapter(BaseModel):
    """
    Root model for the Common Textbook JSON Format.

    Every chapter from any textbook must conform to this schema
    before being ingested into the Neo4j knowledge graph.
    """

    curriculum: str = Field(..., description="Curriculum identifier, e.g. 'ncert'")
    subject: str = Field(..., description="Subject identifier, e.g. 'physics'")
    grade: int = Field(..., ge=1, le=12, description="Grade/class number")
    textbook_name: str = Field(..., description="Full textbook title")
    volume: int = Field(1, ge=1, description="Volume number if textbook is split")
    chapter: Chapter = Field(..., description="The chapter data")

    def build_id_prefix(self) -> str:
        """Build the hierarchical ID prefix: {curriculum}:{subject}:{grade}"""
        return f"{self.curriculum}:{self.subject}:{self.grade}"

    def build_chapter_id(self) -> str:
        """Build the chapter ID: {prefix}:{chapter_number}"""
        return f"{self.build_id_prefix()}:{self.chapter.number}"
