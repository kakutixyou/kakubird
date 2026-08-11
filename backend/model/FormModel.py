from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class FormControlModel:
    """
    フォーム内の個々の入力コントロール（input, select, textarea, button等）のモデル。
    Reactの `useState` の初期値や、入力コンポーネントのProps生成に必要な情報を保持する。
    """
    tag: str  # 例: "input", "textarea", "select", "button"
    name: Optional[str] = None
    control_type: Optional[str] = None  # type属性 (例: "text", "submit", "hidden", "file")
    element_id: Optional[str] = None
    
    # バリデーション・状態管理用メタデータ
    is_required: bool = False
    default_value: Optional[str] = None
    
    # その他の属性（placeholder, disabledなど）
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "name": self.name,
            "type": self.control_type,
            "id": self.element_id,
            "is_required": self.is_required,
            "default_value": self.default_value,
            "attributes": self.attributes,
        }


@dataclass
class FormModel:
    """
    HTMLの <form> 要素全体を表現するデータモデル。
    複数の FormControlModel を管理し、JSX化の際の `onSubmit` イベントや
    フォーム全体の状態管理フック構築のための構造化データを提供する。
    """
    element_id: Optional[str] = None
    method: str = "GET"
    action: Optional[str] = None
    
    # フォーム内の入力コントロール一覧
    controls: List[FormControlModel] = field(default_factory=list)
    
    # フォーム自体の追加属性（クラスなど）
    attributes: Dict[str, str] = field(default_factory=dict)

    # --- React/JSX 変換を見据えた自動判定メタデータ ---
    has_file_upload: bool = field(init=False, default=False)
    react_submit_handler: str = field(init=False, default="handleSubmit")

    def __post_init__(self) -> None:
        """
        初期化時に、属性から特定の振る舞い（ファイルアップロード等）を自動判定する。
        """
        if self.attributes.get("enctype") == "multipart/form-data":
            self.has_file_upload = True

    def add_control(self, control: FormControlModel) -> None:
        """
        フォームに入力コントロールを追加する。
        fileタイプが含まれる場合は自動的にファイルアップロード対応フラグを立てる。
        """
        self.controls.append(control)
        if control.control_type == "file":
            self.has_file_upload = True

    def extract_state_keys(self) -> List[str]:
        """
        Reactの `useState` で管理すべき入力フィールドの name 属性のリストを抽出する。
        （submitボタンや、nameを持たない装飾要素を除外）
        """
        keys = []
        for ctrl in self.controls:
            if ctrl.name and ctrl.control_type not in ("submit", "button", "reset"):
                keys.append(ctrl.name)
        return keys

    def to_dict(self) -> Dict[str, Any]:
        """
        KnowledgeBuilderの `self.meta["forms"]` に集約するための辞書化。
        """
        return {
            "id": self.element_id,
            "method": self.method,
            "action": self.action,
            "has_file_upload": self.has_file_upload,
            "react_submit_handler": self.react_submit_handler,
            "state_keys": self.extract_state_keys(),
            "inputs": [control.to_dict() for control in self.controls],
            "attributes": self.attributes,
        }