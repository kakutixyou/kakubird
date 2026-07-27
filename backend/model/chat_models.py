from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
# 型が原因で動かないエラーを解決するためのpydanticのBaseModelを使用したデータモデル定義


class ChatMessage(BaseModel):
    """チャット履歴の1メッセージ"""

    role: str
    content: str


class ChatRequest(BaseModel):
    """React/Electronから受け取る入力"""

    message: str = Field(..., description="ユーザー入力")

    mode: str = "custom"

    image_base64: Optional[str] = None

    session_id: Optional[str] = None

    history: List[ChatMessage] = Field(default_factory=list)

    force_json_ui: bool = False

    db_type: str = "sqlite"

    db_path: str = "backend/history.db"

    conn_str: str = ""

    # KnowledgeServiceが組み立てる知識
    world_knowledge: Dict[str, Any] = Field(default_factory=dict)


class OrchestratorResponse(BaseModel):
    """Orchestratorから返る共通レスポンス"""

    status: str = "success"

    response_type: str

    content: Any


class ChatResponse(BaseModel):
    """旧API互換"""

    reply: str

    source: str = "custom"


class HistoryItem(BaseModel):
    role: str
    content: str


class NoteItem(BaseModel):
    content: str


class TaskItem(BaseModel):
    title: str
    status: str
    priority: int


class FileItem(BaseModel):
    path: str
    language: str
    size: int
    
class ChatContext(BaseModel):
    """
    ChatServiceが組み立てるAI実行用コンテキスト
    """

    request: ChatRequest

    world_knowledge: Dict[str, Any] = Field(default_factory=dict)

    memory: Dict[str, Any] = Field(default_factory=dict)

    plugins: Dict[str, Any] = Field(default_factory=dict)

    system_prompt: str = ""

    active_handler: Optional[str] = None
    
#     ただし、「chat_models.pyを作れば全部のエラーが消える」わけではありません。 エラーの原因が「型情報がないこと」なら消えます。

# あなたの今のケースを例にすると、

# async def execute_chat(
#     request: BaseModel,
#     background_tasks: BackgroundTasks
# ):

# ここでPylanceは

# request は BaseModel

# としか分かりません。

# だから

# request.message

# を見ると

# BaseModelにmessageなんてありません

# と警告します。

# 同じように

# request.world_knowledge = world_knowledge

# を見ると

# BaseModelにworld_knowledgeなんてありません

# になります。

# chat_models.pyを作る意味

# 例えば

# class ChatRequest(BaseModel):
#     message: str
#     mode: str = "custom"
#     world_knowledge: dict = Field(default_factory=dict)

# を作って

# from api.models.chat_models import ChatRequest

# そして

# async def execute_chat(
#     request: ChatRequest,
#     background_tasks: BackgroundTasks
# ):

# にすると、

# Pylanceは

# request.message

# を見て

# ChatRequestにはmessageがある

# と判断できます。

# さらに

# request.world_knowledge

# も

# ChatRequestにはworld_knowledgeがある

# と判断できます。

# つまり

# Pylanceに「このオブジェクトはこういう形です」と教えるファイルになります。

# 逆に消えないエラーもある

# 例えば

# request.user_name

# と書いたのに

# class ChatRequest(BaseModel):
#     message: str

# しか定義していなければ、

# 属性 user_name がありません

# というエラーは残ります。

# これはPylanceが正しいです。