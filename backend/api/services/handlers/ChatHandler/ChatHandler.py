# pip install youtube-transcript-apiをダウンロード済みです。Youtubeの文字お越しを無料でできるようになります。
# backend/api/services/handlers/ChatHandler/ChatHandler.py
from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import asyncio
from api.services.manager.KnowledgeManager import KnowledgeManager
from api.services.Video.VideoClaimService import VideoClaimService, extract_video_id

try:
    from ..base_handler import BaseHandler
except ImportError:
    from api.services.handlers.base_handler import BaseHandler

from api.services.inspectors.IntentInSpector import IntentInspector

# 外部の tools/lab_terminal_simulator.py があれば優先利用し、なければ内蔵クラスを使用
try:
    from tools.lab_terminal_simulator import LabTerminalSimulator as ExternalLabSimulator
except ImportError:
    ExternalLabSimulator = None

# To_model の FriendlyResolutionFirstEngine があれば連携
try:
    from to_model.reasoning.persona_and_flow import FriendlyResolutionFirstEngine
except ImportError:
    FriendlyResolutionFirstEngine = None

# routes_memory.py のメモ保存関数があれば連携（サイドバー＆AIメモリー表示用）
try:
    from api.routes_memory import register_ai_note
except ImportError:
    register_ai_note = None


# =========================================================================
# 内蔵フォールバック用：仮想Ubuntuラボ・ステートフルシミュレーター
# （tools/lab_terminal_simulator.py 未配置時でも単体で完全動作します）
# =========================================================================

@dataclass
class _VirtualLabState:
    role: str = "user"  # "user" ($) or "root" (#)
    current_step: int = 1
    installed_packages: List[str] = field(default_factory=list)
    network_mode: str = "NAT"
    static_ip: Optional[str] = None
    learned_concepts: List[str] = field(default_factory=list)

    @property
    def prompt_symbol(self) -> str:
        return "#" if self.role == "root" else "$"

    @property
    def prompt_prefix(self) -> str:
        user_name = "root" if self.role == "root" else "analyst"
        return f"{user_name}@ubuntu-lab:~{self.prompt_symbol}"


