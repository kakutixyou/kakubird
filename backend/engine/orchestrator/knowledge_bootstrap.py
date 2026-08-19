# 元Chat_orchestrator.py
# 2. 完璧な「関心の分離（Separation of Concerns）」
# 5つのファイルへの分割案は、それぞれのモジュールが「何をするものか」が明確で美しいです。

# knowledge_bootstrap.py: 起動時の重い処理や外部データ読み込みを隔離できる。

# state_store.py: 「状態（記憶）」の管理。将来的にDB（SQLiteやSupabase）に移行したくなった際も、ここだけ書き換えれば済むようになります。

# handler_scorer.py: 最もロジックが複雑化しやすい「評価・ルーティング基準」を独立させることで、将来的に「スコア計算自体を別の軽量AIにやらせる」といった改修も容易になります。

# response_merger.py: 状態を持たない純粋関数（Pure Function）になるため、バグが起きにくく、ユニットテストが非常に書きやすくなります。

# request_pipeline.py: リクエストが来てから返すまでの「データの流れ」だけを記述できるため、処理の全体像がひと目でわかります。

# backend/services/orchestrator/knowledge_bootstrap.py

import os
from typing import List, Tuple, Any

def load_knowledge_router(knowledge_router_class: Any, base_file_path: str):
    """
    KnowledgeRouterを動的に初期化し、registry.jsonのパスを解決する
    :param knowledge_router_class: KnowledgeRouterのクラスそのもの
    :param base_file_path: 呼び出し元(__file__)のパス
    """
    if knowledge_router_class is None:
        return None

    base_dir = os.path.dirname(os.path.abspath(base_file_path))
    registry_path = os.path.abspath(os.path.join(base_dir, "../knowledge/registry.json"))
    
    if os.path.exists(registry_path):
        print(f"📚 KnowledgeRouter をロードしました: {registry_path}")
        return knowledge_router_class(registry_path)
    
    # フォールバック探索
    fallback_path = "backend/engine/knowledge/registry.json"
    if os.path.exists(fallback_path):
        return knowledge_router_class(fallback_path)
        
    print(" registry.json が見つかりません。ナレッジルーティングはバイパスされます。")
    return None


def load_occupation_and_history_titles(
    knowledge_manager: Any, 
    occupations_dir: str, 
    historical_figures_dir: str
) -> Tuple[List[str], List[str]]:
    """
    職業と歴史人物のタイトル一覧を読み込む
    """
    occupation_titles: List[str] = []
    historical_figures_titles: List[str] = []

    if knowledge_manager is None:
        print(" KnowledgeManager が見つかりません。職業/歴史人物ナレッジはバイパスされます。")
        return occupation_titles, historical_figures_titles

    # 1. 職業タイトルの読み込み
    try:
        occupation_items = knowledge_manager.load_all_json_from_dir(occupations_dir)
        occupation_titles = [item["title"] for item in occupation_items if item.get("title")]
    except Exception as e:
        print(f" 職業タイトル一覧の読み込みに失敗しました: {e}")

    # 2. 歴史人物タイトルの読み込み
    try:
        history_items = knowledge_manager.load_all_json_from_dir(historical_figures_dir)
        for item in history_items:
            try:
                data = item.data  # LazyKnowledgeの本体を開く
            except Exception as e:
                print(f" 歴史人物データの読み込みに失敗しました ({item.rel_path}): {e}")
                continue

            hf = data.get("history_figures", {}) if isinstance(data, dict) else {}
            for group in ("world_history", "japan_history"):
                people = hf.get(group)
                if isinstance(people, list):
                    for p in people:
                        name = p.get("name")
                        if name:
                            historical_figures_titles.append(name)
    except Exception as e:
        print(f" 歴史人物タイトル一覧の読み込みに失敗しました: {e}")

    return occupation_titles, historical_figures_titles