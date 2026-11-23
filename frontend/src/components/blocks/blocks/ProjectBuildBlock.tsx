// ProjectBuildBlock.tsx
import * as React from "react";
import { CodeFormatBlock } from "./CodeFormatBlock";
export type BuildStatus = "pending" | "building" | "success" | "warning" | "error";

export interface BuildStep {
  name: string;
  status: BuildStatus | string;
  message?: string | null;
  progress_percent?: number;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
}

export interface FeatureCheckItem {
  name: string;
  status: string;
  message?: string | null;
}

export interface FeatureCheck {
  key: string;
  title: string;
  status: string;
  summary?: string | null;
  checks: FeatureCheckItem[];
}

export interface GeneratedFileSummary {
  path: string;
  status: BuildStatus | string;
  source?: string | null;
  error?: string | null;
  characters?: number;
}

export interface ValidationIssue {
  level?: string;
  code?: string;
  message?: string;
  file_path?: string | null;
}

export interface ValidationResult {
  success?: boolean;
  status?: BuildStatus | string;
  message?: string;
  checked_files?: number;
  errors?: ValidationIssue[];
  warnings?: ValidationIssue[];
  logs?: string[];
}

export interface RepairAction {
  action?: string;
  file_path?: string | null;
  reason?: string;
  related_errors?: string[];
}

export interface RepairIteration {
  iteration?: number;
  actions?: RepairAction[];
  repaired_files?: string[];
  failed_files?: string[];
  validation_before?: ValidationResult | null;
  validation_after?: ValidationResult | null;
}

export interface RepairResult {
  success?: boolean;
  total_iterations?: number;
  iterations?: RepairIteration[];
  final_validation?: ValidationResult | null;
  error?: string | null;
}

/** 連携ファイル (.py / .java / .ts / .tsx 等) の検知情報 */
export interface ConnectedFileInfo {
  path: string;
  module: string;
  language: string;
  relation: string;
  symbols: string[];
  external: boolean;
  exists_in_project: boolean;
}

/** 公開クラス・メソッド・API等の機能単位 */
export interface SymbolCapabilityInfo {
  name: string;
  kind: string;
  signature: string;
  summary: string;
  line: number;
  end_line?: number | null;
  exported: boolean;
}

/** 既存コードに対する破壊的変更のブロック情報 */
export interface BreakingChangeInfo {
  file_path: string;
  code: string;
  message: string;
  removed_symbols: string[];
  impacted_files: string[];
  action_taken: string;
}

/** 既存コード保護ガードの状態 */
export interface SafetyGuardData {
  mode: string;
  clean_existing_blocked?: boolean;
  protected_files: string[];
  backed_up_files: string[];
  blocked_overwrites: string[];
  proposed_sidecar_files: string[];
  breaking_changes: BreakingChangeInfo[];
  backup_dir?: string | null;
}

/** VS Code連携・1部分のみ修正 (Surgical Partial Patch v2) の結果 */
export interface PartialPatchData {
  success: boolean;
  file_path: string;
  strategy: string;
  target_symbol?: string | null;
  modified_start_line: number;
  modified_end_line: number;
  original_line_count: number;
  new_line_count: number;
  preserved_symbols_count: number;
  hunks_applied?: number;
  added_imports?: string[];
  cross_file_warnings?: string[];
  unified_diff: string;
  before_snippet: string;
  after_snippet: string;
  backup_file_path?: string | null;
  vscode_goto_command: string;
  vscode_diff_command: string;
  vscode_launched?: boolean;
  applied_to_disk?: boolean;
  message: string;
  error?: string | null;
}

/** コード解析結果（目標・連携ファイル・何ができるか） */
export interface CodeAnalysisData {
  target_file: string;
  language: string;
  goal: string;
  summary: string;
  connected_files: ConnectedFileInfo[];
  reverse_dependencies: string[];
  external_packages: string[];
  capabilities: string[];
  symbols: SymbolCapabilityInfo[];
  line_count: number;
  parse_errors: string[];
  safety_guard?: SafetyGuardData | null;
  partial_patch?: PartialPatchData | null;
}

export interface ProjectBuildData {
  project_name: string;
  status: BuildStatus | string;
  message: string;
  files_generated: number;
  project_root?: string | null;
  zip_path?: string | null;
  zip_download_url?: string | null;
  zip_files_added?: number;
  plan?: Record<string, unknown> | null;
  generation: GeneratedFileSummary[];
  write_result?: Record<string, unknown> | null;
  validation?: ValidationResult | null;
  repair?: RepairResult | null;
  steps: BuildStep[];
  logs: string[];
  errors: string[];
  warnings: string[];
  progress_percent: number;
  current_stage: string;
  elapsed_seconds: number;
  estimated_total_minutes?: number | null;
  estimated_remaining_minutes?: number | null;
  estimate_confidence: string;
  feature_checks: FeatureCheck[];
  code_analysis?: CodeAnalysisData | null;
  safety_guard?: SafetyGuardData | null;
  partial_patch?: PartialPatchData | null;
}

