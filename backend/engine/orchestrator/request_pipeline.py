# backend/services/orchestrator/request_pipeline.py

import json
import os
import traceback
from typing import Any, Tuple, List, Dict

# 依存モジュールのインポート
from api.services.inspectors.IntentInSpector import IntentInspector
from api.services.handlers.analysis.ocr_recruit_handler import OcrRecruitHandler
from .response_merger import ResponseMerger

class ChatRequestPipeline:
    """
    ユーザーからのリクエストを受け取り、ナレッジのロード、インテント解析、
    ハンドラーの評価とルーティング、そして最終的なレスポンスの生成までを一貫して行うクラス。
    """
    def __init__(
        self,
        handlers: List[Any],
        knowledge_router: Any,
        knowledge_manager: Any,
        plugin_knowledge_dir: str,
        occupations_dir: str,
        historical_figures_dir: str,
        prompt_builder: Any,
        context_manager: Any,
        state_store: Any,
        scorer: Any,
    ):
        self.handlers = handlers
        self.knowledge_router = knowledge_router
        self.knowledge_manager = knowledge_manager
        self.plugin_knowledge_dir = plugin_knowledge_dir
        self.occupations_dir = occupations_dir
        self.historical_figures_dir = historical_figures_dir
        self.prompt_builder = prompt_builder
        self.context_manager = context_manager
        self.state_store = state_store
        self.scorer = scorer

    async def _invoke_handler(self, handler: Any, request: Any) -> Any:
        """
        特定のハンドラーを実行する。
        get_search_keywordsを持つハンドラー（ChatHandlerなど）には、実行前にナレッジを注入する。
        """
        if hasattr(handler, "get_search_keywords") and self.knowledge_manager is not None:
            try:
                keywords = handler.get_search_keywords(request.message)
            except Exception:
                keywords = []
                print(f"❌ {handler.__class__.__name__}.get_search_keywords で例外が発生しました")
                traceback.print_exc()

            if keywords:
                merged: Dict[str, Any] = {}
                try:
                    merged.update(self.knowledge_manager.search_by_keywords(self.plugin_knowledge_dir, keywords))
                    merged.update(self.knowledge_manager.search_by_keywords(self.occupations_dir, keywords))
                    merged.update(self.knowledge_manager.search_by_keywords(self.historical_figures_dir, keywords))
                except Exception as e:
                    print(f" ナレッジ検索中にエラー（続行します）: {e}")
                    traceback.print_exc()

                setattr(request, "loaded_knowledge", merged)

        return await handler.handle(request)

    async def route_and_execute(self, request: Any) -> Tuple[str, Any]:
        """
        メインの処理フロー
        """
        message = request.message

        # 1. ユーザー発話を履歴に追加
        self.context_manager.add_chat_history("user", message)

        # 📚 2. ナレッジルーティング
        available_keys = []
        loaded_knowledges = []

        if self.knowledge_router:
            try:
                if hasattr(self.knowledge_router, "domains"):
                    available_keys = [domain.name for domain in self.knowledge_router.domains]

                route_result = self.knowledge_router.route(message)
                
                # 型のブレを吸収して安全にリスト化
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
                    full_path = os.path.join("backend/knowledge_store", clean_path)
                    if not os.path.exists(full_path):
                        full_path = os.path.join("knowledge_store", clean_path)

                    if os.path.exists(full_path):
                        with open(full_path, "r", encoding="utf-8") as f:
                            try:
                                loaded_knowledges.append(json.load(f))
                            except json.JSONDecodeError:
                                print(f" ナレッジファイルが破損しています: {full_path}")

                # PromptBuilderにセット
                if hasattr(self.prompt_builder, "set_active_knowledge"):
                    self.prompt_builder.set_active_knowledge(loaded_knowledges)
                else:
                    self.prompt_builder.active_knowledge = loaded_knowledges 
            except Exception as e:
                print(f" ナレッジルーティング中にエラー（続行します）: {e}")
                traceback.print_exc()

        # 🚨 3. メッセージ解析 (IntentInspector) - 1リクエストでここ1回だけ実行！
        try:
            inspector = IntentInspector(message, available_knowledge_keys=available_keys)
        except TypeError:
            inspector = IntentInspector(message)

        inspect_result = inspector.inspect()
        self.context_manager.apply_inspector_result(inspect_result)
        
        # ★ここで request オブジェクトに解析結果を直接生やす（ChatHandler等はこれを使う）
        setattr(request, "intent_analysis", inspect_result)

        # 📸 4. 画像データがある場合のファストパス (OcrRecruitHandler)
        image_data = getattr(request, "image_base64", None)
        if image_data:
            print("📸 画像データを受信！ OcrRecruitHandlerへ直接ルーティング")
            ocr_handler = OcrRecruitHandler()
            result = await ocr_handler.handle(message, image_data)
            if result:
                _, res_content = result
                self.state_store.save_assistant_response_and_state(res_content)
            return result

        # 📡 5. シグナル（文脈）の取得
        current_signals = self.state_store.get_current_signals()
        if current_signals:
            print(f"📡 現在の文脈: {current_signals}")

        # 🎯 6. ハンドラーのスコアリング
        scored_handlers = await self.scorer.score_all(self.handlers, message, current_signals, inspect_result)

        if not scored_handlers:
            return "text", "利用可能なHandlerがありません。"

        top = scored_handlers[0]
        second = scored_handlers[1] if len(scored_handlers) >= 2 else {"handler": None, "score": 0, "size": 0}

        # デバッグブロックの生成（画面表示用）
        debug_block = ResponseMerger.build_routing_debug_block(scored_handlers)

        # 🚀 7. ルーティングの分岐実行
        
        # パターンA: 100点即実行
        if top["score"] == 100:
            print(f"🎯 {top['handler'].__class__.__name__} が100点を獲得")
            result = await self._invoke_handler(top["handler"], request)
            if result is None:
                return "text", "処理に失敗しました。"
            
            res_type, res_content = result
            self.state_store.save_assistant_response_and_state(res_content)
            return res_type, ResponseMerger.attach_debug_block(res_content)

        # パターンB: 全員低スコア (40点未満)
        if top["score"] < 40:
            return "text", {
                "message": "どのエージェントも処理できませんでした。",
                "blocks": [debug_block]
            }

        # パターンC: 競合判定 (スコア差が10以内)
        if second["handler"] is not None and (top["score"] - second["score"]) <= 10:
            print(f"🤔 競合:{top['handler'].__class__.__name__} vs {second['handler'].__class__.__name__}")
            total_size = top["size"] + second["size"]

            # トークン（サイズ）が大きすぎる場合はユーザーに選択を委ねる
            if total_size >= 20000:
                return "text", {
                    "message": f"{top['handler'].__class__.__name__} と {second['handler'].__class__.__name__} が競合しています。\nどちらを優先しますか？",
                    "blocks": [debug_block]
                }
                
            print("🚀 2つのHandlerを実行してマージします。")
            result1 = await self._invoke_handler(top["handler"], request)
            result2 = await self._invoke_handler(second["handler"], request)

            if result1 is None and result2 is None:
                return "text", {"message": "両方のHandlerでエラーが発生しました。", "blocks": [debug_block]}

            if result1 is None:
                res_type, res_content = result2
                self.state_store.save_assistant_response_and_state(res_content)
                return res_type, ResponseMerger.attach_debug_block(res_content)

            if result2 is None:
                res_type, res_content = result1
                self.state_store.save_assistant_response_and_state(res_content)
                return res_type, ResponseMerger.attach_debug_block(res_content)

            # 両方成功した場合はマージ
            res_type1, res_content1 = result1
            res_type2, res_content2 = result2
            merged = ResponseMerger.merge_responses(res_content1, res_content2)
            
            final_type = "ui_code" if merged.get("blocks") else "text"
            self.state_store.save_assistant_response_and_state(merged)
            return final_type, ResponseMerger.attach_debug_block(merged)

        # パターンD: 単独実行
        result = await self._invoke_handler(top["handler"], request)
        if result is None:
            return "text", {"message": "処理中にエラーが発生しました。", "blocks": [debug_block]}

        res_type, res_content = result
        self.state_store.save_assistant_response_and_state(res_content)
        return res_type, ResponseMerger.attach_debug_block(res_content)