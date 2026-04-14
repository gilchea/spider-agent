###helpers/agent.py
"""
Agent module for NL2SQL system.

This module is responsible for:
- Initializing LLM models
- Creating NL2SQL agents with tool integrations
- Providing utility functions for dataset filtering

The agent leverages LangChain's tool-calling capabilities to
convert natural language queries into SQL queries and execute them.
"""
# import os
# import httpx
# from typing import Any, Callable, Dict, List, Optional, Union

# from langchain_groq import ChatGroq
from langchain.agents import create_agent
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

# from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config, wrap_model_call, ModelRequest, ModelResponse
from src.helpers.tools import load_skill
# from langchain.agents.middleware import hook_config

# from src.config import Config
from src.helpers.tools import create_db_tools
from src.helpers.middleware import Middleware1, Middleware2
from src.handlers.logging_config import logger
from src.helpers.SYSTEM_PROMPT import SYSTEM_PROMPT
from src.helpers.llm import LLMFactory

# -------------------------------------------------------------------
# AGENT FACTORY
# -------------------------------------------------------------------

def create_nl2sql_agent(db_id: str):
    """
    Create an NL2SQL agent for a specific database.

    This function initializes the database manager, loads tools,
    configures the language model, and builds a LangChain agent.

    Args:
        db_id (str): Identifier of the target SQLite database.

    Returns:
        Agent: A configured LangChain agent instance.

    Raises:
        RuntimeError: If agent creation fails.
    """
    try:
        logger.info("Creating NL2SQL agent for db_id: %s", db_id)

        # -------------------------------------------------------------------
        # MODEL CONFIGURATION
        # -------------------------------------------------------------------

        llm = LLMFactory()
        gpt_model = llm.get_gpt_model()
        # groq_model = llm.get_groq_model()
        # gemini_model = llm.get_gemini_model() 

        agent = create_agent(
            model = gpt_model,
            # tools=create_db_tools(db_id),
            tools = create_db_tools(db_id)+[load_skill],
            system_prompt=SYSTEM_PROMPT,
            checkpointer=InMemorySaver(),
            middleware = [
                Middleware2(),
                Middleware1()
            ]
        )

        logger.info("NL2SQL agent created successfully for db_id: %s", db_id)

        return agent

    except Exception as e:
        logger.error(
            "Failed to create NL2SQL agent for db_id: %s",
            db_id,
            exc_info=True
        )
        raise RuntimeError(f"Agent creation failed: {str(e)}") from e
    