export interface ProjectBuildBlockProps {
  /** Current block renderer style: <ProjectBuildBlock data={block.data} /> */
  data?: unknown;
  /** Legacy block renderer style: <ProjectBuildBlock block={block} /> */
  block?: { data?: unknown } | null;
  /** Optional backend origin, for example http://localhost:8000. */
  apiBaseUrl?: string;
  className?: string;
  onDownload?: (url: string, data: ProjectBuildData) => void;
  onOptionSelect?: (...args: unknown[]) => void;
}

type UnknownRecord = Record<string, unknown>;

const STATUS_LABELS: Record<string, string> = {
  pending: "待機中",
  building: "生成中",
  success: "完了",
  warning: "保護・警告あり",
  error: "失敗",
};

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  building: "◌",
  success: "✓",
  warning: "!",
  error: "×",
};

const ESTIMATE_CONFIDENCE_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

const RELATION_LABELS: Record<string, string> = {
  imports: "import参照先",
  imported_by: "逆参照（影響範囲）",
  same_package: "同一パッケージ連携",
  pipeline_link: "パイプライン連携",
};

const COLORS = {
  background: "#ffffff",
  border: "#d9e2ec",
  muted: "#5f6c7b",
  text: "#17212b",
  success: "#16794b",
  successSoft: "#e8f7ef",
  warning: "#946200",
  warningSoft: "#fff6d8",
  error: "#b42318",
  errorSoft: "#fff0ee",
  building: "#2463eb",
  buildingSoft: "#edf4ff",
  pending: "#6b7280",
  pendingSoft: "#f2f4f7",
} as const;

const styles: Record<string, React.CSSProperties> = {
  root: {
    width: "100%",
    boxSizing: "border-box",
    border: `1px solid ${COLORS.border}`,
    borderRadius: 16,
    background: COLORS.background,
    color: COLORS.text,
    boxShadow: "0 8px 28px rgba(30, 50, 70, 0.08)",
    overflow: "hidden",
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  header: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 16,
    padding: "20px 22px 16px",
  },
  titleGroup: { minWidth: 0, flex: "1 1 280px" },
  eyebrow: {
    margin: "0 0 5px",
    color: COLORS.muted,
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  title: {
    margin: 0,
    overflowWrap: "anywhere",
    fontSize: 20,
    lineHeight: 1.35,
  },
  message: { margin: "7px 0 0", color: COLORS.muted, fontSize: 14, lineHeight: 1.6 },
  body: { padding: "0 22px 22px" },
  progressTrack: {
    height: 8,
    overflow: "hidden",
    borderRadius: 999,
    background: "#edf1f5",
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
    gap: 10,
    marginTop: 14,
  },
  summaryCard: {
    padding: "12px 14px",
    border: `1px solid ${COLORS.border}`,
    borderRadius: 11,
    background: "#fbfcfe",
  },
  summaryLabel: { color: COLORS.muted, fontSize: 12 },
  summaryValue: { display: "block", marginTop: 4, fontSize: 18, fontWeight: 750 },
  section: { marginTop: 18 },
  sectionTitle: { margin: "0 0 9px", fontSize: 14, fontWeight: 750 },
  analysisCard: {
    padding: "14px 16px",
    border: `1px solid ${COLORS.border}`,
    borderRadius: 12,
    background: "#f8fafc",
  },
  goalBox: {
    padding: "11px 14px",
    borderRadius: 10,
    background: COLORS.buildingSoft,
    borderLeft: `4px solid ${COLORS.building}`,
    fontSize: 14,
    lineHeight: 1.55,
  },
  badgeRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  fileBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "5px 10px",
    borderRadius: 8,
    border: `1px solid ${COLORS.border}`,
    background: "#ffffff",
    fontSize: 12,
    fontWeight: 600,
  },
  langTag: {
    padding: "2px 6px",
    borderRadius: 5,
    background: COLORS.buildingSoft,
    color: COLORS.building,
    fontSize: 10,
    fontWeight: 800,
    textTransform: "uppercase",
  },
  stepList: { display: "grid", gap: 8, margin: 0, padding: 0, listStyle: "none" },
  step: {
    display: "grid",
    gridTemplateColumns: "30px minmax(0, 1fr)",
    gap: 10,
    alignItems: "start",
    padding: "10px 12px",
    border: `1px solid ${COLORS.border}`,
    borderRadius: 10,
  },
  stepName: { fontSize: 14, fontWeight: 700, overflowWrap: "anywhere" },
  stepMessage: { marginTop: 3, color: COLORS.muted, fontSize: 12, lineHeight: 1.5 },
  list: { margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 1.65 },
  details: {
    marginTop: 10,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 10,
    background: "#fbfcfe",
  },
  detailsSummary: { cursor: "pointer", padding: "11px 13px", fontSize: 13, fontWeight: 700 },
  detailsBody: { padding: "0 13px 13px" },
  codeList: {
    maxHeight: 240,
    overflow: "auto",
    margin: 0,
    padding: "10px 12px",
    borderRadius: 8,
    background: "#17212b",
    color: "#e7edf3",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
    fontSize: 12,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    overflowWrap: "anywhere",
  },
  download: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    minHeight: 40,
    padding: "0 16px",
    borderRadius: 10,
    background: COLORS.building,
    color: "#fff",
    fontSize: 14,
    fontWeight: 750,
    textDecoration: "none",
  },
  actionBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "6px 12px",
    borderRadius: 8,
    border: `1px solid ${COLORS.building}`,
    background: COLORS.buildingSoft,
    color: COLORS.building,
    fontSize: 12,
    fontWeight: 700,
    cursor: "pointer",
  },
  notice: { margin: 0, padding: "10px 12px", borderRadius: 9, fontSize: 13, lineHeight: 1.55 },
};

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : value == null ? fallback : String(value);
}

