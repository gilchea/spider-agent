from pydantic import BaseModel, Field
from typing import List
from database import DatabaseManager
from langchain.tools import tool
from config import Config
import os

# 1. Định nghĩa Schema cho các Tool phức tạp
class TableNamesInput(BaseModel):
    table_names: List[str] = Field(
        description="Danh sách tên các bảng cần lấy schema, ví dụ: ['drivers', 'races']"
    )

class SQLQueryInput(BaseModel):
    sql_query: str = Field(
        description="Câu lệnh SQL hoàn chỉnh và hợp lệ để thực thi trên SQLite."
    )

def create_db_tools(db_id: str):
    db_manager = DatabaseManager(db_id)

    @tool
    def list_tables() -> str:
        """Retrieve all table names available in the database.

        This tool should be called first if the database structure is unknown.

        Returns:
            A string listing all table names in the database.
            Example: "Các bảng hiện có: users, orders, products"
        """
        try:
            tables = db_manager.get_table_names()
            return f"Các bảng hiện có: {', '.join(tables)}"
        except Exception as e:
            return f"Lỗi khi lấy danh sách bảng: {str(e)}"

    @tool(args_schema=TableNamesInput)
    def get_schemas(table_names: List[str]) -> str:
        """Retrieve the CREATE TABLE schema definitions for specific tables.

        This tool MUST be used before writing any SQL query to ensure correct
        column names and data types. Do NOT assume schema structure.

        Args:
            table_names: List of table names to retrieve schema for.
                        Example: ["users", "orders"]

        Returns:
            A string containing CREATE TABLE statements for the requested tables.
            If no schema is found, returns an empty string or error message.
        """
        if not table_names:
            return "Lỗi: Danh sách tên bảng không được để trống."
        
        try:
            # table_names bây giờ đã là một List nhờ Pydantic xử lý
            return db_manager.get_schemas(table_names)
        except Exception as e:
            return f"Lỗi khi lấy schema: {str(e)}"

    @tool(args_schema=SQLQueryInput)
    def execute_sql(sql_query: str) -> str:
        """Execute a validated SQL SELECT query on the database and return results.

        This tool should ONLY be called after:
        - Understanding the schema using `get_schemas`
        - Reading any relevant external knowledge if mentioned in the question
        - Ensuring the query is correct and safe

        Args:
            sql_query: A complete and valid SQLite SELECT query.
                    Example: "SELECT name, age FROM users LIMIT 5"

        Returns:
            A string representation of the query result in dictionary format:
            {
                "status": "success",
                "columns": ["col1", "col2"],
                "data": [[val1, val2], ...]
            }

            If execution fails, returns an error message string.
        """
        # Làm sạch query
        clean_query = sql_query.strip().strip("`").replace("sql\n", "")
        
        # Chặn các câu lệnh nguy hiểm (Read-only)
        forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER"]
        if any(keyword in clean_query.upper() for keyword in forbidden_keywords):
            return "Lỗi: Chỉ được phép thực hiện các câu lệnh truy vấn (SELECT)."

        try:
            result = db_manager.execute_query(clean_query)
            if not result:
                return "Truy vấn thành công nhưng không có kết quả trả về."
            return str(result)
        except Exception as e:
            return f"Lỗi thực thi SQL: {str(e)}"
        
    @tool
    def get_external_knowledge(doc_name: str) -> str:
        """Retrieve additional contextual knowledge from an external document.

        This tool should be used when the user query references an
        "External Knowledge File" to provide extra context before choose table to get schema and generating SQL.

        Args:
            doc_name: Name of the document file to retrieve.
                    Example: "schema_description.txt"

        Returns:
            The full text content of the document if found.

            If the file does not exist or is empty, returns an appropriate message.
        """
        # Trường hợp không có tên file (null/None/rỗng)
        if not doc_name: 
            return "Không có kiến thức bổ sung (External Knowledge) cho câu hỏi này."

        path = os.path.join(Config.DOC_ROOT, doc_name)
        
        # Trường hợp có tên file nhưng file không tồn tại trên ổ đĩa
        if not os.path.exists(path):
            return f"Cảnh báo: Tài liệu '{doc_name}' được nhắc đến nhưng không tìm thấy tại {path}."

        # Trường hợp đọc file thành công
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return content if content else "Tài liệu tồn tại nhưng nội dung trống."
        except Exception as e:
            return f"Lỗi khi đọc tài liệu: {str(e)}"
        
    @tool
    def check_syntax(sql_query: str) -> str:
        """Validate the syntax of a SQL SELECT query without executing it.

        This tool should be used before executing a query to ensure it is syntactically correct.

        Args:
            sql_query: A SQL SELECT query to validate.
                    Example: "SELECT * FROM users WHERE age > 30"

        Returns:
            - "Cú pháp SQL hợp lệ." if the query is valid
            - An error message string if the syntax is invalid
        """
        # Làm sạch query
        clean_query = sql_query.strip().strip("`").replace("sql\n", "")
        
        # Chặn các câu lệnh nguy hiểm (Read-only)
        forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER"]
        if any(keyword in clean_query.upper() for keyword in forbidden_keywords):
            return "Lỗi: Chỉ được phép kiểm tra cú pháp cho các câu lệnh truy vấn (SELECT)."

        try:
            db_manager.check_sql_syntax(clean_query)
            return "Cú pháp SQL hợp lệ."
        except Exception as e:
            return f"Lỗi cú pháp SQL: {str(e)}"

    

    return [list_tables, get_schemas, execute_sql, check_syntax, get_external_knowledge]
