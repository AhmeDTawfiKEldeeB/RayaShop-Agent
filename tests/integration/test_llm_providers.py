import pytest

from src.infrastructure.llm.factory import LLMFactory

pytestmark = pytest.mark.integration


class TestGeminiProvider:
    def test_invoke(self):
        llm = LLMFactory.create("gemini")
        result = llm.invoke("Say hello in one word")
        print(f"\n[Gemini] {result.content}")
        assert result.content
        assert len(result.content) > 0

    def test_stream(self):
        llm = LLMFactory.create("gemini")
        chunks = list(llm.stream("Say hi"))
        text = "".join(c.content for c in chunks if c.content)
        print(f"\n[Gemini stream] {text}")
        assert len(chunks) > 0
        assert any(c.content for c in chunks)


class TestOpenRouterProvider:
    def test_invoke(self):
        llm = LLMFactory.create("openrouter")
        result = llm.invoke("who is messi")
        print(f"\n[OpenRouter] {result.content}")
        assert result.content
        assert len(result.content) > 0

    def test_stream(self):
        llm = LLMFactory.create("openrouter")
        chunks = list(llm.stream("Say hi"))
        text = "".join(c.content for c in chunks if c.content)
        print(f"\n[OpenRouter stream] {text}")
        assert len(chunks) > 0
        assert any(c.content for c in chunks)


class TestGroqProvider:
    def test_invoke(self):
        llm = LLMFactory.create("groq")
        result = llm.invoke("Say hello in one word")
        print(f"\n[Groq] {result.content}")
        assert result.content
        assert len(result.content) > 0

    def test_stream(self):
        llm = LLMFactory.create("groq")
        chunks = list(llm.stream("Say hi"))
        text = "".join(c.content for c in chunks if c.content)
        print(f"\n[Groq stream] {text}")
        assert len(chunks) > 0
        assert any(c.content for c in chunks)
