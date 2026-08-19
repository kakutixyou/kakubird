# KnowledgeManager.py
import os
import json
import logging
import re
import time
# import pylanse
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from engine.KnowledgeRouter import KnowledgeRouter
from engine.KnowledgeLoader import KnowledgeLoader

# ===
# ✅ 1. 遅延ロード用のクラス (既存維持：開かずに検索可能)
# ===
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

    # ===
    # ✅ 2. 差分更新 ＆ 分散インデックス対応のビルド処理
    # ===
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
                        "category": data.get("category", "未分類"),
                        "catchphrase": data.get("catchphrase", ""),
                        "video_url": data.get("video_url", ""),  # 動画URLを追加
                        "subjects": data.get("subjects", []),    # 教科・単元を追加
                        "skills": data.get("skills", []),        # 使う力を追加
                        "keywords": retrieval.get("keywords", data.get("keywords", [])),
                        "file_path": rel_path,
                        "size_bytes": file_size,
                        "mtime": mtime
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

    # ===
    # ✅ 3. キャッシュを活用した爆速ロード
    # ===
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
            # ▼ _safe_join_path を経由させて index.json 改ざん時のトラバーサルも防ぐ
            try:
                full_path = self._safe_join_path(rel_path)
            except ValueError:
                logger.warning(f"インデックス内に不正なパスを検出したためスキップ: {rel_path}")
                continue
            
            # 本体が削除されている場合はスキップ
            if not os.path.exists(full_path):
                continue
                
            lazy_item = LazyKnowledge(self.base_dir, full_path, rel_path, metadata=metadata)
            loaded_list.append(lazy_item)

        return loaded_list
    # ===
    # ✅ 4. キーワード検索（Orchestrator側から呼び出す想定）
    # ===
    def search_by_keywords(self, relative_dir_path: str, keywords: list,
                            index_filename: str = "index.json") -> dict:
        """
        指定ディレクトリのインデックスからkeywordsに合致するファイルを探し、
        {ファイル名: 中身(JSON)} の辞書を返す。

        マッチ判定は以下を対象にする（インデックスのメタデータだけ見るので高速）:
          - metadata.keywords / metadata.tags / metadata.title
          - ファイルパス（フォルダ名・ファイル名）
        本体（フルJSON）は、マッチしたファイルだけ遅延ロードする。
        """
        if not keywords:
            return {}

        items = self.load_all_json_from_dir(relative_dir_path, index_filename)
        if not items:
            return {}

        matched = {}
        lowered_keywords = [kw.lower() for kw in keywords]

        for item in items:
            haystack_parts = []
            haystack_parts.extend(item.get("keywords", []) or [])
            haystack_parts.extend(item.get("tags", []) or [])
            haystack_parts.append(item.get("title", "") or "")
            haystack_parts.append(item.rel_path.lower())

            haystack = " ".join(str(p).lower() for p in haystack_parts)

            if any(kw in haystack for kw in lowered_keywords):
                filename = os.path.basename(item.full_path)
                try:
                    matched[filename] = item.data  # ここで初めて本体を開く
                except Exception as e:
                    logger.error(f"知識ファイルのロードに失敗 ({item.rel_path}): {e}")

        return matched
    # ===
    # ファイル書き込み系 (既存維持)
    # ===
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
    def get_career_feed(self, relative_dir_path: str = "knowledge/jobs") -> dict:
        """
        アプリのフィード画面向けに職業リストを返すAPIメソッド。
        動画URLがあるものを優先して上に並べ替えます。
        """
        items = self.load_all_json_from_dir(relative_dir_path)
        
        feed_list = []
        for item in items:
            # item.get() はインデックス（メタデータ）にあれば本体を開かずに一瞬で取得します
            feed_list.append({
                "id": item.get("id"),
                "name": item.get("title"),
                "category": item.get("category"),
                "catchphrase": item.get("catchphrase"),
                "subjects": item.get("subjects"),
                "skills": item.get("skills"),
                "video_url": item.get("video_url"),
                "file_path": item.get("file_path")
            })

        # ソートロジック: 動画URLがあるものを優先（True=1, False=0を利用して降順ソート）
        # 同率の場合はカテゴリ順、さらに名前順
        feed_list.sort(
            key=lambda x: (bool(x["video_url"]), x["category"], x["name"]), 
            reverse=True
        )

        return {
            "status": "success",
            "total_count": len(feed_list),
            "video_count": sum(1 for x in feed_list if x["video_url"]),
            "data": feed_list
        }

    def update_video_url(self, relative_path: str, video_url: str) -> dict:
        """
        特定の職業JSONの動画URLを更新し、保存する管理用APIメソッド。
        チームで動画を見つけた際に、このメソッドを呼ぶだけでDBが更新されます。
        """
        target_path = self._safe_join_path(relative_path)
        
        if not os.path.exists(target_path):
            return {"status": "error", "message": f"ファイルが見つかりません: {relative_path}"}
            
        try:
            # 1. 既存データの読み込み
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 2. データの更新
            data["video_url"] = video_url
            
            # 3. 保存
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # 4. インデックスの再構築（差分更新が走るので高速）
            target_dir = os.path.dirname(target_path)
            self.build_index(target_dir)
            
            logger.info(f"🎥 動画URLを更新しました: {relative_path} -> {video_url}")
            return {"status": "success", "message": "動画URLを更新しました", "path": relative_path}
            
        except Exception as e:
            logger.error(f"動画URL更新エラー ({relative_path}): {e}")
            return {"status": "error", "message": str(e)}