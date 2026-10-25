"""ChatHandler package.

既存の `from api.services.handlers.ChatHandler import ChatHandler`
をそのまま使えるようにする。
少し大事な情報↓
解決手順:

エクスプローラーまたはVS Codeで backend/api/services/handlers/ChatHandler/ フォルダの中身を確認してください。

フォルダ内のファイル構成に合わせて、以下のいずれかの対応を行います。

パターンA（別名のファイルがある場合）: 例えば chat_handler.py などの名前で存在している場合、__init__.py の7行目を from .chat_handler import ChatHandler に修正します。

パターンB（__init__.py 自体に処理を書く、またはファイルが欠損している場合）: __init__.py の from .handler import ChatHandler を削除し、正しいファイルからインポートするか、handler.py を作成して ChatHandler クラスを配置します。
"""

from .ChatHandler import ChatHandler

__all__ = ["ChatHandler"]
