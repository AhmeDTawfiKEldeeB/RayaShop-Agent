from langchain_openai import ChatOpenAI

from src.config.settings import settings


def OpenRouterProvider(**kwargs) -> ChatOpenAI:
    s = settings.llm.openrouter
    return ChatOpenAI(
        model=kwargs.pop("model", s.model),
        api_key=kwargs.pop("api_key", s.api_key),
        base_url=kwargs.pop("base_url", s.base_url),
        **kwargs,
    )
