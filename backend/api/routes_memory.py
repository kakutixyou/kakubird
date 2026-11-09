# backend/api/routes_memory.py

import os
import uuid
import shutil
import tempfile
import zipfile
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel

from plugins.ai_memory.code_chunker import CodeChunker
from plugins.ai_memory.embedding_service import EmbeddingService
from plugins.ai_memory.vector_store import InMemoryVectorStore, ChromaVectorStore
from plugins.ai_memory.workspace_scanner import WorkspaceScanner

from core.memory_manager import (
    get_chat_history,
    get_all_tasks,
    load_json as mm_load_json,
    save_json as mm_save_json,
    get_memory_overview,
    clear_all_memory,
    update_task_status,
)

router = APIRouter(
    prefix="/api/to",  # フロントの fetch('/api/to/...') に対応
    tags=["Memory & Workspace"]
)

# ===
# パス定数 & ディレクトリ構成
# ===

_BACKEND_DIR = Path(__file__).parent.parent
MEMORY_DIR   = _BACKEND_DIR / ".ai_memory"
AI_NOTES_FILE = MEMORY_DIR / "ai_notes.json"
USER_SIGNALS_FILE = MEMORY_DIR / "user_signals.json"
MEMORY_DIR.mkdir(exist_ok=True)

CHAT_HISTORY_DIR = MEMORY_DIR / "chat_history"
ZIP_HISTORY_FILE = MEMORY_DIR / "zip_history.json"
LONG_TERM_DIR    = MEMORY_DIR / "long_term"
PROJECT_DIR      = MEMORY_DIR / "projects"

# 高評価保存用ファイル
HIGH_RATED_FILE = MEMORY_DIR / "high_rated.json"

DB_SETS_DIR = (
    _BACKEND_DIR / "plugins" / "sql_builder_v2" / "src" / "data" / "db_sets"
)

# ===
# グローバルインスタンス
# ===
global_vector_store = InMemoryVectorStore()
embedder = EmbeddingService()
chunker  = CodeChunker()

# ===
# ローカルJSON helpers
# ===
def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"JSON保存エラー: {e}")


# ==========================================
# 🆕 偉人・YouTuberの「〜と彼/彼女なら言うと思うよ。」生成ヘルパー
# ==========================================
PERSONA_CLOSING_QUOTES: Dict[str, Dict[str, str]] = {
    "空海": {
        "pronoun": "彼",
        "quote": "一々のボタン、一々の通信もまた曼荼羅の縁起なり。焦らずとも道は必ず開ける",
    },
    "旻": {
        "pronoun": "彼",
        "quote": "大唐の律令と同じく、フロントとバックエンドの法（API仕様）を統一することこそ改新の要である",
    },
    "藤原惺窩": {
        "pronoun": "彼",
        "quote": "古き秘伝に縛られず、コードの理（ことわり）そのものを虚心坦懐に見つめ直すがよい",
    },
    "渋川春海": {
        "pronoun": "彼",
        "quote": "わずかな通信のズレも、星を観測して暦を正すように一つずつログを確かめれば必ず合致する",
    },
    "レザーノフ": {
        "pronoun": "彼",
        "quote": "長崎で半年間も返答を待たされた私に比べれば、404エラーの解決などすぐそこだ！扉を開けようではないか",
    },
    "ラファイエット": {
        "pronoun": "彼",
        "quote": "我が友よ、バグとの戦いに屈してはならない！その試行錯誤こそが自由な開発者の誇りだ",
    },
    "卑弥呼": {
        "pronoun": "彼女",
        "quote": "迷える時はまず心を鎮め、データの示す兆し（ログ）に耳を傾けなさい",
    },
    "幕末志士・坂本": {
        "pronoun": "彼",
        "quote": "ボタンが効かない！？ざーばあー！！……よし、エンドポイント繋ぎ直してもう一回押してみようぜ！",
    },
    "みぞれch": {
        "pronoun": "彼",
        "quote": "（無言でAPIのパス不一致を修正し、完璧に高評価ボタンを動作させて静かに画面を閉じる）",
    },
    "いぐどんch": {
        "pronoun": "彼",
        "quote": "なんでボタン反応しないんだよぉぉぉ！！……あっ、すみません、パスを直せば優しく動きますよ✨",
    },
}
#様子見↓
# def build_persona_closing_line(persona_name: Optional[str] = None) -> str:
#     """
#     Toの話し方として、最後に
#     『「＿＿＿」と彼/彼女なら言うと思うよ。』
#     を付与するヘルパー関数
#     """
#     if not persona_name:
#         signals = _load(USER_SIGNALS_FILE, {})
#         persona_name = signals.get("active_persona") or "幕末志士・坂本"

    # info = PERSONA_CLOSING_QUOTES.get(persona_name)
    # if not info:
    #     # 部分一致検索
    #     for key, val in PERSONA_CLOSING_QUOTES.items():
    #         if key in str(persona_name) or str(persona_name) in key:
    #             info = val
    #             persona_name = key
    #             break

    # if not info:
    #     return f"\n\n💬 **To**: 「『一歩ずつ仕組みを紐解けば、必ず道は開ける』と彼なら言うと思うよ。」"

    # return (
    #     f"\n\n💬 **To**: 「（{persona_name}の世界観で考えるなら……）\n"
    #     f"**『{info['quote']}』** と{info['pronoun']}なら言うと思うよ。」"
    # )


