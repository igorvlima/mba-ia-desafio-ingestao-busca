"""Clientes LangChain: uma chave por provedor para chat e embeddings."""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


def embeddings(settings):
    if settings.provider == "google":
        return GoogleGenerativeAIEmbeddings(model=settings.embedding_model, api_key=settings.api_key)
    options = dict(model=settings.embedding_model, api_key=settings.api_key,
                   request_timeout=60, max_retries=2)
    if settings.provider == "openrouter":
        # OpenRouter aceita texto, não os arrays de tokens produzidos pelo tokenizer OpenAI.
        options.update(base_url="https://openrouter.ai/api/v1", check_embedding_ctx_length=False)
    return OpenAIEmbeddings(**options)


def chat_model(settings):
    if settings.provider == "google":
        return ChatGoogleGenerativeAI(model=settings.llm_model, api_key=settings.api_key,
                                     temperature=0, max_tokens=1024, timeout=60, max_retries=2)
    options = dict(model=settings.llm_model, api_key=settings.api_key,
                   temperature=0, max_tokens=1024, timeout=60, max_retries=2)
    if settings.provider == "openrouter":
        options.update(base_url="https://openrouter.ai/api/v1",
                       extra_body={"reasoning": {"enabled": False}})
    return ChatOpenAI(**options)
