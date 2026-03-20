import os
from sqlalchemy import create_engine, text, inspect
from config import Config

class DatabaseManager:
    def __init__(self, db_id: str):
        # Xác định đường dẫn file sqlite
        self.db_path = os.path.join(Config.DB_ROOT, f"{db_id}.sqlite")
        if not os.path.exists(self.db_path):
            for root, dirs, files in os.walk(Config.DB_ROOT):
                if f"{db_id}.sqlite" in files:
                    self.db_path = os.path.join(root, f"{db_id}.sqlite")
                    break
        
        # Ở đây dùng đường dẫn tuyệt đối cho chắc chắn
        absolute_path = os.path.abspath(self.db_path)
        self.engine = create_engine(f"sqlite:///{absolute_path}")

    def execute_query(self, sql: str, params=None):
        """Thực thi query sử dụng SQLAlchemy engine"""
        try:
            # Sử dụng context manager để tự động đóng connection
            with self.engine.connect() as conn:
                # Chuyển đổi string SQL thành object text của SQLAlchemy
                stmt = text(sql)
                
                # Thực thi với params nếu có (params nên là dict: {"name": "value"})
                result = conn.execute(stmt, params or {})
                
                # Lấy tên cột nếu kết quả có trả về dòng (SELECT)
                columns = list(result.keys()) if result.returns_rows else []
                
                # Lấy dữ liệu
                data = [list(row) for row in result.fetchall()] if result.returns_rows else []
                
                return {
                    "status": "success", 
                    "data": data, 
                    "columns": columns
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_table_names(self):
        """Sử dụng Inspector của SQLAlchemy để lấy tên bảng chuyên nghiệp hơn"""
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception:
            # Fallback về query nếu có lỗi
            sql = "SELECT name FROM sqlite_master WHERE type='table';"
            res = self.execute_query(sql)
            return [row[0] for row in res['data']] if res['status'] == 'success' else []

    def get_schemas(self, table_names: list):
        """
        Nhận vào danh sách tên bảng và trả về chuỗi CREATE TABLE schema.
        """
        if not table_names:
            return ""

        # Tạo query động với các placeholder :t0, :t1, ...
        placeholders = [f":t{i}" for i in range(len(table_names))]
        sql = f"SELECT sql FROM sqlite_master WHERE type='table' AND name IN ({', '.join(placeholders)});"
        
        # Tạo dictionary params: {"t0": "table1", "t1": "table2", ...}
        params = {f"t{i}": name for i, name in enumerate(table_names)}
        
        res = self.execute_query(sql, params=params)
        
        if res['status'] == 'success' and res['data']:
            schemas = [row[0] for row in res['data'] if row[0]]
            return "\n\n".join(schemas)
        
        return ""
    
    def check_sql_syntax(self, sql: str):
        """Kiểm tra cú pháp SQL bằng cách sử dụng EXPLAIN QUERY PLAN"""
        try:
            with self.engine.connect() as conn:
                stmt = text(f"EXPLAIN QUERY PLAN {sql}")
                conn.execute(stmt)
            return {"status": "valid"}
        except Exception as e:
            return {"status": "invalid", "message": str(e)}
    

# db = DatabaseManager("WWE")
# print(db.get_table_names())
# print(db.get_schemas(['Cards', 'Events']))

# # Sử dụng dấu nháy ba để bao bọc câu lệnh SQL nhiều dòng
# query = """
# WITH MatchDetails AS (
#     SELECT
#         b.name AS titles,
#         m.duration AS match_duration,
#         w1.name || ' vs ' || w2.name AS matches,
#         m.win_type AS win_type,
#         l.name AS location,
#         e.name AS event,
#         ROW_NUMBER() OVER (PARTITION BY b.name ORDER BY m.duration ASC) AS rank
#     FROM 
#         Belts b
#     INNER JOIN Matches m ON m.title_id = b.id
#     INNER JOIN Wrestlers w1 ON w1.id = m.winner_id
#     INNER JOIN Wrestlers w2 ON w2.id = m.loser_id
#     INNER JOIN Cards c ON c.id = m.card_id
#     INNER JOIN Locations l ON l.id = c.location_id
#     INNER JOIN Events e ON e.id = c.event_id
#     INNER JOIN Promotions p ON p.id = c.promotion_id
#     WHERE
#         p.name = 'NXT'
#         AND m.duration IS NOT NULL AND m.duration <> ''
#         AND b.name <> ''
#         AND b.name NOT IN (
#             SELECT name 
#             FROM Belts 
#             WHERE name LIKE '%title change%'
#         )
# ),
# Rank1 AS (
#     SELECT 
#         titles,
#         match_duration,
#         matches
#     FROM 
#         MatchDetails
#     WHERE 
#         rank = 1
# )
# SELECT
#     SUBSTR(matches, 1, INSTR(matches, ' vs ') - 1) AS wrestler1,
#     SUBSTR(matches, INSTR(matches, ' vs ') + 4) AS wrestler2
# FROM
#     Rank1
# ORDER BY match_duration 
# LIMIT 1;
# """

# # Gọi hàm thực thi
# print(db.execute_query(query))