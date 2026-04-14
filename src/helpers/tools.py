###helpers/tools.py
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

from src.helpers.skills import SKILLS
from src.handlers.database import DatabaseManager
from src.config import Config
from src.handlers.logging_config import logger
# from langgraph.prebuilt import InjectedState
# from src.helpers.state import CustomState


# ================================
# Pydantic Schemas
# ================================

class TableNamesInput(BaseModel):
    """
    Input schema for retrieving table schemas.

    Attributes:
        table_names (List[str]): List of table names to retrieve schema for
        vertical (str): Vertical of the database
    """
    table_names: List[str] = Field(
        description="List of table names, e.g. ['users', 'orders']"
    )
    vertical: str = Field(
        description="Vertical of the database, e.g. 'school_scheduling'"
    )


class SQLQueryInput(BaseModel):
    """
    Input schema for SQL query execution.

    Attributes:
        sql_query (str): A complete SQL SELECT query
        vertical (str): Vertical of the database
    """
    sql_query: str = Field(
        description="A complete and valid SQLite SELECT query"
    )
    vertical: str = Field(
        description="Vertical of the database, e.g. 'school_scheduling'"
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
    def get_schemas(table_names: List[str], vertical: str, runtime: ToolRuntime) -> str:
        """
        Retrieve CREATE TABLE schema definitions for specific tables.

        Args:
            table_names (List[str]): List of table names
            vertical (str): "hr_student_admin" | "academic_scheduling" (skill vertical for context đã được load)
            runtime (ToolRuntime): Runtime of the tool

        Returns:
            str: CREATE TABLE statements or error message

        Raises:
            Exception: Internally handled and logged
        """
        # Check if the required skill has been loaded
        skills_loaded = runtime.state.get("skills_loaded", [])

        if vertical not in skills_loaded:
            return (
                f"Error: You must load the '{vertical}' skill first "
                f"to understand the schema of the database. "
                f"Use load_skill('{vertical}') to load the schema."
            )

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
    def execute_sql(sql_query: str, vertical: str, runtime: ToolRuntime) -> str:
        """
        Execute a validated SQL SELECT query on the database.

        Args:
            sql_query (str): SQL SELECT query
            vertical (str): hr_student_admin or academic_scheduling (skill vertical for context đã được load)
            runtime (ToolRuntime): Runtime of the tool

        Returns:
            str: Query result in string format or error message

        Raises:
            Exception: Internally handled and logged
        """
        # Check if the required skill has been loaded
        skills_loaded = runtime.state.get("skills_loaded", [])

        if vertical not in skills_loaded:
            return (
                f"Error: You must load the '{vertical}' skill first "
                f"to understand the database schema before writing queries and executing them. "
                f"Use load_skill('{vertical}') to load the schema."
            )

        try:
            logger.info("Tool execute_sql called")

            clean_query = sql_query.strip().strip("`").replace("sql\n", "")

            result = db_manager.execute_query(clean_query)

            if not result:
                logger.info("Query executed but returned empty result")
                return "Truy vấn thành công nhưng không có kết quả trả về."

            return str(result)

        except Exception as e:
            logger.error("execute_sql failed: %s", str(e), exc_info=True)
            return f"Lỗi thực thi SQL: {str(e)}"

    return [
        # list_tables,
        get_schemas,
        execute_sql,
        # check_syntax,
    ]

from langgraph.types import Command  
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage  

@tool
def load_skill(skill_name: str, runtime: ToolRuntime) -> Command:
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.

    Args:
        skill_name: The name of the skill to load
        runtime (ToolRuntime): Runtime of the tool

    Returns:
        Command: Command to update the state
    """
    # Find and return the requested skill
    for skill in SKILLS:
        if skill["name"] == skill_name:
            skill_content = f"Loaded skill: {skill_name}\n\n{skill['relevant_tables']}"

            # Update state to track loaded skill
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=skill_content,
                            tool_call_id=runtime.tool_call_id,
                        )
                    ],
                    "skills_loaded": [skill_name],
                }
            )

    # Skill not found
    available = ", ".join(s["name"] for s in SKILLS)
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Skill '{skill_name}' not found. Available skills: {available}",
                    tool_call_id=runtime.tool_call_id,
                )
            ]
        }
    )