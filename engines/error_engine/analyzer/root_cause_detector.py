# root_cause_detector.py

from typing import Dict, List, Any


class RootCauseDetector:
    def __init__(self):
        self.rules = {
            "ModuleNotFoundError": {
                "causes": [
                    "ライブラリがインストールされていない",
                    "仮想環境が異なる",
                    "モジュール名のスペルミス"
                ],
                "solutions": [
                    "pip install <module>",
                    "仮想環境を確認する",
                    "import文を確認する"
                ],
                "confidence": 0.95
            },

            "ImportError": {
                "causes": [
                    "モジュールの読み込み失敗",
                    "循環参照",
                    "ライブラリバージョン不一致"
                ],
                "solutions": [
                    "importパスを確認する",
                    "循環参照を解消する",
                    "ライブラリを更新する"
                ],
                "confidence": 0.85
            },

            "AttributeError": {
                "causes": [
                    "Noneが代入されている",
                    "存在しない属性を呼び出している",
                    "オブジェクト型の想定違い"
                ],
                "solutions": [
                    "Noneチェックを追加する",
                    "dir()で属性を確認する",
                    "型をprintして確認する"
                ],
                "confidence": 0.90
            },

            "KeyError": {
                "causes": [
                    "辞書キーが存在しない",
                    "キー名のスペルミス"
                ],
                "solutions": [
                    "dict.keys()で確認する",
                    "get()を利用する"
                ],
                "confidence": 0.92
            },

            "TypeError": {
                "causes": [
                    "型が一致していない",
                    "引数の数が違う",
                    "Noneを渡している"
                ],
                "solutions": [
                    "type()で型確認",
                    "関数定義を確認",
                    "引数を見直す"
                ],
                "confidence": 0.75
            },

            "SyntaxError": {
                "causes": [
                    "括弧不足",
                    "コロン忘れ",
                    "インデント崩れ"
                ],
                "solutions": [
                    "エラー行を確認する",
                    "括弧の対応を確認する",
                    "コードフォーマッターを使う"
                ],
                "confidence": 0.98
            }
        }

    def detect(self, parsed_error: Dict[str, Any]) -> Dict[str, Any]:
        """
        parsed_error例

        {
            "type": "ModuleNotFoundError",
            "message": "No module named 'requests'"
        }
        """

        error_type = parsed_error.get("type")

        if error_type not in self.rules:
            return {
                "error_type": error_type,
                "root_causes": [
                    "未登録エラー"
                ],
                "solutions": [
                    "ログ全体を確認する"
                ],
                "confidence": 0.20
            }

        rule = self.rules[error_type]

        return {
            "error_type": error_type,
            "root_causes": rule["causes"],
            "solutions": rule["solutions"],
            "confidence": rule["confidence"]
        }


if __name__ == "__main__":

    detector = RootCauseDetector()

    sample_error = {
        "type": "ModuleNotFoundError",
        "message": "No module named 'requests'"
    }

    result = detector.detect(sample_error)

    print(result)