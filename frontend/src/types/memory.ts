// frontend/src/types/memory.ts

// ============================================================
// Chat
// ============================================================

export type ChatRole =
  | "user"
  | "assistant"
  | "system";


export interface ChatMessage {
  id: string;

  role: ChatRole;

  content: string;

  timestamp: string;

  metadata: Record<string, unknown>;

  /**
   * get_all_chat_history() を使用した場合に
   * 付与される可能性がある。
   */
  session_id?: string;
}


// ============================================================
// Task
// ============================================================

export type MemoryTaskStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "done"
  | "cancelled";


export type MemoryTaskPriority =
  | "low"
  | "normal"
  | "high";


export interface MemoryTask {
  id: string;

  task_name: string;

  details: string;

  status: MemoryTaskStatus;

  priority: MemoryTaskPriority;

  due_date?: string | null;

  tags: string[];

  created_at: string;

  updated_at: string;
}


// ============================================================
// Long Term Memory
// ============================================================

export interface LongTermMemory {
  id: string;

  /**
   * 例:
   *
   * preference
   * likes
   * interest
   * schedule
   * challenge
   * architecture
   * decision
   * project
   */
  category: string;

  title?: string | null;

  text: string;

  tags: string[];

  metadata: Record<string, unknown>;

  created_at: string;

  updated_at: string;
}


// ============================================================
// Session
// ============================================================

export interface MemorySession {
  session_id: string;

  project_name: string;

  created_at: string;

  last_active: string;

  message_count: number;
}


// ============================================================
// Statistics
// ============================================================

export interface MemoryStatistics {
  chat_sessions: number;

  chat_messages: number;

  long_term_memories: number;

  tasks: number;

  pending_tasks: number;

  projects: number;

  preferences: number;

  schedules: number;

  challenges: number;
}


// ============================================================
// Project Memory
// ============================================================

export interface ProjectMemory {
  project_name?: string;

  updated_at?: string;

  recent_files?: string[];

  /**
   * save_project_memory() は
   * 任意の key/value を保存できるため、
   * その他の値も許可する。
   */
  [key: string]: unknown;
}


// ============================================================
// General Memory
// ============================================================

export type GeneralMemory =
  Record<string, unknown>;


// ============================================================
// Memory Overview
// ============================================================

/**
 * GET /api/memory/overview
 *
 * MemoryManager.tsx が主に利用する型。
 */
export interface MemoryOverview {
  session: MemorySession;

  /**
   * 最近追加・更新された長期記憶
   */
  recent_memories: LongTermMemory[];

  /**
   * 好きなこと・興味
   */
  preferences: LongTermMemory[];

  /**
   * タスク
   */
  tasks: MemoryTask[];

  /**
   * 予定・イベント・締切
   */
  schedules: LongTermMemory[];

  /**
   * 現在セッションの会話履歴
   */
  conversations: ChatMessage[];

  /**
   * 大きな課題・問題・ブロッカー
   */
  challenges: LongTermMemory[];

  /**
   * 長期記憶全体
   */
  long_term_memories: LongTermMemory[];

  /**
   * 最近触ったファイル
   */
  recent_files: string[];

  /**
   * プロジェクト記憶
   */
  projects: ProjectMemory[];

  /**
   * general_memory.json
   */
  general_memory: GeneralMemory;

  /**
   * Memory統計
   */
  statistics: MemoryStatistics;
}


// ============================================================
// API Responses
// ============================================================

export interface MemoryOverviewResponse
  extends MemoryOverview {}


export interface MemoryListResponse<
  T
> {
  count: number;

  memories?: T[];

  tasks?: T[];

  messages?: T[];

  preferences?: T[];

  schedules?: T[];

  challenges?: T[];
}


// ============================================================
// Task API
// ============================================================

export interface TaskCreateRequest {
  task_name: string;

  details?: string;

  status?: MemoryTaskStatus;

  due_date?: string | null;

  priority?: MemoryTaskPriority;

  tags?: string[];
}


export interface TaskStatusUpdateRequest {
  status: MemoryTaskStatus;
}


export interface TaskResponse {
  success?: boolean;

  task: MemoryTask;
}


// ============================================================
// Long Term Memory API
// ============================================================

export interface LongTermMemoryCreateRequest {
  category: string;

  text: string;

  title?: string | null;

  tags?: string[];

  metadata?: Record<string, unknown>;
}


export interface LongTermMemoryUpdateRequest {
  category?: string;

  text?: string;

  title?: string | null;

  tags?: string[];

  metadata?: Record<string, unknown>;
}


export interface LongTermMemoryResponse {
  success: boolean;

  memory: LongTermMemory;
}


// ============================================================
// Clear Memory API
// ============================================================

export interface ClearMemoryError {
  path: string;

  error: string;
}


export interface ClearAllMemoryResponse {
  success: boolean;

  message: string;

  errors: ClearMemoryError[];

  session: MemorySession | null;
}


// ============================================================
// Session API
// ============================================================

export interface SessionResponse {
  session: MemorySession;
}


export interface ActiveProjectUpdateRequest {
  project_name: string;
}


// ============================================================
// Memory Search
// ============================================================

export interface MemorySearchResponse {
  keyword: string;

  results: LongTermMemory[];

  count: number;
}