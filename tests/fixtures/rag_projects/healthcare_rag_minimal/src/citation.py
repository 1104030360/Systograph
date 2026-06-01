def cite_sources_required(
    answer: str,
    source_ids: list[str],
) -> dict[str, object]:
    if not source_ids:
        return {
            "answer": answer,
            "blocked": True,
            "reason": "medical_answer_requires_citation",
        }
    return {
        "answer": answer,
        "blocked": False,
        "source_id": source_ids,
    }
