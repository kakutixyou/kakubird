# backend/services/orchestrator/chat_orchestrator.py

import json
import os
import traceback
import inspect
from pathlib import Path
from typing import Any, Tuple, List, Dict, cast
from engine.context.ContextManager import ContextManager
from engine.prompt.PromptBuilder import PromptBuilder
# 1. IntentInspector のインポート
from api.services.inspectors.IntentInSpector import IntentInspector

# 2. KnowledgeRouter のインポート
from engine.KnowledgeRouter import KnowledgeRouter

# 2.5 KnowledgeManager のインポート
from api.services.manager.KnowledgeManager import KnowledgeManager


from api.services.handlers.project.repomix_Handler import RepomixHandler
from api.services.handlers.project.ProjectBuilderHandler import ProjectBuilderHandler
from api.services.handlers.analysis.ocr_recruit_handler import OcrRecruitHandler
from api.services.handlers.github_handler import GithubHandler
from api.services.handlers.recruit_handler import RecruitHandler
from api.services.handlers.weather_handler import WeatherHandler
from api.services.handlers.database_handler import DatabaseHandler
from api.services.handlers.ollama_handler import OllamaHandler
from api.services.handlers.offline_handler import OfflineFallbackHandler
from api.services.handlers.Scraping_Handler import ScrapingHandler
from api.services.handlers.DesignHandler import DesignHandler  
from api.services.handlers.code.HtmlHandler import HTMLHandler
from api.services.handlers.project.DeploymentHandler import DeploymentHandler
from api.services.handlers.ChatHandler import ChatHandler
from api.services.handlers.code.ConversionJsonHandler import ConversionJsonHandler
from api.services.handlers.code.PHPHandler import PhpHandler
from api.services.handlers.Ckan_API_Collect_handler import APICollectHandler
from api.services.handlers.code.Decompositionhandler import DecompositionHandler
from api.services.handlers.Github_guide_handler import GithubGuideHandler
from engine.orchestrator.base_orchestrator import BaseOrchestrator
from api.services.handlers.LineFormatHandler import LineFormatHandler
from api.services.handlers.perserhandler import ParserHandler
class ChatOrchestrator(BaseOrchestrator):
    def __init__(
        self,
        project_root=None,
        config=None,
        services=None,
    ):
        super().__init__(
            project_root=project_root,
            config=config,
            services=services,
        )

        self.context_manager = ContextManager()
        self.intent_inspector = None 
        self.prompt_builder = PromptBuilder()

        # ✅ KnowledgeRouter の動的初期化 (パスは backend 基準)
        if KnowledgeRouter is not None:
            # サーバーの起動位置に合わせて安全に絶対パス化
            base_dir = os.path.dirname(os.path.abspath(__file__))
            registry_path = os.path.abspath(os.path.join(base_dir, "../knowledge/registry.json"))
            
            if os.path.exists(registry_path):
                self.knowledge_router = KnowledgeRouter(registry_path)
                print(f"📚 KnowledgeRouter をロードしました: {registry_path}")
            else:
                # 起動ディレクトリ直下などからフォールバック探索
                fallback_path = "backend/engine/knowledge/registry.json"
                if os.path.exists(fallback_path):
                    self.knowledge_router = KnowledgeRouter(fallback_path)
                else:
                    print(f" registry.json が見つかりません。ナレッジルーティングはバイパスされます。")
                    self.knowledge_router = None
        else:
            self.knowledge_router = None

        # 記憶・文脈ファイルのパス設定
        self.memory_dir = "backend/.ai_memory"
        self.feedback_file = os.path.join(self.memory_dir, "feedback_scores.json")
        self.signals_file = os.path.join(self.memory_dir, "user_signals.json") 
        
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir, exist_ok=True)

        self.last_used_handler = "Unknown"
        self.active_context = None
        # 例: services/knowledge/domains などのナレッジが置かれている場所を指定
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_knowledge_dirs: list[str | Path] = [
            Path(os.path.abspath(os.path.join(base_dir, "../knowledge/domains")))
        ]
        
        default_manager_base_dir = Path(os.path.abspath(os.path.join(base_dir, "../knowledge")))

        
        # ✅ KnowledgeManager の初期化：職業(occupations)・歴史人物(historical_figures)の
        #    検索・ロードをここで一元管理する。ChatHandler側はファイルI/Oを持たない。
        
        self.plugin_knowledge_dir = os.path.join("plugins", "project_builder", "knowledge")
        self.occupations_dir = os.path.join(self.plugin_knowledge_dir, "Claude_occupations")
        self.historical_figures_dir = os.path.join(self.plugin_knowledge_dir, "Claude_historical_figures")

        occupation_titles: List[str] = []
        historical_figures_titles: List[str] = []

        if KnowledgeManager is not None:
            self.knowledge_manager = KnowledgeManager(base_dir=os.getcwd())

            try:
                occupation_items = self.knowledge_manager.load_all_json_from_dir(self.occupations_dir)
                occupation_titles = [item["title"] for item in occupation_items if item.get("title")]
            except Exception as e:
                print(f" 職業タイトル一覧の読み込みに失敗しました: {e}")

            try:
                history_items = self.knowledge_manager.load_all_json_from_dir(self.historical_figures_dir)
                for item in history_items:
                    try:
                        data = item.data  # LazyKnowledgeの本体を開く
                    except Exception as e:
                        print(f" 歴史人物データの読み込みに失敗しました ({item.rel_path}): {e}")
                        continue

                    hf = data.get("history_figures", {}) if isinstance(data, dict) else {}
                    for group in ("world_history", "japan_history"):
                        people = hf.get(group)
                        if isinstance(people, list):
                            for p in people:
                                name = p.get("name")
                                if name:
                                    historical_figures_titles.append(name)
            except Exception as e:
                print(f" 歴史人物タイトル一覧の読み込みに失敗しました: {e}")
        else:
            self.knowledge_manager = None
            print(" KnowledgeManager が見つかりません。職業/歴史人物ナレッジはバイパスされます。")

        self.handlers = [
            DecompositionHandler(),
            GithubGuideHandler(),
            APICollectHandler(),
            RepomixHandler(),
            ProjectBuilderHandler(),  # ✅ アプリ構築自動化エンジンを最優先
            PhpHandler(),
            ConversionJsonHandler(),
            DeploymentHandler(knowledge_dirs=default_knowledge_dirs,
                manager_base_dir=default_manager_base_dir,
                cache_enabled=True),
            ChatHandler(
                occupation_titles=occupation_titles,
                historical_figures_titles=historical_figures_titles,
            ),
            LineFormatHandler(),
            HTMLHandler(),
            GithubHandler(),
            RecruitHandler(),
            ScrapingHandler(),
            DesignHandler(), 
            WeatherHandler(),
            DatabaseHandler(),
            OllamaHandler(),
            OfflineFallbackHandler(),
            ParserHandler()
        ]

