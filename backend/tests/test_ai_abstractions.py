import pytest

from app.ai.llm.provider import LLMProvider
from app.ai.rag.retriever import TourismRetriever
from app.ai.tools.registry import get_tool_definitions


def test_llm_provider_is_safe_and_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert LLMProvider().enabled is False


@pytest.mark.asyncio
async def test_disabled_llm_returns_deterministic_fallback():
    assert await LLMProvider().structured_json("system", "request") is None


def test_static_retriever_returns_grounded_documents():
    results = TourismRetriever().search("scuba adventure", destination="thailand")
    assert results
    assert all(item["destination"] == "thailand" for item in results)
    assert all("price" not in item["text"].casefold() for item in results)


def test_tool_registry_is_descriptive_and_database_agnostic():
    tools = get_tool_definitions()
    names = {tool["name"] for tool in tools}
    assert "make_trip_cheaper" in names
    assert "get_weather" in names
    assert all(tool["description"] for tool in tools)