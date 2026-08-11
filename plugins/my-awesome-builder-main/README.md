# my-awesome-builder

A monorepo providing an AI-powered chat component, design engine, and block library for modern web applications.

---

## Packages

| Package | Description |
|---|---|
| `packages/ai-chat-component` | React chat UI with automatic SQL/CSS API routing |
| `packages/ai-engine` | Flask backend — design rules engine + chat API |
| `packages/block-library` | Design manifest and block definitions |
| `packages/render-engine` | Page rendering utilities |
| `packages/style-system` | CSS/design rules |

---

## Quick Start

### 1. Backend (ai-engine)

```bash
cd packages/ai-engine
cp .env.example .env          # fill in API keys
pip install -r requirements.txt
python design_api.py           # starts on http://127.0.0.1:8765
```

### 2. Frontend

```bash
npm install                   # install workspace dependencies
npm run dev                   # start Vite dev server
```

---

## Processing Flow

```
[ フロント ]
AiChatPanel（React）
   ↓ 🔵 console.log("1️⃣ [フロント] ユーザーメッセージ送信...")
   ↓      Message / Detected Language / Timestamp

[ バックエンド ]
design_api.py（Flask）  POST /api/chat
   ↓ 🟢 print("2️⃣ [バックエンド] POSTを受信")
   ↓      受信データ / API Key validation

[ 処理 ]
Language Detection → API Routing
   ↓ 🟡 print("3️⃣ [処理] 言語検出とルーティング")
   ↓      検出言語 / confidence / ルート先

[ レスポンス ]
JSON → フロント
   ↓ 🟢 print("4️⃣ [バックエンド] レスポンス生成")
   ↓ 🔵 console.log("5️⃣ [フロント] レスポンス受信")
```

### Browser Console Output Example

```
🔵 [フロント - 1️⃣] ユーザーが質問を送信
   📝 Message          : "Tailwindでボタンスタイルを作りたい"
   🌍 Detected Language: tailwind
   📊 Confidence       : 95%
   🛣️  Route Intent     : css
   ⏱️  Timestamp        : 2026-05-04T10:30:45.123Z
   📜 History turns    : 0

🟡 [処理 - 3️⃣] 言語検出＆ルーティング
   🔍 Language Detection: tailwind  (confidence: 95%)
   🛣️  Routing to        : css API
   📡 Endpoint          : http://127.0.0.1:8765/api/chat
   📐 Processing Mode   : auto

🟢 [バックエンド - 4️⃣] レスポンス生成
   📤 Type             : css
   🌍 Language         : tailwind
   💬 Reply generated  : "CSS/スタイリング APIで処理します..."
   ⏱️  Request time     : 245ms
   ⏱️  Server proc. time: 231ms

🔵 [フロント - 5️⃣] レスポンス受信
   ✅ Status           : 200 OK
   📦 Response Type    : css
   🌍 Language         : tailwind
   💬 Reply            : "CSS/スタイリング APIで処理します..."
   ⏱️  Total time       : 312ms
   ✅ メッセージ追加完了
```

### Python Server Log Example

```
🟢 [バックエンド - 2️⃣] POSTリクエスト受信
   🆔 Request ID : a1b2c3d4
   📥 Path       : /api/chat
   ⏱️  Timestamp  : 2026-05-04T10:30:45.245Z
   📊 Message    : 'Tailwindでボタンスタイルを作りたい'
   📊 Mode       : auto
   📊 History    : 0 turns

🟡 [処理 - 3️⃣] 言語検出＆ルーティング
   🆔 Request ID    : a1b2c3d4
   🔍 Detected Lang : tailwind  (confidence: 95%)
   🛣️  Routing to   : css API
   📐 Mode          : auto
   📊 Scores        : {'tailwind': 5}

🟢 [バックエンド - 4️⃣] レスポンス生成
   🆔 Request ID      : a1b2c3d4
   📤 Type            : css
   🌍 Language        : tailwind
   💬 Reply generated : 'CSS/スタイリング APIで処理します...'
   ⏱️  Processing time : 231ms
```

---

## Environment Variables

### Backend (`packages/ai-engine/.env`)

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8765` | Flask server port |
| `FLASK_DEBUG` | `false` | Enable debug mode |
| `GEMINI_API_KEY` | *(empty)* | Google AI API key |
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic/Claude key |
| `SQL_API_KEY` | *(empty)* | Custom SQL API key |
| `CSS_API_KEY` | *(empty)* | Custom CSS API key |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |

### Frontend (`packages/ai-chat-component`)

| Variable | Default | Description |
|---|---|---|
| `VITE_SQL_CHAT_ENDPOINT` | `http://127.0.0.1:8765/api/chat` | SQL API URL |
| `VITE_CSS_CHAT_ENDPOINT` | `http://127.0.0.1:8766/api/chat` | CSS API URL |
| `VITE_CHAT_ENDPOINT` | `http://127.0.0.1:8765/api/chat` | Default chat API |

---

## API Reference

### `POST /api/chat`

Send a chat message. The server auto-detects the language and routes it.

**Request**
```json
{
  "message": "Tailwindでボタンスタイルを作りたい",
  "history": [],
  "mode": "auto",
  "db_path": "",
  "api_key": "optional-key"
}
```

**Response**
```json
{
  "reply": "CSS/スタイリング APIで処理します...",
  "source": "css",
  "language": "tailwind",
  "confidence": 0.95,
  "request_id": "a1b2c3d4",
  "processing_ms": 231
}
```

### `POST /api/detect-language`

Detect the language/framework from a text snippet.

**Request**
```json
{ "text": "SELECT * FROM users WHERE id = 1" }
```

**Response**
```json
{
  "language": "sql",
  "confidence": 1.0,
  "api_type": "sql",
  "scores": { "sql": 8 }
}
```

### `GET /api/health`

```json
{
  "status": "healthy",
  "timestamp": "2026-05-04T10:30:00.000Z",
  "endpoints": ["/api/chat", "/api/detect-language", "/api/health"]
}
```