# chat_orchestrator.py の _save_assistant_response_and_state を改修

    def _save_assistant_response_and_state(self, res_content: Any):
        try:
            assistant_text = ""
            if isinstance(res_content, dict):
                assistant_text = res_content.get("message", "")
                
                # 👇 ハンドラーから状態更新の要求があれば保存する
                if "update_signals" in res_content:
                    self._save_signals(res_content["update_signals"])
            else:
                assistant_text = str(res_content)

            if assistant_text:
                self.context_manager.add_chat_history("assistant", assistant_text)

            self._update_signals_with_created_files(assistant_text)
            self.context_manager.save_state()
            print("💾 AIの記憶とステートを正常に更新しました。")
        except Exception as e:
            print(f" 記憶の保存中にエラーが発生しました: {e}")

    def _save_signals(self, signals_data: dict):
        """新しいシグナルデータをファイルに上書き保存する"""
        try:
            with open(self.signals_file, "w", encoding="utf-8") as f_out:
                json.dump(signals_data, f_out, ensure_ascii=False, indent=4)
            print("📡 会話状態(Context)を更新しました。")
        except Exception as e:
            print(f" 信号の保存に失敗しました: {e}")

    def _get_current_signals(self) -> dict:
        """user_signals.jsonから現在のシグナル情報を読み込む。存在しない場合は空の辞書を返す。"""
        try:
            if os.path.exists(self.signals_file):
                with open(self.signals_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f" シグナルの読み込みに失敗しました: {e}")
        return {}

    def _update_signals_with_created_files(self, assistant_text: str):
        """AIが生成したテキストから『FILE: パス』を抽出し、直近で触ったファイルとして記憶に焼き付ける"""
        import re
        pattern = r"(?:FILE|File|Path|path):\s*([a-zA-Z0-9_\-\.\/]+)"
        files = re.findall(pattern, assistant_text)

        if files:
            current_signals = self._get_current_signals()
            recent_files = current_signals.setdefault("recent_files", [])

            for f in files:
                clean_file = f.strip()
                if clean_file not in recent_files:
                    recent_files.append(clean_file)

            current_signals["recent_files"] = recent_files[-5:]

            try:
                with open(self.signals_file, "w", encoding="utf-8") as f_out:
                    json.dump(current_signals, f_out, ensure_ascii=False, indent=4)
                print(f"📡 信号(Signals)を更新しました: 最近のファイル={current_signals['recent_files']}")
            except Exception as e:
                print(f" 信号の保存に失敗しました: {e}")

    
    # ✅ ナレッジ注入つきのHandler実行ヘルパー
    #    100点即実行・競合マージ・単独実行のすべての経路から呼ばれる。
    #    get_search_keywords を持つHandler（例: ChatHandler）にだけ、
    #    plugin_knowledge_dir / occupations_dir / historical_figures_dir を
    #    横断検索した結果を request.loaded_knowledge に積んでから handle() を呼ぶ。
    
    async def _invoke_handler(self, handler):
        if hasattr(handler, "get_search_keywords") and self.knowledge_manager is not None:
            try:
                keywords = handler.get_search_keywords(self.message)
            except Exception:
                keywords = []
                print(f"❌ {handler.__class__.__name__}.get_search_keywords で例外")
                traceback.print_exc()

            if keywords:
                merged: Dict[str, Any] = {}
                try:
                    merged.update(
                        self.knowledge_manager.search_by_keywords(self.plugin_knowledge_dir, keywords)
                    )
                    merged.update(
                        self.knowledge_manager.search_by_keywords(self.occupations_dir, keywords)
                    )
                    merged.update(
                        self.knowledge_manager.search_by_keywords(self.historical_figures_dir, keywords)
                    )
                except Exception as e:
                    print(f" ナレッジ検索中にエラー（続行します）: {e}")
                    traceback.print_exc()

                setattr(self.request, "loaded_knowledge", merged)

        return await handler.handle(self.request)

    async def route_and_execute(
        self,
        request,
        **kwargs,
    ):
        self.request = request
        self.message = request.message

        # ユーザー発話を履歴に追加
        self.context_manager.add_chat_history("user", self.message)

        
        # 📚 1. 安全なナレッジルーティング & キーワード抽出
        
        available_keys = []
        loaded_knowledges = []

        if self.knowledge_router:
            try:
                # IntentInspector用の利用可能なナレッジキー（Domain名）を取得
                if hasattr(self.knowledge_router, "domains"):
                    available_keys = [domain.name for domain in self.knowledge_router.domains]

                # ナレッジをルーティング
                route_result = self.knowledge_router.route(self.message)
                
                # ✅ 【エラー1解決】どんな型が返ってきても安全に反復可能な list に変換する
                matched_paths = []
                if route_result is not None:
                    if hasattr(route_result, "matched_files"):
                        matched_paths = route_result.matched_files
                    elif isinstance(route_result, list):
                        matched_paths = route_result
                    elif hasattr(route_result, "__iter__") and not isinstance(route_result, str):
                        matched_paths = list(route_result)
                    else:
                        matched_paths = [route_result]

                # ナレッジファイルのロード
                for path in matched_paths:
                    clean_path = str(path).strip()
                    # 起動基準パスの調整
                    full_path = os.path.join("backend/knowledge_store", clean_path)
                    if not os.path.exists(full_path):
                        full_path = os.path.join("knowledge_store", clean_path)

                    if os.path.exists(full_path):
                        with open(full_path, "r", encoding="utf-8") as f:
                            try:
                                loaded_knowledges.append(json.load(f))
                            except json.JSONDecodeError:
                                print(f" ナレッジファイルが破損しています: {full_path}")
                    else:
                        print(f"🔍 ナレッジファイルが見つかりません: {full_path}")

                # ✅ 【エラー2解決】PromptBuilder に安全にセット
                if hasattr(self.prompt_builder, "set_active_knowledge"):
                    self.prompt_builder.set_active_knowledge(loaded_knowledges)
                else:
                    self.prompt_builder.active_knowledge = loaded_knowledges  # type: ignore
                    print(" PromptBuilder に直接属性を代入しました。")

            except Exception as e:
                print(f" ナレッジルーティング中にエラー（続行します）: {e}")
                traceback.print_exc()
        # 🚨 2. メッセージ解析 (IntentInspector)
        
        # ✅ 【引数不足エラー解決】available_knowledge_keys をキーワード引数で安全に渡す
        try:
            inspector = IntentInspector(self.message, available_knowledge_keys=available_keys)
        except TypeError:
            # 万が一、古いIntentInspectorが残っていた場合のエラー回避策
            inspector = IntentInspector(self.message)  # type: ignore
            print(" 古い IntentInspector が検出されたため、フォールバックで初期化しました。")

        inspect_result = inspector.inspect()
        self.context_manager.apply_inspector_result(inspect_result)

        
        # 📸 画像データがある場合のファストパス
        
        image_data = getattr(self.request, "image_base64", None)

        if image_data:
            print("📸 画像データを受信！ OcrRecruitHandlerへ直接ルーティング")
            ocr_handler = OcrRecruitHandler()
            self.last_used_handler = "OcrRecruitHandler"
            self.active_context = None

            result = await ocr_handler.handle(self.message, image_data)
            
            if result:
                _, res_content = result
                self._save_assistant_response_and_state(res_content)

            return result

        
        # 現在のSignalsを取得
        
        current_signals = self._get_current_signals()
        self.active_context = current_signals.get("active_context")

        if current_signals:
            print(f"📡 現在の文脈: {current_signals}")

        scored_handlers = []

        
        # 各Handlerのスコアを計算
        
        for handler in self.handlers:
            handler_name = handler.__class__.__name__

            try:
                if hasattr(handler, "calculate_score"):
                    sig = inspect.signature(handler.calculate_score)

                    if len(sig.parameters) >= 2:
                        base_score = await handler.calculate_score(
                            self.message,
                            current_signals
                        )
                    else:
                        base_score = await handler.calculate_score(
                            self.message
                        )

                elif hasattr(handler, "can_handle"):
                    can_handle = await handler.can_handle(self.message)
                    base_score = 100 if can_handle else 0
                else:
                    base_score = 0

            except Exception:
                print(f"❌ {handler_name} のscore計算で例外")
                traceback.print_exc()
                base_score = 0

            bonus = self._get_feedback_bonus(self.message, handler_name)
            final_score = base_score + bonus

            estimated_size = getattr(
                handler,
                "estimate_size",
                lambda msg: 1000
            )(self.message)

            print(
                f"🔎 {handler_name}"
                f" -> ベース:{base_score}"
                f" 補正:{bonus}"
                f" 最終:{final_score}"
            )

            scored_handlers.append({
                "handler": handler,
                "score": final_score,
                "size": estimated_size
            })

        
        # スコア順に並び替え
        scored_handlers.sort(
            key=lambda h: h["score"],
            reverse=True
        )

        if not scored_handlers:
            return "text", "利用可能なHandlerがありません。"

        top = scored_handlers[0]
        second = (
            scored_handlers[1]
            if len(scored_handlers) >= 2
            else {
                "handler": None,
                "score": 0,
                "size": 0
            }
        )

        
        # RoutingDebugBlock生成
        
        debug_block = {
            "type": "RoutingDebugBlock",
            "props": {
                "selected": top["handler"].__class__.__name__,
                "handlers": [
                    {
                        "name": h["handler"].__class__.__name__,
                        "score": h["score"]
                    }
                    for h in scored_handlers
                    if h["score"] > 0
                ]
            }
        }

        
        # 共通：データ構造保証 & 警告ブロック回避処理
        
        def attach_debug_block(content: Any) -> Any:
            # 1. content が辞書型でない（単なる文字列など）場合、
            #    フロントエンドがクラッシュしないよう必ず {"message": ..., "blocks": []} にラップします
            if not isinstance(content, dict):
                return {
                    "message": str(content),
                    "blocks": []
                }
            
            # 2. すでに辞書型の場合は、blocks キーが存在することを保証します
            #    (未定義の RoutingDebugBlock は挿入しないため、フロントエンドの警告は完全に消えます)
            if "blocks" not in content:
                content["blocks"] = []

            return content
        
        # 100点なら即実行
        
        if top["score"] == 100:
            print(f"🎯 {top['handler'].__class__.__name__} が100点を獲得")
            self.last_used_handler = top["handler"].__class__.__name__
            result = await self._invoke_handler(top["handler"])

            if result is None:
                return "text", "処理に失敗しました。"

            res_type, res_content = result
            self._save_assistant_response_and_state(res_content)

            return res_type, attach_debug_block(res_content)

        
        # 全員低スコア
        
        if top["score"] < 40:
            return "text", {
                "message": "どのエージェントも処理できませんでした。",
                "blocks": [debug_block]
            }

        
        # 競合判定
        
        if (
            second["handler"] is not None
            and
            (top["score"] - second["score"]) <= 10
        ):
            print(f"🤔 競合:{top['handler'].__class__.__name__} vs {second['handler'].__class__.__name__}")
            total_size = top["size"] + second["size"]

            if total_size >= 20000:
                return "text", {
                    "message": f"{top['handler'].__class__.__name__} と {second['handler'].__class__.__name__} が競合しています。\nどちらを優先しますか？",
                    "blocks": [debug_block]
                }
                
            print("🚀 2つのHandlerを実行してマージします。")
            result1 = await self._invoke_handler(top["handler"])
            result2 = await self._invoke_handler(second["handler"])

            if result1 is None and result2 is None:
                return "text", {
                    "message": "両方のHandlerでエラーが発生しました。",
                    "blocks": [debug_block]
                }

            if result1 is None:
                res_type, res_content = result2
                self.last_used_handler = second["handler"].__class__.__name__
                self._save_assistant_response_and_state(res_content)
                return res_type, attach_debug_block(res_content)

            if result2 is None:
                res_type, res_content = result1
                self.last_used_handler = top["handler"].__class__.__name__
                self._save_assistant_response_and_state(res_content)
                return res_type, attach_debug_block(res_content)

            res_type1, res_content1 = result1
            res_type2, res_content2 = result2
            merged = self._merge_responses(res_content1, res_content2)

            self.last_used_handler = top["handler"].__class__.__name__
            final_type = "ui_code" if merged.get("blocks") else "text"
            self._save_assistant_response_and_state(merged)

            return final_type, attach_debug_block(merged)

        
        # 単独実行
        
        result = await self._invoke_handler(top["handler"])

        if result is None:
            return "text", {
                "message": "処理中にエラーが発生しました。",
                "blocks": [debug_block]
            }

        self.last_used_handler = top["handler"].__class__.__name__
        res_type, res_content = result
        self._save_assistant_response_and_state(res_content)

        return res_type, attach_debug_block(res_content)

    def _get_feedback_bonus(self, message, handler_name) -> int:
        try:
            if not os.path.exists(self.feedback_file):
                return 0

            with open(self.feedback_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            bonus = data.get(handler_name, 0)
            try:
                return int(bonus)
            except Exception:
                return 0
        except Exception:
            return 0

    def _merge_responses(self, c1: Any, c2: Any) -> dict:
        if not isinstance(c1, dict):
            c1 = {"message": str(c1), "blocks": []}

        if not isinstance(c2, dict):
            c2 = {"message": str(c2), "blocks": []}

        return {
            "message":
                c1.get("message", "")
                + "\n\n---\n\n"
                + c2.get("message", ""),

            "blocks":
                c1.get("blocks", [])
                + c2.get("blocks", [])
        }