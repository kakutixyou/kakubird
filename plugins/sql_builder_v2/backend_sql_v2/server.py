#実は普通に使える　
# # ===
# # SQL Builder Professional API Server
# # ===
# # この server.py は単なる起動ファイルではなく、
# # 「AI Runtime Gateway」として機能する。
# #
# # 主な役割:
# # - Router統合
# # - Provider統合
# # - Tool統合
# # - System Discovery
# # - Health監視
# # - Electron / React UIとの接続
# # - AI Runtimeの入口
# #
# # 接続先:
# # frontend(AiChatPanel.jsx)
# # ↓
# # fetch("/api/...")
# # ↓
# # server.py
# # ↓
# # Router
# # ↓
# # Service
# # ↓
# # AI / DB / Tools
# # ===

# import os
# import uvicorn

# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# # ===
# # Router Import
# # ===

# from api import routes_chat
# from api import routes_nlp
# from api import routes_execute
# from api import routes_history
# from api import routes_auth
# from api import routes_system

# # ===
# # DB Init
# # ===

# from db.history_db import init_history_db

# # ===
# # Environment
# # ===

# APP_NAME = "SQL Builder Professional API"
# APP_VERSION = "3.0.0"

# HOST = os.getenv("HOST", "127.0.0.1")
# PORT = int(os.getenv("PORT", "8765"))

# # ===
# # AI Provider Registry
# # ===
# # 将来的に:
# # - OpenAI
# # - Gemini
# # - Claude
# # - Ollama
# # を統一管理する
# # ===

# AVAILABLE_PROVIDERS = {
#     "claude": {
#         "enabled": True,
#         "local": False
#     },
#     "gemini": {
#         "enabled": True,
#         "local": False
#     },
#     "ollama": {
#         "enabled": False,
#         "local": True
#     }
# }

# # ===
# # Tool Registry
# # ===
# # AIが使える機能一覧
# # 将来的にAI Tool Callingへ発展可能
# # ===

# AVAILABLE_TOOLS = {
#     "sql.execute": {
#         "description": "SQLを実行します"
#     },
#     "db.schema": {
#         "description": "DB構造を取得します"
#     },
#     "history.search": {
#         "description": "履歴を検索します"
#     },
#     "system.services": {
#         "description": "利用可能API一覧"
#     }
# }

# # ===
# # Router Registry
# # ===
# # APIを追加する時はここへ登録
# # ===

# ROUTERS = [
#     {
#         "router": routes_chat.router,
#         "prefix": "/api",
#         "tags": ["Chat"]
#     },
#     {
#         "router": routes_nlp.router,
#         "prefix": "/api/nlp",
#         "tags": ["NLP"]
#     },
#     {
#         "router": routes_execute.router,
#         "prefix": "/api/sql",
#         "tags": ["Execution"]
#     },
#     {
#         "router": routes_history.router,
#         "prefix": "/api/history",
#         "tags": ["History"]
#     },
#     {
#         "router": routes_auth.router,
#         "prefix": "/api/auth",
#         "tags": ["Auth"]
#     },
#     {
#         "router": routes_system.router,
#         "prefix": "/api/system",
#         "tags": ["System"]
#     }
# ]

# # ===
# # Lifespan
# # ===
# # サーバー起動時処理
# # ===

# @asynccontextmanager
# async def lifespan(app: FastAPI):

#     print("=====")
#     print("Initializing SQL Builder Runtime...")
#     print("=====")

#     # DB初期化
#     init_history_db()

#     # Provider表示
#     print("\n[Providers]")
#     for name, info in AVAILABLE_PROVIDERS.items():
#         print(f"- {name} | enabled={info['enabled']}")

#     # Tool表示
#     print("\n[Tools]")
#     for tool_name in AVAILABLE_TOOLS.keys():
#         print(f"- {tool_name}")

#     # Router表示
#     print("\n[Routers]")
#     for route in ROUTERS:
#         print(f"- {route['prefix']}")

#     print("\nServer Ready.")
#     print("=====")

#     yield

#     print("\nShutting down server...")

# # ===
# # App Create
# # ===

# app = FastAPI(
#     title=APP_NAME,
#     description="AI Runtime Gateway for Electron + React + SQL",
#     version=APP_VERSION,
#     lifespan=lifespan
# )

# # ===
# # CORS
# # ===
# # Electron / React接続用
# # ===

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ===
# # Router Register
# # ===

# for route in ROUTERS:
#     app.include_router(
#         route["router"],
#         prefix=route["prefix"],
#         tags=route["tags"]
#     )

# # ===
# # Root
# # ===

# @app.get("/")
# async def root():
#     return {
#         "name": APP_NAME,
#         "version": APP_VERSION,
#         "status": "running"
#     }

# # ===
# # Health Check
# # ===

# @app.get("/health", tags=["System"])
# async def health_check():
#     return {
#         "status": "healthy",
#         "version": APP_VERSION
#     }

# # ===
# # Provider Discovery
# # ===
# # AiChatPanel.jsx が Provider一覧を取得可能
# # ===

# @app.get("/api/system/providers")
# async def get_providers():
#     return {
#         "providers": AVAILABLE_PROVIDERS
#     }

# # ===
# # Tool Discovery
# # ===
# # AI利用可能ツール一覧
# # ===

# @app.get("/api/system/tools")
# async def get_tools():
#     return {
#         "tools": AVAILABLE_TOOLS
#     }

# # ===
# # Full System Discovery
# # ===
# # React/Electron側が
# # 動的UI生成できるようにする
# # ===

# @app.get("/api/system/runtime")
# async def runtime_info():
#     return {
#         "app": APP_NAME,
#         "version": APP_VERSION,

#         "providers": AVAILABLE_PROVIDERS,
#         "tools": AVAILABLE_TOOLS,

#         "routes": [
#             {
#                 "path": route["prefix"],
#                 "tags": route["tags"]
#             }
#             for route in ROUTERS
#         ]
#     }

# # ===
# # AI Action Example
# # ===
# # 将来的に:
# # - Tool Calling
# # - Action Button
# # - Dynamic UI
# # に対応可能
# # ===

# @app.get("/api/system/action-example")
# async def action_example():
#     return {
#         "reply": "DBをダウンロードできます",

#         "actions": [
#             {
#                 "type": "download",
#                 "label": "Download Database",
#                 "endpoint": "/api/system/download-db/test.db"
#             }
#         ]
#     }

# # ===
# # Startup
# # ===

# if __name__ == "__main__":

#     uvicorn.run(
#         "server:app",
#         host=HOST,
#         port=PORT,
#         reload=False,
#         log_level="info"
#     )