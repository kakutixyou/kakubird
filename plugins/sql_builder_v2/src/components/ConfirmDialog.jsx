import { useEffect } from "react";

/**
 * 破壊的アクション（DELETE / DROP等）を実行する前の確認用モーダルダイアログ
 * * @param {boolean} isOpen - ダイアログの表示状態
 * @param {string} title - ダイアログのタイトル
 * @param {string} message - 警告メッセージ
 * @param {Function} onConfirm - 「実行する」ボタンが押された時の処理
 * @param {Function} onCancel - 「キャンセル」ボタンや背景が押された時の処理
 */
export function ConfirmDialog({ isOpen, title = "確認", message, onConfirm, onCancel }) {
  // Escキーでキャンセルできるようにする
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (isOpen && e.key === "Escape") {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div style={styles.overlay} onClick={onCancel}>
      {/* e.stopPropagation() で、モーダル本体のクリックが背景(キャンセル)に伝播するのを防ぐ */}
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <span style={styles.icon}>⚠️</span>
          <h3 style={styles.title}>{title}</h3>
        </div>
        
        <div style={styles.body}>
          <p style={styles.messageText}>{message}</p>
        </div>
        
        <div style={styles.actions}>
          <button style={styles.cancelBtn} onClick={onCancel}>
            キャンセル
          </button>
          <button style={styles.confirmBtn} onClick={onConfirm}>
            危険を承知で実行する
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── スタイル定義 ───────────────────────────────────────────────────────────

const styles = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.6)",
    backdropFilter: "blur(2px)", // 背景を少しぼかす（モダンなUI）
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 9999, // 最前面に表示
  },
  modal: {
    backgroundColor: "#1e1e24",
    border: "1px solid #333",
    borderRadius: "8px",
    width: "400px",
    maxWidth: "90%",
    boxShadow: "0 10px 30px rgba(0, 0, 0, 0.5)",
    overflow: "hidden",
    animation: "fadeIn 0.2s ease-out",
  },
  header: {
    backgroundColor: "#2a1515", // 危険を知らせるための薄い赤黒い背景
    padding: "16px",
    display: "flex",
    alignItems: "center",
    gap: "12px",
    borderBottom: "1px solid #442222",
  },
  icon: {
    fontSize: "1.5rem",
  },
  title: {
    margin: 0,
    color: "#ff6b6b", // 警告色のテキスト
    fontSize: "1.2rem",
    fontWeight: "bold",
  },
  body: {
    padding: "20px 16px",
  },
  messageText: {
    margin: 0,
    color: "#ddd",
    fontSize: "0.95rem",
    lineHeight: "1.5",
    whiteSpace: "pre-wrap", // 改行コード(\n)を反映させる
  },
  actions: {
    padding: "12px 16px",
    backgroundColor: "#1a1a1f",
    borderTop: "1px solid #333",
    display: "flex",
    justifyContent: "flex-end",
    gap: "12px",
  },
  cancelBtn: {
    padding: "8px 16px",
    backgroundColor: "transparent",
    color: "#aaa",
    border: "1px solid #555",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.9rem",
  },
  confirmBtn: {
    padding: "8px 16px",
    backgroundColor: "#d32f2f", // 赤色の危険ボタン
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.9rem",
    fontWeight: "bold",
  },
};