"""Clean fake concept:ncert_* nodes from Neo4j and re-seed physics chapters."""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as session:
    # Count fake concept nodes
    result = session.run("""
        MATCH (c:Concept) WHERE c.id STARTS WITH 'concept:ncert_'
        RETURN count(c) AS count
    """)
    count = result.single()["count"]
    print(f"Found {count} fake concept:ncert_* nodes")

    # Delete them (and their relationships)
    if count > 0:
        session.run("""
            MATCH (c:Concept) WHERE c.id STARTS WITH 'concept:ncert_'
            DETACH DELETE c
        """)
        print(f"✅ Deleted {count} fake concept nodes")

    # Verify
    result = session.run("""
        MATCH (c:Concept) WHERE c.id STARTS WITH 'concept:ncert_'
        RETURN count(c) AS count
    """)
    remaining = result.single()["count"]
    print(f"Remaining: {remaining}")

driver.close()
