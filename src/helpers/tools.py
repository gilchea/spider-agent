"""
Tools module for NL2SQL Agent.

This module defines all tools used by the agent to interact with
the SQLite database and external knowledge sources.

It includes:
- Table discovery tools
- Schema retrieval tools
- SQL execution tools
- SQL validation tools
- External knowledge retrieval tools

All tools are designed to be used within a LangChain agent framework,
with proper input validation, logging, and error handling.
"""

import json
import os
from typing import List

from pydantic import BaseModel, Field
from langchain.tools import tool

from src.handlers.database import DatabaseManager
from src.config import Config
from src.helpers.logging_config import logger


# ================================
# Pydantic Schemas
# ================================

class TableNamesInput(BaseModel):
    """
    Input schema for retrieving table schemas.

    Attributes:
        table_names (List[str]): List of table names to retrieve schema for
    """
    table_names: List[str] = Field(
        description="List of table names, e.g. ['users', 'orders']"
    )


class SQLQueryInput(BaseModel):
    """
    Input schema for SQL query execution.

    Attributes:
        sql_query (str): A complete SQL SELECT query
    """
    sql_query: str = Field(
        description="A complete and valid SQLite SELECT query"
    )

class ExternalKnowledgeInput(BaseModel):
    """
    Input schema for retrieving external knowledge.

    Attributes:
        db_id (str): Identifier of the database to retrieve knowledge for
    """
    db_id: str = Field(
        description="Database identifier, e.g. 'Airlines'"
    )


# ================================
# Tool Factory
# ================================

def create_db_tools(db_id: str):
    """
    Create a list of database-related tools for a specific database.

    Args:
        db_id (str): Identifier of the database

    Returns:
        List: List of LangChain tool instances

    Raises:
        ValueError: If DatabaseManager initialization fails
    """
    try:
        logger.info("Creating DB tools for db_id: %s", db_id)
        db_manager = DatabaseManager(db_id)

    except Exception as e:
        logger.error("Failed to create DatabaseManager: %s", str(e), exc_info=True)
        raise ValueError(f"Failed to initialize tools: {str(e)}") from e

    @tool
    def list_tables() -> str:
        """
        Retrieve all table names available in the database.

        Returns:
            str: Comma-separated list of table names

        Raises:
            Exception: Internally handled and logged
        """
        try:
            logger.info("Tool list_tables called")
            tables = db_manager.get_table_names()
            return f"Các bảng hiện có: {', '.join(tables)}"

        except Exception as e:
            logger.error("list_tables failed: %s", str(e), exc_info=True)
            return f"Lỗi khi lấy danh sách bảng: {str(e)}"

    @tool(args_schema=TableNamesInput)
    def get_schemas(table_names: List[str]) -> str:
        """
        Retrieve CREATE TABLE schema definitions for specific tables.

        Args:
            table_names (List[str]): List of table names

        Returns:
            str: CREATE TABLE statements or error message

        Raises:
            Exception: Internally handled and logged
        """
        try:
            logger.info("Tool get_schemas called with tables: %s", table_names)

            if not table_names:
                logger.warning("Empty table_names provided")
                return "Lỗi: Danh sách tên bảng không được để trống."

            return db_manager.get_schemas(table_names)

        except Exception as e:
            logger.error("get_schemas failed: %s", str(e), exc_info=True)
            return f"Lỗi khi lấy schema: {str(e)}"

    @tool(args_schema=SQLQueryInput)
    def execute_sql(sql_query: str) -> str:
        """
        Execute a validated SQL SELECT query on the database.

        Args:
            sql_query (str): SQL SELECT query

        Returns:
            str: Query result in string format or error message

        Raises:
            Exception: Internally handled and logged
        """
        try:
            logger.info("Tool execute_sql called")

            clean_query = sql_query.strip().strip("`").replace("sql\n", "")

            # forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER"]
            # if any(keyword in clean_query.upper() for keyword in forbidden_keywords):
            #     logger.warning("Blocked dangerous SQL query")
            #     return "Lỗi: Chỉ được phép thực hiện các câu lệnh truy vấn (SELECT)."

            result = db_manager.execute_query(clean_query)

            if not result:
                logger.info("Query executed but returned empty result")
                return "Truy vấn thành công nhưng không có kết quả trả về."

            return str(result)

        except Exception as e:
            logger.error("execute_sql failed: %s", str(e), exc_info=True)
            return f"Lỗi thực thi SQL: {str(e)}"

    @tool(args_schema=ExternalKnowledgeInput)
    def get_external_knowledge(db_id: str) -> str:
        """
        Retrieve external knowledge documents associated with a database.

        Args:
            db_id (str): Database identifier

        Returns:
            str: Combined content of external knowledge documents

        Raises:
            Exception: Internally handled and logged
        """
        try:
            logger.info("Tool get_external_knowledge called for db_id: %s", db_id)

            mapping_path = Config.DB_KNOWLEDGE_MAPPING

            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)

            # Create a mapping of db_id to its external knowledge documents
            db_map = {
                item["db"]: item["external_knowledge"]
                for item in mapping
            }

            if db_id not in db_map:
                logger.info("No external knowledge found for db_id: %s", db_id)
                return f"Không có kiến thức bổ sung (External Knowledge) cho database '{db_id}'."

            contents = []

            # for doc_name in db_map[db_id]:
            doc_name = db_map[db_id]  # giả sử chỉ 1 doc cho mỗi db
            path = os.path.join(Config.DOC_ROOT, doc_name)

            if not os.path.exists(path):
                logger.warning("Missing document: %s", doc_name)
                contents.append(f"[Cảnh báo] Không tìm thấy tài liệu: {doc_name}")
                # continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                    if content:
                        contents.append(f"\n===== {doc_name} =====\n{content}")
                    else:
                        contents.append(f"[Cảnh báo] Tài liệu '{doc_name}' rỗng.")

            except Exception as inner_e:
                logger.error("Failed reading document %s: %s", doc_name, str(inner_e), exc_info=True)
                contents.append(f"[Lỗi] Không đọc được '{doc_name}': {str(inner_e)}")

            return "\n".join(contents) if contents else "Không có nội dung external knowledge hợp lệ."

        except Exception as e:
            logger.error("get_external_knowledge failed: %s", str(e), exc_info=True)
            return f"Lỗi khi đọc file mapping db_knowledge.json: {str(e)}"

    @tool
    def check_syntax(sql_query: str) -> str:
        """
        Validate SQL syntax without executing the query.

        Args:
            sql_query (str): SQL query to validate

        Returns:
            str: Validation result message

        Raises:
            Exception: Internally handled and logged
        """
        try:
            logger.info("Tool check_syntax called")

            clean_query = sql_query.strip().strip("`").replace("sql\n", "")

            db_manager.check_sql_syntax(clean_query)

            return "Cú pháp SQL hợp lệ."

        except Exception as e:
            logger.error("check_syntax failed: %s", str(e), exc_info=True)
            return f"Lỗi cú pháp SQL: {str(e)}"

    return [
        list_tables,
        get_schemas,
        execute_sql,
        check_syntax,
        get_external_knowledge
    ]