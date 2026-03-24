# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from src.helpers.agent import create_nl2sql_agent
# from src.handlers.database import DatabaseManager

# app = FastAPI(title="NL2SQL API", version="1.0")

# # Request schemas
# class LoadDBRequest(BaseModel):
#     db_id: str

# class QueryRequest(BaseModel):
#     db_id: str
#     question: str

# # In-memory store (simple) Lưu agent theo db_id
# agents = {}

# # API: Load DB
# @app.post("/load_db")  # Endpoint để load database và tạo agent tương ứng
# def load_database(req: LoadDBRequest):
#     try:
#         db = DatabaseManager(req.db_id) # Tạo instance DatabaseManager để kiểm tra và lấy thông tin database
#         tables = db.get_table_names()

#         agent = create_nl2sql_agent(req.db_id)
#         agents[req.db_id] = agent # Lưu agent vào dictionary để sử dụng cho các truy vấn sau này

#         return {
#             "success": True,
#             "db_id": req.db_id,
#             "tables": tables
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e)) # Trả về lỗi nếu có vấn đề khi load database hoặc tạo agent


# # API: Query
# @app.post("/query") # Endpoint để nhận câu hỏi và trả về kết quả từ agent
# def run_query(req: QueryRequest):
#     try:
#         if req.db_id not in agents: # Kiểm tra nếu agent cho db_id chưa tồn tại, trả về lỗi
#             raise HTTPException(
#                 status_code=400,
#                 detail="Database chưa được load"
#             )

#         agent = agents[req.db_id]

#         input_content = f"Database: {req.db_id}\n"
#         input_content += f"Question: {req.question}"

#         response = agent.invoke({
#             "messages": [
#                 {"role": "user", "content": input_content}
#             ]
#         })

#         output = response["messages"][-1].content

#         return {
#             "success": True,
#             "output": output,
#             "raw": response
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
"""
API Router module for NL2SQL system.

This module defines FastAPI endpoints for:
- Loading a database and initializing an NL2SQL agent
- Executing natural language queries against the database

It uses an in-memory store to cache agents per database ID
for efficient reuse across requests.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from src.helpers.agent import create_nl2sql_agent
from src.handlers.database import DatabaseManager
from src.helpers.logging_config import logger


# -------------------------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------------------------

app = FastAPI(title="NL2SQL API", version="1.0")


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


# -------------------------------------------------------------------
# IN-MEMORY AGENT STORE
# -------------------------------------------------------------------

agents: Dict[str, Any] = {}


# -------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------

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
        agents[req.db_id] = agent

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

        input_content = f"Database: {req.db_id}\n"
        input_content += f"Question: {req.question}"

        response = agent.invoke({
            "messages": [
                {"role": "user", "content": input_content}
            ]
        })

        output = response["messages"][-1].content

        logger.info("Query executed successfully for db_id: %s", req.db_id)

        return {
            "success": True,
            "output": output,
            "raw": response
        }

    except HTTPException:
        # Re-raise HTTP exceptions (do not override)
        raise

    except Exception as e:
        logger.error(
            "Query execution failed for db_id: %s",
            req.db_id,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e)) from e