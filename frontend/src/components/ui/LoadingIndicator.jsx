import React from 'react';

/**
 * ローディング中のアニメーションUI
 */
export function LoadingIndicator() {
  return (
    <div className="flex items-center space-x-2 text-slate-400 text-xs py-2">
      <span className="animate-bounce">●</span>
      <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>●</span>
      <span className="animate-bounce" style={{ animationDelay: '0.4s' }}>●</span>
      <span>AIが思考中...</span>
    </div>
  );
}