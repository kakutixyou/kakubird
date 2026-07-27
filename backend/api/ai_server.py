# =========================================================

# ai_server.py

# Custom AI Unified Backend Server

# FastAPI + Memory + Plugin + RAG + Ollama

# =========================================================
print("AI_SERVER_FILE_LOADED")
import os
import sys
import io
import traceback

import uvicorn

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from memory_manager import load_json, save_json

# =========================================================

# 1. Base Path

# =========================================================
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ROOT_DIR = os.path.dirname(BASE_DIR)

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BASE_DIR)
from api.routes_memory import router as memory_router

SRC_DIR = os.path.join(BASE_DIR, "src")

PLUGIN_DIR = os.path.join(ROOT_DIR, "plugins")

# =========================================================

# 2. sys.path

# =========================================================

PATHS_TO_ADD = [
ROOT_DIR,
BASE_DIR,
SRC_DIR,
PLUGIN_DIR
]

for path in PATHS_TO_ADD:


    if path not in sys.path:
        sys.path.append(path)


# =========================================================

# 3. UTF-8 Fix

# =========================================================

sys.stdout = io.TextIOWrapper(
sys.stdout.buffer,
encoding="utf-8"
)

sys.stderr = io.TextIOWrapper(
sys.stderr.buffer,
encoding="utf-8"
)

# =========================================================

# 4. ENV

# =========================================================

load_dotenv()

OLLAMA_BASE_URL = os.getenv(
"OLLAMA_BASE_URL",
"http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
"OLLAMA_MODEL",
"gemma3"
)

# =========================================================

# 5. Directory Init

# =========================================================

AI_MEMORY_DIR = os.path.join(
BASE_DIR,
".ai_memory"
)

os.makedirs(
AI_MEMORY_DIR,
exist_ok=True
)

# =========================================================

# 6. FastAPI Init

# =========================================================

app = FastAPI(
title="Custom AI Server",
version="3.0"
)

# =========================================================

# 7. CORS

# =========================================================

app.add_middleware(
CORSMiddleware,


allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],


)

# =========================================================

# 8. Boot Logs

# =========================================================

print("=================================================")
print("🚀 AI Server Boot")
print("=================================================")

print(f"📂 ROOT_DIR   : {ROOT_DIR}")
print(f"📂 BASE_DIR   : {BASE_DIR}")
print(f"📂 SRC_DIR    : {SRC_DIR}")
print(f"📂 PLUGIN_DIR : {PLUGIN_DIR}")

print("-------------------------------------------------")

print(f"🤖 OLLAMA_MODEL : {OLLAMA_MODEL}")
print(f"🌐 OLLAMA_URL   : {OLLAMA_BASE_URL}")

print("=================================================")

# =========================================================

# 9. Safe Router Loader

# =========================================================

def safe_include_router(
import_path,
router_name="router"
):
# """
# router import failure isolation


# plugin / route failure should NOT
# crash entire backend
# """

    try:

        print(f"[LOAD] {import_path}")

        module = __import__(
            import_path,
            fromlist=[router_name]
        )

        router = getattr(
            module,
            router_name
        )

        app.include_router(router)

        print(f"[OK] {import_path}")

    except Exception as e:

        print(f"[ERROR] {import_path}")

        print(str(e))

        traceback.print_exc()


# =========================================================

# 10. Router Registration

# =========================================================

safe_include_router("backend.api.routes_chat")

safe_include_router("backend.api.routes_system")

safe_include_router("backend.api.routes_memory")

safe_include_router("backend.api.routes_sql")

safe_include_router("backend.api.routes_css")

safe_include_router("backend.api.routes_note")

safe_include_router("backend.api.routes_project")

# =========================================================

# 11. Health Check

# =========================================================

@app.get("/")
async def root():


 return {

    "status": "ok",

    "message": (
        "Custom AI Server Running"
    ),

    "ollama_model": OLLAMA_MODEL
}


# =========================================================

# 12. Debug Routes

# =========================================================

@app.get("/api/system/ping")
async def ping():


 return {
    "status": "alive"
}


# =========================================================

# 13. Startup

# =========================================================


if __name__ == "__main__":
    print("🚀 Starting Uvicorn")
    uvicorn.run(
        "backend.api.ai_server:app",
        host="127.0.0.1",
        port=8765,
        reload=False   # ← Windowsではreload=Falseが安全
    )
print("🚀 Starting Uvicorn")

