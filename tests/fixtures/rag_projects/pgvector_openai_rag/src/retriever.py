from openai import OpenAI
from pgvector.psycopg import register_vector
from psycopg import connect


def retrieve(question: str) -> list[str]:
    embedding = OpenAI().embeddings.create(
        model="text-embedding-3-small",
        input=question,
    )
    with connect(
        "postgresql://systograph:systograph_test@localhost:5432/systograph"
    ) as conn:
        register_vector(conn)
        rows = conn.execute(
            "select content from documents order by embedding <-> %s limit 3",
            (embedding.data[0].embedding,),
        ).fetchall()
    return [row[0] for row in rows]