function numberValue(value: unknown, fallback = 0): number {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) && number >= 0 ? number : fallback;
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => stringValue(item).trim()).filter(Boolean);
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of values) {
    const trimmed = item.trim();
    if (trimmed && !seen.has(trimmed)) {
      seen.add(trimmed);
      result.push(trimmed);
    }
  }
  return result;
}

function normalizedStatus(value: unknown): BuildStatus {
  const status = stringValue(value, "pending").toLowerCase();
  return status === "building" ||
    status === "success" ||
    status === "warning" ||
    status === "error"
    ? status
    : "pending";
}

function normalizeSteps(value: unknown): BuildStep[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isRecord).map((item) => ({
    name: stringValue(item.name, "Unknown step"),
    status: normalizedStatus(item.status),
    message: item.message == null ? null : stringValue(item.message),
    progress_percent: numberValue(item.progress_percent),
    started_at: item.started_at == null ? null : stringValue(item.started_at),
    finished_at: item.finished_at == null ? null : stringValue(item.finished_at),
    duration_ms: item.duration_ms == null ? null : numberValue(item.duration_ms),
  }));
}

function normalizeFeatureChecks(value: unknown): FeatureCheck[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isRecord).map((item) => ({
    key: stringValue(item.key, "feature"),
    title: stringValue(item.title, "機能確認"),
    status: stringValue(item.status, "pending"),
    summary: item.summary == null ? null : stringValue(item.summary),
    checks: Array.isArray(item.checks)
      ? item.checks.filter(isRecord).map((check) => ({
          name: stringValue(check.name, "確認項目"),
          status: stringValue(check.status, "pending"),
          message: check.message == null ? null : stringValue(check.message),
        }))
      : [],
  }));
}

function normalizeGeneration(
  generationValue: unknown,
  writeResultValue?: unknown,
  planValue?: unknown,
): GeneratedFileSummary[] {
  if (Array.isArray(generationValue) && generationValue.length > 0) {
    return generationValue.filter(isRecord).map((item) => ({
      path: stringValue(item.path, "unknown"),
      status: normalizedStatus(item.status),
      source: item.source == null ? null : stringValue(item.source),
      error: item.error == null ? null : stringValue(item.error),
      characters: numberValue(item.characters),
    }));
  }
  if (isRecord(writeResultValue) && Array.isArray(writeResultValue.files) && writeResultValue.files.length > 0) {
    return writeResultValue.files.filter(isRecord).map((item) => ({
      path: stringValue(item.path, "unknown"),
      status: normalizedStatus(item.status ?? "success"),
      source: "written",
      error: item.error == null ? null : stringValue(item.error),
      characters: numberValue(item.bytes_written),
    }));
  }
  if (isRecord(planValue) && Array.isArray(planValue.file_structure)) {
    return planValue.file_structure.filter(isRecord).map((item) => ({
      path: stringValue(item.path, "unknown"),
      status: "pending",
      source: stringValue(item.type, "planned"),
      error: null,
      characters: 0,
    }));
  }
  return [];
}

function normalizeIssue(value: unknown): ValidationIssue | null {
  if (!isRecord(value)) return null;
  return {
    level: stringValue(value.level),
    code: stringValue(value.code, "VALIDATION"),
    message: stringValue(value.message, "検証エラーです。"),
    file_path: value.file_path == null ? null : stringValue(value.file_path),
  };
}

function normalizeValidation(value: unknown): ValidationResult | null {
  if (!isRecord(value)) return null;
  return {
    success: typeof value.success === "boolean" ? value.success : undefined,
    status: normalizedStatus(value.status ?? (value.success ? "success" : "error")),
    message: stringValue(value.message),
    checked_files: numberValue(value.checked_files),
    errors: Array.isArray(value.errors)
      ? value.errors.map(normalizeIssue).filter((item): item is ValidationIssue => item !== null)
      : [],
    warnings: Array.isArray(value.warnings)
      ? value.warnings.map(normalizeIssue).filter((item): item is ValidationIssue => item !== null)
      : [],
    logs: stringArray(value.logs),
  };
}

