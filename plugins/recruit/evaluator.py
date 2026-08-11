import os
import json
import re
import httpx
from pathlib import Path
import copy

# =========================================================
# Web Search Plugin Import
# =========================================================
try:
    from plugins.recruit.web_search import search_company
except ImportError:
    try:
        from .web_search import search_company
    except ImportError:
        def search_company(name: str) -> str:
            return ""

# ルールファイルのパス
PLUGIN_DIR = os.path.dirname(__file__)
RULES_DIR = os.path.join(PLUGIN_DIR, "rules")

# =========================================================
# フロントエンド (RecruitReportBlock) と完全一致するスキーマ
# =========================================================
OUTPUT_SCHEMA = {
    "company": {
        "name": "不明な企業",
        "industry": None,
        "location": None
    },
    "offer_summary": {
        "headline": "【オフライン解析】文章から自動抽出したデータです",
        "salary_range": { "min": None, "max": None },
        "work_style": { "average_overtime_hours": None, "remote_possible": None, "project_selection": None }
    },
    "recruitment_text_analysis": {
        "work_life_balance_score": 50,
        "technical_growth_score": 50,
        "growth_pressure_score": 50,
        "ses_risk_score": 50,
        "abstract_expression_score": 50,
        "detected_patterns": []
    },
    "ai_analysis": {
        "overall_label": "gray",
        "analysis_comment": [
            "⚠️ AI（Ollama）がオフラインのため、高度な文脈解析は行えませんでした。",
            "💡 その代わり、正規表現エンジンとルール辞書を用いて文章を自動解析しました。"
        ],
        "recommendation": [
            "Ollamaを起動して再度送信すると、より詳細なAI分析が行われます。"
        ]
    }
}

def load_json_rule(filename: str) -> dict:
    file_path = os.path.join(RULES_DIR, filename)
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Rule Load Error ({filename}): {e}")
        return {}

# =========================================================
# 🤖 Ollama 呼び出し関数
# =========================================================
def _call_ollama(system: str, user: str) -> str:
    ollama_url = os.getenv("OLLAMA_URL", "http://100.85.26.46:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma3")
    
    res = httpx.post(
        f"{ollama_url}/api/chat",
        json={
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": False
        },
        timeout=15.0
    )
    res.raise_for_status()
    return res.json()["message"]["content"].strip()

