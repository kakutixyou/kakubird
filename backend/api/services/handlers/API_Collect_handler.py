import re
import json
import traceback
from typing import Any, Dict, Optional, Tuple

import requests


class APICollectHandler:
    """
    目的:
      - ユーザーの入力テキストから 東京都オープンデータAPI情報を抽出
      - 全件取得可能な Python スクリプト文字列を生成
      - フロント(blocks.jsx)で描画可能な blocks 形式で返す

    返却形式:
      ("ui_code", {"message": str, "blocks": list})
      または
      ("text", {"message": str, "blocks": []})
    """

    def __init__(self) -> None:
        self.name = "APICollectHandler"

    # ---------------------------------------------------------
    # Routing score
    # ---------------------------------------------------------
    async def calculate_score(self, message: str, signals: Optional[dict] = None) -> int:
        if not message:
            return 0

        text = message.lower()

        keywords = [
            "api", "json", "xml", "post", "try it out", "execute",
            "ベースurl", "base url", "requestbody", "limit", "offset",
            "catalog.data.metro.tokyo.lg.jp", "service.api.metro.tokyo.lg.jp",
            "api_collect_handler.py", "全文", "ハンドラー", "handler",
            "自作ai", "blocks.jsx", "チャット画面"
        ]

        hit = sum(1 for k in keywords if k in text)

        # 東京API系URLが含まれる場合は強く寄せる
        if ("service.api.metro.tokyo.lg.jp" in text) or ("catalog.data.metro.tokyo.lg.jp" in text):
            return 100

        if hit >= 6:
            return 95
        if hit >= 4:
            return 85
        if hit >= 2:
            return 60
        return 0

    # ---------------------------------------------------------
    # Main entry
    # ---------------------------------------------------------
    async def handle(self, request: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
        try:
            raw_message = getattr(request, "message", "") or ""
            parsed = self._parse_spec_from_text(raw_message)

            # 最低限の必須情報チェック
            if not parsed.get("endpoint_path"):
                return "text", {
                    "message": "API仕様の解析に失敗しました。エンドポイントパス（/api/.../json）が見つかりませんでした。",
                    "blocks": []
                }

            # 念のため軽い疎通チェック（失敗してもコード生成は続行）
            probe_result = self._probe_api_once(parsed)

            generated_code = self._build_generated_python_script(parsed)

            summary_json = {
                "catalog_url": parsed.get("catalog_url"),
                "source_csv_url": parsed.get("source_csv_url"),
                "base_url": parsed.get("base_url"),
                "endpoint_path": parsed.get("endpoint_path"),
                "limit_default": parsed.get("limit_default"),
                "limit_max": parsed.get("limit_max"),
                "output_file": parsed.get("output_filename"),
                "probe": probe_result
            }

            content: Dict[str, Any] = {
                "message": (
                    "API仕様を解析し、全件取得用の堅牢で汎用的なPythonコードを生成しました。"
                    " 下の CodeBlock を保存して実行してください。"
                ),
                "blocks": [
                    {
                        "type": "JsonViewerBlock",
                        "props": {
                            "title": "API解析結果",
                            "json": summary_json
                        }
                    },
                    {
                        "type": "CodeBlock",
                        "props": {
                            "title": "fetch_tokyo_opendata.py",
                            "language": "python",
                            "code": generated_code
                        }
                    }
                ]
            }

            return "ui_code", content

        except Exception as e:
            traceback.print_exc()
            return "text", {
                "message": f"APICollectHandler で例外が発生しました: {e}",
                "blocks": []
            }

    # ---------------------------------------------------------
    # Parse
    # ---------------------------------------------------------
    def _parse_spec_from_text(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "catalog_url": None,
            "source_csv_url": None,
            "base_url": "https://service.api.metro.tokyo.lg.jp",
            "endpoint_path": None,
            "limit_default": 100,
            "limit_max": 1000,
            "output_filename": "tokyo_aed_facilities.json"
        }

        urls = re.findall(r"https?://[^\s]+", text)
        for u in urls:
            if "catalog.data.metro.tokyo.lg.jp" in u:
                result["catalog_url"] = u
            elif "city.sumida.lg.jp" in u and u.endswith(".csv"):
                result["source_csv_url"] = u
            elif "service.api.metro.tokyo.lg.jp" in u and "/api/" in u:
                p = u.replace("https://service.api.metro.tokyo.lg.jp", "")
                result["endpoint_path"] = p

        base_match = re.search(r"ベースURL\s*[\r\n ]*https?://[^\s]+", text, re.IGNORECASE)
        if base_match:
            m = re.search(r"https?://[^\s]+", base_match.group(0))
            if m:
                result["base_url"] = m.group(0).strip()

        ep_match = re.search(r"(/api/[a-zA-Z0-9\-]+/json)", text)
        if ep_match:
            result["endpoint_path"] = ep_match.group(1).strip()

        max_match = re.search(r"最大値は\s*(\d+)", text)
        if max_match:
            result["limit_max"] = int(max_match.group(1))

        if result["endpoint_path"]:
            safe = result["endpoint_path"].replace("/api/", "").replace("/json", "")
            safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", safe)
            result["output_filename"] = f"{safe}_all.json"

        return result

    # ---------------------------------------------------------
    # Optional one-shot probe
    # ---------------------------------------------------------
    def _probe_api_once(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        base_url = spec.get("base_url") or ""
        endpoint_path = spec.get("endpoint_path") or ""
        if not base_url or not endpoint_path:
            return {"ok": False, "reason": "base_url or endpoint_path missing"}

        url = f"{base_url}{endpoint_path}"
        params = {"limit": 1, "offset": 0}
        headers = {"Content-Type": "application/json"}

        try:
            r = requests.post(url, params=params, json={}, headers=headers, timeout=20)
            info: Dict[str, Any] = {
                "ok": r.status_code == 200,
                "status_code": r.status_code
            }
            if r.status_code == 200:
                j = r.json()
                info["total"] = j.get("total")
                info["subtotal"] = j.get("subtotal")
                info["sample_hits_count"] = len(j.get("hits", [])) if isinstance(j.get("hits", []), list) else 0
            else:
                info["body_head"] = (r.text or "")[:200]
            return info
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    # ---------------------------------------------------------
    # Code generator
    # ---------------------------------------------------------
    def _build_generated_python_script(self, spec: Dict[str, Any]) -> str:
        base_url = spec.get("base_url", "https://service.api.metro.tokyo.lg.jp")
        endpoint_path = spec.get("endpoint_path", "/api/unknown/json")
        limit_max = int(spec.get("limit_max", 1000))
        output_filename = spec.get("output_filename", "tokyo_aed_facilities.json")
        catalog_url = spec.get("catalog_url")
        source_csv_url = spec.get("source_csv_url")

        # 生成されるコード（完全版仕様）
        script = f'''import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Any

def fetch_tokyo_opendata(api_url: str, dataset_name: str, limit: int = {limit_max}) -> List[Dict[str, Any]]:
    """
    指定された東京都オープンデータAPIからデータを全件取得する汎用関数。
    内部でセッションを使用し、通信エラー時のハンドリングと進捗表示を行います。
    """
    headers = {{"Content-Type": "application/json"}}
    payload: Dict[str, Any] = {{}}  # 仕様にある通り、簡易実行は {{}} が安全
    all_hits: List[Dict[str, Any]] = []
    offset = 0

    print(f"{{dataset_name}} の全件取得を開始します...")
    print(f"API_URL: {{api_url}}")

    # Sessionを使用することでTCPコネクションを使い回し高速化
    with requests.Session() as session:
        session.headers.update(headers)

        while True:
            params = {{"limit": limit, "offset": offset}}
            print(f"offset={{offset}} から最大 {{limit}} 件をリクエスト中...")

            try:
                # タイムアウトは (接続, 読み込み) で個別に設定
                res = session.post(
                    api_url,
                    params=params,
                    json=payload,
                    timeout=(10.0, 30.0)
                )
                res.raise_for_status()  # 4xx, 5xxエラーをキャッチ
                body = res.json()
                
            except requests.exceptions.HTTPError as e:
                print(f"[ERROR] HTTPエラー ({{res.status_code}}): {{res.text[:300]}}")
                break
            except (requests.RequestException, ValueError) as e:
                print(f"[ERROR] 通信またはJSON解析エラー: {{e}}")
                break

            hits = body.get("hits", [])
            total_count = body.get("total", 0)

            if not hits:
                print("hits が空になったため取得終了。")
                break

            all_hits.extend(hits)
            print(f"現在 {{len(all_hits)}} / {{total_count}} 件取得完了")

            if len(all_hits) >= total_count:
                print("全データの取得が完了しました！")
                break

            offset += limit
            time.sleep(1.0)  # サーバー負荷軽減

    return all_hits


def save_json(data: List[Dict[str, Any]], filepath: str | Path) -> None:
    """取得したデータをJSONとして安全に保存する関数"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 今回チャットから抽出されたメタデータ
    CATALOG_URL = {json.dumps(catalog_url, ensure_ascii=False)}
    SOURCE_CSV_URL = {json.dumps(source_csv_url, ensure_ascii=False)}
    
    BASE_URL = "{base_url}"
    ENDPOINT_PATH = "{endpoint_path}"
    TARGET_API_URL = BASE_URL + ENDPOINT_PATH
    OUTPUT_FILENAME = "{output_filename}"

    if CATALOG_URL:
        print(f"Catalog: {{CATALOG_URL}}")

    # 関数を呼び出してデータを取得
    # 第2引数にはファイル名から推測したデータセット名を渡す
    dataset_name = OUTPUT_FILENAME.replace("_all.json", "")
    rows = fetch_tokyo_opendata(TARGET_API_URL, dataset_name)
    
    if rows:
        save_json(rows, OUTPUT_FILENAME)
        print(f"\\n{{OUTPUT_FILENAME}} に {{len(rows)}} 件のデータを保存しました。")
    else:
        print("\\n保存対象データがありませんでした。")
'''
        return script