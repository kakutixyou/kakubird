from typing import List, Dict, Any, Tuple, Optional
from repositories.sql_repository import SQLRepository
#sql_service.py
class SQLService:
    def __init__(self, repository: SQLRepository):
        self.repo = repository
        # 修正ポイント：許可するテーブルを制限（ホワイトリスト）
        self.allowed_tables = ["users", "products", "orders"] 

    def execute_query(self, query_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._validate_query_data(query_data)
        sql, params = self._build_select(query_data)
        return self.repo.execute(sql, params)

    def _validate_query_data(self, data: Dict[str, Any]) -> None:
        if data.get("table") not in self.allowed_tables:
            raise ValueError(f"Access to table '{data.get('table')}' is not allowed.")
        
        if not data.get("columns") or not isinstance(data["columns"], list):
            raise ValueError("Columns must be a non-empty list")

    def _build_select(self, data: Dict[str, Any]) -> Tuple[str, List[Any]]:
        # 修正ポイント：識別子をダブルクォートで囲む (PostgreSQL/SQLite対応)
        table = f'"{self._sanitize_identifier(data["table"])}"'
        cols = ", ".join([f'"{self._sanitize_identifier(c)}"' for c in data["columns"]])

        sql = f"SELECT {cols} FROM {table}"
        params = []

        # WHERE句
        if "conditions" in data and data["conditions"]:
            clauses = []
            for cond in data["conditions"]:
                field = f'"{self._sanitize_identifier(cond["field"])}"'
                op = self._sanitize_operator(cond["operator"])
                
                # 修正ポイント：プレースホルダをDBに合わせて変更できるようにする
                clauses.append(f"{field} {op} %s") 
                params.append(cond["value"])
            
            sql += " WHERE " + " AND ".join(clauses)

        # LIMITの安全な処理
        if "limit" in data:
            try:
                limit_val = int(data["limit"])
            except (TypeError, ValueError):
                raise ValueError("Limit must be an integer")
            sql += f" LIMIT {limit_val}" # 数値ならパラメータ化せず直接埋め込んでも安全

        return sql, params

    def _sanitize_identifier(self, identifier: str) -> str:
        # 英数字とアンダースコア以外を排除
        if not identifier.replace("_", "").isalnum():
            raise ValueError(f"Invalid characters in identifier: {identifier}")
        return identifier

    def _sanitize_operator(self, operator: str) -> str:
        allowed = ["=", ">", "<", ">=", "<=", "!=", "LIKE"]
        if operator.upper() not in allowed:
            raise ValueError(f"Forbidden operator: {operator}")
        return operator.upper()
    
    # services/sql_service.py に追加するイメージ
def execute_raw_query(self, sql: str) -> list[dict]:
    return self.repository.execute_raw(sql)