"""Neo4j drivers and privacy-safe query instrumentation."""

from __future__ import annotations

from typing import Any

from neo4j import AsyncGraphDatabase, GraphDatabase, RoutingControl
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.config import settings

_driver = None
_async_driver = None
_tracer = trace.get_tracer(__name__)


def _require_config() -> None:
    if not settings.NEO4J_URI or not settings.NEO4J_USER or not settings.NEO4J_PASSWORD:
        raise RuntimeError(
            "Neo4j configuration missing. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD."
        )


def _driver_config() -> dict[str, Any]:
    return {
        "auth": (settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        "connection_timeout": 30,
        "connection_acquisition_timeout": 30,
        "max_transaction_retry_time": 30,
        "max_connection_lifetime": 3600,
        "max_connection_pool_size": 50,
        "keep_alive": True,
    }


def _set_summary_attributes(span, summary, record_count: int) -> None:
    span.set_attribute("db.response.returned_rows", record_count)
    if summary is None:
        return
    available_after = getattr(summary, "result_available_after", None)
    consumed_after = getattr(summary, "result_consumed_after", None)
    if available_after is not None:
        span.set_attribute("neo4j.result_available_after_ms", available_after)
    if consumed_after is not None:
        span.set_attribute("neo4j.result_consumed_after_ms", consumed_after)


def _session_database_kwargs() -> dict[str, str]:
    if settings.NEO4J_DATABASE:
        return {"database": settings.NEO4J_DATABASE}
    return {}


def _execute_database_kwargs() -> dict[str, str]:
    if settings.NEO4J_DATABASE:
        return {"database_": settings.NEO4J_DATABASE}
    return {}


def _query_span(query_name: str, access_mode: str):
    span = _tracer.start_as_current_span(f"neo4j.{query_name}")
    return span, {
        "db.system": "neo4j",
        "db.namespace": settings.NEO4J_DATABASE or "home",
        "db.operation.name": query_name,
        "db.operation.type": access_mode,
    }


def get_driver():
    """Get or create Neo4j driver singleton."""
    global _driver
    if _driver is None:
        _require_config()
        _driver = GraphDatabase.driver(settings.NEO4J_URI, **_driver_config())
    return _driver


def get_async_driver():
    """Get the application-scoped async driver used by request handlers."""
    global _async_driver
    if _async_driver is None:
        _require_config()
        _async_driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, **_driver_config())
    return _async_driver


def close_driver():
    """Close the Neo4j driver."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


async def close_async_driver() -> None:
    global _async_driver
    if _async_driver is not None:
        await _async_driver.close()
        _async_driver = None


async def close_drivers() -> None:
    """Close both request-path and background/script driver pools."""
    close_driver()
    await close_async_driver()


def read_query(query: str, *, _query_name: str = "read", **params) -> list[dict]:
    """Execute a read query and return results as list of dicts."""
    driver = get_driver()
    context, attributes = _query_span(_query_name, "read")
    with context as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        try:
            with driver.session(**_session_database_kwargs()) as session:
                def work(tx):
                    result = tx.run(query, **params)
                    records = list(result)
                    return records, result.consume()

                records, summary = session.execute_read(work)
            _set_summary_attributes(span, summary, len(records))
            return [record.data() for record in records]
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise


def write_query(query: str, *, _query_name: str = "write", **params) -> list[dict]:
    """Execute a write query (CREATE/SET/MERGE) and return results as list of dicts."""
    driver = get_driver()
    context, attributes = _query_span(_query_name, "write")
    with context as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        try:
            with driver.session(**_session_database_kwargs()) as session:
                def work(tx):
                    result = tx.run(query, **params)
                    records = list(result)
                    return records, result.consume()

                records, summary = session.execute_write(work)
            _set_summary_attributes(span, summary, len(records))
            return [record.data() for record in records]
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise


async def async_read_query(query: str, *, _query_name: str = "read", **params) -> list[dict]:
    """Execute a read without blocking FastAPI's event loop."""
    driver = get_async_driver()
    context, attributes = _query_span(_query_name, "read")
    with context as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        try:
            records, summary, _ = await driver.execute_query(
                query,
                parameters_=params,
                routing_=RoutingControl.READ,
                **_execute_database_kwargs(),
            )
            _set_summary_attributes(span, summary, len(records))
            return [record.data() for record in records]
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise


async def async_write_query(query: str, *, _query_name: str = "write", **params) -> list[dict]:
    """Execute a write without blocking FastAPI's event loop."""
    driver = get_async_driver()
    context, attributes = _query_span(_query_name, "write")
    with context as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        try:
            records, summary, _ = await driver.execute_query(
                query,
                parameters_=params,
                routing_=RoutingControl.WRITE,
                **_execute_database_kwargs(),
            )
            _set_summary_attributes(span, summary, len(records))
            return [record.data() for record in records]
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise
