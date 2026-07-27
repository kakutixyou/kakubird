# plugins/github_search/searcher_stream.py (設計)
import sys
import json
import time

def build_math_query(user_msg):
    # 数学キーワード抽出
    return user_msg.replace("似たプロジェクト", "").strip() + " math"

def search_github(msg):
    # 【STEP 1: クエリ構築 (10%)】
    yield json.dumps({"type": "progress", "value": 10, "status": "数学キーワードを抽出中..."})
    query = build_math_query(msg)
    time.sleep(1) # 重い処理のフリ

    # 【STEP 2: GitHub API送信 (40%)】
    yield json.dumps({"type": "progress", "value": 40, "status": "GitHubを検索中..."})
    # (実際にはここでhttpxなどを叩く)
    time.sleep(2) # 重い処理のフリ

    # 【STEP 3: フィルタリング・整形 (70%)】
    yield json.dumps({"type": "progress", "value": 70, "status": "結果を類似度順に並べ替え中..."})
    mock_repos = [
        {"name": "math-race", "url": "#", "description": "Formula racing game", "stars": 102, "language": "Python"}
    ]
    time.sleep(1) # 重い処理のフリ

    # 【STEP 4: 完了 (100%)】
    # dataフィールドに入れて返す
    yield json.dumps({"type": "result", "value": 100, "data": {
        "message": f"GitHubから数学関連の類似プロジェクトを探索しました。",
        "query_used": query,
        "repositories": mock_repos
    }})

if __name__ == "__main__":
    user_msg = sys.argv[1] # 引数でメッセージ受け取る
    for packet in search_github(user_msg):
        print(packet, flush=True) # flushで即時出力