# To(と)/sql_builder_v2/backend_sql_v2/server_Before.py
"""
SQL Builder v2 - Python Backend
FastAPI + SQLite のローカルAPIサーバー
ポート: 8765 (Electronから起動される)

v2変更点:
  - Flask版の自然言語解析ロジック（正規表現・テンプレートビルダー）を移植
  - /analyze, /templates, /build エンドポイントを追加
"""

import re
import sqlite3
import time
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import urllib.parse
# ─── App Setup ───────────────────────────────────────────────────────────────

app = FastAPI(title="SQL Builder API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "file://"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Data Models ─────────────────────────────────────────────────────────────

# ── SQL実行系 ──────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    sql: str
    db_path: str        # ユーザーが選択したDBファイルパス
    params: list = []   # プリペアドステートメント用パラメータ


class ExecuteResult(BaseModel):
    success: bool
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
    affected_rows: int  # INSERT/UPDATE/DELETE用
    error: Optional[str] = None
    query_id: str       # 履歴管理用ID


# ── 自然言語解析系 ─────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    """POST /analyze のリクエストボディ"""
    text: str           # 解析対象の日本語テキスト


class TemplatePart(BaseModel):
    """SQLテンプレートの編集可能パーツ（UIのフォームフィールドに対応）"""
    label: str          # 表示ラベル（例: "左テーブル"）
    value: str          # 初期値
    key: str            # フィールドキー（例: "left_table"）


class AnalysisResponse(BaseModel):
    """POST /analyze のレスポンス"""
    type: str               # テンプレート種別（"select", "left_join" など）
    title: str              # 表示タイトル（例: "LEFT JOIN"）
    icon: str               # アイコン文字
    description: str        # 説明文
    sql: str                # 生成されたSQLテンプレート文字列
    parts: list[TemplatePart]   # UIで編集可能なパーツ一覧
    input: str              # 元の入力テキスト（エコーバック）


class BuildRequest(BaseModel):
    """POST /build のリクエストボディ（ユーザーがパーツを編集してSQL再構築）"""
    type: str
    parts: dict[str, str] = {}


class BuildResponse(BaseModel):
    sql: str
    type: str


# ─── Natural Language → SQL Template Parser ──────────────────────────────────
#
# Flask版 server.py から移植。
# パターン定義 → detect_template_type() → extract_entities() → build_sql_template()
# の順で処理し、AnalysisResponse を組み立てる。

# 副問い合わせを示す日本語パターン
SUBQUERY_PATTERNS = [
    r'の中で.*より(高い|安い|大きい|小さい|多い|少ない)',
    r'の中で.*な.*は',
    r'(?:where|中で).*(?:select|選ぶ|取得)',
    r'([^\s]+)の中で.*([^\s]+)は(何|どんな|どれ)',
]

# JOIN種別ごとの日本語パターン
JOIN_PATTERNS = {
    'inner': [r'と.*を.*結合', r'両方に.*ある', r'一致する.*と'],
    'left':  [r'左.*結合', r'.*を基準に.*含む', r'全て.*と.*あれば', r'のすべてと'],
    'right': [r'右.*結合', r'.*右側', r'.*を基準に.*左'],
    'cross': [r'全組み合わせ', r'直積'],
}

# DML・集計系の日本語パターン
INSERT_PATTERNS = [r'追加', r'挿入', r'新しく.*登録', r'insert', r'入れる']
UPDATE_PATTERNS = [r'更新', r'変更', r'修正', r'update']
DELETE_PATTERNS = [r'削除', r'消す', r'除く', r'delete']
GROUPBY_PATTERNS = [r'グループ', r'集計', r'合計', r'平均', r'count', r'sum', r'avg', r'最大', r'最小']


def detect_template_type(text: str) -> str:
    """
    日本語テキストを正規表現で走査し、最適なSQLテンプレート種別を返す。
    優先順位: subquery > left_join > right_join > inner_join >
              insert > update > delete > group_by > select (デフォルト)
    """
    text_lower = text.lower()

    for pat in SUBQUERY_PATTERNS:
        if re.search(pat, text):
            return 'subquery'

    for pat in JOIN_PATTERNS['left']:
        if re.search(pat, text):
            return 'left_join'

    for pat in JOIN_PATTERNS['right']:
        if re.search(pat, text):
            return 'right_join'

    for pat in JOIN_PATTERNS['inner']:
        if re.search(pat, text):
            return 'inner_join'

    for pat in INSERT_PATTERNS:
        if re.search(pat, text_lower):
            return 'insert'

    for pat in UPDATE_PATTERNS:
        if re.search(pat, text_lower):
            return 'update'

    for pat in DELETE_PATTERNS:
        if re.search(pat, text_lower):
            return 'delete'

    for pat in GROUPBY_PATTERNS:
        if re.search(pat, text_lower):
            return 'group_by'

    return 'select'


def extract_entities(text: str) -> dict:
    """
    日本語テキストからテーブル名・カラム名・WHERE条件を抽出して返す。

    Returns:
        {
            'tables':     list[str],  # 推定テーブル名
            'columns':    list[str],  # 推定カラム名
            'conditions': list[str],  # WHERE条件文字列
            'values':     list[str],  # INSERT用の値（現在は予約）
        }
    """
    entities: dict = {'tables': [], 'columns': [], 'conditions': [], 'values': []}

    # 価格・数値条件（例: "1000円より高い", "500円以上"）
    num_match = re.search(r'(\d+)円(より|以上|以下|未満)(高い|安い|大きい|小さい)?', text)
    if num_match:
        val      = num_match.group(1)
        op_word  = num_match.group(2) + (num_match.group(3) or '')
        # デフォルトは '>'。「より安い/小さい」や「未満」は '<'
        if '以上' in op_word:
            op = '>='
        elif '以下' in op_word:
            op = '<='
        elif '未満' in op_word or 'より安' in op_word or 'より小' in op_word:
            op = '<'
        else:
            op = '>'
        entities['conditions'].append(f'price {op} {val}')

    # 「〇〇の中で」「〇〇テーブル」「〇〇表」からテーブル名候補を抽出
    table_hints = re.findall(r'([ぁ-んァ-ン一-龥a-zA-Z]+)(?:の中で|テーブル|表)', text)
    entities['tables'] = list(dict.fromkeys(table_hints))  # 順序を保ちつつ重複除去

    # 意味的カラムのマッピング
    if '名前' in text or '名称' in text:
        entities['columns'].append('name')
    if '価格' in text or '値段' in text or '金額' in text:
        entities['columns'].append('price')

    return entities


def build_sql_template(template_type: str, text: str, entities: dict) -> dict:
    """
    テンプレート種別とエンティティ情報からSQLテンプレートとUIパーツを生成する。

    Returns:
        Flask版と同じキー構成の dict
        {title, icon, description, sql, parts: [{label, value, key}]}
    """
    tables = entities['tables'] or ['テーブルA', 'テーブルB']
    t1  = tables[0]
    t2  = tables[1] if len(tables) > 1 else tables[0] + '2'
    cols = ', '.join(entities['columns']) if entities['columns'] else '*'
    cond = entities['conditions'][0] if entities['conditions'] else 'カラム = 値'

    # サブクエリの結合キーに使うカラム名（条件の最初の単語、なければ "id"）
    cond_col = cond.split()[0] if entities['conditions'] else 'id'

    templates: dict[str, dict] = {
        'subquery': {
            'title': '副問い合わせ (Subquery)',
            'icon': '◎',
            'description': f'「{text}」→ 外側クエリの条件に内側クエリの結果を使います',
            'sql': (
                f"SELECT {cols}\n"
                f"FROM {t1}\n"
                f"WHERE {cond_col} IN (\n"
                f"    SELECT {cond_col}\n"
                f"    FROM {t1}\n"
                f"    WHERE {cond}\n"
                f");"
            ),
            'parts': [
                {'label': '外側テーブル',  'value': t1,       'key': 'outer_table'},
                {'label': '取得カラム',    'value': cols,      'key': 'select_cols'},
                {'label': '内側テーブル',  'value': t1,       'key': 'inner_table'},
                {'label': '条件',          'value': cond,      'key': 'condition'},
            ],
        },
        'left_join': {
            'title': 'LEFT JOIN',
            'icon': '⊂',
            'description': '左テーブルを基準に右テーブルを結合（右に一致がなくてもNULLで返す）',
            'sql': (
                f"SELECT a.*, b.*\n"
                f"FROM {t1} AS a\n"
                f"LEFT JOIN {t2} AS b\n"
                f"  ON a.id = b.{t1.lower()}_id\n"
                f"WHERE a.{cond};"
            ),
            'parts': [
                {'label': '左テーブル',  'value': t1,                        'key': 'left_table'},
                {'label': '右テーブル',  'value': t2,                        'key': 'right_table'},
                {'label': '結合条件',    'value': f'a.id = b.{t1.lower()}_id', 'key': 'on_clause'},
                {'label': 'WHERE条件',   'value': cond,                      'key': 'where_clause'},
            ],
        },
        'right_join': {
            'title': 'RIGHT JOIN',
            'icon': '⊃',
            'description': '右テーブルを基準に左テーブルを結合',
            'sql': (
                f"SELECT a.*, b.*\n"
                f"FROM {t1} AS a\n"
                f"RIGHT JOIN {t2} AS b\n"
                f"  ON a.id = b.{t1.lower()}_id;"
            ),
            'parts': [
                {'label': '左テーブル',  'value': t1,                        'key': 'left_table'},
                {'label': '右テーブル',  'value': t2,                        'key': 'right_table'},
                {'label': '結合条件',    'value': f'a.id = b.{t1.lower()}_id', 'key': 'on_clause'},
            ],
        },
        'inner_join': {
            'title': 'INNER JOIN',
            'icon': '∩',
            'description': '両テーブルで一致する行だけを返す',
            'sql': (
                f"SELECT a.*, b.*\n"
                f"FROM {t1} AS a\n"
                f"INNER JOIN {t2} AS b\n"
                f"  ON a.id = b.{t1.lower()}_id\n"
                f"WHERE {cond};"
            ),
            'parts': [
                {'label': '左テーブル',  'value': t1,                        'key': 'left_table'},
                {'label': '右テーブル',  'value': t2,                        'key': 'right_table'},
                {'label': '結合条件',    'value': f'a.id = b.{t1.lower()}_id', 'key': 'on_clause'},
                {'label': 'WHERE条件',   'value': cond,                      'key': 'where_clause'},
            ],
        },
        'insert': {
            'title': 'INSERT',
            'icon': '+',
            'description': 'テーブルに新しい行を追加する',
            'sql': (
                f"INSERT INTO {t1} (カラム1, カラム2, カラム3)\n"
                f"VALUES (値1, 値2, 値3);"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,               'key': 'table'},
                {'label': 'カラム',     'value': 'カラム1, カラム2', 'key': 'columns'},
                {'label': '値',         'value': '値1, 値2',        'key': 'values'},
            ],
        },
        'update': {
            'title': 'UPDATE',
            'icon': '↻',
            'description': '既存の行を更新する',
            'sql': (
                f"UPDATE {t1}\n"
                f"SET カラム1 = 新しい値\n"
                f"WHERE {cond};"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,             'key': 'table'},
                {'label': 'SET句',      'value': 'カラム1 = 新しい値', 'key': 'set_clause'},
                {'label': 'WHERE条件',  'value': cond,           'key': 'where_clause'},
            ],
        },
        'delete': {
            'title': 'DELETE',
            'icon': '✕',
            'description': '条件に一致する行を削除する',
            'sql': (
                f"DELETE FROM {t1}\n"
                f"WHERE {cond};"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,   'key': 'table'},
                {'label': 'WHERE条件',  'value': cond, 'key': 'where_clause'},
            ],
        },
        'group_by': {
            'title': 'GROUP BY / 集計',
            'icon': '≡',
            'description': 'グループ単位での集計クエリ',
            'sql': (
                f"SELECT カテゴリ, COUNT(*) AS 件数, AVG(price) AS 平均価格\n"
                f"FROM {t1}\n"
                f"GROUP BY カテゴリ\n"
                f"HAVING COUNT(*) > 1\n"
                f"ORDER BY 件数 DESC;"
            ),
            'parts': [
                {'label': 'テーブル名',   'value': t1,                   'key': 'table'},
                {'label': 'グループカラム', 'value': 'カテゴリ',          'key': 'group_col'},
                {'label': '集計関数',     'value': 'COUNT(*), AVG(price)', 'key': 'agg_funcs'},
                {'label': 'HAVING条件',   'value': 'COUNT(*) > 1',       'key': 'having'},
            ],
        },
        'select': {
            'title': 'SELECT',
            'icon': '▷',
            'description': '基本的なデータ取得クエリ',
            'sql': (
                f"SELECT {cols}\n"
                f"FROM {t1}\n"
                f"WHERE {cond}\n"
                f"ORDER BY id\n"
                f"LIMIT 100;"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,   'key': 'table'},
                {'label': '取得カラム', 'value': cols,  'key': 'select_cols'},
                {'label': 'WHERE条件',  'value': cond, 'key': 'where_clause'},
            ],
        },
    }

    return templates.get(template_type, templates['select'])


