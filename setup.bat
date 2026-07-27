pip show psycopg2-binary > nul 2>&1
pip install fastapi uvicorn python-dotenv httpx
npm install
if errorlevel 1 (
    echo psycopg2-binary をインストールします...
    pip install psycopg2-binary
)

python backend/api/ai_server.py