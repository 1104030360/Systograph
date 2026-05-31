def custom_query_router(question: str) -> str:
    if "urgent" in question.lower():
        return "clinician_handoff"
    return "health_docs"


def route_query(question: str) -> dict[str, str]:
    route = custom_query_router(question)
    return {"route": route, "status": "needs_confirmation"}
