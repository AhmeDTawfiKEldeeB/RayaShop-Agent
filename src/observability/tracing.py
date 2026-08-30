"""Observability and LangSmith tracing module for RayaShop Agent.

Provides @traceable functions for data retrieval, response generation, and complete RAG pipeline tracing.
"""

import os
import logging
from typing import Any, List, Dict, Optional
from dotenv import load_dotenv
from langsmith import traceable

logger = logging.getLogger(__name__)


def setup_langsmith():
    """Ensure LangSmith tracing environment variables are properly exported to os.environ from .env."""
    load_dotenv()
    tracing = os.getenv("LANGSMITH_TRACING", "true")
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    api_key = os.getenv("LANGSMITH_API_KEY")
    project = os.getenv("LANGSMITH_PROJECT", "RayaShopT").strip('"')

    os.environ["LANGSMITH_TRACING"] = tracing
    os.environ["LANGSMITH_ENDPOINT"] = endpoint
    os.environ["LANGSMITH_PROJECT"] = project

    if api_key:
        os.environ["LANGSMITH_API_KEY"] = api_key
        logger.info(
            "LangSmith Tracing initialized: Project='%s', Endpoint='%s'",
            project,
            endpoint,
        )
    else:
        logger.warning(
            "LANGSMITH_API_KEY is missing from environment/dotenv. Tracing may be disabled or unauthenticated."
        )


# Automatically setup on module import
setup_langsmith()


@traceable(name="retrieve_products_data", run_type="retriever")
def trace_retrieval(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Traced retrieval function using @traceable (run_type='retriever').
    
    Executes hybrid search against the active vector database and returns raw product items.
    """
    from src.Agent.tools.retrieval_tool import search_products_raw
    return search_products_raw(query=query, limit=limit)


@traceable(name="generate_shopping_response", run_type="llm")
def trace_generation(user_message: str, context: Optional[str] = None) -> str:
    """Traced generation function using @traceable (run_type='llm').
    
    Invokes the configured LLM with prompt and optional retrieval context.
    """
    from src.infrastructure.llm.factory import LLMFactory
    llm = LLMFactory.create()
    
    prompt = f"User Query: {user_message}\n"
    if context:
        prompt += f"\nRetrieved Products Context:\n{context}\n"
    prompt += "\nProvide a helpful, friendly, and concise response:"

    response = llm.invoke(prompt)
    if hasattr(response, "content"):
        return response.content
    return str(response)


@traceable(name="rag_shopping_pipeline", run_type="chain")
def trace_rag_pipeline(user_query: str, limit: int = 5) -> Dict[str, Any]:
    """Traced end-to-end RAG pipeline using @traceable (run_type='chain').
    
    Combines retrieval and generation into a single traced pipeline span in LangSmith.
    """
    # 1. Traced Retrieval
    products = trace_retrieval(query=user_query, limit=limit)
    
    # 2. Prepare Context
    context_str = "\n".join([
        f"- {p.get('name')} (Price: {p.get('price')} EGP, Brand: {p.get('brand')})"
        for p in products
    ]) if products else "No products found."
    
    # 3. Traced Generation
    ai_response = trace_generation(user_message=user_query, context=context_str)
    
    return {
        "user_query": user_query,
        "retrieved_products": products,
        "response": ai_response
    }
