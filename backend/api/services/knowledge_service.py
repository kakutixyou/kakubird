# backend/api/services/knowledge_service.py
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any

# 将来的に個別のエンジンをインポートする（現在はダミーまたは既存のProjectEngine）
from engine.ProjectKnowledgeEngine import ProjectKnowledgeEngine
# from engine.HtmlKnowledgeEngine import HtmlKnowledgeEngine

class KnowledgeService:
    # 🌟 メモリキャッシュ（FastAPI起動中は保持されるため、毎回50MBのJSONを読む必要がなくなる）
    _world_knowledge_cache: Dict[str, Any] = None
    _file_hashes: Dict[str, str] = {}

    @staticmethod
    def _calculate_hash(filepath: str) -> str:
        """ファイルのSHA-256ハッシュを高速に計算する"""
        if not os.path.exists(filepath):
            return ""
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    @classmethod
    def load_knowledge(cls, project_root: str = ".") -> Dict[str, Any]:
        """
        ハンドラーの変更を検知し、差分更新を行った上で知識パッケージを返す
        """
        knowledge_dir = Path(project_root) / "knowledge"
        handlers_dir = Path(project_root) / "backend" / "api" / "handlers"
        
        os.makedirs(knowledge_dir, exist_ok=True)
        
        needs_rebuild = False
        current_knowledge = {}

        # 1. 差分更新の検知（例: SubstituteHandler.py を監視）
        handler_files = {
            "substitute": handlers_dir / "SubstituteHandler.py",
            "html": handlers_dir / "HtmlHandler.py",
            "github": handlers_dir / "GithubHandler.py",
            # プロジェクト全体のメタデータ監視用
            "project_meta": Path(project_root) / "pyproject.toml" # 例
        }

        for key, filepath in handler_files.items():
            if not filepath.exists():
                continue
                
            current_hash = cls._calculate_hash(str(filepath))
            cached_hash = cls._file_hashes.get(key)

            # ハッシュが変わっていたら（＝コードが書き換えられていたら）更新
            if current_hash != cached_hash:
                print(f"🔄 [KnowledgeService] 変更を検知しました: {filepath.name}")
                
                # 🌟 ここで対応する個別のEngineを呼び出してJSONを再生成する
                # if key == "substitute":
                #     SubstituteKnowledgeEngine(filepath, knowledge_dir / f"{key}_knowledge.json").run()
                # elif key == "project_meta":
                #     ProjectKnowledgeEngine(...).run()
                
                cls._file_hashes[key] = current_hash
                needs_rebuild = True

        # 2. キャッシュの読み込み（変更がなく、メモリにキャッシュがあれば爆速で返す）
        if not needs_rebuild and cls._world_knowledge_cache is not None:
            return cls._world_knowledge_cache

        # 3. 知識の結合（各々のJSONを合体させてひとつのパッケージにする）
        print("🧠 [KnowledgeService] 知識パッケージを（再）構築中...")
        for json_file in knowledge_dir.glob("*_knowledge.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    domain = json_file.stem.replace("_knowledge", "")
                    current_knowledge[domain] = json.load(f)
            except Exception as e:
                print(f" 読み込みエラー {json_file.name}: {e}")

        # メモリに保存して次回以降を爆速にする
        cls._world_knowledge_cache = current_knowledge
        return cls._world_knowledge_cache