function normalizeRepair(value: unknown): RepairResult | null {
  if (!isRecord(value)) return null;
  const rawIterations = Array.isArray(value.iterations) ? value.iterations : [];
  const iterations = rawIterations.filter(isRecord).map((item) => ({
    iteration: numberValue(item.iteration),
    repaired_files: stringArray(item.repaired_files),
    failed_files: stringArray(item.failed_files),
  }));
  const count =
    typeof value.iterations === "number"
      ? value.iterations
      : numberValue(value.total_iterations, iterations.length);
  return {
    success: typeof value.success === "boolean" ? value.success : undefined,
    total_iterations: count,
    iterations,
    final_validation: normalizeValidation(value.final_validation ?? value.validation),
    error: value.error == null ? null : stringValue(value.error),
  };
}

function normalizeSafetyGuard(value: unknown): SafetyGuardData | null {
  if (!isRecord(value)) return null;
  const breaking = Array.isArray(value.breaking_changes)
    ? value.breaking_changes.filter(isRecord).map((item) => ({
        file_path: stringValue(item.file_path),
        code: stringValue(item.code, "BREAKING_CHANGE"),
        message: stringValue(item.message),
        removed_symbols: stringArray(item.removed_symbols),
        impacted_files: stringArray(item.impacted_files),
        action_taken: stringValue(item.action_taken, "blocked_overwrite"),
      }))
    : [];
  return {
    mode: stringValue(value.mode, "safe_preserve"),
    clean_existing_blocked: Boolean(value.clean_existing_blocked),
    protected_files: stringArray(value.protected_files),
    backed_up_files: stringArray(value.backed_up_files),
    blocked_overwrites: stringArray(value.blocked_overwrites),
    proposed_sidecar_files: stringArray(value.proposed_sidecar_files),
    breaking_changes: breaking,
    backup_dir: value.backup_dir == null ? null : stringValue(value.backup_dir),
  };
}

function normalizePartialPatch(value: unknown): PartialPatchData | null {
  if (!isRecord(value)) return null;
  return {
    success: Boolean(value.success),
    file_path: stringValue(value.file_path),
    strategy: stringValue(value.strategy, "symbol_replace"),
    target_symbol: value.target_symbol == null ? null : stringValue(value.target_symbol),
    modified_start_line: numberValue(value.modified_start_line, 1),
    modified_end_line: numberValue(value.modified_end_line, 1),
    original_line_count: numberValue(value.original_line_count),
    new_line_count: numberValue(value.new_line_count),
    preserved_symbols_count: numberValue(value.preserved_symbols_count),
    hunks_applied: numberValue(value.hunks_applied, 1),
    added_imports: stringArray(value.added_imports),
    cross_file_warnings: stringArray(value.cross_file_warnings),
    unified_diff: stringValue(value.unified_diff),
    before_snippet: stringValue(value.before_snippet),
    after_snippet: stringValue(value.after_snippet),
    backup_file_path: value.backup_file_path == null ? null : stringValue(value.backup_file_path),
    vscode_goto_command: stringValue(value.vscode_goto_command),
    vscode_diff_command: stringValue(value.vscode_diff_command),
    vscode_launched: Boolean(value.vscode_launched),
    applied_to_disk: Boolean(value.applied_to_disk),
    message: stringValue(value.message),
    error: value.error == null ? null : stringValue(value.error),
  };
}

function normalizeCodeAnalysis(value: unknown): CodeAnalysisData | null {
  if (!isRecord(value)) return null;
  const connected = Array.isArray(value.connected_files)
    ? value.connected_files.filter(isRecord).map((item) => ({
        path: stringValue(item.path),
        module: stringValue(item.module),
        language: stringValue(item.language, "unknown"),
        relation: stringValue(item.relation, "imports"),
        symbols: stringArray(item.symbols),
        external: Boolean(item.external),
        exists_in_project: Boolean(item.exists_in_project),
      }))
    : [];
  const symbols = Array.isArray(value.symbols)
    ? value.symbols.filter(isRecord).map((item) => ({
        name: stringValue(item.name),
        kind: stringValue(item.kind, "symbol"),
        signature: stringValue(item.signature),
        summary: stringValue(item.summary),
        line: numberValue(item.line, 1),
        end_line: item.end_line == null ? null : numberValue(item.end_line, 1),
        exported: Boolean(item.exported ?? true),
      }))
    : [];
  return {
    target_file: stringValue(value.target_file, "submitted_code.py"),
    language: stringValue(value.language, "python"),
    goal: stringValue(value.goal, "コードの目的を解析中"),
    summary: stringValue(value.summary),
    connected_files: connected,
    reverse_dependencies: stringArray(value.reverse_dependencies),
    external_packages: stringArray(value.external_packages),
    capabilities: stringArray(value.capabilities),
    symbols,
    line_count: numberValue(value.line_count),
    parse_errors: stringArray(value.parse_errors),
    safety_guard: normalizeSafetyGuard(value.safety_guard),
    partial_patch: normalizePartialPatch(value.partial_patch),
  };
}

