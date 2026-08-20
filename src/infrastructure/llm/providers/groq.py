from langchain_groq import ChatGroq

from src.config.settings import settings


def GroqProvider(**kwargs) -> ChatGroq:
    s = settings.llm.groq
    return ChatGroq(
        model=kwargs.pop("model", s.model),
        api_key=kwargs.pop("api_key", s.api_key),
        **kwargs,
    )
