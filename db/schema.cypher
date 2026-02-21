// =============================================================================
// AI Tutor — Neo4j Schema: Constraints & Indexes
// Run this once against a fresh Neo4j database to set up the schema.
// =============================================================================

// ---------------------
// Uniqueness Constraints
// ---------------------

CREATE CONSTRAINT curriculum_id IF NOT EXISTS FOR (c:Curriculum) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT subject_id IF NOT EXISTS FOR (s:Subject) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT textbook_id IF NOT EXISTS FOR (t:Textbook) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (c:Chapter) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT section_id IF NOT EXISTS FOR (s:Section) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT subsection_id IF NOT EXISTS FOR (ss:Subsection) REQUIRE ss.id IS UNIQUE;
CREATE CONSTRAINT worked_example_id IF NOT EXISTS FOR (we:WorkedExample) REQUIRE we.id IS UNIQUE;
CREATE CONSTRAINT diagram_id IF NOT EXISTS FOR (d:Diagram) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT table_id IF NOT EXISTS FOR (tbl:Table) REQUIRE tbl.id IS UNIQUE;
CREATE CONSTRAINT exercise_set_id IF NOT EXISTS FOR (es:ExerciseSet) REQUIRE es.id IS UNIQUE;
CREATE CONSTRAINT exercise_id IF NOT EXISTS FOR (e:Exercise) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT student_id IF NOT EXISTS FOR (s:Student) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT insight_id IF NOT EXISTS FOR (i:Insight) REQUIRE i.id IS UNIQUE;

// ---------------------
// Performance Indexes
// ---------------------

CREATE INDEX insight_active IF NOT EXISTS FOR (i:Insight) ON (i.is_active);
CREATE INDEX insight_type IF NOT EXISTS FOR (i:Insight) ON (i.type);
CREATE INDEX insight_category IF NOT EXISTS FOR (i:Insight) ON (i.category);
CREATE INDEX subsection_order IF NOT EXISTS FOR (ss:Subsection) ON (ss.order);
CREATE INDEX chapter_number IF NOT EXISTS FOR (c:Chapter) ON (c.number);
CREATE INDEX exercise_number IF NOT EXISTS FOR (e:Exercise) ON (e.number);
