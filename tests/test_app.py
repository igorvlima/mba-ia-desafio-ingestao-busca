import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import Settings, ROOT, DEFAULTS
from ingest import load_chunks
from search import SearchService, FALLBACK
from store import collection_name
from providers import chat_model, embeddings
from langchain_core.documents import Document
from langchain_core.messages import AIMessage


class AppTests(unittest.TestCase):
    def test_provider_detection(self):
        for provider in DEFAULTS:
            with self.subTest(provider=provider), patch.dict(os.environ, {f'{provider.upper()}_API_KEY': 'test'}, clear=True), patch('config.load_dotenv'):
                settings = Settings.load()
                self.assertEqual(settings.provider, provider)
                self.assertNotIn('api_key=', repr(settings))
                self.assertTrue(chat_model(settings))
                self.assertTrue(embeddings(settings))

    def test_ambiguous_provider(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test', 'GOOGLE_API_KEY': 'test'}, clear=True), patch('config.load_dotenv'):
            with self.assertRaises(ValueError): Settings.load()

    def test_changed_embedding_uses_separate_collection(self):
        settings = Settings('openai', 'test', 'llm', 'embedding', 'db', 'pdf', ROOT/'document.pdf')
        self.assertNotEqual(collection_name(settings), collection_name(replace(settings, embedding_model='other')))
        self.assertEqual(collection_name(settings), collection_name(replace(settings, llm_model='other')))

    def test_actual_pdf_chunks(self):
        chunks = load_chunks(ROOT/'document.pdf')
        self.assertGreater(len(chunks), 10)
        self.assertTrue(all(0 < len(c.page_content) <= 1000 for c in chunks))
        self.assertTrue(all(c.metadata['page'] >= 1 for c in chunks))
        self.assertIn('85.675.568,77', chunks[0].page_content)

    def test_missing_pdf(self):
        with self.assertRaises(ValueError): load_chunks(ROOT/'missing.pdf')

    def test_empty_pdf(self):
        with patch('ingest.PyPDFLoader') as loader:
            loader.return_value.load.return_value = [Document(page_content='  ')]
            with self.assertRaisesRegex(ValueError, 'OCR'): load_chunks(ROOT/'document.pdf')

    def test_retrieval_and_prompt(self):
        store, llm = MagicMock(), MagicMock()
        store.similarity_search_with_score.return_value = [(Document(page_content='Receita: 10 milhões.', metadata={'page': 2}), 0.1)]
        llm.invoke.return_value = AIMessage(content='A receita foi de 10 milhões.')
        service = SearchService(store=store, llm=llm)
        self.assertEqual(service.answer('Qual a receita?'), 'A receita foi de 10 milhões.')
        store.similarity_search_with_score.assert_called_once_with('Qual a receita?', k=10)
        prompt = llm.invoke.call_args.args[0][1].content
        self.assertIn('Receita: 10 milhões.', prompt)
        self.assertIn('Qual a receita?', prompt)
        self.assertIn(FALLBACK, prompt)

    def test_no_context_does_not_call_llm(self):
        store, llm = MagicMock(), MagicMock()
        store.similarity_search_with_score.return_value = []
        self.assertEqual(SearchService(store=store, llm=llm).answer('Capital?'), FALLBACK)
        llm.invoke.assert_not_called()

    def test_blank_question_does_not_retrieve(self):
        store, llm = MagicMock(), MagicMock()
        self.assertEqual(SearchService(store=store, llm=llm).answer('  '), FALLBACK)
        store.similarity_search_with_score.assert_not_called()


if __name__ == '__main__':
    unittest.main()
