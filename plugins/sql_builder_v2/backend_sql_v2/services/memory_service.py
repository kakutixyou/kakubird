import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db/memory.db"

# 🔹 データベースの初期化（起動時に一度だけ呼ぶと便利です）
async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                type TEXT,          -- task / knowledge / context
                content TEXT,
                priority INTEGER,
                status TEXT DEFAULT 'pending', -- 🆕 進捗管理用カラム
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()

# 🔹 タスク保存（複数タスクの一括保存）
async def save_tasks(user_id: str, tasks: list):
    # 🆕 async with を使うことで、エラー時も自動で安全にクローズされる
    async with aiosqlite.connect(DB_PATH) as db:
        for t in tasks:
            await db.execute("""
                INSERT INTO memory (user_id, type, content, priority)
                VALUES (?, 'task', ?, ?)
            """, (user_id, t["task"], t["priority"]))
        await db.commit()

# 🔹 最新の未完了タスクを取得
async def get_tasks(user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # 🆕 status が 'pending'（未完了）のものだけを取得
        cursor = await db.execute("""
            SELECT id, content, priority
            FROM memory
            WHERE user_id = ? AND type = 'task' AND status = 'pending'
            ORDER BY priority ASC
            LIMIT 3
        """, (user_id,))
        
        rows = await cursor.fetchall()
        
    return [{"id": r[0], "task": r[1], "priority": r[2]} for r in rows]

# 🔹 タスクを「完了」にする機能（おまけ）
async def complete_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE memory SET status = 'completed' WHERE id = ?
        """, (task_id,))
        await db.commit()