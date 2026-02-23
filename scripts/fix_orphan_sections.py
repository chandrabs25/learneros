"""Fix orphan Section nodes in Neo4j by redirecting REQUIRES relationships."""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

driver = GraphDatabase.driver(
    os.environ['NEO4J_URI'],
    auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD'])
)

with driver.session() as session:
    # Get all orphan sections and all real sections
    result = session.run(
        'MATCH (s:Section) WHERE NOT ()-[:CONTAINS]->(s) RETURN s.id as id'
    )
    orphans = [r['id'] for r in result]

    result2 = session.run('MATCH ()-[:CONTAINS]->(s:Section) RETURN s.id as id')
    real_sections = set(r['id'] for r in result2)

    # Build redirect map for fixable orphans
    redirects = {}
    for oid in orphans:
        if oid.startswith('ncert:'):
            parts = oid.split(':')
            if len(parts) >= 5:
                ch_prefix = ':'.join(parts[:4])
                sec_num = parts[4]
                ch_num = parts[3]
                candidate = f'{ch_prefix}:{ch_num}.{sec_num}'
                if candidate in real_sections and candidate != oid:
                    redirects[oid] = candidate

    print(f'Redirecting {len(redirects)} REQUIRES relationships...')

    # Redirect REQUIRES and delete orphan
    for old_id, new_id in redirects.items():
        result = session.run(
            'MATCH (source)-[r:REQUIRES]->(old:Section {id: $old_id}) '
            'MATCH (new_sec:Section {id: $new_id}) '
            'CREATE (source)-[:REQUIRES]->(new_sec) '
            'DELETE r '
            'RETURN count(*) as moved',
            old_id=old_id, new_id=new_id
        )
        moved = result.single()['moved']
        session.run(
            'MATCH (s:Section {id: $old_id}) DETACH DELETE s',
            old_id=old_id
        )
        if moved > 0:
            print(f'  ✅ {old_id} → {new_id} ({moved} rels)')
        else:
            print(f'  🗑️  {old_id} (no rels, deleted)')

    # Delete non-standard ID orphans (no ncert: prefix)
    result = session.run(
        'MATCH (s:Section) WHERE NOT ()-[:CONTAINS]->(s) '
        'AND NOT s.id STARTS WITH "ncert:" '
        'DETACH DELETE s '
        'RETURN count(*) as deleted'
    )
    junk_deleted = result.single()['deleted']
    print(f'\nDeleted {junk_deleted} non-standard ID orphans')

    # Check remaining
    result = session.run(
        'MATCH (s:Section) WHERE NOT ()-[:CONTAINS]->(s) RETURN count(s) as c'
    )
    remaining = result.single()['c']
    print(f'\nRemaining orphan sections: {remaining}')

    if remaining > 0:
        result = session.run(
            'MATCH (s:Section) WHERE NOT ()-[:CONTAINS]->(s) '
            'OPTIONAL MATCH (source)-[:REQUIRES]->(s) '
            'RETURN s.id as id, collect(source.id) as required_by '
            'ORDER BY s.id'
        )
        print('Remaining orphans (cross-chapter refs — kept as-is):')
        for r in result:
            print(f'  {r["id"]:55s} required by {r["required_by"][:2]}')

driver.close()
print('\n✅ Cleanup complete')
