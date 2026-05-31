EMERGENCY_TERMS = {
    "chest pain",
    "trouble breathing",
    "fainting",
    "stroke",
    "severe allergic reaction",
}


def emergency_escalation(question: str) -> bool:
    normalized = question.lower()
    return any(term in normalized for term in EMERGENCY_TERMS)


def no_diagnosis(answer: str) -> str:
    return (
        f"{answer}\n\n"
        "This synthetic assistant does not provide a diagnosis and does not "
        "replace a licensed clinician."
    )


def apply_medical_guardrails(
    question: str,
    draft_answer: str,
) -> dict[str, str]:
    if emergency_escalation(question):
        return {
            "status": "escalate",
            "answer": "Seek urgent medical evaluation for these symptoms.",
        }
    return {
        "status": "ok",
        "answer": no_diagnosis(draft_answer),
    }
