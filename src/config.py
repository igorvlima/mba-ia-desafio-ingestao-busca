"""Configuração central, independente do diretório de execução."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "openai": ("gpt-4.1-mini", "text-embedding-3-small"),
    "google": ("gemini-3.5-flash-lite", "gemini-embedding-001"),
    "openrouter": ("deepseek/deepseek-v4-flash", "openai/text-embedding-3-small"),
}

@dataclass(frozen=True)
class Settings:
    provider: str
    api_key: str = field(repr=False)
    llm_model: str
    embedding_model: str
    database_url: str = field(repr=False)
    collection_name: str
    pdf_path: Path

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env", override=False)
        keys = {p: os.getenv(f"{p.upper()}_API_KEY", "").strip() for p in DEFAULTS}
        key_file = os.getenv("OPENROUTER_API_KEY_FILE", "").strip()
        provider = os.getenv("AI_PROVIDER", "").strip().lower()
        if not provider:
            enabled = [p for p, key in keys.items() if key or (p == "openrouter" and key_file)]
            if len(enabled) != 1:
                raise ValueError("Preencha uma chave no .env ou selecione AI_PROVIDER (openai, google, openrouter).")
            provider = enabled[0]
        if provider not in DEFAULTS:
            raise ValueError("AI_PROVIDER deve ser openai, google ou openrouter.")
        if provider == "openrouter" and not keys[provider] and key_file:
            try:
                keys[provider] = (ROOT / Path(key_file).expanduser()).read_text().strip()
            except OSError:
                raise ValueError("Não foi possível ler OPENROUTER_API_KEY_FILE.") from None
        if not keys[provider]:
            raise ValueError(f"Configure {provider.upper()}_API_KEY no .env.")
        llm, embedding = DEFAULTS[provider]
        return cls(provider, keys[provider], os.getenv("LLM_MODEL", "").strip() or llm,
                   os.getenv("EMBEDDING_MODEL", "").strip() or embedding,
                   os.getenv("DATABASE_URL") or "postgresql+psycopg://postgres:postgres@localhost:5432/rag",
                   os.getenv("COLLECTION_NAME") or "pdf_documents",
                   ROOT / (os.getenv("PDF_PATH") or "document.pdf"))