/** Normalize current, legacy, and ToolResult-wrapped payloads into one UI model. */
export function normalizeProjectBuildData(value: unknown): ProjectBuildData {
  let source: UnknownRecord = isRecord(value) ? value : {};
  if (!source.project_name && isRecord(source.data)) source = source.data;
  const generation = normalizeGeneration(source.generation, source.write_result, source.plan);
  const codeAnalysis = normalizeCodeAnalysis(source.code_analysis);
  const safetyGuard =
    normalizeSafetyGuard(source.safety_guard) ?? codeAnalysis?.safety_guard ?? null;
  const partialPatch =
    normalizePartialPatch(source.partial_patch) ?? codeAnalysis?.partial_patch ?? null;

  const rawRemaining =
    source.estimated_remaining_minutes == null
      ? null
      : Math.min(30, numberValue(source.estimated_remaining_minutes));

  return {
    project_name: stringValue(source.project_name, codeAnalysis?.target_file || "generated-app"),
    status: normalizedStatus(source.status),
    message: stringValue(
      source.message,
      codeAnalysis?.summary || "プロジェクト生成・コード解析結果を表示しています。",
    ),
    files_generated: numberValue(source.files_generated, generation.length),
    project_root: source.project_root == null ? null : stringValue(source.project_root),
    zip_path: source.zip_path == null ? null : stringValue(source.zip_path),
    zip_download_url:
      source.zip_download_url == null ? null : stringValue(source.zip_download_url),
    zip_files_added: numberValue(source.zip_files_added),
    plan: isRecord(source.plan) ? source.plan : null,
    generation,
    write_result: isRecord(source.write_result) ? source.write_result : null,
    validation: normalizeValidation(source.validation),
    repair: normalizeRepair(source.repair),
    steps: normalizeSteps(source.steps),
    logs: stringArray(source.logs),
    errors: stringArray(source.errors),
    warnings: stringArray(source.warnings),
    progress_percent: numberValue(source.progress_percent),
    current_stage: stringValue(source.current_stage, "準備中"),
    elapsed_seconds: numberValue(source.elapsed_seconds),
    estimated_total_minutes:
      source.estimated_total_minutes == null
        ? null
        : Math.min(30, numberValue(source.estimated_total_minutes)),
    estimated_remaining_minutes: rawRemaining,
    estimate_confidence: stringValue(source.estimate_confidence, "low"),
    feature_checks: normalizeFeatureChecks(source.feature_checks),
    code_analysis: codeAnalysis,
    safety_guard: safetyGuard,
    partial_patch: partialPatch,
  };
}

/** Allow only same-app relative URLs and explicit HTTP(S) endpoints. */
export function resolveProjectDownloadUrl(
  value: unknown,
  apiBaseUrl?: string,
): string | null {
  const url = stringValue(value).trim();
  if (!url || /[\u0000-\u001f\u007f\\]/.test(url)) return null;
  if (/^https?:\/\//i.test(url)) {
    return /^https?:\/\/[^\s/?#]+(?:[/?#][^\s]*)?$/i.test(url) ? url : null;
  }
  if (/^[a-z][a-z\d+.-]*:/i.test(url) || url.startsWith("//")) return null;
  const relative = url.startsWith("/") ? url : `/${url}`;
  const base = stringValue(apiBaseUrl).trim().replace(/\/$/, "");
  if (!base) return relative;
  if (!/^https?:\/\//i.test(base)) return null;
  return `${base}${relative}`;
}

function statusColors(statusValue: unknown): { color: string; background: string } {
  const status = normalizedStatus(statusValue);
  if (status === "success") return { color: COLORS.success, background: COLORS.successSoft };
  if (status === "warning") return { color: COLORS.warning, background: COLORS.warningSoft };
  if (status === "error") return { color: COLORS.error, background: COLORS.errorSoft };
  if (status === "building") return { color: COLORS.building, background: COLORS.buildingSoft };
  return { color: COLORS.pending, background: COLORS.pendingSoft };
}

function StatusBadge({ status }: { status: unknown }): React.ReactElement {
  const normalized = normalizedStatus(status);
  const colors = statusColors(normalized);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 10px",
        borderRadius: 999,
        color: colors.color,
        background: colors.background,
        fontSize: 12,
        fontWeight: 750,
        whiteSpace: "nowrap",
      }}
      role="status"
    >
      <span aria-hidden="true">{STATUS_ICONS[normalized]}</span>
      {STATUS_LABELS[normalized]}
    </span>
  );
}

