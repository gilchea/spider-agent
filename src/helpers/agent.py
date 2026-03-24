# from langchain_groq import ChatGroq
# from src.config import Config
# import os
# from langchain.agents import create_agent
# import json
# from src.helpers.tools import create_db_tools
# from src.handlers.database import DatabaseManager
# # from langchain_core.prompts import ChatPromptTemplate
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.agents.middleware.model_fallback import ModelFallbackMiddleware
# # import google.generativeai as genai
# import ssl
# from src.helpers.SYSTEM_PROMPT import SYSTEM_PROMPT

# cert_path = str(Config.CERT)

# # ✅ QUAN TRỌNG
# os.environ["SSL_CERT_FILE"] = cert_path
# os.environ["REQUESTS_CA_BUNDLE"] = cert_path

# print("Using cert:", cert_path)

# ssl._create_default_https_context = ssl.create_default_context(
#     cafile=cert_path
# )

# def get_local_instances(file_path: str):
#     """Lọc các item có instance_id bắt đầu bằng 'local'."""
#     local_items = []
#     with open(file_path, 'r', encoding='utf-8') as f:
#         for line in f:
#             item = json.loads(line)
#             if str(item.get("instance_id", "")).startswith("local"):
#                 local_items.append(item)
#     return local_items
    
# def create_nl2sql_agent(db_id: str):
#     # Tạo instance DatabaseManager cho db_id cụ thể
#     db_manager = DatabaseManager(db_id)
    
#     # model_groq = ChatGroq(
#     #     model=Config.GROQ_MODEL_NAME,
#     #     groq_api_key=Config.GROQ_API_KEY,
#     #     temperature=0 )

#     # model_qwen = ChatGoogleGenerativeAI(model=Config.QWEN_MODEL_NAME, google_api_key=Config.QWEN_API_KEY)
    
#     model_gemini = ChatGoogleGenerativeAI(model=Config.GEMINI_MODEL_NAME, google_api_key=Config.GEMINI_API_KEY)

#     # agent = create_agent(
#     #     model=model_qwen,
#     #     tools=create_db_tools(db_id),
#     #     system_prompt=SYSTEM_PROMPT,
#     #     middleware= [ModelFallbackMiddleware(
#     #         model_groq, model_gemini
#     #     )]
#     # )

#     agent = create_agent(
#         model=model_gemini,
#         tools=create_db_tools(db_id),
#         system_prompt=SYSTEM_PROMPT
#     )

#     return agent

"""
Agent module for NL2SQL system.

This module is responsible for:
- Initializing LLM models
- Configuring SSL for secure API communication
- Creating NL2SQL agents with tool integrations
- Providing utility functions for dataset filtering

The agent leverages LangChain's tool-calling capabilities to
convert natural language queries into SQL queries and execute them.
"""

import os
import json
import ssl
from typing import List, Dict, Any

from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.middleware.model_fallback import ModelFallbackMiddleware

from src.config import Config
from src.helpers.tools import create_db_tools
from src.handlers.database import DatabaseManager
from src.helpers.logging_config import logger
from src.helpers.SYSTEM_PROMPT import SYSTEM_PROMPT


# -------------------------------------------------------------------
# SSL CONFIGURATION
# -------------------------------------------------------------------

cert_path = str(Config.CERT)

try:
    os.environ["SSL_CERT_FILE"] = cert_path
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path

    ssl._create_default_https_context = ssl.create_default_context(
        cafile=cert_path
    )

    logger.info("SSL configured successfully with cert: %s", cert_path)

except Exception as e:
    logger.error("Failed to configure SSL: %s", str(e), exc_info=True)
    raise RuntimeError(f"SSL configuration failed: {str(e)}") from e


# -------------------------------------------------------------------
# UTILITIES
# -------------------------------------------------------------------

def get_local_instances(file_path: str) -> List[Dict[str, Any]]:
    """
    Filter dataset items whose instance_id starts with 'local'.

    Args:
        file_path (str): Path to the JSONL file.

    Returns:
        List[Dict[str, Any]]: Filtered list of local instances.

    Raises:
        ValueError: If file cannot be read or JSON parsing fails.
    """
    try:
        local_items: List[Dict[str, Any]] = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)

                if str(item.get("instance_id", "")).startswith("local"):
                    local_items.append(item)

        logger.info("Loaded %d local instances from %s", len(local_items), file_path)
        return local_items

    except Exception as e:
        logger.error(
            "Failed to load local instances from file: %s",
            file_path,
            exc_info=True
        )
        raise ValueError(f"Error reading local instances: {str(e)}") from e


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

        # Initialize DatabaseManager (kept for consistency, even if not directly used here)
        db_manager = DatabaseManager(db_id)

        # -------------------------------------------------------------------
        # MODEL CONFIGURATION
        # -------------------------------------------------------------------

        # model_groq = ChatGroq(
        #     model=Config.GROQ_MODEL_NAME,
        #     groq_api_key=Config.GROQ_API_KEY,
        #     temperature=0
        # )

        # model_qwen = ChatGoogleGenerativeAI(
        #     model=Config.QWEN_MODEL_NAME,
        #     google_api_key=Config.QWEN_API_KEY
        # )

        model_gemini = ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL_NAME,
            google_api_key=Config.GEMINI_API_KEY
        )

        # -------------------------------------------------------------------
        # AGENT CREATION
        # -------------------------------------------------------------------

        # agent = create_agent(
        #     model=model_qwen,
        #     tools=create_db_tools(db_id),
        #     system_prompt=SYSTEM_PROMPT,
        #     middleware=[ModelFallbackMiddleware(model_groq, model_gemini)]
        # )

        agent = create_agent(
            model=model_gemini,
            tools=create_db_tools(db_id),
            system_prompt=SYSTEM_PROMPT
        )

        # agent = create_agent(
        #     model=model_groq,
        #     tools=create_db_tools(db_id),
        #     system_prompt=SYSTEM_PROMPT
        # )

        logger.info("NL2SQL agent created successfully for db_id: %s", db_id)

        return agent

    except Exception as e:
        logger.error(
            "Failed to create NL2SQL agent for db_id: %s",
            db_id,
            exc_info=True
        )
        raise RuntimeError(f"Agent creation failed: {str(e)}") from e
    