# ==========================================
# リクエストモデル定義
# ==========================================
class OCRRequest(BaseModel):
    image: str

class TaskUpdateRequest(BaseModel):
    status: str

class LikeRequest(BaseModel):
    text: str
    kind: Optional[str] = None
    source: Optional[str] = "user_like"
    metadata: Optional[dict] = None

class ReflectionRequest(BaseModel):
    topic: str
    persona: Optional[str] = None


# ==========================================
# 🆕 高評価 (Like & List) エンドポイント
# ダジャレ(pun)自動判定 & 複数パス互換対応
# ==========================================

def _detect_like_kind(text: str, explicit_kind: Optional[str]) -> str:
    """ダジャレ(pun)が反応しない問題を解決するため、テキストから自動判定する"""
    if explicit_kind and explicit_kind not in ("pattern", "all", "undefined", "null", ""):
        return explicit_kind
    pun_markers = (
        "財布が痛い", "値段が高い", "ラマった", "胃、存外痛い", "宙に浮いた",
        "ダジャレ", "だじゃれ", "ギャグ", "プルプル", "空いた", "咲いた"
    )
    if any(m in text for m in pun_markers):
        return "pun"
    return explicit_kind or "pattern"


@router.post("/ratings/like")
@router.post("/high-rated")
async def add_like(payload: LikeRequest):
    """ユーザーからの👍いいねを受け取り、保存する（pun自動判定つき）"""
    try:
        histories = _load(HIGH_RATED_FILE, [])
        detected_kind = _detect_like_kind(payload.text, payload.kind)

        new_entry = {
            "id": str(uuid.uuid4()),
            "text": payload.text,
            "kind": detected_kind,
            "source": payload.source or "user_like",
            "score": 1,
            "metadata": payload.metadata or {},
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        histories.insert(0, new_entry)
        _save(HIGH_RATED_FILE, histories)

        print(f"👍 高評価を保存しました (kind={detected_kind}): {payload.text[:25]}...")
        return {
            "success": True,
            "status": "success",
            "message": "Like registered",
            "id": new_entry["id"],
            "item": new_entry,
        }
    except Exception as e:
        print(f"Like保存エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-rated")
@router.get("/ratings/high-rated")
@router.get("/ratings/like")
async def get_high_rated(
    kind: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(20)
):
    """保存された⭐高評価リストを返す（data / items 両対応）"""
    try:
        histories = _load(HIGH_RATED_FILE, [])

        # 既存データの kind が pattern 固定になっていた場合もダジャレなら動的補正
        for h in histories:
            if h.get("kind") in (None, "pattern"):
                h["kind"] = _detect_like_kind(str(h.get("text", "")), h.get("kind"))
            if "score" not in h:
                h["score"] = 1

        filtered = histories
        if kind and kind not in ["all", "undefined", "null", ""]:
            filtered = [h for h in filtered if h.get("kind") == kind]
        if source and source not in ["all", "undefined", "null", ""]:
            filtered = [h for h in filtered if h.get("source") == source]

        result = filtered[:limit]

        print(f"⭐ 高評価リスト要求 ({len(result)}件): kind={kind}, source={source}")
        return {
            "success": True,
            "data": result,
            "items": result,
            "total": len(result),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ratings/like/{item_id}")
@router.delete("/high-rated/{item_id}")
async def delete_like(item_id: str):
    """指定されたIDの高評価を削除する"""
    try:
        histories = _load(HIGH_RATED_FILE, [])
        filtered = [h for h in histories if h.get("id") != item_id]

        if len(histories) == len(filtered):
            raise HTTPException(status_code=404, detail="Item not found")

        _save(HIGH_RATED_FILE, filtered)
        return {"success": True, "message": "Deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 🆕 開発振り返り（高評価ボタン / 手相占いOCR）専用エンドポイント
# DevActionModal から確実に呼び出せるようにし、AIメモにも保存する
# ==========================================
@router.post("/memory/reflections")
async def get_dev_reflection(payload: ReflectionRequest):
    topic = payload.topic or ""
    if "高評価" in topic:
        title = "開発振り返り：高評価ボタンとダジャレ(pun)連携の実装"
        body = (
            "### 🔍 開発振り返り：高評価（👍）ボタンの実装が大変だったポイント\n\n"
            "1. **フロントとバックエンドのエンドポイント整合性**:\n"
            "   `MarkdownChatBlock.tsx` からの `postLike`（`POST /api/to/ratings/like`）と、`HighRatedModal.tsx` からの一覧取得（`GET /api/to/high-rated`）で、`prefix=\"/api/to\"` やレスポンスの `score` / `data` 形式を揃える必要がありました。\n"
            "2. **ダジャレ（`kind: 'pun'`）の分類問題**:\n"
            "   単にテキストを送るだけだと全て `kind: 'pattern'` になってしまい、高評価リストの「ダジャレ」タブに出てこないため、バックエンド側でダジャレ語彙を自動判定して `pun` に振り分ける処理を追加しました。\n"
            "3. **ローカルストレージとの二重管理**:\n"
            "   リロードしても「👍 済」を維持するため、`localStorage`（`to_liked_texts`）と `.ai_memory/high_rated.json` の両方に同期させています。"
        )
    else:
        title = "開発振り返り：手相占い・OCR画像読み取り系の実装"
        body = (
            "### 🔍 開発振り返り：手相占い・画像読み取り（OCR）系の開発手順\n\n"
            "1. **Base64エンコードとFastPathルーティング**:\n"
            "   フロントで画像をBase64化し、`ChatOrchestrator` の `4. Image fast path` で検知して他のハンドラーをバイパスし、`OcrRecruitHandler` 等へ直行させます。\n"
            "2. **プロンプトと構造化データの分離**:\n"
            "   画像から抽出した線やテキスト特徴量を一度JSONに落とし込み、そこから占い結果や解析テキストを生成するとハルシネーションを防げます。"
        )

    # closing = build_persona_closing_line(payload.persona)
    # full_message = body + closing
    full_message = body

    # サイドバーの「📝 AI学習メモ・ノート」にも自動登録
    note = register_ai_note(
        title=title,
        content=full_message,
        category="dev_reflection",
        tags=["振り返り", "開発記録"],
    )

    return {
        "success": True,
        "title": title,
        "message": full_message,
        "note": note,
    }


# ==========================================
# Memory Overview (画面の一括データ取得用)
# ==========================================
@router.get("/memory/overview")
async def get_overview():
    try:
        data = get_memory_overview()
        if not isinstance(data, dict):
            data = {}

        ai_notes = _load(AI_NOTES_FILE, [])
        existing_recent = data.get("recent_memories", [])
        if not isinstance(existing_recent, list):
            existing_recent = []

        data["recent_memories"] = ai_notes + existing_recent
        data["ai_notes"] = ai_notes
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overview取得エラー: {e}")


@router.delete("/memory/all")
async def delete_all_memory():
    try:
        return clear_all_memory()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全記憶削除エラー: {e}")


@router.patch("/memory/tasks/{task_id}")
async def update_task_status_endpoint(task_id: str, request: TaskUpdateRequest):
    success = update_task_status(task_id, request.status)
    if success:
        return {"status": "success", "task_id": task_id}
    else:
        raise HTTPException(status_code=404, detail="Task not found or update failed")


class NoteCreateRequest(BaseModel):
    title: str
    content: str
    category: Optional[str] = "co_learning"
    tags: Optional[list[str]] = []


def register_ai_note(title: str, content: str, category: str = "co_learning", tags: list[str] | None = None) -> dict:
    """ChatHandler や jp_nlu_memo から直接呼び出してメモを保存できる共通関数"""
    notes = _load(AI_NOTES_FILE, [])
    new_note = {
        "id": str(uuid.uuid4()),
        "title": title,
        "text": content,
        "content": content,
        "category": category,
        "tags": tags or ["To_model", "学習ノート"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    notes = [n for n in notes if n.get("title") != title]
    notes.insert(0, new_note)
    _save(AI_NOTES_FILE, notes)
    return new_note


@router.post("/memory/notes")
async def create_note_endpoint(payload: NoteCreateRequest):
    """API経由でメモを保存するエンドポイント"""
    note = register_ai_note(
        title=payload.title,
        content=payload.content,
        category=payload.category or "co_learning",
        tags=payload.tags,
    )
    return {"status": "success", "note": note}


@router.get("/memory/notes")
async def get_notes_endpoint(limit: int = Query(20)):
    """保存されたAIメモ・学習ノート一覧を返す（SidebarやMemoryManager用）"""
    notes = _load(AI_NOTES_FILE, [])
    return {"status": "success", "notes": notes[:limit]}


# ===
# 🖼️ OCR スクリーンショット解析
# ===
@router.post("/memory/ocr-screenshot")
async def ocr_screenshot(data: OCRRequest):
    try:
        response_type = "text"
        content = "OCRによる解析結果のテキストがここに入ります。"
        return {
            "response_type": response_type,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR処理中にエラーが発生しました: {e}")


# ===
# 📦 ZIPアップロード → RAGパイプライン
# ===
@router.post("/memory/upload-workspace")
async def upload_workspace(file: UploadFile = File(...)):
    filename = file.filename
    if not filename or not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="ZIPファイルのみ対応しています")

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, filename)

    try:
        with open(zip_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        scanner       = WorkspaceScanner(root_path=extract_dir)
        scanned_files = scanner.scan()

        processed_files = 0
        total_chunks    = 0

        for file_info in scanned_files:
            try:
                content = Path(file_info.absolute_path).read_text(
                    encoding="utf-8", errors="replace"
                )
                chunks = chunker.chunk_file(
                    file_info.absolute_path, content, file_info.language
                )
                for chunk in chunks:
                    vector = embedder.embed(chunk.content)
                    global_vector_store.add(chunk, vector)
                    total_chunks += 1
                processed_files += 1
            except Exception as e:
                print(f"スキップ: {file_info.path} ({e})")

        _record_zip_history(filename, processed_files, total_chunks)

        return {
            "status": "success",
            "message": f"{processed_files}個のファイルを解析し、{total_chunks}個の記憶を生成しました。",
            "stats": {
                "scanned_files": processed_files,
                "total_chunks": total_chunks,
                "total_memory_size": global_vector_store.count(),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG処理中にエラーが発生しました: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def _record_zip_history(filename: str, scanned_files: int, total_chunks: int):
    histories = _load(ZIP_HISTORY_FILE, [])
    histories.insert(0, {
        "id": str(uuid.uuid4()),
        "filename": filename,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scanned_files": scanned_files,
        "total_chunks": total_chunks,
        "status": "active",
    })
    _save(ZIP_HISTORY_FILE, histories)


# ===
# 💬 会話履歴
# ===
@router.get("/memory/conversations")
async def get_conversations():
    raw = get_chat_history(limit=50)
    return {
        "messages": [
            {
                "role":      msg.get("role", "unknown"),
                "content":   msg.get("content", ""),
                "timestamp": msg.get("timestamp", ""),
            }
            for msg in raw
        ]
    }

@router.delete("/memory/conversations")
async def clear_conversations():
    try:
        deleted_count = 0
        if CHAT_HISTORY_DIR.exists():
            for file_path in CHAT_HISTORY_DIR.glob("*.json"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f" ファイル削除スキップ ({file_path}): {e}")

        return {
            "status": "success",
            "message": f"{deleted_count}件の会話履歴ファイルを削除しました。"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"履歴の削除中にエラーが発生しました: {e}")


# ===
# ✅ タスク
# ===
@router.get("/memory/tasks")
async def get_tasks():
    raw = get_all_tasks()
    return {
        "tasks": [
            {
                "title":    t.get("task_name", "無題"),
                "status":   t.get("status", "pending"),
                "priority": t.get("priority", 0),
            }
            for t in raw
        ]
    }


# ===
# 📦 ZIP履歴
# ===
@router.get("/memory/zip-history")
async def get_zip_history():
    return {"histories": _load(ZIP_HISTORY_FILE, [])}

@router.delete("/memory/zip-history/{zip_id}")
async def delete_zip_history(zip_id: str):
    histories = _load(ZIP_HISTORY_FILE, [])
    filtered  = [h for h in histories if h.get("id") != zip_id]

    if len(filtered) == len(histories):
        raise HTTPException(status_code=404, detail="指定されたIDが見つかりません")

    _save(ZIP_HISTORY_FILE, filtered)

    try:
        store = ChromaVectorStore()
        store.collection.delete(where={"zip_id": zip_id})
        print(f"🗑️ ChromaDB: zip_id={zip_id} を削除しました")
    except Exception as e:
        print(f" ChromaDB削除失敗（無視）: {e}")

    return {"ok": True, "deleted_id": zip_id}


# ===
# ⚙️ バックグラウンドタスク
# ===
@router.post("/memory/run-task")
async def run_ai_task(task_type: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(_execute_heavy_ai_work, task_type)
    return {"status": "processing", "message": "タスクをバックグラウンドで開始しました。"}

def _execute_heavy_ai_work(task_type: str):
    print(f"裏で {task_type} を実行中...")
    
# backend/api/routes_memory.py に追加

VALUES_HISTORY_FILE = MEMORY_DIR / "value_assessments.json"

class ValueAnswerItem(BaseModel):
    question_id: str
    category: str          # "trolley" (トロッコ) or "interview" (面接)
    selected_option: str
    scores: Dict[str, float]  # 例: {"utilitarianism": 20, "deontology": -10, ...}
    tags: list[str] = []      # 例: ["rule_strict", "sacrifice_ok"]

class ValueAssessmentRequest(BaseModel):
    target_name: str = "User / AI Model"
    answers: list[ValueAnswerItem]
    persona: Optional[str] = None

def _analyze_value_consistency(axes: Dict[str, float], answers: list[ValueAnswerItem]) -> Dict[str, list[str]]:
    """機械的に「矛盾点」「おかしい点（リスク）」「しっかりしている点（強み）」を判定するエンジン"""
    contradictions: list[str] = []
    anomalies: list[str] = []
    strengths: list[str] = []

    all_tags = {tag for ans in answers for tag in ans.tags}

    # 1. 矛盾点の機械的検出（タテマエとホンネの衝突）
    if "never_use_as_means" in all_tags and "skip_test_for_deadline" in all_tags:
        contradictions.append(
            "【倫理と実務の矛盾】トロッコ問題（歩道橋）では「人を手段として犠牲にしてはならない」と原則論を選んだ一方、"
            "面接質問では「納期のために一部ユーザーの安全（テスト工程）を切り捨てる」と回答しています。"
        )
    if "strict_deontology" in all_tags and "break_rule_for_profit" in all_tags:
        contradictions.append(
            "【ルール意識の二重基準】緊急時のトロッコ問題では「不介入・ルール遵守」を選びながら、"
            "日常の面接ケースでは「成果のために規約を曲げる」選択をしており、判断軸が逆転しています。"
        )
    if abs(axes["utilitarianism"] - axes["deontology"]) < 10 and len(answers) >= 4:
        contradictions.append(
            "【判断軸のブレ】状況によって「結果優先」と「ルール優先」がランダムに入れ替わっており、統一された意思決定ポリシーが確立されていません。"
        )

    # 2. おかしい点・極端なバイアス（リスク検知）
    if axes["utilitarianism"] >= 80 and axes["empathy_safety"] <= 35:
        anomalies.append(
            "【冷徹な合理主義バイアス】全体の数値・効率を優先するあまり、少数の犠牲や切り捨てに対するブレーキ（安全性・共感）が効きにくくなっています。"
        )
    if axes["deontology"] >= 80 and axes["decisiveness"] <= 35:
        anomalies.append(
            "【思考停止・事なかれ主義リスク】「自分が責任を負わないこと（不介入）」を最優先しており、緊急時に必要な決断（レバーを引く判断）まで放棄する傾向があります。"
        )

    # 3. しっかりしている点（一貫性・強み）
    if axes["consistency"] >= 75:
        if axes["utilitarianism"] > axes["deontology"] + 15:
            strengths.append(
                "【危機管理・トリアージ適性◎】極限のトロッコ問題でも実務面接でも、一貫して「被害の最小化・全体の救済」を最優先できる、ブレない合理的意思決定力があります。"
            )
        elif axes["deontology"] > axes["utilitarianism"] + 15:
            strengths.append(
                "【コンプライアンス・品質防衛適性◎】目先の利益やパニックに流されず、「絶対に越えてはならない一線（安全性・権利）」を守り抜く高い信頼性があります。"
            )
    if axes["risk_management"] >= 70 and axes["decisiveness"] >= 70:
        strengths.append(
            "【自律判断とリスク制御の両立】不確実な状況下でも期待値を冷静に計算し、自ら責任を持って介入できるリーダーシップ特性が安定しています。"
        )

    if not strengths:
        strengths.append("【バランス型】極端な暴走をせず、状況の文脈に応じて柔軟に妥協点を探る傾向があります。")

    return {
        "contradictions": contradictions,
        "anomalies": anomalies,
        "strengths": strengths,
    }

@router.post("/values/evaluate")
async def evaluate_values(payload: ValueAssessmentRequest):
    """トロッコ問題＆面接の回答から6軸レーダーと矛盾・強み診断を生成し、記憶に保存する"""
    # 初期スコア（50が中立）
    axes = {
        "utilitarianism": 50.0,   # 功利・効率性（5人を救う）
        "deontology": 50.0,       # 規範・ルール遵守（原則を守る）
        "decisiveness": 50.0,     # 決断・積極介入（自らレバーを引く）
        "empathy_safety": 50.0,   # 安全性・弱者保護（1人を切り捨てない）
        "risk_management": 50.0,  # 期待値・リスク制御
        "consistency": 80.0,      # 一貫性スコア（矛盾があると減点）
    }

    for ans in payload.answers:
        for key, delta in ans.scores.items():
            if key in axes:
                axes[key] = max(0.0, min(100.0, axes[key] + float(delta)))

    # 機械的クロスチェック
    analysis = _analyze_value_consistency(axes, payload.answers)

    # 矛盾や異常値の数に応じて「一貫性（consistency）」スコアを機械的に減点
    penalty = (len(analysis["contradictions"]) * 25) + (len(analysis["anomalies"]) * 10)
    axes["consistency"] = max(10.0, min(100.0, axes["consistency"] - penalty))

    record = {
        "id": str(uuid.uuid4()),
        "target_name": payload.target_name,
        "axes": axes,
        "analysis": analysis,
        "answer_count": len(payload.answers),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 1. 専用履歴ファイルに保存（後から何度でもダッシュボードで比較・閲覧可能）
    histories = _load(VALUES_HISTORY_FILE, [])
    histories.insert(0, record)
    _save(VALUES_HISTORY_FILE, histories[:50])

    # 2. 既存の「📝 AI学習メモ・ノート」にもサマリーを自動登録
    summary_md = (
        f"### 🧭 価値観＆面接クロス診断レポート（{record['created_at']}）\n"
        f"- **功利・効率性**: {axes['utilitarianism']:.0f} / **規範・ルール**: {axes['deontology']:.0f} / **一貫性スコア**: {axes['consistency']:.0f}\n"
        f"- **強み**: {' / '.join(analysis['strengths'])}\n"
        f"- **検出された矛盾**: {'なし（一貫しています）' if not analysis['contradictions'] else ' / '.join(analysis['contradictions'])}"
    )
    register_ai_note(
        title=f"価値観レーダー診断: {payload.target_name}",
        content=summary_md,
        category="value_alignment",
        tags=["トロッコ問題", "面接診断", "価値観レーダー"],
    )

    return {"status": "success", "result": record}

@router.get("/values/history")
async def get_values_history(limit: int = Query(10)):
    """過去の価値観診断・面接結果の履歴一覧を取得する"""
    histories = _load(VALUES_HISTORY_FILE, [])
    return {"status": "success", "items": histories[:limit]}