/**
 * apiKeyManager.js
 * ================
 * Reads API keys from the environment and provides them to API calls.
 * Supports both Vite (VITE_) and Create-React-App (REACT_APP_) conventions.
 *
 * NOTE: API keys are never hard-coded here. They must be set as environment
 * variables before the app is built / started.
 */

const readEnv = (key) => {
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return import.meta.env[key] ?? null;
  }
  if (typeof process !== 'undefined' && process.env) {
    return process.env[key] ?? null;
  }
  return null;
};

/**
 * Known API key environment variable names.
 */
const API_KEY_ENV_NAMES = {
  /** Gemini / Google AI */
  GEMINI: ['VITE_GEMINI_API_KEY', 'REACT_APP_GEMINI_API_KEY', 'GEMINI_API_KEY'],
  /** OpenAI */
  OPENAI: ['VITE_OPENAI_API_KEY', 'REACT_APP_OPENAI_API_KEY', 'OPENAI_API_KEY'],
  /** Anthropic / Claude */
  ANTHROPIC: ['VITE_ANTHROPIC_API_KEY', 'REACT_APP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'],
  /** Custom SQL API */
  SQL_API: ['VITE_SQL_API_KEY', 'REACT_APP_SQL_API_KEY', 'SQL_API_KEY'],
  /** Custom CSS API */
  CSS_API: ['VITE_CSS_API_KEY', 'REACT_APP_CSS_API_KEY', 'CSS_API_KEY'],
};

/**
 * Read a specific API key by provider name.
 *
 * @param {'GEMINI'|'OPENAI'|'ANTHROPIC'|'SQL_API'|'CSS_API'} provider
 * @returns {string|null}
 */
export function getAPIKey(provider) {
  const names = API_KEY_ENV_NAMES[provider];
  if (!names) return null;

  for (const name of names) {
    const value = readEnv(name);
    if (value) return value;
  }
  return null;
}

/**
 * Build an Authorization header value when a key is available.
 *
 * @param {'GEMINI'|'OPENAI'|'ANTHROPIC'|'SQL_API'|'CSS_API'} provider
 * @returns {{ Authorization: string }|{}}
 */
export function getAuthHeader(provider) {
  const key = getAPIKey(provider);
  if (!key) return {};
  return { Authorization: `Bearer ${key}` };
}

/**
 * Check if a key is available for a given provider.
 *
 * @param {'GEMINI'|'OPENAI'|'ANTHROPIC'|'SQL_API'|'CSS_API'} provider
 * @returns {boolean}
 */
export function hasAPIKey(provider) {
  return getAPIKey(provider) !== null;
}

export default { getAPIKey, getAuthHeader, hasAPIKey };
