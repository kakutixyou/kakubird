# Widget Guide – BookCMS への新しい API ウィジェットの追加方法

## 概要

BookCMS のウィジェットシステムは、**プラグイン方式**で設計されています。  
新しい API ウィジェットを追加するには、以下の 3 ステップだけです。

1. `js/widgets/` に新しいウィジェットファイルを作成する
2. `BaseWidget` を継承してクラスを定義する
3. `index.html` でファイルを読み込む

---

## ファイル構成

```
js/
├── widget-system.js          # コアフレームワーク（変更不要）
├── page-manager.js           # ページ管理（変更不要）
└── widgets/
    ├── dog-api-widget.js     # Dog API ウィジェット（参考実装）
    ├── rakuten-api-widget.js # （追加例）
    └── weather-api-widget.js # （追加例）
```

---

## ステップ 1 – ウィジェットファイルを作成する

`js/widgets/my-new-widget.js` を作成します。

```js
'use strict';

class MyNewWidget extends BaseWidget {
  constructor() {
    super({
      id: 'my-new-widget',          // 一意な ID
      label: 'マイ新しいAPI',        // ボタンに表示されるラベル
      icon: '🌟',                   // ボタンに表示される絵文字
      endpoint: 'https://api.example.com/random', // API エンドポイント
    });
  }

  /**
   * APIレスポンスから表示に必要なデータを抽出し、DOM要素を返す。
   * @param {Object} data - fetchData() が返した JSON オブジェクト
   * @returns {HTMLElement}
   */
  render(data) {
    const wrapper = document.createElement('div');
    wrapper.className = 'widget-content';

    // ここで data から必要な値を取り出して DOM を組み立てる
    const p = document.createElement('p');
    p.textContent = data.result ?? JSON.stringify(data);
    wrapper.appendChild(p);

    return wrapper;
  }
}

// 最後に必ずレジストリへ登録する
WidgetRegistry.register(new MyNewWidget());
```

---

## ステップ 2 – `index.html` でファイルを読み込む

`index.html` の「Register additional widgets here」コメントの直後に
`<script>` タグを追記します。

```html
<!-- index.html 抜粋 -->
<script src="js/widgets/dog-api-widget.js"></script>
<script src="js/widgets/my-new-widget.js"></script>  <!-- ← 追加 -->
```

ページをリロードすると、サイドバーに新しいボタンが自動的に表示されます。

---

## カスタマイズポイント

### fetchData() のオーバーライド

デフォルトの `fetchData()` はシンプルな GET リクエストを行います。  
認証ヘッダーやクエリパラメータが必要な場合はオーバーライドしてください。

```js
async fetchData() {
  const res = await fetch(`${this.endpoint}?applicationId=YOUR_APP_ID`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

> **セキュリティ注意事項**: API キーをフロントエンドのコードに直接書くことは避けてください。  
> 本番環境ではバックエンドのプロキシサーバー経由で API を叩くことを推奨します。

### 複数の API エンドポイントを使う

コンストラクタで `this.endpoint` 以外のプロパティも自由に定義できます。

```js
constructor() {
  super({ id: 'weather', label: '天気', icon: '⛅', endpoint: 'https://api.weather.example.com/current' });
  this.forecastEndpoint = 'https://api.weather.example.com/forecast';
}

async fetchData() {
  const [current, forecast] = await Promise.all([
    fetch(this.endpoint).then(r => r.json()),
    fetch(this.forecastEndpoint).then(r => r.json()),
  ]);
  return { current, forecast };
}
```

---

## 既存ウィジェット一覧

| ID        | ラベル    | API エンドポイント                            |
|-----------|-----------|-----------------------------------------------|
| `dog-api` | 犬の画像  | `https://dog.ceo/api/breeds/image/random`     |

---

## よくある質問 (FAQ)

**Q: ウィジェットを追加したのにボタンが表示されない**  
A: `WidgetRegistry.register(new MyNewWidget())` が呼ばれているか確認してください。  
また、`<script>` の読み込み順が `widget-system.js` より後になっているか確認してください。

**Q: API が CORS エラーを返す**  
A: 外部 API の多くはブラウザからの直接アクセスを制限しています。  
バックエンドプロキシを用意するか、API 側で CORS を許可する設定が必要です。

**Q: 将来的に OAuth 認証が必要な API を追加したい**  
A: `fetchData()` をオーバーライドして `Authorization` ヘッダーを付与してください。  
トークンの取得・管理はバックエンドサービスに委ねることを強く推奨します。
