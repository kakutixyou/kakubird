# To-main/backend/src/plugins/Algorithm_search_engine/search_service.py
import os
import sys
import chromadb

# =========================================================
# パス調整：plugin/ フォルダの自作モジュールを読み込めるようにする
# =========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# backendの3階層上（プロジェクトのルート）に plugin/ がある構造に対応
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 自作のRAGパーツ群をインポート
try:
    from plugin.ai_memory.code_chunker import CodeChunker
    from plugin.ai_memory.embedding_service import EmbeddingService
    print("🤖 自作RAGコンポーネント (Chunker / Embedding) の読み込みに成功しました。")
except ImportError as e:
    print(f"⚠️ 自作RAGコンポーネントのインポートに失敗しました。パスを確認してください: {e}")
    # フォールバック用のダミー（エラー落ち防止）
    class CodeChunker:
        def __init__(self, *args, **kwargs): pass
        def chunk_file(self, f, c, l): return []
    class EmbeddingService:
        def embed(self, t): return [0.0]*128
        def embed_many(self, ts): return [[0.0]*128]

# =========================================================
# ChromaDBの保存先パスを設定
# =========================================================
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR)) # backend フォルダ
CHROMA_DB_PATH = os.path.join(BASE_DIR, "data", "vector_db", "chroma_store")

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection(name="project_memory")

# インスタンスの初期化
chunker = CodeChunker(max_lines=100)
embedding_service = EmbeddingService() # デフォルトでOllamaEmbeddingProviderが動きます

# =========================================================
# 1. 記憶を保存する関数（ZIPアップロード時に呼び出される）
# =========================================================
def save_memory(texts: list[str], source_names: list[str] = None): # type: ignore
    """
    ファイルを自動でコードチャンク（関数・クラス単位）に分解し、
    Ollamaでベクトル化してChromaDBに保存する
    """
    if not texts:
        return

    source_names = source_names or ["unknown"] * len(texts)
    
    all_documents = []
    all_metadatas = []
    all_ids = []

    for text, filename in zip(texts, source_names):
        # ① 拡張子から言語を簡易判定
        ext = os.path.splitext(filename.lower())[1]
        if ext == ".py":
            lang = "python"
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            lang = "javascript"
        else:
            lang = "generic"

        # ② 自作の CodeChunker で関数・クラスごとに細切れにする
        chunks = chunker.chunk_file(filename, text, lang)
        
        for chunk in chunks:
            all_documents.append(chunk.content)
            all_ids.append(chunk.chunk_id) # code_chunkerが生成した一意のハッシュID
            all_metadatas.append({
                "source": chunk.file_path,
                "symbol": chunk.symbol or "none",
                "start_line": chunk.start_line,
                "end_line": chunk.end_line
            })

    if not all_documents:
        print("⚠️ 有効なコードチャンクが抽出されませんでした。")
        return

    print(f"🧠 {len(all_documents)} 個のコードチャンクを Ollama でベクトル化中...")
    
    # ③ 自作の EmbeddingService (Ollama) で一括ベクトル化
    # ※ 量が多い場合はOllamaの負荷を下げるため embed_many を使用
    all_embeddings = embedding_service.embed_many(all_documents)

    # ④ ベクトルとデータをChromaDBにまとめて突っ込む
    collection.add(
        ids=all_ids,
        embeddings=all_embeddings,  # 👈 ココ！Ollamaで作った本物のベクトルを渡す
        documents=all_documents,
        metadatas=all_metadatas  # type: ignore
    )
    print(f"✅ ChromaDBに保存完了！(総チャンク数: {collection.count()}個)")

# =========================================================
# 2. 記憶を検索する関数（AIチャット時に呼び出される）
# =========================================================
def search_memory(query: str, n_results: int = 3) -> str:
    """
    ユーザーの質問をOllamaでベクトル化し、ChromaDBから最も近いコード片を検索する
    """
    if collection.count() == 0:
        return ""

    # ① ユーザーの質問をOllamaでベクトル化する（保存時と同じ脳みそで検索するため）
    query_vector = embedding_service.embed(query)

    # ② ベクトル検索を実行
    results = collection.query(
        query_embeddings=[query_vector],  # 👈 ココ！ベクトルで検索をかける
        n_results=n_results
    )

    # ③ 検索結果をAIが読みやすい参考資料の形に整形
    documents = results.get("documents")
    metadatas = results.get("metadatas")
    
    if not documents or not documents[0]:
        return ""

    context_parts = []
    # 見つかったコードチャンクとメタデータ（ファイル名や行数）を綺麗に結合
    for doc, meta in zip(documents[0], metadatas[0]): # type: ignore
        header = f"--- File: {meta['source']} (Line {meta['start_line']}-{meta['end_line']}, Symbol: {meta['symbol']}) ---"
        context_parts.append(f"{header}\n{doc}")

    return "\n\n".join(context_parts)