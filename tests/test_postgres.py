"""Opt-in: PostgreSQL real com embeddings determinísticos, sem chamadas pagas."""
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import Settings, ROOT
from ingest import ingest_pdf
from store import vector_store
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.documents import Document
from sqlalchemy import select, func

@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Defina TEST_DATABASE_URL para testar PostgreSQL real.')
class PostgresTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings('openai', 'unused', 'unused', 'fake-16', os.environ['TEST_DATABASE_URL'],
                                 'db_test_' + uuid.uuid4().hex, ROOT/'document.pdf')
        self.patch = patch('store.embeddings', return_value=DeterministicFakeEmbedding(size=16))
        self.patch.start()
        self.store = vector_store(self.settings)

    def tearDown(self):
        self.store.delete_collection()
        self.patch.stop()

    def count(self):
        with self.store.session_maker() as session:
            collection = self.store.get_collection(session)
            return session.scalar(select(func.count()).select_from(self.store.EmbeddingStore).where(
                self.store.EmbeddingStore.collection_id == collection.uuid))

    def test_pdf_persistence_reingestion_and_search(self):
        count = ingest_pdf(self.settings)
        self.assertGreater(count, 10)
        self.assertEqual(self.count(), count)
        self.assertEqual(ingest_pdf(self.settings), count)
        self.assertEqual(self.count(), count)
        with self.store.session_maker() as session:
            collection = self.store.get_collection(session)
            text = session.scalar(select(self.store.EmbeddingStore.document).where(
                self.store.EmbeddingStore.collection_id == collection.uuid).limit(1))
        results = self.store.similarity_search_with_score(text, k=10)
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0][0].page_content, text)
        self.assertLess(abs(results[0][1]), 0.00001)

    def test_replace_and_preserve_on_embedding_failure(self):
        with patch('ingest.load_chunks', return_value=[Document(page_content='Original')]):
            ingest_pdf(self.settings)
        with patch('store.embeddings') as factory:
            factory.return_value.embed_documents.side_effect = RuntimeError('simulated API failure')
            with self.assertRaises(RuntimeError): ingest_pdf(self.settings)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.store.similarity_search('Original', k=1)[0].page_content, 'Original')
        with patch('ingest.load_chunks', return_value=[Document(page_content='Substituído')]):
            ingest_pdf(self.settings)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.store.similarity_search('Substituído', k=1)[0].page_content, 'Substituído')

    def test_database_failure_rolls_back_replacement(self):
        with patch('ingest.load_chunks', return_value=[Document(page_content='Preservado')]):
            ingest_pdf(self.settings)
        broken = Document(page_content='Novo', metadata={'invalid_json': object()})
        with patch('ingest.load_chunks', return_value=[broken]):
            with self.assertRaises(TypeError): ingest_pdf(self.settings)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.store.similarity_search('Preservado', k=1)[0].page_content, 'Preservado')

    def test_different_dimensions_in_isolated_collections(self):
        ingest_pdf(self.settings)
        other = replace(self.settings, embedding_model='fake-8')
        with patch('store.embeddings', return_value=DeterministicFakeEmbedding(size=8)):
            second = vector_store(other)
            try:
                with patch('ingest.load_chunks', return_value=[Document(page_content='Outra coleção')]):
                    ingest_pdf(other)
                self.assertEqual(second.similarity_search('Outra coleção', k=10)[0].page_content, 'Outra coleção')
                self.assertEqual(len(self.store.similarity_search('Original', k=10)), 10)
            finally:
                second.delete_collection()

if __name__ == '__main__':
    unittest.main()
