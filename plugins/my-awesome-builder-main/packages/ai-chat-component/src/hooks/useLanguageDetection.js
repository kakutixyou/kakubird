/**
 * useLanguageDetection.js
 * =======================
 * React hook that detects the programming language / styling framework
 * from a given text string and returns a result that updates reactively.
 */

import { useState, useCallback } from 'react';
import { detectLanguage, LANGUAGES } from '../utils/languageDetector.js';

/**
 * useLanguageDetection — detect language from a text string.
 *
 * @returns {{
 *   language: string,
 *   confidence: number,
 *   scores: Record<string,number>,
 *   detect: (text: string) => void,
 *   reset: () => void,
 * }}
 */
export function useLanguageDetection() {
  const [result, setResult] = useState({
    language: LANGUAGES.UNKNOWN,
    confidence: 0,
    scores: {},
  });

  const detect = useCallback((text) => {
    const detected = detectLanguage(text ?? '');
    setResult(detected);
    return detected;
  }, []);

  const reset = useCallback(() => {
    setResult({ language: LANGUAGES.UNKNOWN, confidence: 0, scores: {} });
  }, []);

  return {
    language: result.language,
    confidence: result.confidence,
    scores: result.scores,
    detect,
    reset,
  };
}

export default useLanguageDetection;
