# backend/schemas/nlp_models.py

from pydantic import BaseModel, Field

# ===
# NLPルーター用のデータ構造（スキーマ）定義
# PydanticのBaseModelを継承することで、自動的にデータの型チェックが行われます
# ===

class AnalysisRequest(BaseModel):
    """自然言語解析APIのリクエスト用モデル"""
    text: str = Field(..., description="ユーザーが入力した自然言語のクエリ（例: '価格が1000円より高い商品'）")


class TemplatePart(BaseModel):
    """UIの各入力フォームを構成するためのパーツ定義"""
    label: str = Field(..., description="UIで表示するラベル名（例: 'テーブル名', 'WHERE条件'）")
    value: str = Field(..., description="初期値としてセットされる文字列")
    key: str = Field(..., description="システム内で識別するためのキー（例: 'table', 'where_clause'）")


class AnalysisResponse(BaseModel):
    """自然言語解析APIのレスポンス用モデル"""
    type: str = Field(..., description="判定されたSQLテンプレートの種別（例: 'select', 'left_join'）")
    title: str = Field(..., description="UIに表示するテンプレートのタイトル")
    icon: str = Field(..., description="UIに表示するアイコン文字")
    description: str = Field(..., description="テンプレートの簡単な説明文")
    sql: str = Field(..., description="画面表示用のプレビューSQL")
    parts: list[TemplatePart] = Field(..., description="UI描画に必要な入力パーツの配列")
    input: str = Field(..., description="ユーザーが最初に入力した元のテキスト")


class BuildRequest(BaseModel):
    """最終的なSQL構築APIのリクエスト用モデル"""
    type: str = Field(..., description="ベースとなるテンプレートの種別")
    # default_factory=dict を指定することで、空の辞書をデフォルト値として安全に扱えます
    parts: dict[str, str] = Field(default_factory=dict, description="ユーザーがUIで編集・確定したパーツのキーと値のペア")


class BuildResponse(BaseModel):
    """最終的なSQL構築APIのレスポンス用モデル"""
    sql: str = Field(..., description="実際にデータベースへ送信可能な完成済みSQL")
    type: str = Field(..., description="使用されたテンプレート種別")