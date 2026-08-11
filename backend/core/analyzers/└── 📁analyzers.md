└── 📁analyzers
    ├── tag_analyzer.py       # タグ一覧、出現回数、セマンティックタグ（作成済）
    ├── attribute_analyzer.py # 属性、ID、クラス、およびインラインイベント(on*)の抽出
    ├── dom_analyzer.py       # DOMの深度計算、ComponentTreeの構築（構造解析）
    ├── component_analyzer.py # ルール/意味論/CustomElementsからのコンポーネント推測
    ├── script_analyzer.py    # <script>タグの抽出とコード本文の保持
    ├── css_analyzer.py       # <style>タグの抽出とCSSコードの保持
    ├── metrics_analyzer.py   # スコア計算、複雑度計算（評価フィードバック系）