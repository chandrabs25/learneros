"""
Neo4j driver singleton — shared across all routers.
"""

from contextlib import asynccontextmanager
from neo4j import GraphDatabase

from app.config import settings

_driver = None


def get_driver():
    """Get or create Neo4j driver singleton."""
    global _driver
    if _driver is None:
        if not settings.NEO4J_URI or not settings.NEO4J_USER or not settings.NEO4J_PASSWORD:
            raise RuntimeError("Neo4j configuration missing. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD.")
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


def close_driver():
    """Close the Neo4j driver."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def read_query(query: str, **params) -> list[dict]:
    """Execute a read query and return results as list of dicts."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]


def write_query(query: str, **params) -> list[dict]:
    """Execute a write query (CREATE/SET/MERGE) and return results as list of dicts."""
    driver = get_driver()
    with driver.session() as session:
        result = session.execute_write(lambda tx: list(tx.run(query, **params)))
        return [record.data() for record in result]
