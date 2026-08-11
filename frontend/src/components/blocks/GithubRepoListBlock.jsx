// frontend/src/components/blocks/GithubRepoListBlock.jsx

import React from 'react';

export default function GithubRepoListBlock({ block }) {
  // 安全に props を取り出す
  const repos = block?.props?.repos || [];

  // リポジトリが空の場合
  if (!repos.length) {
    return (
      <div className="text-sm text-slate-500 dark:text-slate-400">
        リポジトリが見つかりませんでした。
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {repos.map((repo, index) => {
        const repoUrl =
          repo.url ||
          repo.html_url ||
          `https://github.com/${repo.name || ''}`;

        return (
          <a
            key={repo.id || index}
            href={repoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="
              block
              rounded-xl
              border
              border-slate-200
              dark:border-slate-700
              bg-white
              dark:bg-slate-900/40
              p-5
              shadow-sm
              transition-all
              duration-200
              hover:border-indigo-400
              hover:shadow-lg
              hover:-translate-y-0.5
              group
            "
          >
            {/* =========================================
                タイトル
            ========================================= */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <h3
                  className="
                    text-base
                    font-extrabold
                    text-indigo-600
                    dark:text-indigo-400
                    truncate
                    group-hover:underline
                  "
                >
                  {repo.name || 'Unknown Repository'}
                </h3>

                {/* owner */}
                {repo.owner && (
                  <p className="text-xs text-slate-400 mt-1">
                    {/* 👇 オブジェクトの場合は login を、文字列の場合はそのまま表示するように安全対策 */}
                    by {repo.owner.login || repo.owner}
                  </p>
                )}
              </div>

              {/* stars */}
              <div
                className="
                  flex
                  items-center
                  gap-1
                  text-xs
                  font-mono
                  text-slate-500
                  shrink-0
                "
              >
                <span>⭐</span>
                <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">
                  {repo.stars ?? 0}
                </span>
              </div>
            </div>

            {/* =========================================
                説明文
            ========================================= */}
            <div className="mt-3">
              <p
                className="
                  text-sm
                  text-slate-600
                  dark:text-slate-400
                  leading-relaxed
                  line-clamp-3
                "
              >
                {repo.description || 'No description provided.'}
              </p>
            </div>

            {/* =========================================
                下部情報
            ========================================= */}
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {/* language */}
              {repo.language && (
                <span
                  className="
                    px-2.5
                    py-1
                    rounded-full
                    text-xs
                    font-medium
                    bg-slate-100
                    dark:bg-slate-800
                    text-slate-700
                    dark:text-slate-200
                  "
                >
                  {repo.language}
                </span>
              )}

              {/* forks */}
              {repo.forks !== undefined && (
                <span
                  className="
                    text-xs
                    text-slate-500
                    dark:text-slate-400
                  "
                >
                  🍴 Forks: {repo.forks}
                </span>
              )}

              {/* updated_at */}
              {repo.updated_at && (
                <span
                  className="
                    text-xs
                    text-slate-400
                    dark:text-slate-500
                  "
                >
                  Updated: {repo.updated_at}
                </span>
              )}
            </div>
          </a>
        );
      })}
    </div>
  );
}