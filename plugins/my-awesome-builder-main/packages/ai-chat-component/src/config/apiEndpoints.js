/**
 * apiEndpoints.js
 * ===============
 * Configurable API endpoint definitions for the AI Chat Component.
 * Override via environment variables (VITE_ prefix for Vite projects,
 * REACT_APP_ prefix for Create-React-App projects).
 */

const env = (key, fallback) => {
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return import.meta.env[key] ?? fallback;
  }
  if (typeof process !== 'undefined' && process.env) {
    return process.env[key] ?? fallback;
  }
  return fallback;
};

/**
 * Default API endpoint configuration.
 * All values can be overridden via environment variables.
 */
export const API_ENDPOINTS = {
  /**
   * SQL-related chat endpoint.
   * Handles questions about databases, queries, schemas, etc.
   */
  SQL_CHAT: env('VITE_SQL_CHAT_ENDPOINT', env('REACT_APP_SQL_CHAT_ENDPOINT', 'http://127.0.0.1:8765/api/chat')),

  /**
   * CSS/styling chat endpoint.
   * Handles questions about CSS, Tailwind, SCSS, UI styling, etc.
   */
  CSS_CHAT: env('VITE_CSS_CHAT_ENDPOINT', env('REACT_APP_CSS_CHAT_ENDPOINT', 'http://127.0.0.1:8766/api/chat')),

  /**
   * Design engine endpoint (from packages/ai-engine/design_engine.py).
   * Used for theme/block suggestions.
   */
  DESIGN_API: env('VITE_DESIGN_API_ENDPOINT', env('REACT_APP_DESIGN_API_ENDPOINT', 'http://127.0.0.1:5000/api/design')),

  /**
   * Generic fallback chat endpoint used when routing is ambiguous.
   */
  DEFAULT_CHAT: env('VITE_CHAT_ENDPOINT', env('REACT_APP_CHAT_ENDPOINT', 'http://127.0.0.1:8765/api/chat')),
};

/**
 * Create a custom endpoint config by merging overrides with defaults.
 *
 * @param {Partial<typeof API_ENDPOINTS>} overrides
 * @returns {typeof API_ENDPOINTS}
 */
export function createEndpointConfig(overrides = {}) {
  return { ...API_ENDPOINTS, ...overrides };
}

export default API_ENDPOINTS;