function NoticeList({
  title,
  values,
  tone,
}: {
  title: string;
  values: string[];
  tone: "error" | "warning";
}): React.ReactElement | null {
  const deduplicated = uniqueStrings(values);
  if (!deduplicated.length) return null;
  const colors = statusColors(tone);
  return (
    <section style={styles.section} aria-label={title}>
      <h4 style={styles.sectionTitle}>{title}</h4>
      <div style={{ ...styles.notice, color: colors.color, background: colors.background }}>
        <ul style={styles.list}>
          {deduplicated.map((value, index) => (
            <li key={`${value}-${index}`}>{value}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function issueText(issue: ValidationIssue): string {
  const location = issue.file_path ? ` [${issue.file_path}]` : "";
  return `${issue.code || "VALIDATION"}: ${issue.message || "検証エラーです。"}${location}`;
}

function featureStatus(status: string): BuildStatus {
  const value = status.toLowerCase();
  if (value === "checking") return "building";
  if (value === "planned" || value === "not_verified") return "pending";
  return normalizedStatus(value);
}

function featureStatusLabel(status: string): string {
  const value = status.toLowerCase();
  if (value === "checking") return "確認中";
  if (value === "planned") return "検出・連携予定";
  if (value === "not_verified") return "未確認";
  return STATUS_LABELS[normalizedStatus(value)];
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}秒`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}分${Math.round(seconds % 60)}秒`;
}

export function ProjectBuildBlock({
  data,
  block,
  apiBaseUrl,
  className,
  onDownload,
  onOptionSelect,
}: ProjectBuildBlockProps): React.ReactElement {
  const instanceId = React.useId();
  const stepsHeadingId = `${instanceId}-steps`;
  const build = React.useMemo(
    () => normalizeProjectBuildData(data ?? block?.data),
    [data, block?.data],
  );
  const status = normalizedStatus(build.status);
  const colors = statusColors(status);
  const completedSteps = build.steps.filter((step) =>
    ["success", "warning", "error"].includes(normalizedStatus(step.status)),
  ).length;
  const calculatedProgress = build.steps.length
    ? Math.round((completedSteps / build.steps.length) * 100)
    : status === "building"
      ? 10
      : 0;
  const progress = Math.min(
    100,
    status === "success" ? 100 : build.progress_percent || calculatedProgress,
  );
  const downloadUrl = resolveProjectDownloadUrl(build.zip_download_url, apiBaseUrl);
  const validationErrors = (build.validation?.errors ?? []).map(issueText);
  const validationWarnings = (build.validation?.warnings ?? []).map(issueText);
  const repairedFiles =
    build.repair?.iterations?.flatMap((item) => item.repaired_files ?? []) ?? [];
  const analysis = build.code_analysis;
  const guard = build.safety_guard ?? analysis?.safety_guard ?? null;
  const partialPatch = build.partial_patch ?? analysis?.partial_patch ?? null;

  return (
    <article
      className={className}
      style={{ ...styles.root, borderTop: `4px solid ${colors.color}` }}
      aria-label={`${build.project_name} のプロジェクト生成・コード解析結果`}
      aria-busy={status === "building"}
    >
      <header style={styles.header}>
        <div style={styles.titleGroup}>
          <p style={styles.eyebrow}>
            {partialPatch
              ? "Surgical Partial Patch & Safety Guard"
              : analysis
                ? "Code Inspector & Safety Guard"
                : "Project Build"}
          </p>
          <h3 style={styles.title}>{build.project_name}</h3>
          <p style={styles.message} aria-live="polite">
            {build.message}
          </p>
        </div>
        <StatusBadge status={status} />
      </header>

      <div style={styles.body}>
        <div
          style={styles.progressTrack}
          role="progressbar"
          aria-label="処理の進捗"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
        >
          <div
            style={{
              width: `${progress}%`,
              height: "100%",
              borderRadius: 999,
              background: colors.color,
              transition: "width 240ms ease",
            }}
          />
        </div>

        <p style={{ ...styles.message, marginTop: 10 }} aria-live="polite">
          現在の工程: <strong>{build.current_stage}</strong>
          {build.estimated_remaining_minutes != null &&
          build.estimated_remaining_minutes > 0 &&
          status === "building"
            ? ` ／ 完成までの推定 約${build.estimated_remaining_minutes}分`
            : ""}
          {build.estimate_confidence
            ? `（精度: ${
                ESTIMATE_CONFIDENCE_LABELS[build.estimate_confidence] ||
                build.estimate_confidence
              }）`
            : ""}
        </p>

        {/* ✂️ VS Code 1部分のみ修正レポート */}
        {partialPatch && (
          <section style={styles.section} aria-label="1部分のみ修正レポート">
            <h4 style={styles.sectionTitle}>
              ✂️ 1部分のみ修正レポート（{partialPatch.file_path} : L{partialPatch.modified_start_line}〜L{partialPatch.modified_end_line}
              {partialPatch.hunks_applied && partialPatch.hunks_applied > 1
                ? ` / ${partialPatch.hunks_applied}箇所同時適用`
                : ""}
              ）
            </h4>
            <div style={styles.analysisCard}>
              <p style={{ margin: "0 0 10px", fontSize: 13 }}>
                {partialPatch.message}
              </p>
              {partialPatch.added_imports && partialPatch.added_imports.length > 0 && (
                <p style={{ margin: "0 0 10px", fontSize: 12, color: COLORS.building, fontWeight: 600 }}>
                  📦 先頭へ自動追加した import: <code>{partialPatch.added_imports.join(", ")}</code>
                </p>
              )}
              {partialPatch.unified_diff && (
                // <pre style={styles.codeList}>{partialPatch.unified_diff}</pre>
                <div style={{ marginTop: 10 }}>
                  <CodeFormatBlock language="diff" code={partialPatch.unified_diff} />
                </div>
              )}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
                <button
                  type="button"
                  style={styles.actionBtn}
                  onClick={() =>
                    onOptionSelect?.({
                      action: "vscode_open_diff",
                      file_path: partialPatch.file_path,
                      command: partialPatch.vscode_diff_command,
                    })
                  }
                >
                  💻 VS CodeでDiffを開く
                </button>
                <button
                  type="button"
                  style={styles.actionBtn}
                  onClick={() =>
                    onOptionSelect?.({
                      action: "vscode_goto_line",
                      file_path: partialPatch.file_path,
                      line: partialPatch.modified_start_line,
                      command: partialPatch.vscode_goto_command,
                    })
                  }
                >
                  🔍 該当行 (L{partialPatch.modified_start_line}) をVS Codeで開く
                </button>
              </div>
            </div>
          </section>
        )}

        {/* コード解析（目標・連携 .py / .java ファイル・できること） */}
        {analysis && (
          <section style={styles.section} aria-label="コード解析と連携ファイル検知">
            <h4 style={styles.sectionTitle}>
              コード解析レポート（{analysis.target_file} / {analysis.language.toUpperCase()}）
            </h4>
            <div style={styles.analysisCard}>
              <div style={styles.goalBox}>
                <strong>🎯 目標 (Goal):</strong> {analysis.goal}
              </div>

              <div style={{ marginTop: 14 }}>
                <strong style={{ fontSize: 13 }}>
                  🔗 つながっているファイル（{analysis.connected_files.length}件）
                </strong>
                {analysis.connected_files.length > 0 ? (
                  <div style={styles.badgeRow}>
                    {analysis.connected_files.map((conn, idx) => (
                      <span key={`${conn.path}-${idx}`} style={styles.fileBadge}>
                        <span style={styles.langTag}>{conn.language}</span>
                        <code>{conn.path}</code>
                        <span style={{ color: COLORS.muted, fontSize: 11 }}>
                          ({RELATION_LABELS[conn.relation] || conn.relation})
                        </span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p style={styles.stepMessage}>
                    外部の .py / .java ファイルへの内部依存はありません（単体で動作可能）。
                  </p>
                )}
              </div>

              {analysis.capabilities.length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <strong style={{ fontSize: 13 }}>
                    ⚡ このコードで何ができるか（{analysis.capabilities.length}件）
                  </strong>
                  <ul style={{ ...styles.list, marginTop: 6 }}>
                    {analysis.capabilities.slice(0, 10).map((cap, idx) => (
                      <li key={`${cap}-${idx}`}>{cap}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </section>
        )}

        {/* 既存コード保護ガード状態 */}
        {guard && (
          <section style={styles.section} aria-label="既存コード保護ガード">
            <h4 style={styles.sectionTitle}>🛡️ 既存コード保護ガード (Non-Destructive Guard)</h4>
            <div
              style={{
                ...styles.notice,
                color: guard.breaking_changes.length > 0 ? COLORS.warning : COLORS.success,
                background:
                  guard.breaking_changes.length > 0 ? COLORS.warningSoft : COLORS.successSoft,
              }}
            >
              <div>
                <strong>保護モード:</strong> {guard.mode} ／{" "}
                <strong>保護対象ファイル:</strong> {guard.protected_files.length}件 ／{" "}
                <strong>破壊的変更ブロック:</strong> {guard.blocked_overwrites.length}件
                {guard.backup_dir ? ` ／ 自動バックアップ作成済み` : ""}
              </div>
              {guard.breaking_changes.length > 0 && (
                <ul style={{ ...styles.list, marginTop: 6 }}>
                  {guard.breaking_changes.map((bc, idx) => (
                    <li key={`${bc.file_path}-${idx}`}>
                      <code>{bc.file_path}</code>: {bc.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        )}

        <div style={styles.summaryGrid}>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>
              {analysis ? "関連・対象ファイル" : "生成ファイル"}
            </span>
            <strong style={styles.summaryValue}>{build.files_generated}</strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>
              {analysis ? "検出機能・シンボル" : "検証ファイル"}
            </span>
            <strong style={styles.summaryValue}>
              {analysis
                ? analysis.capabilities.length
                : (build.validation?.checked_files ?? 0)}
            </strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>
              {partialPatch ? "維持シンボル数" : guard ? "保護・ブロック数" : "自動修復"}
            </span>
            <strong style={styles.summaryValue}>
              {partialPatch
                ? `${Math.max(0, partialPatch.preserved_symbols_count - 1)}件`
                : guard
                  ? `${guard.protected_files.length}件`
                  : `${build.repair?.total_iterations ?? 0}回`}
            </strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>進捗</span>
            <strong style={styles.summaryValue}>{progress}%</strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>経過時間</span>
            <strong style={styles.summaryValue}>{formatElapsed(build.elapsed_seconds)}</strong>
          </div>
          <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>ZIP内ファイル</span>
            <strong style={styles.summaryValue}>{build.zip_files_added ?? 0}</strong>
          </div>
        </div>

        {build.feature_checks.length > 0 && (
          <section style={styles.section} aria-label="機能別の確認状況">
            <h4 style={styles.sectionTitle}>機能・連携別の確認状況</h4>
            <div style={{ display: "grid", gap: 10 }}>
              {build.feature_checks.map((feature, index) => {
                const tone = featureStatus(feature.status);
                const featureColors = statusColors(tone);
                return (
                  <div
                    key={`${feature.key}-${index}`}
                    style={{
                      padding: "12px 14px",
                      border: `1px solid ${COLORS.border}`,
                      borderLeft: `4px solid ${featureColors.color}`,
                      borderRadius: 10,
                      background: featureColors.background,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                      <strong>{feature.title}</strong>
                      <span
                        style={{ color: featureColors.color, fontSize: 12, fontWeight: 750 }}
                      >
                        {featureStatusLabel(feature.status)}
                      </span>
                    </div>
                    {feature.summary && <p style={styles.stepMessage}>{feature.summary}</p>}
                    {feature.checks.length > 0 && (
                      <ul style={{ ...styles.list, marginTop: 8 }}>
                        {feature.checks.map((check, checkIndex) => (
                          <li key={`${check.name}-${checkIndex}`}>
                            <strong>{featureStatusLabel(check.status)}</strong> — {check.name}
                            {check.message ? `: ${check.message}` : ""}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {build.steps.length > 0 && (
          <section style={styles.section} aria-labelledby={stepsHeadingId}>
            <h4 id={stepsHeadingId} style={styles.sectionTitle}>
              実行工程
            </h4>
            <ol style={styles.stepList}>
              {build.steps.map((step, index) => {
                const stepStatus = normalizedStatus(step.status);
                const stepColors = statusColors(stepStatus);
                return (
                  <li key={`${step.name}-${index}`} style={styles.step}>
                    <span
                      aria-hidden="true"
                      style={{
                        display: "grid",
                        width: 26,
                        height: 26,
                        placeItems: "center",
                        borderRadius: 999,
                        color: stepColors.color,
                        background: stepColors.background,
                        fontWeight: 800,
                      }}
                    >
                      {STATUS_ICONS[stepStatus]}
                    </span>
                    <div>
                      <div style={styles.stepName}>{step.name}</div>
                      {step.message && <div style={styles.stepMessage}>{step.message}</div>}
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        )}

        <NoticeList title="エラー" values={[...build.errors, ...validationErrors]} tone="error" />
        <NoticeList
          title="警告・保護通知"
          values={[...build.warnings, ...validationWarnings]}
          tone="warning"
        />

        {build.generation.length > 0 && (
          <details style={styles.details}>
            <summary style={styles.detailsSummary}>
              対象・関連ファイル一覧（{build.generation.length}）
            </summary>
            <div style={styles.detailsBody}>
              <ul style={styles.list}>
                {build.generation.map((file, index) => (
                  <li key={`${file.path}-${index}`}>
                    <code>{file.path}</code> — {STATUS_LABELS[normalizedStatus(file.status)]}
                    {file.source ? ` / ${file.source}` : ""}
                    {file.error ? ` / ${file.error}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          </details>
        )}

        {build.repair && (
          <details style={styles.details}>
            <summary style={styles.detailsSummary}>
              自動修復結果（{build.repair.total_iterations ?? 0}回）
            </summary>
            <div style={styles.detailsBody}>
              {repairedFiles.length ? (
                <ul style={styles.list}>
                  {repairedFiles.map((path, index) => (
                    <li key={`${path}-${index}`}>
                      <code>{path}</code>
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={styles.message}>修復されたファイルはありません。</p>
              )}
              {build.repair.error && (
                <p style={{ ...styles.notice, ...statusColors("error"), marginTop: 10 }}>
                  {build.repair.error}
                </p>
              )}
            </div>
          </details>
        )}

        {build.logs.length > 0 && (
          <details style={styles.details}>
            <summary style={styles.detailsSummary}>ターミナル・ビルドログ（{build.logs.length}）</summary>
            <div style={styles.detailsBody}>
              {/* 💡 生の <pre> タグから置き換えます */}
              <CodeFormatBlock language="bash" code={build.logs.join("\n")} />
            </div>
          </details>
        )}

        {status === "success" && downloadUrl && (
          <section style={{ ...styles.section, display: "flex", justifyContent: "flex-end" }}>
            <a
              href={downloadUrl}
              download={`${build.project_name}.zip`}
              style={styles.download}
              onClick={() => onDownload?.(downloadUrl, build)}
            >
              <span aria-hidden="true">↓</span>
              ZIPをダウンロード
            </a>
          </section>
        )}
      </div>
    </article>
  );
}

export default ProjectBuildBlock;