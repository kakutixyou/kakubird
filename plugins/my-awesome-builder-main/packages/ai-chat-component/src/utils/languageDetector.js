/**
 * languageDetector.js
 * ===================
 * Detects the programming language / styling framework context from user input.
 * Used to adapt the format and vocabulary of AI responses.
 */

/** Supported language/framework identifiers */
export const LANGUAGES = {
  TAILWIND: 'tailwind',
  CSS: 'css',
  SCSS: 'scss',
  POSTCSS: 'postcss',
  STYLED_COMPONENTS: 'styled-components',
  CSS_MODULES: 'css-modules',
  SQL: 'sql',
  REACT: 'react',
  UNKNOWN: 'unknown',
};

/**
 * Keyword map: language id → array of trigger keywords (lower-case).
 */
const LANGUAGE_KEYWORDS = {
  [LANGUAGES.TAILWIND]: [
    'tailwind', 'tw-', 'utility class', 'utility-class', 'jit', 'purge',
    'tailwindcss', 'bg-', 'text-', 'flex ', 'grid ', 'p-', 'm-', 'rounded',
    'shadow', 'hover:', 'focus:', 'dark:', 'responsive',
  ],
  [LANGUAGES.SCSS]: [
    'scss', 'sass', '$variable', '@mixin', '@include', '@extend', '@use',
    '@forward', 'nesting', 'ampersand',
  ],
  [LANGUAGES.POSTCSS]: [
    'postcss', 'autoprefixer', '@apply', 'css variable', 'custom property',
    'var(--', ':root',
  ],
  [LANGUAGES.STYLED_COMPONENTS]: [
    'styled-components', 'styled.', 'css`', 'createGlobalStyle',
    'ThemeProvider', 'keyframes`',
  ],
  [LANGUAGES.CSS_MODULES]: [
    'css module', 'css modules', '.module.css', 'composes',
  ],
  [LANGUAGES.SQL]: [
    'sql', 'select ', 'insert ', 'update ', 'delete ', 'create table',
    'drop table', 'join ', 'where ', 'group by', 'order by', 'having ',
    'sqlite', 'postgresql', 'mysql', 'database', 'schema', 'query', 'クエリ',
    'データベース', 'テーブル',
  ],
  [LANGUAGES.REACT]: [
    'react', 'jsx', 'tsx', 'usestate', 'useeffect', 'component', 'props',
    'hook', 'context', 'redux', 'zustand',
  ],
  [LANGUAGES.CSS]: [
    'css', 'stylesheet', 'selector', 'property', 'cascade', 'specificity',
    'media query', 'animation', 'transition', 'flexbox', 'grid',
    'スタイル', 'スタイリング',
  ],
};

/**
 * Score a text against each language's keyword list.
 *
 * @param {string} text - User input text
 * @returns {{ language: string, confidence: number, scores: Record<string,number> }}
 */
export function detectLanguage(text) {
  const lower = text.toLowerCase();
  const scores = {};

  for (const [lang, keywords] of Object.entries(LANGUAGE_KEYWORDS)) {
    scores[lang] = keywords.reduce((sum, kw) => {
      // Count occurrences for higher confidence on repeated mentions
      const regex = new RegExp(kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      const matches = lower.match(regex);
      return sum + (matches ? matches.length : 0);
    }, 0);
  }

  const maxScore = Math.max(...Object.values(scores));
  if (maxScore === 0) {
    return { language: LANGUAGES.UNKNOWN, confidence: 0, scores };
  }

  const language = Object.keys(scores).find(k => scores[k] === maxScore);
  // Normalize confidence to [0, 1] based on max possible hits
  const confidence = Math.min(maxScore / 5, 1);

  return { language, confidence, scores };
}

/**
 * Determine if the detected language is CSS/styling-related.
 *
 * @param {string} language - Result from detectLanguage().language
 * @returns {boolean}
 */
export function isStylingLanguage(language) {
  return [
    LANGUAGES.TAILWIND,
    LANGUAGES.CSS,
    LANGUAGES.SCSS,
    LANGUAGES.POSTCSS,
    LANGUAGES.STYLED_COMPONENTS,
    LANGUAGES.CSS_MODULES,
  ].includes(language);
}

/**
 * Determine if the detected language is SQL-related.
 *
 * @param {string} language - Result from detectLanguage().language
 * @returns {boolean}
 */
export function isSQLLanguage(language) {
  return language === LANGUAGES.SQL;
}

export default detectLanguage;
