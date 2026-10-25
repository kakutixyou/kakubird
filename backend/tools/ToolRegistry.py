# api/services/tools/registry/ToolRegistry.py

from __future__ import annotations

import copy
import logging
from typing import Any, Callable, Dict, List, Optional

# 先ほど作成された ToolRouter と ToolSpec をインポート
try:
    from api.services.tools.ToolRouter import ToolRouter, ToolSpec
except ModuleNotFoundError:
    from backend.api.services.tools.ToolRouter import ToolRouter, ToolSpec

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    LLM向けのツール定義（Schema）と、実行環境（ToolRouter）を統合管理するレジストリ。
    
    PromptBuilderはここから get_all_schemas() で LLM に教える仕様書を取得し、
    OrchestratorはLLMが選んだツールを router.execute() に渡します。
    """

    def __init__(self, router: Optional[ToolRouter] = None) -> None:
        # 外部からRouterが渡されなければ内部で生成する
        self.router = router or ToolRouter()
        
        # LLMに渡すためのツール定義（JSON Schema）を保持
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        target: Any,
        method: Optional[str] = "execute",
        aliases: Optional[List[str]] = None,
        run_in_thread: bool = False,
    ) -> None:
        """
        ツールをLLM用スキーマと実行ルーターの両方に一括登録する。

        Parameters
        ----------
        name : str
            ツール名（正規表現 ^[a-z][a-z0-9_.-]{0,63}$ に従うこと）
        description : str
            LLMがこのツールをいつ、どう使うべきかの説明
        parameters : Dict[str, Any]
            ツールの引数スキーマ（JSON Schema形式）
        target : Any
            実行される関数、またはクラスのインスタンス
        method : Optional[str]
            targetがクラスインスタンスの場合、実行するメソッド名
        aliases : Optional[List[str]]
            ツールの別名
        run_in_thread : bool
            同期関数を非同期環境で安全に実行するためにスレッドを使用するかどうか
        """
        # 1. LLM向けのスキーマを登録
        self._schemas[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }

        # 2. ToolRouter への登録（実際の実行情報）
        if callable(target) and method is None:
            self.router.register_callable(
                name=name,
                function=target,
                aliases=aliases or [],
                run_in_thread=run_in_thread,
                metadata={"schema": self._schemas[name]}
            )
        else:
            self.router.register(
                name=name,
                target=target,
                method=method,
                aliases=aliases or [],
                run_in_thread=run_in_thread,
                metadata={"schema": self._schemas[name]}
            )
            
        logger.debug(f"🔧 [ToolRegistry] ツール登録完了: {name}")

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        PromptBuilder 等へ渡すための全ツール仕様（Schema）を取得する。
        誤って上書きされないようディープコピーを返す。
        """
        return [copy.deepcopy(schema) for schema in self._schemas.values()]

    def get_schemas_by_names(self, names: List[str]) -> List[Dict[str, Any]]:
        """
        特定のモード（例: コーディング中、雑談中）で許可されたツール群のみの仕様を取得する。
        """
        return [
            copy.deepcopy(self._schemas[name]) 
            for name in names 
            if name in self._schemas
        ]

    def setup_default_tools(self) -> None:
        """
        システム標準のツール群を登録する。
        将来的には ToolDiscovery.py によって /tools フォルダを自動スキャンして
        登録する仕組み（Auto-loader）に置き換えることを推奨。
        """
        # ========================================================
        # [移行期対応]
        # 現在の handlers フォルダ内の機能を Tool として登録する例。
        # 新しい tools/ ディレクトリのクラスが完成次第、import 先を切り替えます。
        # ========================================================

        # --- 1. Math / Calculator ---
        try:
            from api.services.handlers.Math_Handler.handler import MathHandler
            self.register_tool(
                name="math_calculator",
                description="複雑な数式や自然言語混じりの計算要求を処理します。例: '22000000000+34000'",
                parameters={
                    "formula": "計算したい数式 (例: '22000000000+34000')"
                },
                target=MathHandler(),
                method="handle" # 古いHandlerの実行メソッドを指定
            )
        except Exception as e:
            logger.warning(f"MathHandler の読み込みをスキップしました: {e}")

        # --- 2. Filesystem / File Write ---
        try:
            from api.services.handlers.FileWriteHandler import FileWriteHandler
            self.register_tool(
                name="file_writer",
                description="指定されたパスにファイルを作成、またはソースコードを書き出します。",
                parameters={
                    "file_path": "保存先のファイルパス（例: 'src/components/Button.jsx'）",
                    "content": "ファイルに書き込むテキストまたはコード全体"
                },
                target=FileWriteHandler(),
                method="handle"
            )
        except Exception as e:
            logger.warning(f"FileWriteHandler の読み込みをスキップしました: {e}")

        # --- 3. Weather ---
        try:
            from api.services.handlers.weather_handler import WeatherHandler
            self.register_tool(
                name="weather_search",
                description="指定された地域・都市の現在の天気や予報を取得します。",
                parameters={
                    "location": "天気を知りたい都市名（例: '東京'）"
                },
                target=WeatherHandler(),
                method="handle"
            )
        except Exception as e:
            logger.warning(f"WeatherHandler の読み込みをスキップしました: {e}")


# ============================================================
# Standalone Test
# ============================================================
if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.DEBUG)

    registry = ToolRegistry()
    registry.setup_default_tools()

    print("\n=== 📜 LLMへ渡すツール仕様 (PromptBuilder用) ===")
    print(json.dumps(registry.get_all_schemas(), ensure_ascii=False, indent=2))
    
    print("\n=== ⚙️ ToolRouter に登録されているツール群 ===")
    print(json.dumps(registry.router.list_tools(), ensure_ascii=False, indent=2))