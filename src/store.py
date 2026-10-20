"""Uma coleção por espaço de embeddings; sem dimensão fixa compartilhada entre coleções."""
import hashlib
from langchain_postgres import PGVector
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from providers import embeddings


def collection_name(settings):
    identity = f"{settings.provider}:{settings.embedding_model}"
    digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
    return f"{settings.collection_name}_{digest}"


def vector_store(settings):
    # PGVector compartilha a tabela entre coleções. Sem embedding_length, a coluna vector
    # suporta diferentes dimensões; coleções distintas impedem misturar espaços vetoriais.
    engine = create_engine(settings.database_url, poolclass=NullPool,
                           connect_args={"connect_timeout": 10})
    return PGVector(embeddings=embeddings(settings), connection=engine,
                    collection_name=collection_name(settings), use_jsonb=True,
                    collection_metadata={"provider": settings.provider,
                                         "embedding_model": settings.embedding_model})
