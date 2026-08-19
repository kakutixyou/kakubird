# backend/api/services/handlers/ConversionJsonHandler.py

import json
import os
import zipfile
import uuid
import re
import textwrap
import traceback
from typing import Dict, Any, Tuple, Optional
from api.services.handlers.base_handler import BaseHandler
# 環境に合わせてパスを調整してください
from api.services.inspectors.IntentInSpector import IntentInspector


class ConversionJsonHandler(BaseHandler):
    """
    テキストのJSON化、およびJSONデータの英語翻訳（値のみ翻訳・キー維持）を
    統合して行うハンドラー。ファイルの一括処理とチャット直打ちの両方に対応。
    """

    def __init__(self, llm_service=None, knowledge_manager=None):
        """
        :param llm_service: LLMを呼び出すサービス
        :param knowledge_manager: ファイル操作を行う KnowledgeManager のインスタンス
        """
        super().__init__()
        self.llm_service = llm_service
        self.knowledge_manager = knowledge_manager
        
        # 1度にLLMに投げるキーの数（トークン数上限に合わせて調整してください）
        self.chunk_size = 50 

    async def can_handle(self, message: str) -> bool:
        msg = message.lower()
        keywords = ["json", "json形式", "json化", "jsonに変換", "convert json", "to json", "英訳", "翻訳", "translate"]
        return any(k in msg for k in keywords)

    async def calculate_score(self, message: str, signals=None) -> int:
        if message.strip().startswith("/json"):
            return 100

        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        # データ変換モードと判定された場合
        if analysis.get("mode") == "data_conversion":
            return analysis.get("score", 85)

        # 翻訳指示が含まれる場合もスコアを加算
        if "json" in message.lower() and ("英訳" in message or "翻訳" in message):
            return 90

        return 0

    async def handle(self, message: str, parsed_intent: Dict[str, Any] = None) -> Tuple[str, Any]:
        """
        メイン処理（BaseHandlerの規格に準拠）
        ※Orchestrator側が Dict を直接期待している場合は Tuple ではなく Dict を返すように変更してください。
        """
        print("🌍 [ConversionJsonHandler] JSONの変換・翻訳処理を開始します...")
        parsed_intent = parsed_intent or {}
        targets = parsed_intent.get("targets", [])

        try:
            # 
            # パターンA: ターゲットファイルが指定されている場合 (ZIP化処理)
            # 
            if targets and self.knowledge_manager:
                result_dict = self._process_files(targets)
                return ("ui_code", result_dict)

            # 
            # パターンB: チャットへの直打ちテキスト/JSONの場合
            # 
            # 1. テキストからJSONデータを構築/抽出する (旧File 2のロジック)
            parsed_original = self._extract_or_convert_to_json(message)
            
            if not parsed_original or len(parsed_original) == 0:
                return ("text", {"role": "ai", "content": "翻訳するJSONファイル、または有効なJSON形式のテキストが見つかりませんでした。"})

            # 2. LLMを使って英訳処理 (旧File 1のロジック)
            translated_dict = self._translate_in_chunks(parsed_original)

            # 3. フロントエンドのUIブロック用にフォーマットして返す
            response_dict = {
                "response_type": "ui_code",
                "message": "JSONデータの英訳が完了しました。以下の結果を確認してください。",
                "blocks": [
                    {
                        "type": "conversion_jsonBlock", 
                        "props": {
                            "originalJson": json.dumps(parsed_original, indent=2, ensure_ascii=False),
                            "translatedJson": json.dumps(translated_dict, indent=2, ensure_ascii=False),
                            "title": "JSON Translation Result"
                        }
                    }
                ]
            }
            return ("ui_code", response_dict)

        except Exception as e:
            traceback.print_exc()
            print(f" [ConversionJsonHandler] 全体エラー: {str(e)}")
            return ("text", {"role": "ai", "content": f"処理中にエラーが発生しました: {str(e)}"})

    # ---------------------------------------------------
    # ファイル処理系のメソッド
    # ---------------------------------------------------

    def _process_files(self, targets: list) -> dict:
        results = []
        translated_files = []

        for target_file_path in targets:
            try:
                assert self.knowledge_manager is not None
                original_content_str = self.knowledge_manager.read_file(target_file_path)
                if not original_content_str:
                    raise ValueError("ファイルが空、または読み込めませんでした。")
                
                parsed_original = json.loads(original_content_str)
                translated_dict = self._translate_in_chunks(parsed_original)
                
                formatted_json_str = json.dumps(translated_dict, ensure_ascii=False, indent=2)
                new_file_path = self._generate_en_path(target_file_path)
                
                success = self.knowledge_manager.write_file(new_file_path, formatted_json_str)

                if success:
                    results.append({
                        "status": "success",
                        "original_path": target_file_path,
                        "new_file_path": new_file_path
                    })
                    translated_files.append(new_file_path)
                else:
                    results.append({
                        "status": "error",
                        "original_path": target_file_path,
                        "message": "ファイルの保存に失敗しました。"
                    })

            except Exception as e:
                print(f" [ConversionJsonHandler] エラーが発生しました ({target_file_path}): {str(e)}")
                results.append({"status": "error", "original_path": target_file_path, "message": f"処理エラー: {str(e)}"})

        zip_download_url = self._create_zip(translated_files)

        return {
            "response_type": "ui_code",
            "message": f"{len(targets)}件中 {len(translated_files)}件 の翻訳処理が完了しました。",
            "blocks": [
                {
                    "type": "conversion_jsonBlock", 
                    "props": {
                        "results": results,
                        "zip_download_url": zip_download_url
                    }
                }
            ]
        }

    def _create_zip(self, translated_files: list) -> Optional[str]:
        if not translated_files:
            return None
            
        try:
            export_dir = os.path.join("data", "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            zip_filename = f"translated_jsons_{uuid.uuid4().hex[:8]}.zip"
            zip_filepath = os.path.join(export_dir, zip_filename)
            
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in translated_files:
                    actual_path = getattr(self.knowledge_manager, "get_absolute_path", lambda p: p)(file_path)
                    arcname = os.path.basename(file_path)
                    if os.path.exists(actual_path):
                        zipf.write(actual_path, arcname=arcname)
            
            return f"/api/files/download?path={zip_filepath}"
        except Exception as e:
            print(f" [ConversionJsonHandler] ZIP作成エラー: {str(e)}")
            return None

    def _generate_en_path(self, original_path: str) -> str:
        base_name, ext = os.path.splitext(original_path)
        if ext.lower() == '.json':
            return f"{base_name}.en.json"
        return f"{original_path}.en.json"

    # ---------------------------------------------------
    # LLM翻訳系のメソッド
    # ---------------------------------------------------

    def _translate_in_chunks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        JSONをチャンク分割してLLMで翻訳し結合する
        """
        if not self.llm_service:
            print(" LLMサービスが存在しないため、翻訳をスキップします。")
            return data

        keys = list(data.keys())
        translated_result = {}

        for i in range(0, len(keys), self.chunk_size):
            chunk_keys = keys[i:i + self.chunk_size]
            chunk_data = {k: data[k] for k in chunk_keys}
            
            prompt = self._build_prompt(json.dumps(chunk_data, ensure_ascii=False))
            translated_text = self.llm_service.generate_text(prompt)
            
            try:
                clean_text = translated_text.replace("```json", "").replace("```", "").strip()
                parsed_chunk = json.loads(clean_text)
                translated_result.update(parsed_chunk)
            except json.JSONDecodeError:
                print(" [ConversionJsonHandler] LLMが不正なJSONを返しました。原文を維持します。")
                translated_result.update(chunk_data) 

        return translated_result

    def _build_prompt(self, json_str: str) -> str:
        return f"""
以下のJSONデータの「値（Value）」部分だけを自然な英語に翻訳してください。
キー（Key）は絶対に翻訳したり変更したりしないでください。
結果は純粋なJSONフォーマットのみを出力してください。

【対象のJSON】
{json_str}
"""

    # ---------------------------------------------------
    # テキスト解析・JSON化系のメソッド (旧File2から統合)
    # ---------------------------------------------------

    def _extract_or_convert_to_json(self, message: str) -> dict:
        """
        生のJSON文字列か、または「キー：値」形式のテキストからJSON辞書を構築する
        """
        message = message.strip()
        
        # 1. まずはそのままJSONとしてパースを試みる
        try:
            return json.loads(message)
        except json.JSONDecodeError:
            pass
            
        # 2. マークダウンの```json ```が含まれている場合は抽出
        match = re.search(r'```(?:json)?(.*?)```', message, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
                
        # 3. どちらでもない場合、「りんご：Apple」のようなテキストベースの変換を試行
        lines = [x.strip() for x in message.splitlines() if x.strip()]
        data = {}

        for line in lines:
            if "：" in line:
                key, value = line.split("：", 1)
                data[key.strip()] = value.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
            elif "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip()
            elif "＝" in line:
                key, value = line.split("＝", 1)
                data[key.strip()] = value.strip()
            else:
                m = re.match(r"^(.+?)（(.+?)）$", line)
                if m:
                    data[m.group(1).strip()] = m.group(2).strip()

        return data

    def estimate_size(self, message: str) -> int:
        return len(message)