from sentence_transformers import CrossEncoder


def rerank(question: str, documents: list[str]) -> list[str]:
    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    scores = model.predict([(question, document) for document in documents])
    ranked = sorted(zip(scores, documents, strict=True), reverse=True)
    return [document for _score, document in ranked]
