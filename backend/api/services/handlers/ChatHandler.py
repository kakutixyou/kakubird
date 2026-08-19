# chathandler.py
import json
from typing import Any, Dict, List, Optional, Tuple

from api.services.handlers.base_handler import BaseHandler
from api.services.inspectors.IntentInSpector import IntentInspector


class ChatHandler(BaseHandler):
    
    """
    通常会話・システム仕組み説明・自己防衛(メンタル/リーガル)・
    職業ナレッジ(単元マッピング/歴史人物)への応答を担当するHandler。

    ファイルI/O（knowledgeフォルダの検索・読み込み）は一切行わない。
    ・occupation_titles / historical_figures_titles は Orchestrator が
      KnowledgeManager 経由で起動時に読み込んで渡す
    ・request.loaded_knowledge は Orchestrator が実行直前に
      KnowledgeManager.search_by_keywords() の結果を積んで渡す
    """

    # 「歴史人物について聞いている」と判定するトリガーワード
    HISTORY_TRIGGER_WORDS = [
        "偉人", "歴史上", "歴史の", "有名な人", "誰がいる", "人物", "歴史人物",
        "世界史", "日本史", "歴史", "存在するか", "テスト"
    ]

    def __init__(
        self,
        occupation_titles: Optional[List[str]] = None,
        historical_figures_titles: Optional[List[str]] = None,
        debug_knowledge_titles: Optional[List[str]] = None, # 👈 追加
    ):
        self.occupation_titles = occupation_titles or []
        self.historical_figures_titles = historical_figures_titles or []
        self.debug_knowledge_titles = debug_knowledge_titles or [] # 👈 追加

    # ===
    # マッチング（開発ナレッジ）を追加
    # ===
    def _match_debug_knowledge(self, message: str) -> Optional[str]:
        # JSONの title や keywords が Orchestrator 側から渡される想定
        for title in self.debug_knowledge_titles:
            if title and title.lower() in message.lower():
                return title
        
        # もし特定のキーワード（例：「プロンプト」「デバッグ」）で汎用的に
        # 反応させたい場合は、ここの条件を工夫します。
        return None
    
    # スコア計算
    

    async def calculate_score(self, message: str, current_signals: dict = None) -> int:
        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        # 🚨 パターンS：自己防衛（メンタル・リーガル）モード
        # 限界を迎えている時は、他のあらゆるハンドラーを差し置いて最優先で発火させる（確定100点）
        if analysis.get("mode") == "self_defense":
            return 100

        # ---------------------------------------------------------
        # パターンA：システムの仕組みやルールについて聞かれている場合
        # ---------------------------------------------------------
        if analysis["mode"] == "system_inquiry":
            return analysis["score"]

        # ---------------------------------------------------------
        # パターンO：職業名 or 歴史人物名がメッセージに含まれている場合
        # ---------------------------------------------------------
        if self._match_occupation(message) or self._match_historical_figure(message):
            return 95

        # ---------------------------------------------------------
        # パターンD：開発ナレッジがメッセージに含まれている場合
        # ---------------------------------------------------------
        if self._match_debug_knowledge(message):
            return 90

        # ---------------------------------------------------------
        # パターンB：どの専門分野（デプロイ、UI、JSON等）でもない場合
        # ---------------------------------------------------------
        if analysis["mode"] == "unknown":
            score = 60
            active_context = current_signals.get("active_context") if current_signals else None
            if active_context:
                score = 45

            if len(message.strip()) < 10:
                score = 70
            return min(score, 85)

        return 0

    def estimate_size(self, message: str) -> int:
        return 500
    # マッチング（職業名 / 歴史人物名）

    def _match_occupation(self, message: str) -> Optional[str]:
        for title in self.occupation_titles:
            if title and title in message:
                return title
        return None

    def _match_historical_figure(self, message: str) -> Optional[str]:
        for name in self.historical_figures_titles:
            if name and name in message:
                return name
        return None

    def _is_history_question(self, message: str) -> bool:
        return any(w in message for w in self.HISTORY_TRIGGER_WORDS)

    
    # ナレッジ検索キーワード（Orchestratorが呼び出す）
    def get_search_keywords(self, message: str) -> list:
        # 技術系 + 防衛系トリガーキーワード
        base_keywords = [
            # 技術系
            "react", "electron", "aws", "docker", "github", "flask", "fastapi", "python", "sql", "video", "ui",
            # 防衛系 (mental.json, legal.json などを引っ掛けるため)
            "法律", "下請法", "労働", "メンタル", "限界", "疲れた", "終わらない", "スケジュール", "理不尽", "ガントチャート"
        ]
        candidates = base_keywords + self.occupation_titles + self.historical_figures_titles
        return [kw for kw in candidates if kw.lower() in message.lower()]

    
    # 応答組み立て：職業（単元マッピング）
    # ===
    # 応答組み立て：開発ナレッジ・デバッグ履歴
    # ===
    def _build_debug_knowledge_response(self, matched_title: str, loaded_knowledge: dict) -> str:
        # loaded_knowledge の中から該当するデータを検索
        record = next(
            (d for d in loaded_knowledge.values()
             if d.get("title") == matched_title or d.get("category") in ["debug_history", "prompt_engineering"]),
            None
        )
        
        if record is None:
            return f"「{matched_title}」に関する開発ノウハウが見つかりませんでした。"

        # JSONの各フィールドからMarkdownを組み立てる
        lines = [
            f"## 🛠️ 開発ナレッジ: {record.get('title', matched_title)}", 
            "",
            record.get("summary", ""),
            ""
        ]

        # 結論・結果
        result_data = record.get("result", {})
        if result_data.get("final_response"):
            lines.append(f"**📌 結論**: {result_data['final_response']}")
            lines.append("")

        # 得られた教訓 (lessons_learned)
        lessons = record.get("lessons_learned", [])
        if lessons:
            lines.append("### 💡 得られた教訓")
            for lesson in lessons:
                lines.append(f"- {lesson}")
            lines.append("")

        # 会話例 (conversation_examples) - アプリ内で「会話」として見せるのに最適
        examples = record.get("conversation_examples", [])
        if examples:
            lines.append("### 💬 過去のQA例")
            for ex in examples:
                lines.append(f"**Q**: {ex.get('user', '')}")
                lines.append(f"**A**: {ex.get('assistant', '')}")
                lines.append("")

        return "\n".join(lines)

    def _build_occupation_response(self, matched_title: str, loaded_knowledge: dict) -> str:
        occ = next(
            (d for d in loaded_knowledge.values()
             if d.get("title") == matched_title and "subjects" in d),
            None
        )
        if occ is None:
            return f"「{matched_title}」についての知識データが見つかりませんでした。"

        lines = [f"## {occ['title']}（{occ.get('category', '')}）", "", occ.get("summary", ""), ""]

        math_units = occ.get("subjects", {}).get("math", [])
        if math_units:
            lines.append("### 📐 数学とのつながり")
            lines += [f"- **{u['stage']} {u['unit']}**：{u['connection']}" for u in math_units]
            lines.append("")

        science_units = occ.get("subjects", {}).get("science", [])
        if science_units:
            lines.append("### 🔬 理科とのつながり")
            lines += [f"- **{u['stage']} {u['unit']}**：{u['connection']}" for u in science_units]

        return "\n".join(lines)

    
    # 応答組み立て：職業 → 歴史人物一覧
    

    def _build_history_response(self, matched_title: str, loaded_knowledge: dict) -> str:
        record = next(
            (d for d in loaded_knowledge.values()
             if d.get("occupation_title") == matched_title and "history_figures" in d),
            None
        )
        if record is None:
            return f"「{matched_title}」に関する歴史人物データがまだありません。"

        world = record["history_figures"].get("world_history")
        japan = record["history_figures"].get("japan_history")

        if world in (None, "該当なし") and japan in (None, "該当なし"):
            return f"「{matched_title}」として特に有名な歴史上の人物は、現時点のデータでは該当なしです。"

        lines = [f"## {matched_title}として知られる歴史上の人物", ""]

        if japan not in (None, "該当なし"):
            lines.append("### 🇯🇵 日本史")
            for p in japan:
                lines.append(f"- **{p['name']}**（{p['era']}）：{p['achievement']}")
                lines.append(f"  → {p['connection']}")
            lines.append("")

        if world not in (None, "該当なし"):
            lines.append("### 🌍 世界史")
            for p in world:
                lines.append(f"- **{p['name']}**（{p['era']}）：{p['achievement']}")
                lines.append(f"  → {p['connection']}")

        return "\n".join(lines)

    
    # 応答組み立て：人物名 → 個人プロフィール
    

    def _build_person_response(self, matched_name: str, loaded_knowledge: dict) -> str:
        for data in loaded_knowledge.values():
            hf = data.get("history_figures")
            if not hf:
                continue
            for group_key, group_label in (("japan_history", "🇯🇵 日本史"), ("world_history", "🌍 世界史")):
                people = hf.get(group_key)
                if isinstance(people, list):
                    for p in people:
                        if p.get("name") == matched_name:
                            lines = [
                                f"## {p['name']}（{p['era']}）",
                                "",
                                p["achievement"],
                                "",
                                f"職業との関連：{data.get('occupation_title', '')}",
                                f"→ {p['connection']}",
                            ]
                            return "\n".join(lines)
        return f"「{matched_name}」についての知識データが見つかりませんでした。"

    
    # ハンドル本体
    

    def _log_debug(self, message: str): 
        print(f"🔎 [ChatHandler] {message}", flush=True)

    async def handle(self, request) -> Tuple[str, Any]:
        message = request.message if hasattr(request, "message") else ""
        inspector = IntentInspector(message)
        analysis = inspector.inspect()
        loaded_knowledge = getattr(request, "loaded_knowledge", {}) or {}

        self._log_debug(f"受信メッセージ: {message!r}")
        self._log_debug(f"IntentInspector.mode = {analysis.get('mode')}")
        self._log_debug(f"loaded_knowledge のキー一覧: {list(loaded_knowledge.keys())}")

        # ------------------------------------------------
        # 🛡️ 自己防衛モード
        # ------------------------------------------------
        if analysis.get("mode") == "self_defense":
            self._log_debug("→ self_defense 分岐へ")
            knowledge_str = (
                json.dumps(loaded_knowledge, ensure_ascii=False, indent=2)
                if loaded_knowledge else ""
            )
            defense_prompt = f"""
あなたはシステム開発者を守る専属のリーガル＆メンタルアドバイザーAIです。
...(既存のまま)...
"""
            return "prompt", defense_prompt

        # ------------------------------------------------
        # 👤 人物名マッチ
        # ------------------------------------------------
        matched_person = self._match_historical_figure(message)
        self._log_debug(f"_match_historical_figure() 結果: {matched_person!r}")

        if matched_person:
            self._log_debug("→ 人物プロフィール分岐へ")
            if not loaded_knowledge:
                self._log_debug(" loaded_knowledge が空。KnowledgeManager検索がヒットしなかった可能性")
                return "text", f"「{matched_person}」の知識データが読み込まれませんでした。"
            result = self._build_person_response(matched_person, loaded_knowledge)
            self._log_debug(f"_build_person_response() の戻り値: {result[:80]!r}...")
            return "text", result
        # 🛠️ 開発ナレッジ・デバッグ履歴マッチ (追加部分)
        matched_debug = self._match_debug_knowledge(message)
        self._log_debug(f"_match_debug_knowledge() 結果: {matched_debug!r}")

        if matched_debug:
            self._log_debug("→ 開発ナレッジ分岐へ")
            if not loaded_knowledge:
                return "text", f"「{matched_debug}」の知識データが読み込まれませんでした。"
            
            result = self._build_debug_knowledge_response(matched_debug, loaded_knowledge)
            return "text", result
        # ------------------------------------------------
        # 💼 職業名マッチ
        # ------------------------------------------------
        matched_title = self._match_occupation(message)
        self._log_debug(f"_match_occupation() 結果: {matched_title!r}")

        if matched_title:
            is_history = self._is_history_question(message)
            self._log_debug(f"_is_history_question() 結果: {is_history}")

            if not loaded_knowledge:
                self._log_debug(" loaded_knowledge が空。get_search_keywords() が空配列を返した"
                                "か、KnowledgeManager.search_by_keywords() がヒットしなかった可能性")
                return "text", f"「{matched_title}」の知識データが読み込まれませんでした。"

            if is_history:
                self._log_debug("→ 歴史人物レスポンス分岐へ")
                # tobi.json が loaded_knowledge に入っているか個別確認
                found_history_record = any(
                    d.get("occupation_title") == matched_title and "history_figures" in d
                    for d in loaded_knowledge.values()
                )
                self._log_debug(f"occupation_title一致 かつ history_figures を持つレコードの有無: {found_history_record}")
                if not found_history_record:
                    self._log_debug(
                        f" loaded_knowledge の中身: "
                        f"{[{'file': k, 'keys': list(v.keys())} for k, v in loaded_knowledge.items()]}"
                    )
                result = self._build_history_response(matched_title, loaded_knowledge)
                self._log_debug(f"_build_history_response() の戻り値: {result!r}")
                return "text", result

            self._log_debug("→ 単元マッピング(occupation)分岐へ（history判定がFalseだったため）")
            result = self._build_occupation_response(matched_title, loaded_knowledge)
            return "text", result

        if analysis["mode"] == "system_inquiry":
            knowledge = getattr(request, "world_knowledge", {})

            if not knowledge:
                return "text", "現在、システム（To）の詳しいルールや知識データ（JSON）が読み込まれていません。"

            response_lines = [
                "システムの仕組み（JSONデータ）についてご説明しますね。\n",
                "現在、私が把握している「To」の内部ルールは以下の通りです：\n"
            ]

            for key, value in knowledge.items():
                response_lines.append(f"### 📌 {key}")
                if isinstance(value, list):
                    if not value:
                        response_lines.append("  データがありません。")
                    else:
                        [response_lines.append(f"  ・{item}") for item in value]
                elif isinstance(value, dict):
                    if not value:
                        response_lines.append("  設定がありません。")
                    else:
                        [response_lines.append(f"  ・{sub_key}: {sub_value}") for sub_key, sub_value in value.items()]
                else:
                    response_lines.append(f"  {value}")
                response_lines.append("")

            return "text", "\n".join(response_lines)

            # ------------------------------------------------
            # どれにも当てはまらなかった場合
            # ------------------------------------------------
        return "text", "うまく回答を用意できませんでした。別の聞き方でもう一度お願いします。"
    # except Exception as e:
    #     import traceback; traceback.print_exc()
    #     return "text", f"処理中にエラーが発生しました: {e}"
                
            
    async def _handle_game_search(self, message: str, current_signals: dict) -> Tuple[str, Any]:
        # ===
        # 1. 状態の初期化（高度なプロファイリングモデル）
        # ===
        state = current_signals.get("game_search_state", {
            "facts": {},                # 確定した事実 (例: PvP, カードゲーム)
            "user_opinions": {},        # ユーザーの主観 (例: 4+4+2が使いやすい)
            "ai_inferences": {          # AIの推論 (仮説, 確信度, 証拠, 反証)
                "playstyle": {
                    "hypothesis": "不明",
                    "confidence": 0.0,
                    "evidence": [],
                    "contradictions": []
                }
            },
            "missing_keys": ["genre", "play_style", "resource_management", "weakness_cover"],
            "phase": "exploration",     # exploration -> profiling -> deep_dive -> conclusion
            "conversation_summary": ""  # 過去の会話の要約
        })

        # ===
        # 2. 終了シグナルと知識化
        # ===
        end_keywords = ["ありがと", "助かった", "もういいや", "終わる", "満足"]
        if any(kw in message for kw in end_keywords) or state["phase"] == "conclusion":
            playstyle_hyp = state["ai_inferences"]["playstyle"]["hypothesis"]
            
            response = (
                f"こちらこそ相談に乗らせてくれてありがとう！\n"
                f"話を聞く限り、あなたは「{playstyle_hyp}」を重視するタイプみたいだね。\n"
                f"今の構成をベースに、また新しい戦術を思いついたらぜひ聞かせてね。"
            )
            # 知識化: ここで state["conversation_summary"] などを JSON として保存する処理を呼ぶ
            current_signals["active_context"] = None
            current_signals["game_search_state"] = {}
            return "text", {"message": response, "update_signals": current_signals}

        # ===
        # 3. 情報抽出と状態の更新 (SignalExtractor & StateUpdater)
        # ===
        extracted_info = 0 # 今回のターンで得られた情報の数

        # 例: 構成と主観の抽出
        if "4+4+2" in message:
            state["user_opinions"]["preferred_deck"] = "4+4+2(+2)"
            extracted_info += 1

        # 例: 仮説の生成と反証の処理 (Confidence Update)
        playstyle_info = state["ai_inferences"]["playstyle"]
        
        if "ダメージ" in message and "確実" in message:
            playstyle_info["hypothesis"] = "安定ダメージ重視"
            playstyle_info["evidence"].append("確実なダメージを好む発言")
            playstyle_info["confidence"] = min(playstyle_info["confidence"] + 0.4, 0.9)
            if "play_style" in state["missing_keys"]:
                state["missing_keys"].remove("play_style")
            extracted_info += 1
            
        elif "壊せるなら" in message or "一撃" in message:
            # 既存の仮説への反証を追加し、仮説をアップデート
            playstyle_info["contradictions"].append("高確率なら一撃も好む")
            playstyle_info["hypothesis"] = "高勝率なら高リターンも許容する安定志向"
            # 反証が出たので一度確信度を下げるが、新しい仮説として再構築する
            playstyle_info["confidence"] = 0.85 
            extracted_info += 1

        # フェーズの進行判定
        if len(state["missing_keys"]) <= 2:
            state["phase"] = "deep_dive"

        # ===
        # 4. 応答の組み立て (Response Builder)
        # ===
        response_blocks = []

        # ① 共感・リアクション (アンケート化を防ぐためのクッション)
        if "4+4+2" in message:
            response_blocks.append("なるほど、今は4+4+2の編成が一番ダメージ出しやすく感じてるんだね。")
        elif extracted_info > 0:
            response_blocks.append("うんうん、なるほど。")

        # ② 確信度(Confidence)に基づく推論の開示
        confidence = playstyle_info["confidence"]
        hypothesis = playstyle_info["hypothesis"]

        if confidence >= 0.9:
            response_blocks.append(f"そこまでハッキリしてるなら、キミのプレイスタイルは完全に「{hypothesis}」だね。")
        elif confidence >= 0.75:
            response_blocks.append(f"これまでの話を聞くと、キミは「{hypothesis}」なタイプっぽいね。")
        elif confidence >= 0.5:
            response_blocks.append(f"もしかして、一発のロマンより「{hypothesis}」な戦い方のほうが好きだったりする？")

        # ③ 情報価値に基づく質問選択 (Question Selector)
        # 今回のターンで十分な情報(2つ以上)が取れた場合は、質問せずにターンを返す
        if extracted_info < 2:
            if state["phase"] == "exploration":
                if "genre" in state["missing_keys"]:
                    response_blocks.append("ちなみに、ジャンルはアクション？それともカードゲームみたいな頭脳戦？")
            elif state["phase"] == "deep_dive":
                if "weakness_cover" in state["missing_keys"]:
                    response_blocks.append("その構成だとHPが低めになりそうだけど、弱点はどうやってカバーしてるの？")

        # 組み立てたブロックを結合
        response_msg = " ".join(response_blocks)

        # ===
        # 5. 会話サマリーの更新と保存
        # ===
        # 実際にはここでLLMを使って、これまでの state と message から要約文を生成・追記する
        state["conversation_summary"] = f"ユーザーは{state['user_opinions'].get('preferred_deck', '特定')}の構成を好む。"

        current_signals["game_search_state"] = state
        
        return "text", {
            "message": response_msg,
            "update_signals": current_signals
        }