from citation import cite_sources_required
from fastapi import FastAPI
from guardrails import apply_medical_guardrails

app = FastAPI()


@app.post("/medical-query")
def medical_query(payload: dict[str, str]) -> dict[str, object]:
    guarded = apply_medical_guardrails(
        payload["question"],
        "Use saline rinse as described in the cited synthetic guideline.",
    )
    cited = cite_sources_required(
        guarded["answer"],
        ["guideline:synthetic-primary-care-triage"],
    )
    return {"medical_domain": "healthcare", "guarded": guarded, "cited": cited}
