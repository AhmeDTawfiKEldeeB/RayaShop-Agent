"""Unit tests for the explicit LangGraph workflow."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.Agent.graph import _route_after_guardrail

# --------------------------------------------------------------------------- routing


class TestRouteAfterGuardrail:
    def test_blocked_routes_to_end(self):
        assert _route_after_guardrail({"blocked": True}) == "blocked"

    def test_unblocked_routes_to_continue(self):
        assert _route_after_guardrail({"blocked": False}) == "continue"

    def test_no_blocked_key_routes_to_continue(self):
        assert _route_after_guardrail({}) == "continue"


# --------------------------------------------------------------------------- guardrail node


class TestGuardrailNode:
    def test_greeting_blocks(self):
        from src.Agent.nodes.guardrail import guardrail_node

        state = {"messages": [HumanMessage(content="hello")]}
        result = guardrail_node(state)
        assert result["blocked"] is True
        msgs = result["messages"]
        assert len(msgs) == 1
        assert isinstance(msgs[0], AIMessage)
        assert "RayaShop" in msgs[0].content or "raya" in msgs[0].content.lower()

    def test_product_query_passes(self):
        from src.Agent.nodes.guardrail import guardrail_node

        state = {"messages": [HumanMessage(content="I want a Samsung phone")]}
        result = guardrail_node(state)
        assert result == {"blocked": False}

    def test_empty_messages_passes(self):
        from src.Agent.nodes.guardrail import guardrail_node

        result = guardrail_node({"messages": []})
        assert result == {"blocked": False}


# --------------------------------------------------------------------------- respond node


class TestRespondNode:
    def test_format_products_with_results(self):
        from src.Agent.nodes.respond import _format_products

        products = [
            {"name": "iPhone 15", "price": 50000, "old_price": 55000, "stock_status": "In Stock"},
            {"name": "Galaxy S24", "price": 35000, "stock_status": "Out of Stock"},
        ]
        result = _format_products(products)
        assert "iPhone 15" in result
        assert "50,000 EGP" in result
        assert "was 55,000" in result
        assert "Galaxy S24" in result
        assert "35,000 EGP" in result

    def test_format_products_empty(self):
        from src.Agent.nodes.respond import _format_products

        assert _format_products([]) == "No products found."

    def test_respond_node_includes_summary_in_context(self):
        from src.Agent.nodes.respond import respond_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Here are some phones")

        state = {
            "messages": [HumanMessage(content="phones")],
            "summary": "User budget is 20k EGP, prefers Samsung.",
            "search_results": [],
        }

        with patch("src.Agent.nodes.respond.LLMFactory") as mock_factory:
            mock_factory.create.return_value = mock_llm
            respond_node(state)

        call_args = mock_llm.invoke.call_args[0][0]
        assert isinstance(call_args[0], SystemMessage)
        assert isinstance(call_args[1], SystemMessage)
        assert "20k EGP" in call_args[1].content
        assert isinstance(call_args[2], HumanMessage)

    def test_respond_node_no_summary_includes_all_messages(self):
        from src.Agent.nodes.respond import respond_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="response")

        state = {
            "messages": [HumanMessage(content="hi"), HumanMessage(content="phones")],
            "summary": None,
            "search_results": [],
        }

        with patch("src.Agent.nodes.respond.LLMFactory") as mock_factory:
            mock_factory.create.return_value = mock_llm
            respond_node(state)

        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args) == 3  # system + msg1 + msg2


# --------------------------------------------------------------------------- full graph integration


class TestGraphFlow:
    def test_greeting_terminates_early(self):
        """Greeting should be blocked by guardrail — no retrieval, no LLM."""
        from src.Agent.graph import build_graph

        graph = build_graph()

        with (
            patch("src.Agent.nodes.retrieval.search_products_raw") as mock_search,
            patch("src.Agent.nodes.respond.LLMFactory") as mock_llm_factory,
        ):
            result = graph.invoke(
                {"messages": [("human", "hello")]},
                config={"configurable": {"thread_id": "test-greeting"}},
            )

            mock_search.assert_not_called()
            mock_llm_factory.create.assert_not_called()
            assert result.get("blocked") is True

    def test_product_query_reaches_retrieval_and_respond(self):
        """Product query should flow through memory → retrieve → respond."""
        from src.Agent.graph import build_graph

        graph = build_graph()

        fake_products = [{"name": "iPhone 15", "price": 50000, "stock_status": "In Stock"}]

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="iPhone 15 is available for 50,000 EGP")

        with (
            patch("src.Agent.nodes.retrieval.search_products_raw", return_value=fake_products) as mock_search,
            patch("src.Agent.nodes.respond.LLMFactory") as mock_factory,
        ):
            mock_factory.create.return_value = mock_llm
            result = graph.invoke(
                {"messages": [("human", "I want a Samsung phone")]},
                config={"configurable": {"thread_id": "test-product"}},
            )

            mock_search.assert_called_once()
            mock_llm.invoke.assert_called_once()
            assert result["messages"][-1].content == "iPhone 15 is available for 50,000 EGP"

    def test_empty_search_still_responds(self):
        """Empty search results should still reach the respond node."""
        from src.Agent.graph import build_graph

        graph = build_graph()

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="No matching products found. What brand are you looking for?")

        with (
            patch("src.Agent.nodes.retrieval.search_products_raw", return_value=[]),
            patch("src.Agent.nodes.respond.LLMFactory") as mock_factory,
        ):
            mock_factory.create.return_value = mock_llm
            graph.invoke(
                {"messages": [("human", "quantum flux capacitor")]},
                config={"configurable": {"thread_id": "test-empty"}},
            )

            mock_llm.invoke.assert_called_once()
            call_args = mock_llm.invoke.call_args[0][0]
            system_content = call_args[0].content
            assert "No products found" in system_content

    def test_no_react_remains(self):
        """Verify no create_react_agent import or usage exists in graph."""
        import inspect

        import src.Agent.graph as graph_mod

        source = inspect.getsource(graph_mod)
        assert "create_react_agent" not in source
        assert "ReAct" not in source
