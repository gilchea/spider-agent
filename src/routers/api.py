###routers/api.py
"""
API Router module for NL2SQL system.

This module defines FastAPI endpoints for:
- Loading a database and initializing an NL2SQL agent
- Executing natural language queries against the database

It uses an in-memory store to cache agents per database ID
for efficient reuse across requests.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel # For request validation
from typing import Dict, Any
from openai import RateLimitError
import httpx
import json
import time

from src.helpers.agent import create_nl2sql_agent
from src.handlers.database import DatabaseManager
from src.handlers.logging_config import logger


# -------------------------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------------------------

app = FastAPI(title="NL2SQL", version="1.0")

#-------------------------------------------------------------------
# UTILS
#-------------------------------------------------------------------

def extract_text(answer):
    if isinstance(answer, list):
        return answer[0].get("text", "")
    return answer

# -------------------------------------------------------------------
# REQUEST SCHEMAS
# -------------------------------------------------------------------

class LoadDBRequest(BaseModel):
    """
    Request schema for loading a database.

    Attributes:
        db_id (str): Identifier of the database to load.
    """
    db_id: str


class QueryRequest(BaseModel):
    """
    Request schema for querying the database.

    Attributes:
        db_id (str): Identifier of the database.
        question (str): Natural language query from the user.
    """
    db_id: str
    question: str
    session_id: str 


# -------------------------------------------------------------------
# IN-MEMORY AGENT STORE
# -------------------------------------------------------------------

agents: Dict[str, Any] = {}


# -------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------
# @app.post("/reset_memory")
# def reset_memory(req: LoadDBRequest):
#     if req.db_id in agents:
#         agents[req.db_id] = create_nl2sql_agent(req.db_id)
#     return {"success": True}

@app.post("/load_db")
def load_database(req: LoadDBRequest) -> Dict[str, Any]:
    """
    Load a database and initialize its corresponding NL2SQL agent.

    This endpoint:
    - Validates the database existence
    - Retrieves table metadata
    - Creates and caches an agent instance

    Args:
        req (LoadDBRequest): Request containing database ID.

    Returns:
        Dict[str, Any]: Response containing success status, db_id, and table names.

    Raises:
        HTTPException: If database loading or agent creation fails.
    """
    try:
        logger.info("Loading database with db_id: %s", req.db_id)

        db = DatabaseManager(req.db_id)
        tables = db.get_table_names()

        agent = create_nl2sql_agent(req.db_id)
        agents[req.db_id] = agent # Cache the agent for future queries

        logger.info(
            "Database loaded successfully: %s | Tables: %s",
            req.db_id,
            tables
        )

        return {
            "success": True,
            "db_id": req.db_id,
            "tables": tables
        }

    except Exception as e:
        logger.error(
            "Failed to load database: %s",
            req.db_id,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/query")
def run_query(req: QueryRequest) -> Dict[str, Any]:
    """
    Execute a natural language query using the NL2SQL agent.

    This endpoint:
    - Validates that the database has been loaded
    - Sends the user query to the agent
    - Returns the processed result

    Args:
        req (QueryRequest): Request containing db_id and user question.

    Returns:
        Dict[str, Any]: Response with query result and raw agent output.

    Raises:
        HTTPException:
            - 400 if database is not loaded
            - 500 if query execution fails
    """
    try:
        logger.info(
            "Received query for db_id: %s | Question: %s",
            req.db_id,
            req.question
        )

        if req.db_id not in agents:
            logger.warning("Database not loaded: %s", req.db_id)
            raise HTTPException(
                status_code=400,
                detail="Database chưa được load"
            )

        agent = agents[req.db_id]

        # input_content = f"Database: {req.db_id}\n"
        # input_content += f"Question: {req.question}"

        # thread_id = f"session_{req.db_id}"  # đơn giản cho 1 user
        thread_id = f"{req.session_id}_{req.db_id}" #

        start_time = time.perf_counter()

        response = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": req.question}
                ]
            },
            {
                "configurable": {
                    "thread_id": thread_id
                }
            }
        )

        end_time = time.perf_counter()
        execution_time = round(end_time - start_time, 2)  # giây 

        output = response["messages"][-1].content
        output_text = extract_text(output)

        logger.info("Query executed successfully for db_id: %s", req.db_id)

        # Try to parse output as JSON to extract data and columns if available
        data = None
        columns = None

        try:
            parsed = json.loads(output_text)

            if isinstance(parsed, dict) and "data" in parsed:
                data = parsed.get("data")
                columns = parsed.get("columns")

        except Exception:
            pass
        
        # clean_answer = extract_text(output)
        return {
            "success": True,
            "answer": output_text,  # text trả lời
            "data": data,         # bảng
            "columns": columns,
            "raw": response,
            "execution_time": execution_time
        }

    except RateLimitError:
        logger.warning("LLM quota exceeded")
        raise HTTPException(
            status_code=429,
            detail="LLM quota exceeded"
        )

    except httpx.ConnectError:
        logger.error("This model is currently experiencing high demand")
        raise HTTPException(
            status_code=503,
            detail="This model is currently experiencing high demand"
        )

    except httpx.ReadTimeout:
        logger.error("LLM timeout")
        raise HTTPException(
            status_code=504,
            detail="LLM timeout"
        )

    except Exception as e:
        logger.error("Unexpected error", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )