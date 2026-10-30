# Shooter dev docs

このリポジトリには、シューティングゲーム向けの生成モデルとアセット解決の土台を追加しました。

主な追加先:
- project_generation/shooter_templates/
- project_generation/shooter_project/
- handlers/AssetHandler.py
- tools/game_logger.py

初期設定:
- drop_interval_sec = 3
- boss hp = 200
- player lives = 2
- attack up = 永続 +3
- damage nullify = 10秒無効化

次の段階では、本体側のゲーム画面とこの JSON を接続して、実際の動作確認を行う。