# ─── SQLite Manager ──────────────────────────────────────────────────────────

HISTORY_DB_PATH = Path.home() / ".sql_builder" / "history.sqlite"
HISTORY_DB_PATH.parent.mkdir(exist_ok=True)


def init_history_db():
    """クエリ履歴テーブルを初期化"""
    with sqlite3.connect(HISTORY_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id          TEXT PRIMARY KEY,
                sql         TEXT NOT NULL,
                db_path     TEXT NOT NULL,
                success     INTEGER NOT NULL,
                row_count   INTEGER,
                error       TEXT,
                executed_at REAL NOT NULL
            )
        """)


# @contextmanager
# def get_user_db(db_path: str):
#     """ユーザーのSQLiteファイルへの安全な接続"""
#     path = Path(db_path)
#     if not path.exists():
#         raise FileNotFoundError(f"DB not found: {db_path}")
#     if path.suffix not in (".sqlite", ".db", ".sqlite3"):
#         raise ValueError(f"Unsupported file type: {path.suffix}")

#     conn = sqlite3.connect(str(path), check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     conn.execute("PRAGMA journal_mode=WAL")
#     conn.execute("PRAGMA foreign_keys=ON")
#     try:
#         yield conn
#     finally:
#         conn.close()


def save_to_history(query_id: str, sql: str, db_path: str, result: ExecuteResult):
    """実行結果を履歴DBに保存"""
    try:
        with sqlite3.connect(HISTORY_DB_PATH) as conn:
            conn.execute(
                """INSERT INTO query_history
                   (id, sql, db_path, success, row_count, error, executed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (query_id, sql, db_path, int(result.success),
                 result.row_count, result.error, time.time())
            )
    except Exception:
        pass


