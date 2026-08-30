import logging
from langgraph.prebuilt import create_react_agent
from src.Agent.checkpointer import get_checkpointer
from src.config.settings import settings
from src.infrastructure.llm.factory import LLMFactory
from src.Agent.tools.retrieval_tool import retrieve_products
from src.Agent.tools.memory_tool import save_user_preference, get_user_preferences

logger = logging.getLogger(__name__)

_agent = None


def get_shopping_agent():
    """Create and return a LangGraph ReAct agent bound to the product retrieval and memory tools.
    
    Uses a singleton instance so the agent graph is built and compiled only ONCE.
    """
    global _agent
    if _agent is None:
        logger.info("Initializing and compiling Shopping Agent graph (singleton)...")
        # 1. Instantiate the LLM dynamically based on project settings (.env)
        llm = LLMFactory.create()

        # 2. Define the available tools
        tools = [
            retrieve_products,
            save_user_preference,
            get_user_preferences,
        ]

        # 3. System prompt instructions
        system_prompt = (
            "You are RayaShop's official shopping assistant. Your goal is to help users find products.\n"
            "You have access to these tools:\n"
            "- `retrieve_products`: Search the product database.\n"
            "- `save_user_preference`: Save user constraints (e.g. brand, max budget, color) or user details (e.g. name) for this thread.\n"
            "- `get_user_preferences`: Retrieve all previously saved preferences for this thread.\n\n"
            "Conversational Memory Guidelines:\n"
            "- Always query `get_user_preferences` at the beginning of a conversation or when a new search request is made to see if there are stored preferences.\n"
            "- If a user explicitly states a preference, brand constraint, or budget limit, "
            "explicitly save it using `save_user_preference` so it persists across conversation turns.\n"
            "- If you know the user's name, address them by name to show you remember them.\n"
            "- When searching for products, prioritize any stored constraints automatically.\n\n"
            "CRITICAL Response Guidelines:\n"
            "- NEVER include any URLs or links in your response. The product panel on the right side of the UI handles product display with images and links.\n"
            "- Keep your responses SHORT and conversational (2-3 sentences max). Do NOT list products with full details.\n"
            "- Just briefly mention what you found (e.g. 'لقيتلك 5 تكييفات من شارب، الأسعار تبدأ من 15,000 جنيه. شوف المنتجات على اليمين!').\n"
            "- If NO relevant products match the query, explicitly say that no matching products were found.\n"
            "- NEVER use markdown headers (###), bullet points, or long formatted lists in your chat response.\n"
            "- Answer in the same language the user uses. If they speak Arabic, respond in Arabic.\n"
            "- Be friendly, casual, and helpful like a real Egyptian shop assistant."
        )

        # 4. Get the shared Postgres checkpointer
        checkpointer = get_checkpointer()

        # 5. Create the LangGraph agent with checkpointer
        _agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
            checkpointer=checkpointer,
        )
        logger.info("Shopping Agent graph successfully compiled.")
        
    return _agent
