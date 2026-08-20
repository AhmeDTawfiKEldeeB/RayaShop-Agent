from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.settings import settings


def GeminiProvider(**kwargs) -> ChatGoogleGenerativeAI:
    s = settings.llm.gemini
    return ChatGoogleGenerativeAI(
        model=kwargs.pop("model", s.model),
        google_api_key=kwargs.pop("api_key", s.api_key),
        **kwargs,
    )