# ─── API Endpoints ───────────────────────────────────────────────────────────

# ── 自然言語解析 ────────────────────────────────────────────────────────────

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """
    日本語テキストを受け取り、最適なSQLテンプレートを推定して返す。

    処理フロー:
      1. detect_template_type()  → テンプレート種別を判定
      2. extract_entities()      → テーブル名・カラム名・条件を抽出
      3. build_sql_template()    → SQLとUIパーツを生成
      4. AnalysisResponse へ変換して返却
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="テキストが空です")

    template_type = detect_template_type(text)
    entities      = extract_entities(text)
    raw           = build_sql_template(template_type, text, entities)

    # dict[str, str] の parts を TemplatePart モデルに変換
    parts = [TemplatePart(**p) for p in raw["parts"]]

    return AnalysisResponse(
        type        = template_type,
        title       = raw["title"],
        icon        = raw["icon"],
        description = raw["description"],
        sql         = raw["sql"],
        parts       = parts,
        input       = text,
    )


@app.get("/templates", response_model=list[AnalysisResponse])
async def get_all_templates():
    """
    全テンプレート種別のサンプルを一覧で返す（UIのギャラリー表示用）。
    """
    all_types = [
        'subquery', 'left_join', 'right_join', 'inner_join',
        'insert', 'update', 'delete', 'group_by', 'select',
    ]
    dummy_entities = {'tables': ['table_a', 'table_b'], 'columns': [], 'conditions': []}
    results = []
    for t in all_types:
        raw   = build_sql_template(t, '', dummy_entities)
        parts = [TemplatePart(**p) for p in raw["parts"]]
        results.append(AnalysisResponse(
            type        = t,
            title       = raw["title"],
            icon        = raw["icon"],
            description = raw["description"],
            sql         = raw["sql"],
            parts       = parts,
            input       = '',
        ))
    return results


@app.post("/build", response_model=BuildResponse)
async def build_custom(request: BuildRequest):
    """
    ユーザーが編集したパーツ（テーブル名・条件など）からSQLを再構築して返す。
    """
    t     = request.type
    parts = request.parts

    if t == 'subquery':
        cols     = parts.get('select_cols', '*')
        key_col  = cols.split(',')[0].strip()
        sql = (
            f"SELECT {cols}\n"
            f"FROM {parts.get('outer_table', 'table_a')}\n"
            f"WHERE {key_col} IN (\n"
            f"    SELECT {key_col}\n"
            f"    FROM {parts.get('inner_table', 'table_a')}\n"
            f"    WHERE {parts.get('condition', '条件')}\n"
            f");"
        )
    elif t in ('left_join', 'right_join', 'inner_join'):
        join_kw = {
            'left_join':  'LEFT JOIN',
            'right_join': 'RIGHT JOIN',
            'inner_join': 'INNER JOIN',
        }[t]
        where_clause = parts.get('where_clause', '')
        where = f"\nWHERE {where_clause}" if where_clause else ''
        sql = (
            f"SELECT a.*, b.*\n"
            f"FROM {parts.get('left_table', 'table_a')} AS a\n"
            f"{join_kw} {parts.get('right_table', 'table_b')} AS b\n"
            f"  ON {parts.get('on_clause', 'a.id = b.table_a_id')}{where};"
        )
    elif t == 'insert':
        sql = (
            f"INSERT INTO {parts.get('table', 'table_a')} ({parts.get('columns', 'col1, col2')})\n"
            f"VALUES ({parts.get('values', 'val1, val2')});"
        )
    elif t == 'update':
        sql = (
            f"UPDATE {parts.get('table', 'table_a')}\n"
            f"SET {parts.get('set_clause', 'col = value')}\n"
            f"WHERE {parts.get('where_clause', '条件')};"
        )
    elif t == 'delete':
        sql = (
            f"DELETE FROM {parts.get('table', 'table_a')}\n"
            f"WHERE {parts.get('where_clause', '条件')};"
        )
    elif t == 'group_by':
        sql = (
            f"SELECT {parts.get('group_col', 'category')}, COUNT(*) AS 件数\n"
            f"FROM {parts.get('table', 'table_a')}\n"
            f"GROUP BY {parts.get('group_col', 'category')}\n"
            f"HAVING {parts.get('having', 'COUNT(*) > 0')};"
        )
    else:  # select (default)
        sql = (
            f"SELECT {parts.get('select_cols', '*')}\n"
            f"FROM {parts.get('table', 'table_a')}\n"
            f"WHERE {parts.get('where_clause', '条件')};"
        )

    return BuildResponse(sql=sql, type=t)


# ── SQL実行 ─────────────────────────────────────────────────────────────────

@app.post("/execute", response_model=ExecuteResult)
async def execute_sql(req: ExecuteRequest):
    """
    SQLを実行してJSONで結果を返す。
    SELECT → rows返却 / INSERT・UPDATE・DELETE → affected_rows返却
    """
    query_id = str(uuid.uuid4())[:8]
    start    = time.perf_counter()

    try:
        with get_user_db(req.db_path) as conn:
            cursor     = conn.execute(req.sql, req.params)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if cursor.description:
                # SELECT系
                columns = [desc[0] for desc in cursor.description]
                rows    = [list(row) for row in cursor.fetchall()]
                result  = ExecuteResult(
                    success=True, columns=columns, rows=rows,
                    row_count=len(rows), execution_time_ms=round(elapsed_ms, 2),
                    affected_rows=0, query_id=query_id,
                )
            else:
                # DML系
                conn.commit()
                result = ExecuteResult(
                    success=True, columns=[], rows=[],
                    row_count=0, execution_time_ms=round(elapsed_ms, 2),
                    affected_rows=cursor.rowcount, query_id=query_id,
                )

    except FileNotFoundError as e:
        result = ExecuteResult(
            success=False, columns=[], rows=[], row_count=0,
            execution_time_ms=0, affected_rows=0,
            error=f"DB file not found: {e}", query_id=query_id,
        )
    except sqlite3.OperationalError as e:
        result = ExecuteResult(
            success=False, columns=[], rows=[], row_count=0,
            execution_time_ms=0, affected_rows=0,
            error=f"SQL Error: {e}", query_id=query_id,
        )
    except Exception:
        result = ExecuteResult(
            success=False, columns=[], rows=[], row_count=0,
            execution_time_ms=0, affected_rows=0,
            error=f"Unexpected error: {traceback.format_exc()}", query_id=query_id,
        )

    save_to_history(query_id, req.sql, req.db_path, result)
    return result


@app.get("/history")
async def get_history(limit: int = 50):
    """クエリ実行履歴を新しい順に返す"""
    with sqlite3.connect(HISTORY_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM query_history ORDER BY executed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/tables")
async def get_tables(db_path: str):
    """指定DBのテーブル一覧とスキーマを返す"""
    with get_user_db(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        result = {}
        for (table_name,) in tables:
            cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            result[table_name] = [
                {"name": c[1], "type": c[2], "pk": bool(c[5])}
                for c in cols
            ]
        return result


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# 接続関数に read_only フラグを追加
@contextmanager
def get_user_db(db_path: str, read_only: bool = False):
    """ユーザーのSQLiteファイルへの安全な接続（統一版）"""

    path = Path(db_path)

    if not path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    if path.suffix not in (".sqlite", ".db", ".sqlite3"):
        raise ValueError(f"Unsupported file type: {path.suffix}")

    # URI形式に変換
    db_uri = f"file:{urllib.parse.quote(str(path))}"

    if read_only:
        db_uri += "?mode=ro"

    conn = sqlite3.connect(db_uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        yield conn
    finally:
        conn.close()
        
@app.get("/export/json")
async def export_to_json(db_path: str):
    """DBの全テーブルデータをJSONとして返す"""
    result = {}
    try:
        with get_user_db(db_path, read_only=True) as conn:
            # 1. テーブル一覧を取得
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            
            for (table_name,) in tables:
                # 2. 各テーブルの全データを取得
                cursor = conn.execute(f"SELECT * FROM {table_name}")
                # 列名を取得
                columns = [col[0] for col in cursor.description]
                # データを辞書のリストに変換
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                result[table_name] = rows
                
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    init_history_db()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")