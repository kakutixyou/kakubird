// frontend/src/components/MemoryManager.jsx

import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

const API_BASE = "http://localhost:8765/api/memory";

// ============================================================
// 共通
// ============================================================

const safeArray = (value) => {
  return Array.isArray(value) ? value : [];
};

const safeObject = (value) => {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
};

const formatDate = (value) => {
  if (!value) return "日時不明";

  try {
    return String(value).replace("T", " ").slice(0, 19);
  } catch {
    return String(value);
  }
};

const truncate = (text, max = 180) => {
  if (!text) return "";

  const value = String(text);

  if (value.length <= max) {
    return value;
  }

  return `${value.slice(0, max)}…`;
};

// ============================================================
// Toast
// ============================================================

function useToast() {
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, type = "success") => {
    setToast({
      message,
      type,
    });

    window.setTimeout(() => {
      setToast(null);
    }, 3200);
  }, []);

  return {
    toast,
    showToast,
  };
}

// ============================================================
// 小コンポーネント
// ============================================================

function EmptyState({
  icon = "📭",
  title = "記憶なし",
  description = "まだ保存されている情報はありません。",
}) {
  return (
    <div
      style={{
        padding: "36px 20px",
        textAlign: "center",
        color: "#64748b",
      }}
    >
      <div
        style={{
          fontSize: 36,
          marginBottom: 10,
        }}
      >
        {icon}
      </div>

      <div
        style={{
          color: "#cbd5e1",
          fontWeight: 700,
          marginBottom: 5,
        }}
      >
        {title}
      </div>

      <div
        style={{
          fontSize: 13,
        }}
      >
        {description}
      </div>
    </div>
  );
}