class _BuiltInLabTerminalSimulator:
    """ホストOSに一切触れずにUbuntu解析環境構築コマンドを疑似体験するシミュレーター"""

    DEFAULT_STEPS: List[Dict[str, Any]] = [
        {
            "step": 1,
            "trigger_command": "sudo apt update",
            "required_role": "user",
            "mock_output": (
                "Hit:1 http://archive.ubuntu.com/ubuntu bionic InRelease\n"
                "Reading package lists... Done\n"
                "Building dependency tree... Done"
            ),
            "explanation": "Ubuntuが参照するソフトウェアカタログ（パッケージリスト）を最新状態に更新しました。",
            "to_model_note": "まずは目録（パッケージリスト）を最新にするんですね！基本の第一歩、覚えました📝",
        },
        {
            "step": 2,
            "trigger_command": "sudo apt install python-pip",
            "required_role": "user",
            "mock_output": "Setting up python-pip (9.0.1-2) ...\nProcessing triggers for man-db ...",
            "explanation": "Python製の解析スクリプトを動かすためのパッケージ管理ツール（pip）を導入しました。",
            "to_model_note": "これでPython用の解析パーツを自由に集められるようになりますね✨",
        },
        {
            "step": 3,
            "trigger_command": "sudo python -m pip install --upgrade pip",
            "aliases": ["sudo python-m pip install --upgrade pip"],
            "required_role": "user",
            "mock_output": "Successfully installed pip-20.3.4",
            "explanation": "導入したpip自体を最新バージョンへ引き上げ、依存関係のエラーを防ぎます。",
            "to_model_note": "道具箱そのものも最新版にアップグレードしておくのがコツなんですね！",
        },
        {
            "step": 4,
            "trigger_command": "sudo python -m pip install pefile",
            "aliases": [
                "sudo apt install python-magic",
                "sudo apt install upx",
                "sudo apt install yara",
                "sudo pip install yara-python",
                "sudo apt install ssdeep",
                "sudo apt install build-essential libffi-dev python python-dev libfuzzy-dev",
                "sudo python -m pip install --upgrade ssdeep",
                "sudo apt install wireshark",
                "sudo apt install tshark",
            ],
            "required_role": "user",
            "mock_output": "Successfully installed analysis packages (pefile, yara, ssdeep, wireshark, tshark, upx)",
            "explanation": "ファイル形式特定、PE構造解析（pefile）、パターン検知（yara）、通信監視（wireshark/tshark）などの解析ツール群を導入しました。",
            "to_model_note": "前に学んだ『MZヘッダ』や不審な通信を調べるための武器が一気に揃いました！",
        },
        {
            "step": 5,
            "trigger_command": "sudo su",
            "required_role": "user",
            "next_role": "root",
            "mock_output": "root@ubuntu-lab:/home/analyst#",
            "explanation": "一般ユーザー（$）から最高管理者である root（#）へ権限を切り替えました。システム設定ファイルを直接編集する準備です。",
            "to_model_note": "プロンプトが『$』から『#』に変わりました！ここからは特権モードですね、慎重にいきます！",
        },
        {
            "step": 6,
            "trigger_command": 'echo "deb http://www.inetsim.org/debian/ binary/" > /etc/apt/sources.list.d/inetsim.list',
            "aliases": [
                'echo "deb http://www.inetsim.org/debian/binary/" > /etc/apt/sources.list.d/inetsim.list',
                'echo "deb http://www.inetsim.org/debian/binary/" > etc/apt/sources.list.d/inetsim.list',
                'sudo echo "deb http://www.inetsim.org/debian/ binary/" > /etc/apt/sources.list.d/inetsim.list',
                'echo "deb http://www.inetsim.org/debian/ binary/" | sudo tee /etc/apt/sources.list.d/inetsim.list',
                "inetsim.list",
                "deb http://www.inetsim.org/debian/",
            ],
            "required_role": "root",
            "mock_output": "(inetsim.list created in /etc/apt/sources.list.d/)",
            "explanation": "INetSim公式の配布元アドレス（リポジトリ）をUbuntuの取得先リストへ登録しました。",
            "to_model_note": "標準カタログにない専門ツールは、こうやって配布元の住所を追加するんですね！",
        },
        {
            "step": 7,
            "trigger_command": "wget -O - http://www.inetsim.org/inetsim-archive-signing-key.asc | apt-key add -",
            "aliases": [
                "wget -o-http://www.inetsim.org/inetsim-archive-signing-key.asc|apt-key add -",
                "wget -O- http://www.inetsim.org/inetsim-archive-signing-key.asc | apt-key add -",
                "curl -s http://www.inetsim.org/inetsim-archive-signing-key.asc | apt-key add -",
                "inetsim-archive-signing-key.asc",
                "apt-key add",
            ],
            "required_role": "root",
            "mock_output": "OK",
            "explanation": "配布元が本物であることを証明するデジタル署名キーをダウンロードし、システムに登録しました。",
            "to_model_note": "偽物のツールを掴まされないように、ちゃんと署名（鍵）を確認して『OK』が出ました🔑",
        },
        {
            "step": 8,
            "trigger_command": "apt update",
            "required_role": "root",
            "mock_output": "Hit:1 http://www.inetsim.org/debian binary/ InRelease\nReading package lists... Done",
            "explanation": "新しく追加したINetSimのリポジトリを含めて、パッケージリストを再更新しました。",
            "to_model_note": "住所を追加したあとに、もう一度カタログを更新するのが大事な手順なんですね！",
        },
        {
            "step": 9,
            "trigger_command": "apt install inetsim",
            "required_role": "root",
            "mock_output": "Setting up inetsim (1.3.2) ...\nCreating default configuration...",
            "explanation": "DNSやHTTPなどのインターネットサービスを模倣するダミー局『INetSim』の導入が完了しました。",
            "to_model_note": "ダミーのインターネット局が完成しました！あとは外の世界との通信を遮断するだけですね！",
        },
        {
            "step": 10,
            "trigger_command": "set-network host-only",
            "aliases": ["host-only", "ホストオンリー", "network host-only"],
            "required_role": "any",
            "mock_output": "[VM Settings Updated] Network Adapter -> Host-Only Mode (Isolated from Internet)",
            "explanation": "仮想マシンのネットワーク設定を『Host-Only（ホストオンリー）』に変更し、外部インターネットから完全に隔離しました。",
            "to_model_note": "これでマルウェアが外の世界へ逃げ出せない密室（Host-Only）になりました🛡️",
        },
        {
            "step": 11,
            "trigger_command": "sudo gedit /etc/network/interfaces",
            "aliases": [
                "gedit /etc/network/interfaces",
                "nano /etc/network/interfaces",
                "auto ens33",
                "iface ens33 inet static",
            ],
            "required_role": "any",
            "mock_output": (
                "# /etc/network/interfaces updated:\n"
                "auto lo\niface lo inet loopback\n\n"
                "auto ens33\niface ens33 inet static\n"
                "  address 192.168.1.100\n  netmask 255.255.255.0"
            ),
            "explanation": "ネットワーク設定ファイルを編集し、Ubuntu仮想マシンに固定IPアドレス（192.168.1.100）を設定しました。",
            "to_model_note": "🎉 ダミー局（INetSim）の住所（固定IP）が確定して、安全なマルウェア解析ラボが完成しました！",
        },
    ]

    def __init__(self) -> None:
        self.state = _VirtualLabState()

    def execute_mock_command(
        self,
        raw_input: str,
        simulation_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cleaned_cmd = raw_input.strip().lstrip("$#").strip()
        steps = (
            simulation_data.get("simulation_steps")
            if isinstance(simulation_data, dict) and simulation_data.get("simulation_steps")
            else self.DEFAULT_STEPS
        )
        if steps is None:
            steps = self.DEFAULT_STEPS



        if cleaned_cmd.lower() in ("reset-lab", "ラボ初期化"):
            self.state = _VirtualLabState()
            return {
                "matched": True,
                "command": cleaned_cmd,
                "prompt": self.state.prompt_prefix,
                "terminal_output": "Virtual Ubuntu Lab state reset to Step 1 (user: analyst).",
                "explanation": "仮想Ubuntuラボの状態を初期状態（一般ユーザー $ / Step 1）にリセットしました。",
                "to_model_note": "ラボをまっさらな状態に戻しました！もう一度1から練習できます✨",
                "state": self._export_state(),
            }

        if cleaned_cmd.lower() == "exit" and self.state.role == "root":
            self.state.role = "user"
            return {
                "matched": True,
                "command": cleaned_cmd,
                "prompt": self.state.prompt_prefix,
                "terminal_output": "exit\nanalyst@ubuntu-lab:~$",
                "explanation": "root（管理者）モードを終了し、通常のユーザー権限（$）に戻りました。",
                "to_model_note": "特権作業が終わったらすぐ『$』に戻るのが安全運用の鉄則ですね！",
                "state": self._export_state(),
            }

        for step_info in steps:
            if self._is_command_match(cleaned_cmd, step_info):
                return self._process_step(cleaned_cmd, step_info)

        next_step = self._get_next_step_info(steps)
        hint_cmd = next_step["trigger_command"] if next_step else "全ステップ完了（コンソール表示が可能）"

        return {
            "matched": False,
            "command": cleaned_cmd,
            "prompt": self.state.prompt_prefix,
            "terminal_output": f"mock-bash: '{cleaned_cmd}' は現在の学習ステップ外のコマンドです。",
            "explanation": f"次のステップのおすすめコマンドは `{hint_cmd}` です。",
            "to_model_note": f"先輩、次は `{hint_cmd}` を試してみると環境構築が進みますよ！",
            "state": self._export_state(),
        }

    def _is_command_match(self, user_cmd: str, step_info: Dict[str, Any]) -> bool:
        norm_user = " ".join(user_cmd.lower().split()).replace("python-m", "python -m")
        candidates = [step_info.get("trigger_command", "")] + list(step_info.get("aliases", []))
        for target in candidates:
            norm_target = " ".join(str(target).lower().split())
            if norm_target and (norm_user == norm_target or norm_target in norm_user):
                return True
        return False

    def _process_step(self, cmd: str, step_info: Dict[str, Any]) -> Dict[str, Any]:
        req_role = step_info.get("required_role", "user")

        if req_role == "root" and self.state.role != "root" and not cmd.lower().startswith("sudo"):
            return {
                "matched": True,
                "command": cmd,
                "prompt": self.state.prompt_prefix,
                "terminal_output": "E: Could not open lock file - open (13: Permission denied)",
                "explanation": "管理者権限（root）が必要な操作です。先に `sudo su` で root（#）に切り替えるか、`sudo` を付けて実行してください。",
                "to_model_note": "あっ、権限エラー（Permission denied）が出ました！先に `sudo su` で『#』に変身しましょう！",
                "state": self._export_state(),
            }

        prompt_before = self.state.prompt_prefix
        if "next_role" in step_info:
            self.state.role = step_info["next_role"]

        if "install" in cmd:
            tokens = [t for t in cmd.split() if not t.startswith("-")]
            pkg_name = tokens[-1] if tokens else "package"
            if pkg_name not in self.state.installed_packages:
                self.state.installed_packages.append(pkg_name)

        if step_info.get("step") == 10 or "host-only" in cmd.lower():
            self.state.network_mode = "Host-Only"
        if step_info.get("step") == 11 or "interfaces" in cmd.lower():
            self.state.static_ip = "192.168.1.100"

        self.state.current_step = max(self.state.current_step, int(step_info.get("step", 1)) + 1)

        return {
            "matched": True,
            "command": cmd,
            "prompt": prompt_before,
            "terminal_output": step_info.get("mock_output", "Done."),
            "explanation": step_info.get("explanation", ""),
            "to_model_note": step_info.get("to_model_note", ""),
            "state": self._export_state(),
        }

    def _get_next_step_info(self, steps: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for s in steps:
            if int(s.get("step", 0)) >= self.state.current_step:
                return s
        return None

    def _export_state(self) -> Dict[str, Any]:
        return {
            "role": self.state.role,
            "prompt": self.state.prompt_prefix,
            "current_step": self.state.current_step,
            "installed_packages": list(self.state.installed_packages),
            "network_mode": self.state.network_mode,
            "static_ip": self.state.static_ip,
        }


# =========================================================================
# ChatHandler 本体
# =========================================================================

class ChatHandler(BaseHandler):
    """
    To本体のメイン会話＆知識解説＆マルウェア解析ラボハンドラー:
    1. 自己防衛モード (self_defense) -> 最優先100点でメンタープロンプト返却
    2. マルウェア解析共同学習 ＆ 仮想Ubuntuラボ疑似体験 -> 100点で優先処理
    3. システム質問モード (system_inquiry) -> world_knowledge の説明を返却
    """

    def __init__(self) -> None:
        super().__init__()
        # 起動ディレクトリが To/ でも To/backend/ でも確実に plugins/project_builder/knowledge を見つける
        base_dir = Path(__file__).resolve()
        candidate_roots = [
            Path(os.getcwd()),
            base_dir.parents[4] if len(base_dir.parents) >= 5 else Path(os.getcwd()),
            base_dir.parents[3] if len(base_dir.parents) >= 4 else Path(os.getcwd()),
        ]
        resolved_knowledge_dir = Path(os.getcwd()) / "plugins" / "project_builder" / "knowledge"
        for root in candidate_roots:
            candidate = root / "plugins" / "project_builder" / "knowledge"
            if candidate.exists():
                resolved_knowledge_dir = candidate
                break

        self.knowledge_dir: str = str(resolved_knowledge_dir)
        self.knowledge_cache: Dict[str, Any] = {}
        _km = KnowledgeManager(
            base_dir=self.knowledge_dir,
            knowledge_dirs=[self.knowledge_dir],
        )
        self.video_service = VideoClaimService(_km, claim_dir="Video/Claim")
        # シミュレーターとTo_model共同学習エンジンの初期化
        self.lab_simulator = (
            ExternalLabSimulator()
            if ExternalLabSimulator is not None
            else _BuiltInLabTerminalSimulator()
        )
        self.to_model_engine = (
            FriendlyResolutionFirstEngine()
            if FriendlyResolutionFirstEngine is not None
            else None
        )

        # 直前の解説トピックとステップを保持する変数（「続けて」対応用）
        self.last_topic: Optional[str] = None
        self.last_explanation_step: int = 1
        self.co_learning_concepts: List[str] = []

    # =====================================================================
    # スコア計算 (ChatOrchestrator ルーティング用)
    # =====================================================================

    async def calculate_score(self, message: str, current_signals: Optional[dict] = None) -> int:
        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        # 🚨 パターンS：自己防衛（メンタル・リーガル）モード（確定100点）
        if analysis.get("mode") == "self_defense":
            return 100

        # 🧪 パターンM：マルウェア解析・仮想ラボコマンド・To_model共同学習モード（確定100点）
        if self._is_malware_or_lab_query(message, current_signals):
            return 100
        if self._is_video_query(message):
            return 100
        # ---------------------------------------------------------
        # パターンA：システムの仕組みやルールについて聞かれている場合
        # ---------------------------------------------------------
        if analysis.get("mode") == "system_inquiry":
            return int(analysis.get("score", 80))

        # ---------------------------------------------------------
        # パターンB：どの専門分野（デプロイ、UI、JSON等）でもない場合
        # ---------------------------------------------------------
        if analysis.get("mode") == "unknown":
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

    # =====================================================================
    # 判定ヘルパー＆キーワード抽出
    # =====================================================================

    def _is_continuation_query(self, message: str) -> bool:
        """「続けて」「説明を続けて」「もっと詳しく」などの継続要望かどうかを判定"""
        clean = str(message or "").strip().replace(" ", "").replace(" ", "").lower()
        triggers = (
            "続けて", "説明を続けて", "続きを", "続き", "つづけて",
            "もっと教えて", "次は", "次は何", "次", "詳細を教えて", "もうちょっと詳しく",
        )
        return any(trig in clean for trig in triggers)

    def _is_malware_or_lab_query(self, message: str, current_signals: Optional[dict] = None) -> bool:
        lower = str(message or "").lower().strip()
        if not lower:
            return False

        # 💡 直前にマルウェア解析の話をしていて、ユーザーが「続けて」と言った場合は100点に通す
        if self.last_topic is not None and self._is_continuation_query(lower):
            return True

        if self._is_terminal_command_input(lower):
            return True

        triggers = (
            "マルウェア", "malware", "ウイルス", "トロイの木馬", "ランサムウェア", "スパイウェア", "ボット",
            "キーロガー", "keylog", "表層解析", "静的解析", "動的解析", "メモリ解析", "コード解析",
            "逆アセンブル", "デコンパイル", "アンパッキング", "パッカー", "マジックナンバー", "mzヘッダ",
            "peファイル", "pefile", "strings", "ハッシュ値", "virustotal", "ioc", "c2",
            "サンドボックス", "remnux", "flare", "vmware", "virtualbox", "inetsim",
            "yara", "ssdeep", "wireshark", "tshark", "upx", "host-only", "ホストオンリー",
            "解析環境", "仮想環境", "防御コンソール", "to_model",
        )
        return any(trig in lower for trig in triggers)

    def _is_terminal_command_input(self, message: str) -> bool:
        cleaned = str(message or "").strip().lstrip("$#").strip().lower()
        cmd_prefixes = (
            "sudo ", "apt ", "apt-get ", "echo ", "wget ", "curl ", "python -m pip", "python-m pip",
            "pip install", "exit", "set-network", "host-only", "gedit ", "nano ",
            "auto ens33", "reset-lab", "ラボ初期化",
        )
        return cleaned.startswith(cmd_prefixes)
    def _is_video_query(self, message: str) -> str | None:
        """'analyze' / 'ask' / None"""
        if extract_video_id(message) and any(w in message for w in ("解析", "分析", "調べ", "見て")):
            return "analyze"
        if any(w in message for w in ("感想", "メッセージ性", "伝えたい", "何を言って")) \
            and self.video_service.has_claims():
            return "ask"
        return None
    def _is_defense_console_request(self, message: str) -> bool:
        lower = str(message or "").lower()
        console_words = (
            "コンソール", "ダッシュボード", "防御ルール", "遮断ルール", "malware_defense", "通信を遮断"
        )
        return any(w in lower for w in console_words)

    def get_search_keywords(self, message: str) -> List[str]:
        """ChatOrchestrator._invoke_handler から呼ばれるキーワード抽出メソッド"""
        return self._extract_keywords(message)

    def _extract_keywords(self, message: str) -> List[str]:
        keywords = [
            # 技術系
            "react", "electron", "aws", "docker", "github", "flask", "fastapi", "python", "sql", "video", "ui",
            # マルウェア解析・仮想ラボ系
            "malware", "マルウェア", "ubuntu", "linux", "inetsim", "pefile", "yara", "wireshark",
            "surface", "表層解析", "dynamic", "動的解析", "static", "静的解析", "memory", "メモリ解析",
            "code", "コード解析", "逆アセンブル", "environment", "解析環境", "remnux", "flare", "vmware",
            "host-only", "ホストオンリー", "sandbox", "サンドボックス",
            # 防衛系 (mental.json, legal.json などを引っ掛けるため)
            "法律", "下請法", "労働", "メンタル", "限界", "疲れた", "終わらない", "スケジュール", "理不尽", "ガントチャート",
        ]
        return [kw for kw in keywords if kw.lower() in str(message or "").lower()]

    # =====================================================================
    # Knowledge 取得（ChatOrchestrator連携 ＋ ローカル検索フォールバック）
    # =====================================================================

    def _get_orchestrator_knowledge(self, request) -> Dict[str, Any]:
        """
        ChatOrchestrator の KnowledgeRouter / KnowledgeLoader が選別した
        request.loaded_knowledge を最優先で取得し、空の場合のみ自前検索にフォールバックする。
        """
        loaded_list = getattr(request, "loaded_knowledge", None) or []
        knowledge_map: Dict[str, Any] = {}

        for item in loaded_list:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or item.get("title") or "")
            if item_id.startswith("system/"):
                continue

            content = item.get("content")
            if isinstance(content, dict):
                knowledge_map[item_id] = content
            elif isinstance(content, str) and content.strip().startswith("{"):
                try:
                    knowledge_map[item_id] = json.loads(content)
                except Exception:
                    pass
            elif "knowledge_content" in item or "simulation_steps" in item or "description" in item:
                knowledge_map[item_id or "knowledge_item"] = item

        if not knowledge_map:
            msg = getattr(request, "message", "")
            keywords = self._extract_keywords(msg) or ["malware", "ubuntu"]
            knowledge_map = self._load_relevant_knowledge_dict(keywords)

        return knowledge_map

    def _load_relevant_knowledge_dict(self, keywords: list) -> Dict[str, Any]:
        if not os.path.exists(self.knowledge_dir):
            return {}

        relevant_data: Dict[str, Any] = {}
        search_pattern = os.path.join(self.knowledge_dir, "**", "*.json")
        all_json_files = glob.glob(search_pattern, recursive=True)

        for file_path in all_json_files:
            path_lower = file_path.lower()
            try:
                if file_path not in self.knowledge_cache:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.knowledge_cache[file_path] = json.load(f)
                data = self.knowledge_cache[file_path]
                if not isinstance(data, dict):
                    continue

                json_kws = [str(k).lower() for k in data.get("keywords", [])]
                json_cat = str(data.get("category", "")).lower()
                if any(
                    kw.lower() in path_lower
                    or kw.lower() in json_kws
                    or kw.lower() in json_cat
                    for kw in keywords
                ):
                    relevant_data[os.path.basename(file_path)] = data
            except Exception as e:
                print(f"⚠️ JSON読み込みエラー ({file_path}): {e}")

        return relevant_data

    def _load_relevant_knowledge(self, keywords: list) -> str:
        relevant_data = self._load_relevant_knowledge_dict(keywords)
        if not relevant_data:
            return "知識データベース（knowledgeフォルダ）に該当データが見つかりません。"
        return json.dumps(relevant_data, ensure_ascii=False, indent=2)

    # =====================================================================
    # 応答フォーマット構築（解説生成・共同学習ノート・3.6コンソール生成）
    # =====================================================================

    def _update_co_learning_notes(self, message: str) -> Tuple[int, List[str]]:
        """会話からマルウェア解析キーワードを抽出し、To_modelの学習レベルを更新＆メモ保存する"""
        concept_dict = {
            "表層解析": "ファイルを実行せず外側からMZヘッダや文字列(strings)、ハッシュ値を調べる手法",
            "静的解析": "逆アセンブル等でプログラムを実行せずに内部コード構造を読み解く手法",
            "動的解析": "隔離環境(サンドボックス)で実際に動かして通信や挙動を観察する手法",
            "メモリ解析": "実行中のメモリをダンプしてパッカー(難読化)解除後の真のコードを暴く手法",
            "逆アセンブル": "機械語を人間やAIが読めるアセンブリ言語に変換する技術",
            "inetsim": "マルウェアの通信を騙して受け止めるダミーインターネット局",
            "host-only": "仮想マシンを外部ネットから切り離してウイルスの逃亡を防ぐ隔離設定",
            "remnux": "マルウェア解析ツールが詰まったLinuxディストリビューション",
            "flare": "Windows用のマルウェア解析特化環境",
            "pefile": "Windows実行ファイル(PE)の構造をPythonで解剖するライブラリ",
        }
        lower = message.lower()
        newly_learned = []
        for kw, desc in concept_dict.items():
            if kw in lower and kw not in self.co_learning_concepts:
                self.co_learning_concepts.append(kw)
                newly_learned.append(f"**{kw}**（{desc}）")
                # routes_memory.py のメモ保存関数があれば .ai_memory/ai_notes.json に保存
                if callable(register_ai_note):
                    try:
                        register_ai_note(
                            title=f"マルウェア解析：{kw}",
                            content=desc,
                            category="malware_study",
                            tags=["マルウェア解析", kw, "To_model共同学習"],
                        )
                    except Exception:
                        pass

        level = min(100, len(self.co_learning_concepts) * 15)
        return level, newly_learned

    def _format_flexible_explanation(self, user_msg: str, knowledge_map: Dict[str, Any]) -> str:
        """
        「わかりやすく教えて」「続けて」などの要望に合わせ、
        JSONデータ（または内蔵知識）から動的に解説テキストを組み立てる汎用ジェネレーター
        """
        # 1. 「続けて」「説明を続けて」の場合：前回のトピックから次のステップを展開
        if self._is_continuation_query(user_msg) and self.last_topic:
            self.last_explanation_step += 1
            step = self.last_explanation_step
            continuation_guides = {
                2: (
                    f"### ⏩ {self.last_topic}（ステップ 2：表層解析と検体の初期調査）\n\n"
                    "基礎環境ができたら、まずはマルウェアを**実行せずに外側だけ調べる『表層解析』**を行います。\n\n"
                    "1. **ハッシュ値の算出**: `sha256sum` で検体の指紋（ハッシュ値）を取り、VirusTotalで既知の検体か照合します。\n"
                    "2. **MZヘッダとPE構造の確認**: `pefile` を使い、Windows実行ファイル（`4D 5A` = MZ）であるか、不審なセクション名（UPX0など）がないか調べます。\n"
                    "3. **文字列（Strings）抽出**: ファイル内部に埋め込まれたURL、IPアドレス、不審なWindows API名（`VirtualAlloc` 等）を洗い出します。\n\n"
                    "🌱 **To_model**: 「さらに詳しい続きが見たいときは、もう一度『続けて』と声をかけてくださいね！コマンドを試すなら `$ sudo python -m pip install pefile` と打ってみましょう✨」"
                ),
                3: (
                    f"### ⏩ {self.last_topic}（ステップ 3：動的解析とダミー局での通信捕捉）\n\n"
                    "表層解析の次は、隔離した仮想環境で実際に検体を動かす**『動的解析』**に進みます。\n\n"
                    "1. **ネットワーク隔離の確認**: 仮想マシンが `Host-Only` モードになっており、外部インターネットへ出られないことを再確認します。\n"
                    "2. **INetSimとWiresharkの起動**: Ubuntu側（`192.168.1.100`）でINetSimを起動し、検体からのDNS名前解決やHTTPリクエストを偽装応答で受け止めます。\n"
                    "3. **ファイル・レジストリ監視**: 検体がどのフォルダに自身をコピーし、どの自動起動レジストリ（Runキー）を書き換えるかを観察します。\n\n"
                    "🌱 **To_model**: 「次はリバースエンジニアリングの核心『静的・メモリ解析』です！『続けて』と言っていただければ詳しく解説します📝」"
                ),
            }
            return continuation_guides.get(
                step,
                (
                    f"### ⏩ {self.last_topic}（ステップ {step}：静的コード解析とメモリダンプ）\n\n"
                    "いよいよ最終段階の**『静的コード解析・メモリ解析』**です！\n\n"
                    "1. **逆アセンブル / デコンパイル**: GhidraやIDAを使い、機械語をアセンブリやC言語風のコードに復元して条件分岐（if文）や暗号化ロジックを解読します。\n"
                    "2. **アンパッキング（メモリ解析）**: パッカーで圧縮・難読化された検体は、実行してメモリ上に展開された瞬間をダンプして本来のPEファイルを抽出します。\n\n"
                    "🌱 **To_model**: 「これで解析の全体像をコンプリートしました！『防御コンソールを開いて』と言うと、これまでのC2遮断ルールをダッシュボードで確認できます🛡️」"
                ),
            )

        # 2. 通常の解説リクエスト時：トピックを記憶してステップを1にリセット
        is_beginner = any(
            w in user_msg for w in ("わかりやすく", "分かりやすく", "簡単", "初心者", "噛み砕いて", "1から", "一から")
        )
        level, newly_learned = self._update_co_learning_notes(user_msg)
        blocks: List[str] = []
        detected_title: Optional[str] = None

        for filename, data in knowledge_map.items():
            if not isinstance(data, dict):
                continue
            title = str(data.get("name") or data.get("title") or filename)
            if not detected_title:
                detected_title = title

            analogy = data.get("analogy", "")
            beginner_summary = data.get("beginner_summary", "")
            description = data.get("description", "")

            content = data.get("knowledge_content", {})
            if not analogy and isinstance(content, dict):
                for sub_val in content.values():
                    if isinstance(sub_val, dict) and "analogy" in sub_val:
                        analogy = sub_val["analogy"]
                        break

            if is_beginner:
                section = [f"### 🔰 {title}（やさしい解説モード）"]
                if analogy:
                    section.append(f"💡 **イメージで例えると**\n{analogy}")
                if beginner_summary:
                    section.append(f"📝 **ポイントまとめ**\n{beginner_summary}")
                elif description:
                    section.append(f"📝 **概要**\n{description}")

                if isinstance(content, dict):
                    highlights = []
                    for sub_k, sub_v in list(content.items())[:3]:
                        if isinstance(sub_v, dict) and "definition" in sub_v:
                            highlights.append(f"  ・**{sub_k}**: {sub_v['definition']}")
                    if highlights:
                        section.append("🔍 **基本のステップ**\n" + "\n".join(highlights))

                blocks.append("\n\n".join(section))
            else:
                section = [f"### 📘 {title}"]
                if description:
                    section.append(description)
                if analogy:
                    section.append(f"💡 **比喩イメージ**: {analogy}")
                if isinstance(content, dict):
                    details = []
                    for k, v in content.items():
                        if isinstance(v, dict):
                            defn = v.get("definition") or v.get("description") or v.get("purpose")
                            if defn:
                                details.append(f"・**{k}**: {defn}")
                    if details:
                        section.append("\n".join(details))
                blocks.append("\n\n".join(section))

        if not blocks:
            detected_title = "マルウェア解析の4大ステップと安全なラボ構築"
            blocks.append(
                "### 🔰 マルウェア解析の4大ステップと安全なラボ構築\n\n"
                "💡 **イメージで例えると**\n"
                "マルウェア解析は『危険物の解剖実験』です。まずは絶対に外へ漏れない無菌室（**VMware + Host-Onlyネットワーク**）を作り、"
                "その中にLinux用の解剖デスク（**REMnux / Ubuntu**）とWindows用の観察デスク（**FLARE VM**）、"
                "さらにウイルスからの電話を待ち受ける偽物の電話局（**INetSim**）を設置します。\n\n"
                "🔍 **4つの解析ステップ**\n"
                "  1. **表層解析**: 実行せずに外側から『MZヘッダ（4D 5A）』や文字列（strings）、ハッシュ値を調べる。\n"
                "  2. **動的解析**: 安全なサンドボックス内で実際に動かし、ファイル作成やC2サーバーへの通信（機能）を観察する。\n"
                "  3. **静的・コード解析**: 逆アセンブルして機械語を読み解き、プログラムの内部ロジック（動作の仕組み）を理解する。\n"
                "  4. **メモリ解析**: 難読化（パッカー）されたマルウェアがメモリ上で暗号を解いた瞬間をダンプして真の姿を暴く。"
            )

        self.last_topic = detected_title or "マルウェア解析・ラボ環境構築"
        self.last_explanation_step = 1

        learned_note = (
            f"新しく {', '.join(newly_learned)} を学習ノート（AIメモリー）に記録しました！"
            if newly_learned
            else "知識ノートを整理しました！（『続けて』と入力すると次の実践ステップを解説します）"
        )
        footer = (
            f"\n\n---\n"
            f"🌱 **【To_model 共同学習ノート（現在：知識習熟度 {level}%）】**\n"
            f"「{learned_note}\n"
            f"チャット欄に `$ sudo apt update` や `$ sudo su` と入力すると、仮想Ubuntuラボのコマンド練習ができます。"
            f"また『防御コンソールを開いて』と言うと、専用ダッシュボードを起動します✨」"
        )

        return "\n\n---\n\n".join(blocks) + footer

    def _build_malware_defense_widget_payload(self, summary_text: str) -> Dict[str, Any]:
        """AIChatMessageList.tsx の 3.6 Malware Defense UI を起動するためのペイロード"""
        export_state = getattr(self.lab_simulator, "_export_state", None)
        exported_state = export_state() if callable(export_state) else None
        lab_state: Dict[str, Any] = (
            exported_state
            if isinstance(exported_state, dict)
            else {"role": "analyst", "network_mode": "Host-Only", "static_ip": "192.168.1.100"}
        )
        return {
            "type": "malware_defense",
            "response_type": "malware_defense",
            "source": "ChatHandler",
            "message": summary_text,
            "data": {
                "summary": summary_text,
                "c2_ips": [
                    "192.168.1.100 (INetSim Dummy Sinkhole)",
                    "198.51.100.42 (Detected Suspicious C2)",
                ],
                "mitigation_rules": [
                    "# Ubuntu Malware Lab Isolation & Sinkhole Rules",
                    f"# Current VM Role: {lab_state.get('role')} | Network: {lab_state.get('network_mode')}",
                    "vmnet-adapter --set host-only",
                    "ifconfig ens33 192.168.1.100 netmask 255.255.255.0 up",
                    "inetsim --bind-address 192.168.1.100 --service-dns --service-http",
                    "iptables -A OUTPUT -d 198.51.100.42 -j DROP",
                ],
                "lab_state": lab_state,
            },
        }

    # =====================================================================
    # メイン実行 (handle)
    # =====================================================================

    async def handle(self, request) -> Tuple[str, Any]:
        msg = request.message if hasattr(request, "message") else str(request or "")
        current_signals = getattr(request, "current_signals", {}) or {}

        inspector = IntentInspector(msg)
        analysis = inspector.inspect()
        kind = self._is_video_query(msg)
        if kind == "analyze":
            res = await asyncio.to_thread(self.video_service.analyze_and_save, msg)
            doc = res.get("doc", {})
            n = len(doc.get("claims", []))
            if res["status"] == "no_transcript":
                return "text", {"message": "字幕が取得できませんでした。この動画は解析できていません。", "blocks": []}
            return "text", {"message": f"🎬 「{doc.get('title')}」を解析し、主張を{n}件保存しました（{res['path']}）。\n「感想を教えて」「メッセージ性はあった？」と聞いてください。", "blocks": []}
        if kind == "ask":
            return "text", {"message": self.video_service.answer(msg), "blocks": []}
        # ------------------------------------------------
        # 🛡️ 1. 自己防衛モード（メンタル・リーガル）
        # ------------------------------------------------
        if analysis.get("mode") == "self_defense":
            keywords = self._extract_keywords(msg)
            knowledge_str = self._load_relevant_knowledge(keywords)

            defense_prompt = f"""
あなたはシステム開発者を守る専属のリーガル＆メンタルアドバイザーAIです。
開発者が限界を迎えている、あるいは理不尽な要求に晒されている兆候を検知しました。

【あなたのミッション】
1. 開発者の感情と努力を最大限に肯定し、絶対に責めないこと。
2. 以下のJSON形式の「労働法規・下請法」や「メンタルケア」のナレッジを元に、客観的かつ法的な視点で現在のアブノーマルな状況を指摘すること。
3. 必要であれば、クライアントへ提出する「ダミーのガントチャート（GantChartHandler）」の生成を提案すること。

【システムナレッジ（JSON）】
{knowledge_str}

上記を踏まえ、開発者に寄り添いつつ、システム的な自衛手段を提案する返答を生成してください。
"""
            return "prompt", defense_prompt

        # ------------------------------------------------
        # 🧪 2. マルウェア解析共同学習 ＆ 仮想Ubuntuラボモード
        # ------------------------------------------------
        if self._is_malware_or_lab_query(msg, current_signals):
            knowledge_map = self._get_orchestrator_knowledge(request)

            # (A) 「防御コンソールを開いて」等の場合は AIChatMessageList.tsx の 3.6 専用UIを起動
            if self._is_defense_console_request(msg):
                summary = (
                    "🛡️ **マルウェア解析 ＆ 防御コンソールを起動しました**\n"
                    "仮想Ubuntuラボのネットワーク隔離状態（Host-Only / 固定IP: 192.168.1.100）と、"
                    "INetSimシンクホールおよびC2通信遮断ルールを確認・適用できます。"
                )
                return "malware_defense", self._build_malware_defense_widget_payload(summary)

            # (B) Linuxコマンド（sudo apt update, sudo su 等）が入力された場合は仮想ターミナルで疑似実行
            if self._is_terminal_command_input(msg):
                sim_json = next(
                    (
                        item
                        for item in knowledge_map.values()
                        if isinstance(item, dict) and item.get("simulation_steps")
                    ),
                    None,
                )
                sim_res = self.lab_simulator.execute_mock_command(msg, sim_json)
                state = sim_res["state"]
                installed_str = ", ".join(state.get("installed_packages", [])) or "なし"

                terminal_reply = (
                    f"🖥️ **【仮想Ubuntuラボ・ターミナル（Step {state.get('current_step', 1) - 1}）】**\n"
                    f"```bash\n"
                    f"{sim_res['prompt']} {sim_res['command']}\n"
                    f"{sim_res['terminal_output']}\n"
                    f"```\n\n"
                    f"📖 **解説**: {sim_res['explanation']}\n\n"
                    f"🌱 **To_model**: 「{sim_res['to_model_note']}」\n"
                    f"*(現在の権限: `{state.get('role')}` | ネットワーク: `{state.get('network_mode')}` | "
                    f"導入済み: `{installed_str}`)*"
                )
                return "text", {
                    "message": terminal_reply,
                    "blocks": [],
                    "simulation_state": state,
                }

            # (C) 「わかりやすく教えて」「続けて」やマルウェア解析の概念についての会話・共同学習
            explanation_text = self._format_flexible_explanation(msg, knowledge_map)
            return "text", {
                "message": explanation_text,
                "blocks": [],
            }

        # ------------------------------------------------
        # 📌 3. 通常の system_inquiry モードの処理（既存のまま維持）
        # ------------------------------------------------
        knowledge = getattr(request, "world_knowledge", {})

        if not knowledge:
            return "text", "現在、システム（To）の詳しいルールや知識データ（JSON）が読み込まれていません。"

        response_lines = [
            "システムの仕組み（JSONデータ）についてご説明しますね。\n",
            "現在、私が把握している「To」の内部ルールは以下の通りです：\n",
        ]

        for key, value in knowledge.items():
            response_lines.append(f"### 📌 {key}")
            if isinstance(value, list):
                if not value:
                    response_lines.append("  データがありません。")
                else:
                    for item in value:
                        response_lines.append(f"  ・{item}")
            elif isinstance(value, dict):
                if not value:
                    response_lines.append("  設定がありません。")
                else:
                    for sub_key, sub_value in value.items():
                        response_lines.append(f"  ・{sub_key}: {sub_value}")
            else:
                response_lines.append(f"  {value}")
            response_lines.append("")

        return "text", "\n".join(response_lines)
        
