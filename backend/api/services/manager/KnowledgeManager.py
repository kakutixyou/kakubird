# KnowledgeManager.py
import os
import json
import logging
import re
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================================================
# ✅ 1. 遅延ロード用のクラス (既存維持：開かずに検索可能)
# =========================================================
class LazyKnowledge:
    def __init__(self, base_dir, full_path, rel_path, metadata=None):
        self.base_dir = base_dir
        self.full_path = full_path
        self.rel_path = rel_path
        self._parsed_data = None
        self._metadata = metadata or {}

    @property
    def data(self):
        if self._parsed_data is None:
            try:
                with open(self.full_path, "r", encoding="utf-8") as f:
                    self._parsed_data = json.load(f)
            except Exception as e:
                logger.error(f"遅延ロード失敗 ({self.rel_path}): {e}")
                self._parsed_data = {}
        return self._parsed_data

    def __getitem__(self, key):
        # メタデータに存在するキーなら、本体を開かずに返す（超高速）
        if key in self._metadata:
            return self._metadata[key]
            
        data = self.data
        if key == "file_path": return self.rel_path
        if key == "id": return data.get("id", os.path.splitext(os.path.basename(self.full_path))[0])
        if key == "title": return data.get("title", data.get("name", os.path.basename(self.full_path)))
        if key == "content": return data
        
        # ネストされた取得用
        if key == "retrieval":
            retrieval = data.get("retrieval", {})
            return {
                "keywords": retrieval.get("keywords", data.get("keywords", [])),
                "message_examples": retrieval.get("message_examples", data.get("message_examples", [])),
                "intent": retrieval.get("intent", data.get("intent", [])),
                "tags": retrieval.get("tags", data.get("tags", []))
            }
        return data.get(key)
        
    def get(self, key, default=None):
        try:
            val = self[key]
            return val if val is not None else default
        except KeyError:
            return default