function Section({
  title,
  icon,
  count,
  children,
  description,
  action,
}) {
  return (
    <section
      style={{
        background: "#111827",
        border: "1px solid #1f2937",
        borderRadius: 16,
        overflow: "hidden",
        boxShadow: "0 8px 30px rgba(0,0,0,0.18)",
      }}
    >
      <div
        style={{
          padding: "16px 18px",
          borderBottom: "1px solid #1f2937",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 12,
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <span>{icon}</span>

            <h2
              style={{
                margin: 0,
                fontSize: 16,
                color: "#f8fafc",
              }}
            >
              {title}
            </h2>

            {typeof count === "number" && (
              <span
                style={{
                  background: "#1e293b",
                  color: "#94a3b8",
                  padding: "2px 8px",
                  borderRadius: 999,
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                {count}
              </span>
            )}
          </div>

          {description && (
            <div
              style={{
                marginTop: 5,
                color: "#64748b",
                fontSize: 12,
              }}
            >
              {description}
            </div>
          )}
        </div>

        {action}
      </div>

      <div
        style={{
          padding: 14,
        }}
      >
        {children}
      </div>
    </section>
  );
}

function MemoryCard({
  icon = "🧠",
  title,
  text,
  date,
  tags = [],
  accent = "#6366f1",
  extra,
}) {
  return (
    <article
      style={{
        border: "1px solid #1f2937",
        borderLeft: `3px solid ${accent}`,
        background: "#0f172a",
        borderRadius: 10,
        padding: 13,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 9,
        }}
      >
        <span
          style={{
            fontSize: 18,
          }}
        >
          {icon}
        </span>

        <div
          style={{
            minWidth: 0,
            flex: 1,
          }}
        >
          {title && (
            <div
              style={{
                color: "#e2e8f0",
                fontWeight: 700,
                fontSize: 13,
                marginBottom: 5,
                wordBreak: "break-word",
              }}
            >
              {title}
            </div>
          )}

          {text && (
            <div
              style={{
                color: "#94a3b8",
                fontSize: 12,
                lineHeight: 1.65,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {text}
            </div>
          )}

          {extra}

          {tags.length > 0 && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 5,
                marginTop: 8,
              }}
            >
              {tags.map((tag, index) => (
                <span
                  key={`${tag}-${index}`}
                  style={{
                    color: "#93c5fd",
                    background: "#172554",
                    borderRadius: 999,
                    fontSize: 10,
                    padding: "2px 7px",
                  }}
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}

          {date && (
            <div
              style={{
                marginTop: 8,
                fontSize: 10,
                color: "#475569",
                textAlign: "right",
              }}
            >
              {formatDate(date)}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

function StatCard({
  icon,
  label,
  value,
}) {
  return (
    <div
      style={{
        border: "1px solid #1f2937",
        background: "#111827",
        borderRadius: 12,
        padding: "13px 15px",
      }}
    >
      <div
        style={{
          color: "#64748b",
          fontSize: 11,
        }}
      >
        {icon} {label}
      </div>

      <div
        style={{
          color: "#f8fafc",
          fontSize: 23,
          fontWeight: 800,
          marginTop: 4,
        }}
      >
        {value ?? 0}
      </div>
    </div>
  );
}

// ============================================================
// MemoryManager
// ============================================================

export default function MemoryManager() {
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState("");

  const [memory, setMemory] = useState({
    session: {},
    recent_memories: [],
    preferences: [],
    tasks: [],
    schedules: [],
    conversations: [],
    challenges: [],
    long_term_memories: [],
    recent_files: [],
    projects: [],
    statistics: {},
  });

  const { toast, showToast } = useToast();

  // ==========================================================
  // API
  // ==========================================================

  const loadMemory = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/overview`, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(
          `Memory API Error: ${response.status}`,
        );
      }

      const data = await response.json();

      setMemory({
        session: safeObject(data.session),

        recent_memories: safeArray(
          data.recent_memories,
        ),

        preferences: safeArray(
          data.preferences,
        ),

        tasks: safeArray(
          data.tasks,
        ),

        schedules: safeArray(
          data.schedules,
        ),

        conversations: safeArray(
          data.conversations || data.messages,
        ),

        challenges: safeArray(
          data.challenges,
        ),

        long_term_memories: safeArray(
          data.long_term_memories,
        ),

        recent_files: safeArray(
          data.recent_files,
        ),

        projects: safeArray(
          data.projects,
        ),

        statistics: safeObject(
          data.statistics,
        ),
      });
    } catch (err) {
      console.error(err);

      setError(
        "記憶データを取得できませんでした。バックエンドの /api/memory/overview を確認してください。",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // ==========================================================
  // 全削除
  // ==========================================================

  const handleClearAllMemory = useCallback(async () => {
    const firstConfirm = window.confirm(
      "AIが保存している記憶をすべて削除します。\n\n会話履歴・タスク・長期記憶・プロジェクト記憶などが削除対象です。\n\n本当に続行しますか？",
    );

    if (!firstConfirm) {
      return;
    }

    const secondConfirm = window.confirm(
      "この操作は元に戻せません。\n本当に全記憶を削除しますか？",
    );

    if (!secondConfirm) {
      return;
    }

    setClearing(true);

    try {
      const response = await fetch(
        `${API_BASE}/all`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error(
          `Clear memory failed: ${response.status}`,
        );
      }

      showToast(
        "AIの記憶をすべて削除しました。",
      );

      await loadMemory();
    } catch (err) {
      console.error(err);

      showToast(
        "記憶の全削除に失敗しました。",
        "error",
      );
    } finally {
      setClearing(false);
    }
  }, [loadMemory, showToast]);

  // ==========================================================
  // 個別タスク状態変更
  // ==========================================================

  const handleTaskStatus = useCallback(
    async (taskId, status) => {
      try {
        const response = await fetch(
          `${API_BASE}/tasks/${taskId}`,
          {
            method: "PATCH",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              status,
            }),
          },
        );

        if (!response.ok) {
          throw new Error(
            `Task update failed: ${response.status}`,
          );
        }

        setMemory((prev) => ({
          ...prev,

          tasks: prev.tasks.map(
            (task) =>
              task.id === taskId
                ? {
                    ...task,
                    status,
                  }
                : task,
          ),
        }));

        showToast(
          "タスク状態を更新しました。",
        );
      } catch (err) {
        console.error(err);

        showToast(
          "タスクの更新に失敗しました。",
          "error",
        );
      }
    },
    [showToast],
  );

  // ==========================================================
  // データ整理
  // ==========================================================

  const pendingTasks = useMemo(
    () =>
      memory.tasks.filter(
        (task) =>
          task.status !== "completed" &&
          task.status !== "done",
      ),
    [memory.tasks],
  );

  const recentConversations = useMemo(
    () =>
      [...memory.conversations]
        .reverse()
        .slice(0, 12),
    [memory.conversations],
  );

  const recentMemories = useMemo(() => {
    if (
      memory.recent_memories.length > 0
    ) {
      return memory.recent_memories.slice(
        0,
        10,
      );
    }

    return [...memory.long_term_memories]
      .reverse()
      .slice(0, 10);
  }, [
    memory.recent_memories,
    memory.long_term_memories,
  ]);

  // ==========================================================
  // ロード
  // ==========================================================

  useEffect(() => {
    loadMemory();
  }, [loadMemory]);

  // ==========================================================
  // Loading
  // ==========================================================

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100%",
          background: "#020617",
          color: "#94a3b8",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: 40,
        }}
      >
        <div
          style={{
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 38,
              marginBottom: 12,
            }}
          >
            🧠
          </div>

          <div>
            AI Memoryを読み込んでいます…
          </div>
        </div>
      </div>
    );
  }

  // ==========================================================
  // Render
  // ==========================================================

  return (
    <>
      <div
        style={{
          minHeight: "100%",
          background: "#020617",
          color: "#cbd5e1",
          padding: "28px 24px 60px",
          fontFamily:
            "'Inter', 'Helvetica Neue', Arial, sans-serif",
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
          }}
        >
          {/* ==================================================
              Header
          ================================================== */}

          <header
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 18,
              flexWrap: "wrap",
              marginBottom: 24,
            }}
          >
            <div>
              <h1
                style={{
                  color: "#f8fafc",
                  fontSize: 28,
                  margin: 0,
                  fontWeight: 850,
                }}
              >
                🧠 AI Memory Center
              </h1>

              <p
                style={{
                  margin:
                    "7px 0 0",
                  color: "#64748b",
                  fontSize: 13,
                }}
              >
                AIが現在保持している記憶・会話・タスク・予定・課題を確認できます。
              </p>

              {memory.session
                ?.project_name && (
                <div
                  style={{
                    marginTop: 8,
                    fontSize: 11,
                    color: "#475569",
                  }}
                >
                  Current Project:{" "}
                  <strong
                    style={{
                      color: "#94a3b8",
                    }}
                  >
                    {
                      memory.session
                        .project_name
                    }
                  </strong>
                </div>
              )}
            </div>

            <div
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                onClick={loadMemory}
                style={{
                  border:
                    "1px solid #334155",
                  background: "#0f172a",
                  color: "#cbd5e1",
                  borderRadius: 9,
                  padding:
                    "9px 14px",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                🔄 再読み込み
              </button>

              <button
                type="button"
                disabled={clearing}
                onClick={
                  handleClearAllMemory
                }
                style={{
                  border:
                    "1px solid #7f1d1d",
                  background:
                    clearing
                      ? "#291414"
                      : "#1f1013",
                  color: "#f87171",
                  borderRadius: 9,
                  padding:
                    "9px 14px",
                  cursor: clearing
                    ? "wait"
                    : "pointer",
                  fontWeight: 700,
                }}
              >
                {clearing
                  ? "削除中…"
                  : "🗑 全記憶を消去"}
              </button>
            </div>
          </header>

          {/* ==================================================
              Error
          ================================================== */}

          {error && (
            <div
              style={{
                border:
                  "1px solid #7f1d1d",
                background: "#1f1013",
                color: "#fca5a5",
                borderRadius: 10,
                padding:
                  "12px 14px",
                marginBottom: 20,
                fontSize: 12,
              }}
            >
              ⚠ {error}
            </div>
          )}

          {/* ==================================================
              Statistics
          ================================================== */}

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit,minmax(150px,1fr))",
              gap: 10,
              marginBottom: 22,
            }}
          >
            <StatCard
              icon="💬"
              label="会話"
              value={
                memory.statistics
                  .chat_messages ??
                memory.conversations
                  .length
              }
            />

            <StatCard
              icon="🧠"
              label="長期記憶"
              value={
                memory.statistics
                  .long_term_memories ??
                memory
                  .long_term_memories
                  .length
              }
            />

            <StatCard
              icon="✅"
              label="タスク"
              value={
                memory.statistics
                  .tasks ??
                memory.tasks.length
              }
            />

            <StatCard
              icon="📁"
              label="プロジェクト"
              value={
                memory.statistics
                  .projects ??
                memory.projects.length
              }
            />

            <StatCard
              icon="⚠"
              label="大きな課題"
              value={
                memory.challenges.length
              }
            />
          </div>

          {/* ==================================================
              Main grid
          ================================================== */}

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit,minmax(360px,1fr))",
              gap: 16,
            }}
          >
            {/* 最近の記憶 */}

            <Section
              icon="🕒"
              title="最近の記憶"
              count={
                recentMemories.length
              }
              description="最近AIが保持した重要な情報"
            >
              {recentMemories.length ===
              0 ? (
                <EmptyState
                  icon="🧠"
                  title="最近の記憶なし"
                />
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 8,
                  }}
                >
                  {recentMemories.map(
                    (item, index) => (
                      <MemoryCard
                        key={
                          item.id ??
                          index
                        }
                        icon="🧠"
                        title={
                          item.title ||
                          item.category ||
                          "記憶"
                        }
                        text={truncate(
                          item.text ||
                            item.content ||
                            item.value,
                        )}
                        tags={safeArray(
                          item.tags,
                        )}
                        date={
                          item.created_at ||
                          item.updated_at
                        }
                        accent="#8b5cf6"
                      />
                    ),
                  )}
                </div>
              )}
            </Section>

            {/* 好きなこと */}

            <Section
              icon="💜"
              title="好きなこと・興味"
              count={
                memory.preferences.length
              }
              description="AIが覚えている好みや興味"
            >
              {memory.preferences
                .length === 0 ? (
                <EmptyState
                  icon="💜"
                  title="好みの記憶なし"
                  description="preference / likes カテゴリの長期記憶をここに表示できます。"
                />
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 8,
                  }}
                >
                  {memory.preferences.map(
                    (item, index) => (
                      <MemoryCard
                        key={
                          item.id ??
                          index
                        }
                        icon="💜"
                        title={
                          item.title ||
                          item.category ||
                          "興味"
                        }
                        text={truncate(
                          item.text ||
                            item.content,
                        )}
                        tags={safeArray(
                          item.tags,
                        )}
                        date={
                          item.created_at
                        }
                        accent="#ec4899"
                      />
                    ),
                  )}
                </div>
              )}
            </Section>

            {/* タスク */}

            <Section
              icon="✅"
              title="現在のタスク"
              count={
                pendingTasks.length
              }
              description="未完了の作業・やること"
            >
              {pendingTasks.length ===
              0 ? (
                <EmptyState
                  icon="🎉"
                  title="未完了タスクなし"
                />
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 8,
                  }}
                >
                  {pendingTasks.map(
                    (task) => (
                      <MemoryCard
                        key={task.id}
                        icon="✅"
                        title={
                          task.task_name ||
                          task.title ||
                          "タスク"
                        }
                        text={truncate(
                          task.details ||
                            task.text,
                        )}
                        date={
                          task.updated_at ||
                          task.created_at
                        }
                        accent="#22c55e"
                        extra={
                          <div
                            style={{
                              marginTop: 9,
                              display:
                                "flex",
                              alignItems:
                                "center",
                              gap: 8,
                            }}
                          >
                            <span
                              style={{
                                fontSize: 10,
                                color:
                                  "#64748b",
                              }}
                            >
                              {
                                task.status
                              }
                            </span>

                            <button
                              type="button"
                              onClick={() =>
                                handleTaskStatus(
                                  task.id,
                                  "completed",
                                )
                              }
                              style={{
                                marginLeft:
                                  "auto",
                                background:
                                  "#052e16",
                                color:
                                  "#4ade80",
                                border:
                                  "1px solid #14532d",
                                borderRadius: 7,
                                cursor:
                                  "pointer",
                                padding:
                                  "4px 8px",
                                fontSize: 10,
                              }}
                            >
                              完了
                            </button>
                          </div>
                        }
                      />
                    ),
                  )}
                </div>
              )}
            </Section>

            {/* 予定 */}

            <Section
              icon="📅"
              title="予定"
              count={
                memory.schedules.length
              }
              description="予定・締切・イベント"
            >
              {memory.schedules.length ===
              0 ? (
                <EmptyState
                  icon="📅"
                  title="予定なし"
                  description="schedule / event カテゴリを追加するとここへ表示できます。"
                />
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 8,
                  }}
                >
                  {memory.schedules.map(
                    (schedule, index) => (
                      <MemoryCard
                        key={
                          schedule.id ??
                          index
                        }
                        icon="📅"
                        title={
                          schedule.title ||
                          schedule.name ||
                          "予定"
                        }
                        text={truncate(
                          schedule.details ||
                            schedule.text,
                        )}
                        date={
                          schedule.date ||
                          schedule
                            .scheduled_at ||
                          schedule
                            .created_at
                        }
                        accent="#06b6d4"
                      />
                    ),
                  )}
                </div>
              )}
            </Section>

            {/* 大きな課題 */}

            <Section
              icon="⚠️"
              title="大きな課題"
              count={
                memory.challenges.length
              }
              description="プロジェクト上の重要な問題や未解決事項"
            >
              {memory.challenges.length ===
              0 ? (
                <EmptyState
                  icon="✨"
                  title="重大な課題なし"
                  description="challenge / issue / problem カテゴリの記憶を表示できます。"
                />
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 8,
                  }}
                >
                  {memory.challenges.map(
                    (issue, index) => (
                      <MemoryCard
                        key={
                          issue.id ??
                          index
                        }
                        icon="⚠️"
                        title={
                          issue.title ||
                          issue.category ||
                          "課題"
                        }
                        text={truncate(
                          issue.text ||
                            issue.details,
                        )}
                        tags={safeArray(
                          issue.tags,
                        )}
                        date={
                          issue.updated_at ||
                          issue.created_at
                        }
                        accent="#f97316"
                      />
                    ),
                  )}
                </div>
              )}
            </Section>

            {/* 最近触ったファイル */}

            <Section
              icon="📂"
              title="最近のファイル"
              count={
                memory.recent_files.length
              }
              description="最近AIが参照・編集したファイル"
            >
              {memory.recent_files
                .length === 0 ? (
                <EmptyState
                  icon="📂"
                  title="ファイル記憶なし"
                />
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 6,
                  }}
                >
                  {memory.recent_files.map(
                    (file, index) => (
                      <div
                        key={`${file}-${index}`}
                        style={{
                          background:
                            "#0f172a",
                          border:
                            "1px solid #1f2937",
                          borderRadius: 8,
                          padding:
                            "9px 11px",
                          color:
                            "#94a3b8",
                          fontSize: 11,
                          fontFamily:
                            "monospace",
                          wordBreak:
                            "break-all",
                        }}
                      >
                        📄{" "}
                        {typeof file ===
                        "string"
                          ? file
                          : file.path ||
                            file.file_path ||
                            JSON.stringify(
                              file,
                            )}
                      </div>
                    ),
                  )}
                </div>
              )}
            </Section>
          </div>

          {/* ==================================================
              会話履歴
          ================================================== */}

          <div
            style={{
              marginTop: 16,
            }}
          >
            <Section
              icon="💬"
              title="最近の会話履歴"
              count={
                memory.conversations.length
              }
              description="現在のセッションで保存されている会話"
            >
              {recentConversations.length ===
              0 ? (
                <EmptyState
                  icon="💬"
                  title="会話履歴なし"
                />
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 8,
                  }}
                >
                  {recentConversations.map(
                    (message, index) => {
                      const isUser =
                        message.role ===
                        "user";

                      return (
                        <div
                          key={
                            message.id ??
                            index
                          }
                          style={{
                            background:
                              isUser
                                ? "#172554"
                                : "#0f172a",
                            border:
                              "1px solid #1e293b",
                            borderRadius: 10,
                            padding:
                              "10px 13px",
                          }}
                        >
                          <div
                            style={{
                              display:
                                "flex",
                              alignItems:
                                "center",
                              justifyContent:
                                "space-between",
                              gap: 10,
                              marginBottom: 5,
                            }}
                          >
                            <strong
                              style={{
                                fontSize: 11,
                                color:
                                  isUser
                                    ? "#93c5fd"
                                    : "#c4b5fd",
                              }}
                            >
                              {isUser
                                ? "👤 User"
                                : "🤖 AI"}
                            </strong>

                            <span
                              style={{
                                fontSize: 9,
                                color:
                                  "#475569",
                              }}
                            >
                              {formatDate(
                                message.timestamp ||
                                  message.created_at,
                              )}
                            </span>
                          </div>

                          <div
                            style={{
                              fontSize: 12,
                              lineHeight: 1.65,
                              color:
                                "#cbd5e1",
                              whiteSpace:
                                "pre-wrap",
                              wordBreak:
                                "break-word",
                            }}
                          >
                            {truncate(
                              message.content ||
                                message.text,
                              500,
                            )}
                          </div>
                        </div>
                      );
                    },
                  )}
                </div>
              )}
            </Section>
          </div>

          {/* ==================================================
              Session info
          ================================================== */}

          <div
            style={{
              marginTop: 16,
              padding:
                "14px 16px",
              background: "#0f172a",
              border:
                "1px solid #1e293b",
              borderRadius: 10,
              color: "#475569",
              fontSize: 10,
              fontFamily: "monospace",
            }}
          >
            <div>
              Session ID:{" "}
              {memory.session
                ?.session_id ||
                "なし"}
            </div>

            <div>
              Last Active:{" "}
              {memory.session
                ?.last_active ||
                "不明"}
            </div>

            <div>
              Message Count:{" "}
              {memory.session
                ?.message_count ??
                memory.conversations
                  .length}
            </div>
          </div>
        </div>
      </div>

      {/* ======================================================
          Toast
      ====================================================== */}

      {toast && (
        <div
          style={{
            position: "fixed",
            right: 22,
            bottom: 22,
            zIndex: 10000,
            borderRadius: 10,
            padding: "11px 16px",
            fontSize: 12,
            fontWeight: 700,

            background:
              toast.type === "error"
                ? "#2a1014"
                : "#052e16",

            border:
              toast.type === "error"
                ? "1px solid #7f1d1d"
                : "1px solid #166534",

            color:
              toast.type === "error"
                ? "#f87171"
                : "#4ade80",

            boxShadow:
              "0 12px 35px rgba(0,0,0,.4)",
          }}
        >
          {toast.type === "error"
            ? "⚠ "
            : "✓ "}
          {toast.message}
        </div>
      )}
    </>
  );
}