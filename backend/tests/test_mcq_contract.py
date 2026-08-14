from __future__ import annotations

from app.services.mcq import mcq_validation_errors


def test_mcq_validation_errors_identify_fields_without_content() -> None:
    errors = mcq_validation_errors(
        {
            "question": "Question content must not appear in telemetry",
            "options": {"A": "", "B": "Two", "C": "Three", "D": "Four"},
            "correct_answer": "first",
            "explanation": "",
            "subsection_id": "subsection:target",
            "key_terms": [],
        },
        require_subsection=True,
        require_key_terms=True,
    )

    assert errors == [
        "missing_option_A",
        "invalid_correct_answer",
        "missing_explanation",
    ]
    assert "Question content" not in " ".join(errors)