# =========================================================
# メインの評価ロジック
# =========================================================
def evaluate(ocr_text: str) -> dict:
 
    # -----------------------------------------------------
    # 【フェーズ1】ルールベース評価 (JSON辞書の完全活用)
    # -----------------------------------------------------
    agent_profile = {}
    agent_greeting = ""
    agent_writing_style = ""
    black_rules = load_json_rule("black_patterns.json")
    white_rules = load_json_rule("white_patterns.json")
    
    detected = []
    
    # 全5項目の初期スコア
    wlb_score = 50
    tech_score = 50
    pressure = 50
    ses_risk = 50
    abstract_score = 50
    
    # 🚨 ブラック検知 (black_patterns.json)
    if black_rules:
        fake_white = black_rules.get("fake_white_flags", {})
        for kw in fake_white.get("keywords", []):
            if kw in ocr_text:
                detected.append({"word": kw, "count": ocr_text.count(kw)})
                abstract_score += fake_white.get("risk_score", 15)
                pressure += 5

        hidden_dispatch = black_rules.get("hidden_dispatch_flags", {})
        for kw in hidden_dispatch.get("keywords", []):
            if kw in ocr_text:
                detected.append({"word": kw, "count": ocr_text.count(kw)})
                ses_risk += hidden_dispatch.get("risk_score", 15)
                tech_score -= 10

        no_record = black_rules.get("no_record_warnings", {})
        for kw in no_record.get("keywords", []):
            if kw in ocr_text:
                detected.append({"word": kw, "count": ocr_text.count(kw)})
                abstract_score += no_record.get("risk_score", 10)
                
        pressure_flags = black_rules.get("pressure_flags", {"keywords": ["圧倒的成長", "成果主義", "起業", "幹部候補", "裁量"], "risk_score": 15})
        for kw in pressure_flags.get("keywords", []):
            if kw in ocr_text:
                detected.append({"word": f"🔥 {kw}", "count": ocr_text.count(kw)})
                pressure += pressure_flags.get("risk_score", 15)
                wlb_score -= 10
                
    # 🌟 株式会社RJCなどのような「未経験特化型SES」を炙り出す専用ロジック
    if "未経験" in ocr_text and "研修" in ocr_text:
        detected.append({"word": "未経験研修（SES示唆）", "count": 1})
        ses_risk += 25
        tech_score -= 15

    # 🌟 「老舗なのに実績不透明」な隠れSESリスク検知
    founded_year_match = re.search(r'設立.*?([12][0-9]{3})年', ocr_text)
    is_old_company = False
    
    if founded_year_match:
        try:
            if 2026 - int(founded_year_match.group(1)) >= 10:
                is_old_company = True
        except ValueError:
            pass
            
    if not is_old_company:
         founded_years_match = re.search(r'設立.*?([1-9][0-9])年', ocr_text)
         if founded_years_match:
             try:
                 if int(founded_years_match.group(1)) >= 10:
                     is_old_company = True
             except ValueError:
                 pass

    if is_old_company:
        track_record_keywords = ["導入実績", "主要取引先", "自社開発", "受託開発", "自社プロダクト", "開発実績"]
        has_track_record = any(kw in ocr_text for kw in track_record_keywords)
        
        if not has_track_record:
            detected.append({"word": "🕵️ 老舗なのに実績不透明（隠れSES警戒）", "count": 1})
            ses_risk += 20
            abstract_score += 15
    # （evaluator.py のフェーズ1、ブラック検知のループ内に追加）
        
        fixed_overtime = black_rules.get("fixed_overtime_flags", {})
        for kw in fixed_overtime.get("keywords", []):
            if kw in ocr_text:
                detected.append({"word": f"⚠️ {kw}", "count": ocr_text.count(kw)})
                abstract_score += fixed_overtime.get("risk_score", 20)
                wlb_score -= 15 # みなし残業はWLBに直結するため、WLBスコアをガッツリ下げる
                pressure += 10
    # ✨ ホワイト検知 (white_patterns.json)
    if white_rules:
        for kw in white_rules.get("objective_data", []):
            if kw in ocr_text:
                detected.append({"word": f"✨ {kw}", "count": ocr_text.count(kw)})
                wlb_score += 15
                abstract_score -= 10

        for kw in white_rules.get("solid_systems", []):
            if kw in ocr_text:
                detected.append({"word": f"✨ {kw}", "count": ocr_text.count(kw)})
                wlb_score += 10
                
        tech_env = white_rules.get("tech_environment", ["モダンな", "コードレビュー", "勉強会", "カンファレンス", "技術書", "フルスタック", "アジャイル", "自社開発"])
        for kw in tech_env:
            if kw in ocr_text:
                detected.append({"word": f"💻 {kw}", "count": ocr_text.count(kw)})
                tech_score += 15
                ses_risk -= 5

    # リミッター (スコアが 0〜100 の範囲に収まるようにする)
    wlb_score = max(0, min(100, wlb_score))
    tech_score = max(0, min(100, tech_score))
    pressure = max(0, min(100, pressure))
    ses_risk = max(0, min(100, ses_risk))
    abstract_score = max(0, min(100, abstract_score))

    base_result = copy.deepcopy(OUTPUT_SCHEMA)
    base_result["recruitment_text_analysis"]["work_life_balance_score"] = wlb_score
    base_result["recruitment_text_analysis"]["technical_growth_score"] = tech_score
    base_result["recruitment_text_analysis"]["growth_pressure_score"] = pressure
    base_result["recruitment_text_analysis"]["ses_risk_score"] = ses_risk
    base_result["recruitment_text_analysis"]["abstract_expression_score"] = abstract_score
    
    if ses_risk >= 70 or pressure >= 80:
        base_result["ai_analysis"]["overall_label"] = "black"
    elif wlb_score >= 80 and ses_risk < 60:
        base_result["ai_analysis"]["overall_label"] = "white"

    # =====================================================
    # 🌟 オフライン情報抽出エンジン（正規表現）
    # =====================================================
    company_match = re.search(r'([^\n]*(?:株式会社|合同会社|Inc\.|Corp\.)[^\n]*)', ocr_text)
    if company_match:
        base_result["company"]["name"] = company_match.group(1).strip()[:30]
    else:
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        for line in lines[:5]:
            if 2 <= len(line) <= 20 and "求人" not in line and "募集" not in line:
                base_result["company"]["name"] = line + "（推定）"
                break
                
    # 🌐 NEW: 抽出した企業名を使ってBrave APIで口コミを検索する
    web_snippets = ""
    company_name = base_result["company"].get("name", "")
    if company_name and "不明" not in company_name and "推定" not in company_name:
        print(f"🔍 企業名「{company_name}」でWeb検索(口コミ・評判)を開始します...")
        try:
            web_snippets = search_company(company_name)
            if web_snippets:
                base_result["ai_analysis"]["analysis_comment"].append(f"🌐 Web上で「{company_name}」の口コミ・評判データを取得しました。")
                detected.append({"word": "🌐 Web口コミ情報あり", "count": 1})
        except Exception as e:
            print(f"Web Search Failed: {e}")

    salary_matches = re.findall(r'([0-9]{2,4})(?:万|万円)', ocr_text)
    if salary_matches:
        numbers = [int(m) * 10000 for m in salary_matches]
        if len(numbers) >= 2:
            base_result["offer_summary"]["salary_range"]["min"] = min(numbers)
            base_result["offer_summary"]["salary_range"]["max"] = max(numbers)
        elif len(numbers) == 1:
            base_result["offer_summary"]["salary_range"]["min"] = numbers[0]
            base_result["offer_summary"]["salary_range"]["max"] = numbers[0]
            
        min_salary = base_result["offer_summary"]["salary_range"].get("min")
        if min_salary and 1000000 <= min_salary < 3500000:
            detected.append({"word": "💸 低水準な給与（350万未満）", "count": 1})
            base_result["ai_analysis"]["analysis_comment"].append(
                f"⚠️ 提示されている下限給与（{min_salary // 10000}万円）が相場より低い水準です。評価制度や昇給ペースを必ず確認してください。"
            )
            
    prefectures = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
    for pref in prefectures:
        pref_match = re.search(r'([^\n]*' + pref + r'[都道府県]?[^\n]*)', ocr_text)
        if pref_match:
            loc = pref_match.group(1).strip()
            loc = re.sub(r'^(勤務地|所在地|アクセス)[：:\s]+', '', loc)
            base_result["company"]["location"] = loc[:30]
            break
            
    overtime_match = re.search(r'残業.*?([0-9]{1,3})\s*(?:時間|h|H)', ocr_text, flags=re.IGNORECASE)
    if overtime_match:
        base_result["offer_summary"]["work_style"]["average_overtime_hours"] = int(overtime_match.group(1))
        
    if re.search(r'(リモート|在宅|テレワーク)', ocr_text):
        base_result["offer_summary"]["work_style"]["remote_possible"] = True

    base_result["recruitment_text_analysis"]["detected_patterns"] = detected
    # =====================================================
    # ⏰ 勤務時間・就業時間の明記チェック
    # =====================================================
    # 「勤務時間」「フレックス」という単語や、「09:00～18:00」のような時間表記を探す
    working_hours_match = re.search(
        r'(勤務時間|就業時間|フレックス|コアタイム|[0-9]{1,2}[:：][0-9]{2}\s*[～\-]\s*[0-9]{1,2}[:：][0-9]{2})',
        ocr_text
    )
    
    working_hours_keywords = [
        "勤務時間",
        "就業時間",
        "所定労働時間",
        "実働",
        "フレックス",
        "フレックスタイム",
        "コアタイム",
        "スーパーフレックス",
        "裁量労働制",
        "時差出勤"
    ]
    has_working_hours = (
    working_hours_match is not None
    or any(k in ocr_text for k in working_hours_keywords))
    
    risk = (
    ses_risk * 0.4 +
    pressure * 0.3 +
    abstract_score * 0.3
)
    if risk < 25:
        base_result["ai_analysis"]["overall_label"] = "white"

    elif risk < 40:
        base_result["ai_analysis"]["overall_label"] = "light_gray_to_white"

    elif risk < 55:
        base_result["ai_analysis"]["overall_label"] = "gray_to_white"

    elif risk < 70:
        base_result["ai_analysis"]["overall_label"] = "gray"

    elif risk < 85:
        base_result["ai_analysis"]["overall_label"] = "gray_to_black"

    else:
        base_result["ai_analysis"]["overall_label"] = "black"
    has_working_hours_info = working_hours_match or any(keyword in ocr_text for keyword in working_hours_keywords)
    if has_working_hours_info:
        detected.append({"word": "⏰ 勤務形態の明記あり（透明性高）", "count": 1})
        current_wlb = base_result["recruitment_text_analysis"]["work_life_balance_score"]
        current_abs = base_result["recruitment_text_analysis"]["abstract_expression_score"]

        base_result["recruitment_text_analysis"]["work_life_balance_score"] = min(100, current_wlb + 10)
        base_result["recruitment_text_analysis"]["abstract_expression_score"] = max(0, current_abs - 10)
    else:
        detected.append({"word": "⚠️ 勤務時間の明記なし（要注意）", "count": 1})
        current_wlb = base_result["recruitment_text_analysis"]["work_life_balance_score"]
        current_abs = base_result["recruitment_text_analysis"]["abstract_expression_score"]

        base_result["recruitment_text_analysis"]["abstract_expression_score"] = min(100, current_abs + 15)
        base_result["recruitment_text_analysis"]["work_life_balance_score"] = max(0, current_wlb - 15)
        base_result["ai_analysis"]["analysis_comment"].append(
            "⚠️ 勤務時間やコアタイムが明記されていません。常駐先依存（SES）や、裁量労働制で長時間労働になるリスクがあります。"
        )
    # -----------------------------------------------------
    # 【フェーズ2】AI（Ollama）による高度な分析に挑戦
    # -----------------------------------------------------
    try:
        system_prompt = (
            "あなたはプロのITエンジニア専門転職エージェントです。ユーザーが提供する求人情報を分析し、"
            "必ず以下のJSONスキーマと全く同じ構造で出力してください。JSON以外のテキストは一切含めないでください。\n\n"
            "【🚨重要ルール】\n"
            "・給与や残業時間、勤務地、業種などの情報が記載されていない場合は、妄想せずに必ず `null` を設定してください。\n"
            "・情報が極端に少ないスカウトメールであっても、必ずすべてのJSONキーを含めて出力してください。\n\n"
            "```json\n"
            "{\n"
            "  \"company\": { \"name\": \"企業名\", \"industry\": \"業種 (不明ならnull)\", \"location\": \"勤務地 (不明ならnull)\" },\n"
            "  \"offer_summary\": { \"headline\": \"求人のキャッチコピー\", \"salary_range\": { \"min\": 4000000, \"max\": 8000000 }, \"work_style\": { \"average_overtime_hours\": 20, \"remote_possible\": true, \"project_selection\": false } },\n"
            "  \"recruitment_text_analysis\": { \"work_life_balance_score\": 70, \"technical_growth_score\": 80, \"growth_pressure_score\": 40, \"ses_risk_score\": 20, \"abstract_expression_score\": 30, \"detected_patterns\": [ { \"word\": \"キーワード\", \"count\": 1 } ] },\n"
            "  \"ai_analysis\": { \"overall_label\": \"white または gray_to_white または gray または black\", \"analysis_comment\": [ \"コメント1\", \"コメント2\" ], \"recommendation\": [ \"質問1\", \"質問2\" ] }\n"
            "}\n"
            "```"
        )
        
        detected_words = [d['word'] for d in detected]
        
        user_prompt = (
            f"以下の求人テキストを分析し、指定されたJSONフォーマットで出力してください。\n\n"
            f"【💡ルールベースエンジンの事前分析データ（参考）】\n"
            f"・検知された特徴的キーワード: {detected_words}\n"
            f"・WLBスコア: {wlb_score}/100\n"
            f"・技術成長スコア: {tech_score}/100\n"
            f"・プレッシャースコア: {pressure}/100\n"
            f"・SESリスクスコア: {ses_risk}/100\n"
            f"・抽象的表現スコア: {abstract_score}/100\n\n"
        )
        

        # 🌐 Webの検索結果があればプロンプトに流し込む！
        if web_snippets:
            user_prompt += (
                f"【🌐 Web検索で得られた企業の評判・口コミ（重要）】\n"
                f"以下のネットの口コミも踏まえて、実際の労働環境を「analysis_comment」に厳しく反映してください。\n"
                f"{web_snippets}\n\n"
            )
            
        user_prompt += f"【求人テキスト】\n{ocr_text}"
        
        ai_response_text = _call_ollama(system_prompt, user_prompt)
        
        # JSON部分を安全に抽出（マークダウンが無い場合にも対応）
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = ai_response_text.strip()
        ai_result = json.loads(json_str)
        # JSONスキーマのバリデーション（最低限のキーが存在するか）
        if "company" in ai_result and "offer_summary" in ai_result and "recruitment_text_analysis" in ai_result and "ai_analysis" in ai_result:
            return ai_result    
        else:
            print("⚠️ AIの返答はJSON形式でしたが、スキーマが不完全でした。オフライン解析結果を返します。")
            return base_result
    except Exception as e:
        print(f"⚠️ AI分析中にエラーが発生しました: {e}")
        return base_result
    