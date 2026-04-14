###handlers/database.py
"""
Database Manager module for SQLite-based NL2SQL system.

This module provides a DatabaseManager class responsible for:
- Managing connections to SQLite databases
- Executing SQL queries safely using SQLAlchemy
- Retrieving database metadata such as table names and schemas

The module includes structured logging and error handling
to support debugging and production monitoring.
"""

import os
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine, text, inspect
from src.config import Config
from src.handlers.logging_config import logger


class DatabaseManager:
    """
    Manages SQLite database connections and operations.

    This class provides utility methods for executing queries,
    retrieving schema information, and validating SQL syntax
    in a safe and controlled manner.
    """

    def __init__(self, db_id: str):
        """
        Initialize DatabaseManager with a specific database ID.

        This method locates the SQLite database file and initializes
        a SQLAlchemy engine for database interactions.

        Args:
            db_id (str): Identifier of the database (without .sqlite extension)

        Raises:
            ValueError: If database file cannot be found or engine creation fails
        """
        try:
            logger.info("Initializing DatabaseManager for db_id: %s", db_id)

            # Resolve database path
            self.db_path = os.path.join(Config.DB_ROOT, f"{db_id}.sqlite")

            if not os.path.exists(self.db_path):
                logger.warning("Database not found at root path, searching recursively...")
                for root, _, files in os.walk(Config.DB_ROOT):
                    if f"{db_id}.sqlite" in files:
                        self.db_path = os.path.join(root, f"{db_id}.sqlite")
                        break

            absolute_path = os.path.abspath(self.db_path)

            if not os.path.exists(absolute_path):
                raise ValueError(f"Database file not found for db_id: {db_id}")

            self.engine = create_engine(f"sqlite:///{absolute_path}")
            logger.info("Database engine created successfully for: %s", absolute_path)

        except Exception as e:
            logger.error("Failed to initialize DatabaseManager: %s", str(e), exc_info=True)
            raise ValueError(f"Database initialization failed: {str(e)}") from e

    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a SQL query using SQLAlchemy engine.

        This method safely executes a SQL query and returns structured results.
        It supports parameterized queries to prevent SQL injection.

        Args:
            sql (str): SQL query string to execute
            params (Optional[Dict[str, Any]]): Parameters for the query

        Returns:
            Dict[str, Any]:
                {
                    "status": "success" | "error",
                    "data": List[List[Any]],
                    "columns": List[str],
                    "message": Optional[str]
                }

        Raises:
            Exception: Internally caught and logged, not raised to caller
        """
        try:
            sql = sql.strip().strip("`").replace("sql\n", "")

            # Only allow SELECT or WITH
            if not sql.lower().startswith(("select", "with")):
                logger.warning("Invalid SQL type detected")
                return {
                    "status": "invalid",
                    "message": "Chỉ cho phép SELECT hoặc WITH query"
                }

            # Block dangerous keywords
            forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER"]
            if any(keyword in sql.upper() for keyword in forbidden_keywords):
                logger.warning("Dangerous SQL keyword detected")
                return {
                    "status": "invalid",
                    "message": "Query chứa từ khóa không hợp lệ"
                }

            logger.info("Executing SQL query: %s", sql)

            with self.engine.connect() as conn:
                stmt = text(sql)
                result = conn.execute(stmt, params or {})

                columns = list(result.keys()) if result.returns_rows else []
                data = [list(row) for row in result.fetchall()] if result.returns_rows else []

                logger.info("Query executed successfully. Rows returned: %d", len(data))

                return {
                    "status": "success",
                    "data": data,
                    "columns": columns
                }

        except Exception as e:
            logger.error("SQL execution failed: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    def get_table_names(self) -> List[str]:
        """
        Retrieve all table names from the SQLite database.

        This method first attempts to use SQLAlchemy Inspector.
        If it fails, it falls back to querying sqlite_master.

        Returns:
            List[str]: List of table names in the database

        Raises:
            Exception: Internally handled, fallback logic applied
        """
        try:
            logger.info("Fetching table names using SQLAlchemy inspector")
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            logger.info("Retrieved %d tables", len(tables))
            return tables

        except Exception as e:
            logger.warning("Inspector failed, falling back to raw SQL: %s", str(e))

            try:
                sql = "SELECT name FROM sqlite_master WHERE type='table';"
                res = self.execute_query(sql)

                if res["status"] == "success":
                    tables = [row[0] for row in res["data"]]
                    logger.info("Fallback query retrieved %d tables", len(tables))
                    return tables

                return []

            except Exception as inner_e:
                logger.error("Failed to fetch table names: %s", str(inner_e), exc_info=True)
                return []

    def get_schemas(self, table_names: List[str]) -> str:
        """
        Retrieve CREATE TABLE schema definitions for given tables.

        Args:
            table_names (List[str]): List of table names

        Returns:
            str: Concatenated CREATE TABLE statements separated by newlines

        Raises:
            Exception: Internally handled and logged
        """
        try:
            logger.info("Fetching schema for tables: %s", table_names)

            if not table_names:
                logger.warning("Empty table_names input")
                return ""

            placeholders = [f":t{i}" for i in range(len(table_names))]
            sql = f"""
                SELECT sql
                FROM sqlite_master
                WHERE type='table'
                AND name IN ({', '.join(placeholders)});
            """

            params = {f"t{i}": name for i, name in enumerate(table_names)}
            res = self.execute_query(sql, params=params)

            if res["status"] == "success" and res["data"]:
                schemas = [row[0] for row in res["data"] if row[0]]
                logger.info("Retrieved schema for %d tables", len(schemas))
                return "\n\n".join(schemas)

            logger.warning("No schema found for given tables")
            return ""

        except Exception as e:
            logger.error("Failed to fetch schemas: %s", str(e), exc_info=True)
            return ""

    # def check_sql_syntax(self, sql: str) -> Dict[str, str]:
    #     """
    #     Validate SQL query syntax using EXPLAIN QUERY PLAN.

    #     This method ensures that the SQL query is:
    #     - Read-only (SELECT or WITH)
    #     - Free from dangerous operations (DROP, DELETE, etc.)
    #     - Compatible with the database schema

    #     The query is NOT executed.

    #     Args:
    #         sql (str): SQL query string to validate

    #     Returns:
    #         Dict[str, str]:
    #             {
    #                 "status": "valid" | "invalid",
    #                 "message": Optional[str]
    #             }

    #     Raises:
    #         Exception: Internally handled and logged
    #     """
    #     try:
    #         logger.info("Validating SQL syntax")

    #         clean_sql = sql.strip().strip("`").replace("sql\n", "")

    #         # Only allow SELECT or WITH
    #         if not clean_sql.lower().startswith(("select", "with")):
    #             logger.warning("Invalid SQL type detected")
    #             return {
    #                 "status": "invalid",
    #                 "message": "Chỉ cho phép SELECT hoặc WITH query"
    #             }

    #         # Block dangerous keywords
    #         forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER"]
    #         if any(keyword in clean_sql.upper() for keyword in forbidden_keywords):
    #             logger.warning("Dangerous SQL keyword detected")
    #             return {
    #                 "status": "invalid",
    #                 "message": "Query chứa từ khóa không hợp lệ"
    #             }

    #         with self.engine.connect() as conn:
    #             stmt = text("EXPLAIN QUERY PLAN " + clean_sql)
    #             conn.execute(stmt)

    #         logger.info("SQL syntax is valid")
    #         return {"status": "valid"}

    #     except Exception as e:
    #         logger.error("SQL syntax validation failed: %s", str(e), exc_info=True)
    #         return {
    #             "status": "invalid",
    #             "message": str(e)
    #         }