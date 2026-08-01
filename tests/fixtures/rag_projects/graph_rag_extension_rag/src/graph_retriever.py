from neo4j import GraphDatabase
from qdrant_client import QdrantClient


def entity_extraction(question: str) -> list[str]:
    tokens = question.replace("?", "").split()
    return [token for token in tokens if token[:1].isupper()]


class GraphRAGRetriever:
    def __init__(self) -> None:
        self.graph = GraphDatabase.driver("bolt://localhost:7687")
        self.vector_store = QdrantClient(url="http://localhost:6333")

    def graph_retriever(self, question: str) -> list[str]:
        entities = entity_extraction(question)
        query = """
        MATCH (entity:HealthEntity)-[:RELATED_TO*1..2]-(neighbor)
        WHERE entity.name IN $entities
        RETURN neighbor.summary AS summary
        LIMIT 5
        """
        with self.graph.session(database="systograph_graph") as session:
            records = session.run(query, entities=entities)
            return [record["summary"] for record in records]

    def hybrid_retrieve(self, question: str) -> list[str]:
        graph_context = self.graph_retriever(question)
        vector_hits = self.vector_store.search(
            collection_name="health_chunks",
            query_vector=[0.0, 0.1],
            limit=3,
        )
        vector_context = [hit.payload["text"] for hit in vector_hits]
        return graph_context + vector_context
