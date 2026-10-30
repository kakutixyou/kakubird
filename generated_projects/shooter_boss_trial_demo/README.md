# Shooter Boss Trial Demo

このフォルダは、モデル定義に基づく最小シューティングゲームのデモです。

- config.js: ゲーム設定とアイテム効果の定義
- app.js: 実行ロジックとログ記録
- index.html: canvas UI を描画

実行時の振る舞い:
- 3秒ごとにアイテムが落ちる
- 攻撃力 +3 の永続バフ
- 10秒ダメージ無効化シールド
- ボスHP 200
- 残機 2

ログ:
- ブラウザの開発者ツールで `window.__shooterEvents` を確認できます
- `window.exportShooterLog()` で JSON 文字列を取得できます
- `window.exportShooterSummary()` で最終サマリーも取得できます

ブラウザで開くと遊べます:

1. `index.html` をブラウザで開く
2. WASD または 矢印キーで移動
3. Space で弾を発射
4. ボスを倒し、アイテムを拾う
5. 開発者ツールで log を確認し、設定と実行のズレを確認する