class KnowledgeManager:
    def __init__(self, base_dir="."):
        self.base_dir = os.path.abspath(base_dir)
        # ③ メモリキャッシュ: 2回目以降のディスクアクセスをゼロにする
        self._index_cache = {}

    def _safe_join_path(self, relative_path):
        normalized_rel_path = relative_path.replace("\\", "/").strip("/")
        target_path = os.path.abspath(os.path.join(self.base_dir, normalized_rel_path))
        if not target_path.startswith(self.base_dir):
            raise ValueError(f"不正なパス: {relative_path}")
        return target_path

    # =========================================================
    # ✅ 2. 差分更新 ＆ 分散インデックス対応のビルド処理
    # =========================================================
    def build_index(self, target_dir: str, index_filename: str = "index.json"):
        """
        ① & ⑤: ターゲットディレクトリ内に index_filename を作成（複数インデックス対応）
        ②: mtimeとサイズを見て、更新されたファイルだけJSONを開く（差分更新）
        """
        start_time = time.time()
        index_path = os.path.join(target_dir, index_filename)
        
        # 既存のインデックスをロード (差分チェック用)
        existing_index = {}
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    existing_index = json.load(f)
            except Exception:
                logger.warning(f"既存のインデックスが破損しているため再構築します: {index_path}")

        new_index = {}
        total_bytes = 0
        parsed_count = 0
        skipped_count = 0

        logger.info(f"インデックスの差分構築を開始します: {target_dir} -> {index_filename}")

        for root, _, files in os.walk(target_dir):
            for file in files:
                if not file.lower().endswith(".json"):
                    continue
                if file == index_filename:
                    continue # インデックス自身は除外

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.base_dir).replace("\\", "/")
                
                try:
                    mtime = os.path.getmtime(full_path)
                    file_size = os.path.getsize(full_path)
                    total_bytes += file_size

                    # ② 差分チェック: mtimeとサイズが同じならJSONを開かずに前回のメタデータを流用
                    old_meta = existing_index.get(rel_path)
                    if old_meta and old_meta.get("mtime") == mtime and old_meta.get("size_bytes") == file_size:
                        new_index[rel_path] = old_meta
                        skipped_count += 1
                        continue

                    # 新規追加、または更新されたファイルだけを開く
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    retrieval = data.get("retrieval", {})
                    
                    # ④ 検索用データの拡充
                    metadata = {
                        "id": data.get("id", os.path.splitext(file)[0]),
                        "title": data.get("title", data.get("name", file)),
                        "keywords": retrieval.get("keywords", data.get("keywords", [])),
                        "intent": retrieval.get("intent", data.get("intent", [])),
                        "tags": retrieval.get("tags", data.get("tags", [])),
                        "category": data.get("category", ""),
                        "language": data.get("language", ""),
                        "framework": data.get("framework", ""),
                        "difficulty": data.get("difficulty", ""),
                        "updated_at": data.get("updated_at", ""),
                        "score": data.get("score", 0),
                        "file_path": rel_path,
                        "size_bytes": file_size,
                        "mtime": mtime  # 差分比較用
                    }
                    new_index[rel_path] = metadata
                    parsed_count += 1

                except Exception as e:
                    logger.error(f"インデックス構築中のエラー ({rel_path}): {e}")

        # ディスクに保存
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(new_index, f, ensure_ascii=False, indent=2)

        # ③ メモリキャッシュも更新
        self._index_cache[index_path] = new_index

        elapsed = time.time() - start_time
        mb_size = total_bytes / (1024 * 1024)
        
        print("\n" + "="*55)
        print(f"📊 [KnowledgeManager] インデックス構築完了")
        print(f" 📁 ターゲット   : {index_path}")
        print(f" 🔄 新規/更新読込: {parsed_count} 件")
        print(f" ⏭  読込スキップ : {skipped_count} 件 (キャッシュ利用)")
        print(f" 💾 総データ量   : {total_bytes:,} Bytes ({mb_size:.2f} MB)")
        print(f" ⏱ 処理時間     : {elapsed:.3f} 秒")
        print("="*55 + "\n")

    # =========================================================
    # ✅ 3. キャッシュを活用した爆速ロード
    # =========================================================
    def load_all_json_from_dir(self, relative_dir_path: str, index_filename: str = "index.json", force_rebuild=False) -> list:
        """
        指定したディレクトリのインデックスからLazyKnowledgeのリストを生成する。
        """
        target_dir = self._safe_join_path(relative_dir_path)
        index_path = os.path.join(target_dir, index_filename)

        if not os.path.exists(target_dir):
            logger.warning(f"ディレクトリが存在しません: {target_dir}")
            return []

        index_data = None

        # ③ メモリキャッシュの活用
        if not force_rebuild and index_path in self._index_cache:
            index_data = self._index_cache[index_path]
            # logger.info(f"オンメモリキャッシュから爆速ロード: {index_filename}")
        else:
            # キャッシュになければディスクから読む。無ければ作る。
            if force_rebuild or not os.path.exists(index_path):
                self.build_index(target_dir, index_filename)
            
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                self._index_cache[index_path] = index_data
            except Exception as e:
                logger.error(f"インデックスの読み込みに失敗: {e}")
                return []

        # オブジェクトの生成 (ここはメタデータを渡すだけなので一瞬)
        loaded_list = []
        for rel_path, metadata in index_data.items():
            full_path = os.path.join(self.base_dir, rel_path)
            
            # 本体が削除されている場合はスキップ
            if not os.path.exists(full_path):
                continue
                
            lazy_item = LazyKnowledge(self.base_dir, full_path, rel_path, metadata=metadata)
            loaded_list.append(lazy_item)

        return loaded_list

    # =========================================================
    # ファイル書き込み系 (既存維持)
    # =========================================================
    def write_file(self, relative_path, content):
        try:
            target_path = self._safe_join_path(relative_path)
            parent_dir = os.path.dirname(target_path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"ファイル保存中にエラーが発生しました ({relative_path}): {str(e)}")
            return False

    def write_from_json_data(self, files_list):
        success_files, failed_files = [], []
        for file_info in files_list:
            path = file_info.get("path")
            content = file_info.get("content")
            if path and content is not None:
                if self.write_file(path, content):
                    success_files.append(path)
                else:
                    failed_files.append(path)
        return {"success": success_files, "failed": failed_files}

    def write_from_markdown_text(self, markdown_text):
        pattern = r"(?i)(?:file|path)[\s:\*]*([a-zA-Z0-9_\-\.\/]+)\s*\n+```[a-zA-Z0-9]*\n([\s\S]*?)\n```"
        matches = re.findall(pattern, markdown_text)
        files_to_write = [{"path": p.strip(), "content": c} for p, c in matches]
        return self.write_from_json_data(files_to_write)