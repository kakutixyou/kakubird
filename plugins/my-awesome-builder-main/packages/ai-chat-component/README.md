# @my-awesome-builder/ai-chat-component

An independent, reusable AI Chat Component that automatically routes user messages to the appropriate API (SQL or CSS) and adapts its response format based on the detected programming language.

## Features

- **Automatic API Routing** — Detects from user input whether to call the SQL API or the CSS API
- **Language Detection** — Identifies the user's preferred styling framework (Tailwind, CSS, SCSS, PostCSS, styled-components, CSS Modules) and passes that context to the AI
- **API Key Management** — Reads keys from environment variables (`VITE_*` / `REACT_APP_*`) without hard-coding any secrets
- **Configurable Endpoints** — All API URLs are overridable via environment variables or runtime props
- **Chat History** — Maintains multi-turn conversation context
- **Modular Design** — Can be dropped into any React project

---

## Installation

This package lives inside the monorepo at `packages/ai-chat-component`.  
In another workspace package (e.g. `jimdo_Studio_replica_2`) add it as a dependency:

```json
{
  "dependencies": {
    "@my-awesome-builder/ai-chat-component": "workspace:*"
  }
}
```

---

## Quick Start

```jsx
// 1. Import the component and its styles
import { AIChatPanel } from '@my-awesome-builder/ai-chat-component';
import '@my-awesome-builder/ai-chat-component/styles';

// 2. Render anywhere in your React app
export default function App() {
  return (
    <AIChatPanel
      dbPath="/data/myapp.db"   // passed to SQL API requests
      showRoutingBadge          // shows "SQL API" / "CSS API" as you type
    />
  );
}
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_SQL_CHAT_ENDPOINT` | `http://127.0.0.1:8765/api/chat` | SQL chat API URL |
| `VITE_CSS_CHAT_ENDPOINT` | `http://127.0.0.1:8766/api/chat` | CSS chat API URL |
| `VITE_CHAT_ENDPOINT` | `http://127.0.0.1:8765/api/chat` | Fallback API URL |
| `VITE_DESIGN_API_ENDPOINT` | `http://127.0.0.1:5000/api/design` | Design engine API URL |
| `VITE_SQL_API_KEY` | *(none)* | Bearer token for the SQL API |
| `VITE_CSS_API_KEY` | *(none)* | Bearer token for the CSS API |
| `VITE_GEMINI_API_KEY` | *(none)* | Gemini API key |
| `VITE_OPENAI_API_KEY` | *(none)* | OpenAI API key |
| `VITE_ANTHROPIC_API_KEY` | *(none)* | Anthropic API key |

> **Note**: All `VITE_*` variables work in Vite projects. For Create-React-App use `REACT_APP_*` equivalents.

---

## AIChatPanel Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `dbPath` | `string` | `''` | SQLite database path forwarded to SQL API requests |
| `greeting` | `string` | Japanese greeting | Override the initial AI greeting message |
| `endpointOverrides` | `object` | `{}` | Override endpoints at runtime: `{ sql: '...', css: '...' }` |
| `className` | `string` | `''` | Extra CSS class on the outer wrapper |
| `placeholder` | `string` | Japanese hint | Textarea placeholder text |
| `showRoutingBadge` | `boolean` | `true` | Show a preview badge indicating which API will receive the message |

---

## Package Structure

```
packages/ai-chat-component/
├── src/
│   ├── components/
│   │   ├── AIChatPanel.jsx        ← Main component
│   │   ├── ChatMessage.jsx        ← Single message bubble
│   │   └── index.js
│   ├── hooks/
│   │   ├── useChatHistory.js      ← Conversation state management
│   │   ├── useAPIRouter.js        ← React hook for API routing
│   │   └── useLanguageDetection.js ← Detect programming language
│   ├── utils/
│   │   ├── apiRouter.js           ← Route messages to SQL/CSS API
│   │   ├── languageDetector.js    ← Identify language preference
│   │   └── apiKeyManager.js       ← Read API keys from environment
│   ├── config/
│   │   └── apiEndpoints.js        ← Configurable endpoint definitions
│   ├── styles/
│   │   └── chat-panel.css         ← BEM-namespaced styles
│   └── index.js                   ← Public exports
├── package.json
└── README.md
```

---

## API Routing Logic

The component uses keyword scoring to determine the routing intent:

| User input contains… | Routed to |
|---|---|
| `SELECT`, `SQL`, `クエリ`, `データベース`… | SQL API (`VITE_SQL_CHAT_ENDPOINT`) |
| `CSS`, `Tailwind`, `SCSS`, `bg-`, `flex`… | CSS API (`VITE_CSS_CHAT_ENDPOINT`) |
| Ambiguous | Default API (`VITE_CHAT_ENDPOINT`) |

A small routing preview badge is shown as the user types (controlled by the `showRoutingBadge` prop).

---

## Detected Languages

| Language ID | Triggers |
|---|---|
| `tailwind` | `tailwind`, `bg-`, `text-`, `hover:`, utility classes… |
| `css` | `css`, `stylesheet`, `selector`, `media query`… |
| `scss` | `scss`, `sass`, `$variable`, `@mixin`… |
| `postcss` | `postcss`, `@apply`, `var(--`, `:root`… |
| `styled-components` | `styled.`, `css\``, `ThemeProvider`… |
| `css-modules` | `.module.css`, `composes`… |
| `sql` | `SELECT`, `JOIN`, `sqlite`, `データベース`… |
| `react` | `react`, `jsx`, `hook`, `useState`… |

---

## Using Individual Utilities

```js
import {
  detectLanguage,
  resolveRoute,
  sendMessage,
  LANGUAGES,
  ROUTE_INTENT,
} from '@my-awesome-builder/ai-chat-component';

// Detect language
const { language, confidence } = detectLanguage('How do I center a div with Tailwind?');
// → { language: 'tailwind', confidence: 0.4, scores: {...} }

// Preview routing
const { intent, endpoint } = resolveRoute('SELECT * FROM users WHERE id = 1');
// → { intent: 'sql', endpoint: 'http://...', language: 'sql', confidence: 0.8 }

// Send a message directly
const result = await sendMessage({
  message: 'Write a Tailwind button',
  history: [],
  dbPath: '',
});
// → { reply: '...', source: 'css', intent: 'css', language: 'tailwind' }
```

---

## Styling / Theming

The component uses CSS custom properties (tokens) defined under `.ai-chat` namespace.
Override them in your project's CSS:

```css
:root {
  --ai-chat-header-bg: #7c3aed;       /* purple header */
  --ai-chat-user-bubble-bg: #7c3aed;  /* purple user bubbles */
  --ai-chat-radius: 16px;
}
```

---

## Compatibility

- React 18+
- Vite or Create-React-App (or any bundler that supports ES modules)
- Node 18+
