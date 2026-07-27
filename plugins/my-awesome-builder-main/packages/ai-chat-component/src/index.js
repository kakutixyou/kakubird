/**
 * src/index.js
 * ============
 * Public API for @my-awesome-builder/ai-chat-component.
 *
 * Usage:
 *   import { AIChatPanel, useChatHistory, useAPIRouter } from '@my-awesome-builder/ai-chat-component';
 *   import '@my-awesome-builder/ai-chat-component/styles';
 */

// Components
export { default as AIChatPanel } from './components/AIChatPanel.jsx';
export { default as ChatMessage } from './components/ChatMessage.jsx';

// Hooks
export { useChatHistory } from './hooks/useChatHistory.js';
export { useAPIRouter } from './hooks/useAPIRouter.js';
export { useLanguageDetection } from './hooks/useLanguageDetection.js';

// Utilities
export { sendMessage, resolveRoute, ROUTE_INTENT } from './utils/apiRouter.js';
export { detectLanguage, isStylingLanguage, isSQLLanguage, LANGUAGES } from './utils/languageDetector.js';
export { getAPIKey, getAuthHeader, hasAPIKey } from './utils/apiKeyManager.js';

// Config
export { API_ENDPOINTS, createEndpointConfig } from './config/apiEndpoints.js';
