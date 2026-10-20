"""Extrai o PDF e substitui o documento da coleção atual de forma transacional."""
import hashlib
import sys
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete
from config import Settings
from store import vector_store


def load_chunks(path):
    if not path.is_file():
        raise ValueError("PDF não encontrado. Confira PDF_PATH no .env.")
    pages = PyPDFLoader(str(path)).load()
    pages = [page for page in pages if page.page_content.strip()]
    if not pages:
        raise ValueError("O PDF não contém texto extraível. PDFs digitalizados precisam de OCR antes da ingestão.")
    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150).split_documents(pages)
    for index, chunk in enumerate(chunks):
        chunk.metadata = {"source": path.name, "page": chunk.metadata.get("page", 0) + 1,
                          "chunk": index}
    return chunks


def ingest_pdf(settings=None):
    settings = settings or Settings.load()
    chunks = load_chunks(settings.pdf_path)
    store = vector_store(settings)
    # Todas as chamadas externas ocorrem antes da transação: falha não apaga o PDF anterior.
    vectors = store.embeddings.embed_documents([chunk.page_content for chunk in chunks])
    if len(vectors) != len(chunks) or not vectors or any(len(v) != len(vectors[0]) for v in vectors):
        raise ValueError("O provedor retornou embeddings inválidos.")
    # PGVector não oferece substituição atômica de toda a coleção pela API pública.
    # Usamos suas entidades SQLAlchemy, com a versão fixada em requirements.txt.
    with store.session_maker() as session, session.begin():
        collection = store.get_collection(session)
        if collection is None:
            raise ValueError("Coleção não encontrada.")
        session.execute(delete(store.EmbeddingStore).where(store.EmbeddingStore.collection_id == collection.uuid))
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            identity = f"{collection.uuid}:{index}:{chunk.page_content}"
            session.add(store.EmbeddingStore(id=hashlib.sha256(identity.encode()).hexdigest(),
                        collection_id=collection.uuid, embedding=vector,
                        document=chunk.page_content, cmetadata=chunk.metadata))
    return len(chunks)


def main():
    try:
        count = ingest_pdf()
        print(f"Ingestão concluída: {count} chunks salvos no PostgreSQL.")
        return 0
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
    except Exception as exc:
        # Mensagens de SDK/SQL podem conter credenciais, URLs ou conteúdo do PDF.
        print(f"Falha na ingestão ({type(exc).__name__}). Verifique banco, PDF, modelo, chave e saldo.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
