"""Fix remaining 29 orphan Section nodes in Neo4j."""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

driver = GraphDatabase.driver(
    os.environ['NEO4J_URI'],
    auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD'])
)


def redirect_requires(session, old_id, new_id):
    """Move REQUIRES relationships from old section to new section, then delete old."""
    q_move = (
        "MATCH (source)-[r:REQUIRES]->(old:Section {id: $old_id}) "
        "MATCH (new_sec:Section {id: $new_id}) "
        "CREATE (source)-[:REQUIRES]->(new_sec) "
        "DELETE r "
        "RETURN count(*) as moved"
    )
    result = session.run(q_move, old_id=old_id, new_id=new_id)
    moved = result.single()['moved']

    q_del = "MATCH (s:Section {id: $old_id}) DETACH DELETE s"
    session.run(q_del, old_id=old_id)
    return moved


with driver.session() as session:
    # Get all real sections for validation
    result = session.run(
        'MATCH ()-[:CONTAINS]->(s:Section) RETURN s.id as id'
    )
    real_sections = set(r['id'] for r in result)

    # Manual fix mappings
    fixes = {
        # Chapter-level refs → first section
        'ncert:biology:11:2':  'ncert:biology:11:2:2',
        'ncert:biology:11:3':  'ncert:biology:11:3:3',
        'ncert:biology:11:5':  'ncert:biology:11:5:5',
        'ncert:biology:11:6':  'ncert:biology:11:6:6.1',
        'ncert:biology:11:7':  'ncert:biology:11:7:7.1',
        'ncert:biology:11:8':  'ncert:biology:11:8:8.1',
        'ncert:biology:12:2':  'ncert:biology:12:2:2.1',
        'ncert:biology:12:4':  'ncert:biology:12:4:4',
        'ncert:biology:12:6':  'ncert:biology:12:6:6.1',
        'ncert:biology:12:7':  'ncert:biology:12:7:7',
        'ncert:biology:12:9':  'ncert:biology:12:9:9',
        'ncert:chemistry:11:2': 'ncert:chemistry:11:2:2',
        'ncert:chemistry:12:6': 'ncert:chemistry:12:6:6',
        'ncert:chemistry:12:7': 'ncert:chemistry:12:7:7',

        # Subsection refs → parent or closest section
        'ncert:biology:11:19:19.2.2': 'ncert:biology:11:19:19.2',
        'ncert:biology:11:6:2.1':     'ncert:biology:11:6:6.2',
        'ncert:biology:11:6:3':       'ncert:biology:11:6:6.2',
        'ncert:biology:11:16:0':      'ncert:biology:11:16:16',

        # Chemistry subsection refs
        'ncert:chemistry:11:6:6.11.1': 'ncert:chemistry:11:6:6.11',
        'ncert:chemistry:11:6:6.6.2':  'ncert:chemistry:11:6:6.6',
        'ncert:chemistry:12:10:10.1.2': 'ncert:chemistry:12:10:10.1',
        'ncert:chemistry:12:1:1.3.2':   'ncert:chemistry:12:1:1.3',
        'ncert:chemistry:12:1:1.4.3':   'ncert:chemistry:12:1:1.4',
        'ncert:chemistry:12:6:6.4.2':   'ncert:chemistry:12:6:6.4',
        'ncert:chemistry:12:6:7.1':     'ncert:chemistry:12:6:6.7',
        'ncert:chemistry:12:7:7.4':     'ncert:chemistry:12:7:7.4.1',
        'ncert:chemistry:12:8:intro':   'ncert:chemistry:12:8:8',
    }

    # Verify targets exist
    print('Verifying fix targets...')
    verified = {}
    for old, new in fixes.items():
        if new in real_sections:
            verified[old] = new
        else:
            print(f'  ⚠️  Target not found: {new} (for {old}) — will delete orphan')

    # Apply verified fixes
    print(f'\nApplying {len(verified)} redirects...')
    for old_id, new_id in verified.items():
        moved = redirect_requires(session, old_id, new_id)
        print(f'  ✅ {old_id} → {new_id} ({moved} rels)')

    # Delete unverified orphans (target doesn't exist)
    unverified = set(fixes.keys()) - set(verified.keys())
    for old_id in unverified:
        session.run("MATCH (s:Section {id: $old_id}) DETACH DELETE s", old_id=old_id)
        print(f'  🗑️  Deleted {old_id} (target not found)')

    # Delete the 2 chemistry chapters that don't exist (ch1, ch9)
    for missing in ['ncert:chemistry:11:1', 'ncert:chemistry:11:9']:
        session.run("MATCH (s:Section {id: $id}) DETACH DELETE s", id=missing)
        print(f'  🗑️  Deleted {missing} (chapter not in DB)')

    # Final check
    result = session.run(
        'MATCH (s:Section) WHERE NOT ()-[:CONTAINS]->(s) '
        'RETURN count(s) as c'
    )
    remaining = result.single()['c']
    print(f'\n=== Remaining orphan sections: {remaining} ===')

    if remaining > 0:
        result = session.run(
            'MATCH (s:Section) WHERE NOT ()-[:CONTAINS]->(s) '
            'RETURN s.id as id ORDER BY s.id'
        )
        for r in result:
            print(f'  {r["id"]}')

driver.close()
print('\n✅ Done')
