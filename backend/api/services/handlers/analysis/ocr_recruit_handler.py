# backend/api/services/handlers/ocr_recruit_handler.py
import base64
import json
import traceback
from typing import Tuple, Any, List, Optional
from pydantic import BaseModel, Field
from core.job_database import save_job_to_db
# ※ Google GenAI SDK (google-genai) を使用する想定
from google import genai
from google.genai import types

# ===
# 1. AIに確実なJSONを作らせるためのスキーマ定義 (Pydantic)
# ===
class SalaryRange(BaseModel):
    min: Optional[int] = Field(None, description="最低年収（円単位）")
    max: Optional[int] = Field(None, description="最高年収（円単位）")

class WorkStyle(BaseModel):
    average_overtime_hours: Optional[int] = Field(None, description="平均残業時間")
    remote_possible: bool = Field(False, description="リモートワーク可能か")
    project_selection: bool = Field(False, description="案件選択制度があるか")

class Company(BaseModel):
    name: str = Field(..., description="企業名")
    industry: Optional[str] = Field(None, description="業種")
    location: Optional[str] = Field(None, description="勤務地")

class OfferSummary(BaseModel):
    headline: Optional[str] = Field(None, description="求人のキャッチコピー")
    salary_range: Optional[SalaryRange] = None
    work_style: Optional[WorkStyle] = None

class DetectedPattern(BaseModel):
    word: str = Field(..., description="検出されたキーワード")
    count: int = Field(..., description="出現回数")

class TextAnalysis(BaseModel):
    work_life_balance_score: int = Field(..., description="ワークライフバランス (0-100)")
    technical_growth_score: int = Field(..., description="技術成長環境 (0-100)")
    growth_pressure_score: int = Field(..., description="成長プレッシャー (0-100)")
    ses_risk_score: int = Field(..., description="SES・客先常駐リスク (0-100)")
    abstract_expression_score: int = Field(..., description="抽象的表現の多さ (0-100)")
    detected_patterns: List[DetectedPattern] = []

class AiAnalysis(BaseModel):
    overall_label: str = Field(..., description="総合評価: 'white', 'gray_to_white', 'gray', 'black' のいずれか")
    analysis_comment: List[str] = Field(..., description="AI分析コメント（配列）")
    recommendation: List[str] = Field(..., description="面談で確認すべき質問（配列）")

class RecruitEvaluationSchema(BaseModel):
    company: Company
    offer_summary: OfferSummary
    recruitment_text_analysis: TextAnalysis
    ai_analysis: AiAnalysis

# ===
# 2. ハンドラー本体
# ===
class OcrRecruitHandler:
    """
    画像を直接受け取り、Gemini Visionを使って求人情報を構造化JSONに変換するハンドラー
    """
    
    async def handle(self, message: str, image_base64: str) -> Tuple[str, Any]:
        print("📸 OCR Recruit Handler 発動: Gemini Vision 解析モード")
        
        try:
            # 1. Base64文字列のクレンジング（"data:image/png;base64," のようなプレフィックスを除去）
            if "," in image_base64:
                image_base64 = image_base64.split(",")[-1]
            image_bytes = base64.b64decode(image_base64)
            
            # 2. Gemini APIのクライアント初期化
            client = genai.Client()
            
            # 3. Geminiに渡す画像オブジェクトを作成
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg" # 判別をサボってjpeg指定でもGeminiは賢く読んでくれます
            )
            
            prompt = f"""
            あなたは優秀なITエンジニア専門のキャリアコンサルタントです。
            添付された画像（求人票、スカウトメール、または企業の採用ページスクショ）を読み取り、
            エンジニア目線で分析を行って、指定されたJSONスキーマに沿って出力してください。
            
            ユーザーからの追加メッセージ: {message if message else "特になし"}
            """

            print("🤖 Geminiに画像とプロンプトを送信中...")
            
            # 4. Structured Outputs (構造化出力) を使って確実なJSONを取得
            response = client.models.generate_content(
                model='gemini-1.5-pro', # 速度重視なら gemini-1.5-flash に変更
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RecruitEvaluationSchema,
                    temperature=0.1 # ハルシネーションを防ぐため低めに設定
                ),
            )
            
# 5. 返ってきたJSON文字列を辞書型(dict)にパース
            evaluation_result = json.loads(response.text)
            company_name = evaluation_result.get("company", {}).get("name", "該当企業")
            
            # 🌟🌟🌟 ここで自動保存を実行！ 🌟🌟🌟
            save_job_to_db(evaluation_result)
            
            # 6. フロントエンドが待ち構えているフォーマットに包んで返す
            content = {
                # メッセージも「保存しました」に変えてあげると親切です
                "message": f"🤖 {company_name} の求人画像を解析し、データベースに保存しました！",
                "blocks": [
                    {
                        "type": "RecruitReportBlock",
                        "props": { "data": evaluation_result }
                    },
                    {
                        "type": "ChatActionBlock",
                        "props": {
                            "title": "次の一手:",
                            "actions": [
                                {
                                    "label": "この求人の懸念点を深掘り",
                                    "icon": "🚩",
                                    "next_prompt": f"{company_name}の求人について、SESリスクや残業の観点でもう少し詳しく教えて"
                                },
                                # 👇 自動保存になったので、ボタンの役割を「保存」から「一覧を見る」に変更！
                                {
                                    "label": "保存済みの求人一覧を見る",
                                    "icon": "📂",
                                    "next_prompt": "データベースに保存した求人データの一覧を表示して"
                                }
                            ]
                        }
                    }
                ]
            }
            return "ui_code", content

        except Exception as e:
            error_details = traceback.format_exc()
            print(f"🚨 OCR 解析エラー:\n{error_details}")
            return "text", "画像の解析中にエラーが発生しました。画像が不鮮明か、APIの制限に引っかかった可能性があります。"