/**
 * useAPIRouter.js
 * ===============
 * React hook that wraps the apiRouter utility, providing loading state
 * and error handling for use inside React components.
 */

import { useState, useCallback } from 'react';
import { sendMessage, resolveRoute } from '../utils/apiRouter.js';

/**
 * useAPIRouter — send messages via the automatic API router.
 *
 * @param {object} [options]
 * @param {string} [options.dbPath=''] - Database path forwarded to the SQL API.
 * @param {object} [options.endpointOverrides={}] - Override specific route endpoints.
 *
 * @returns {{
 *   isLoading: boolean,
 *   lastIntent: string|null,
 *   lastLanguage: string|null,
 *   send: (message: string, history: Array) => Promise<{reply:string,source:string,intent:string,language:string}>,
 *   previewRoute: (message: string) => {intent:string,endpoint:string,language:string,confidence:number},
 * }}
 */
export function useAPIRouter({ dbPath = '', endpointOverrides = {} } = {}) {
  const [isLoading, setIsLoading] = useState(false);
  const [lastIntent, setLastIntent] = useState(null);
  const [lastLanguage, setLastLanguage] = useState(null);

  const send = useCallback(
    async (message, history = []) => {
      setIsLoading(true);
      try {
        const result = await sendMessage({
          message,
          history,
          dbPath,
          endpointOverrides,
        });
        setLastIntent(result.intent);
        setLastLanguage(result.language);
        return result;
      } finally {
        setIsLoading(false);
      }
    },
    [dbPath, endpointOverrides],
  );

  const previewRoute = useCallback(
    (message) => resolveRoute(message),
    [],
  );

  return { isLoading, lastIntent, lastLanguage, send, previewRoute };
}

export default useAPIRouter;
