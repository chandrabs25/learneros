"""Schema migration coverage for durable learner-evidence jobs."""

from scripts.setup_constraints import CONSTRAINTS, INDEXES


def test_learner_evidence_job_schema_supports_claim_and_recovery_queries() -> None:
    assert (
        "LearnerEvidenceJob",
        "id",
        "learner_evidence_job_id_unique",
        "UNIQUE",
    ) in CONSTRAINTS
    indexed_properties = {
        prop for label, prop, _name in INDEXES if label == "LearnerEvidenceJob"
    }
    assert indexed_properties == {"status", "lease_expires_at", "created_at"}
