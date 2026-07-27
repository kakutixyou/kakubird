// frontend/src/components/MemoryManager.jsx
import React, { useState, useRef, useCallback } from "react";

// 🌟 バックエンドの ai_server.py のポート(8765)に合わせて修正
const API = "http://localhost:8765/api/memory";

// ── トースト ──────────────────────────────────
const useToast = () => {
  const [toast, setToast] = useState(null);
  const show = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };
  return [toast, show];
};

// ── ドロップゾーン ────────────────────────────
const DropZone = ({ onFiles, busy }) => {
  const ref = useRef();
  const [over, setOver] = useState(false);
  const pick = useCallback(files => {
    const imgs = [...files].filter(f => f.type.startsWith("image/"));
    if (imgs.length) onFiles(imgs);
  }, [onFiles]);

  return (
    <label style={{
      display: "block", border: `2px dashed ${over ? "#4f8ef7" : "#2a2d3a"}`,
      borderRadius: 10, padding: "28px 0", textAlign: "center",
      background: over ? "rgba(79,142,247,.06)" : "#13151e",
      cursor: busy ? "wait" : "pointer", transition: "all .18s",
      userSelect: "none",
    }}
    onDragOver={e => { e.preventDefault(); setOver(true); }}
    onDragLeave={() => setOver(false)}
    onDrop={e => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files); }}
    >
      <input ref={ref} type="file" accept="image/*" multiple hidden
        onChange={e => pick(e.target.files)} />
      {busy
        ? <span style={{ color: "#4f8ef7", fontSize: ".9rem" }}>⏳ OCR処理中…</span>
        : <>
            <div style={{ fontSize: "1.8rem", marginBottom: 6 }}>📸</div>
            <div style={{ color: "#c8cde0", fontWeight: 600, fontSize: ".9rem" }}>
              スクリーンショットをドロップ（複数可）
            </div>
            <div style={{ color: "#4a4f65", fontSize: ".75rem", marginTop: 3 }}>
              求人・フォルダ構成を自動で判別して保存します
            </div>
          </>
      }
    </label>
  );
};

// ── タブ ─────────────────────────────────────
const Tab = ({ label, count, active, onClick }) => (
  <button onClick={onClick} style={{
    background: "none", border: "none", cursor: "pointer",
    padding: "8px 16px", borderRadius: 7, fontFamily: "inherit",
    fontSize: ".85rem", fontWeight: active ? 700 : 500,
    color: active ? "#4f8ef7" : "#5a6070",
    background: active ? "rgba(79,142,247,.1)" : "transparent",
    transition: "all .15s",
  }}>
    {label}
    {count > 0 && (
      <span style={{
        marginLeft: 6, fontSize: ".7rem", fontWeight: 700,
        background: active ? "#4f8ef7" : "#2a2d3a",
        color: active ? "#fff" : "#8090a0",
        padding: "1px 7px", borderRadius: 10,
      }}>{count}</span>
    )}
  </button>
);

// ── 求人カード ────────────────────────────────
const JobCard = ({ job, onDelete }) => {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      background: "#13151e", border: "1px solid #1e2130",
      borderRadius: 10, padding: "16px 18px",
      borderLeft: "3px solid #4f8ef7",
      transition: "transform .15s",
    }}
    onMouseEnter={e => e.currentTarget.style.transform = "translateY(-1px)"}
    onMouseLeave={e => e.currentTarget.style.transform = "translateY(0)"}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: ".95rem", color: "#e0e4f0" }}>
            {job.company_name || "会社名不明"}
          </div>
          <div style={{ fontSize: ".8rem", color: "#4f8ef7", marginTop: 2 }}>
            {job.job_title || "職種不明"}
          </div>
        </div>
        <button onClick={() => onDelete("job", job.id)} style={{
          background: "none", border: "1px solid #ef444440", color: "#ef4444",
          borderRadius: 6, padding: "3px 9px", fontSize: ".72rem",
          cursor: "pointer", fontFamily: "inherit",
        }}>消す</button>
      </div>

      <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: "5px 14px" }}>
        {job.contact  && <Info icon="✉" v={job.contact} />}
        {job.salary   && <Info icon="💴" v={job.salary} />}
        {job.location && <Info icon="📍" v={job.location} />}
      </div>

      {job.memo && (
        <div style={{
          marginTop: 8, fontSize: ".76rem", color: "#8090a0",
          background: "#0e1018", borderRadius: 6, padding: "6px 10px",
        }}>{job.memo}</div>
      )}

      {job.raw_text && (
        <>
          <button onClick={() => setOpen(v => !v)} style={{
            background: "none", border: "none", color: "#4a5060",
            fontSize: ".72rem", cursor: "pointer", marginTop: 6, fontFamily: "inherit",
          }}>{open ? "▲ 閉じる" : "▼ OCR全文"}</button>
          {open && (
            <pre style={{
              fontSize: ".68rem", color: "#5a6070", background: "#0a0c12",
              borderRadius: 6, padding: "8px 10px", marginTop: 4, whiteSpace: "pre-wrap",
              wordBreak: "break-all", maxHeight: 160, overflowY: "auto", margin: "4px 0 0",
            }}>{job.raw_text}</pre>
          )}
        </>
      )}

      <div style={{ fontSize: ".68rem", color: "#3a3f50", marginTop: 8, textAlign: "right" }}>
        {job.created_at?.slice(0, 16).replace("T", " ")}
      </div>
    </div>
  );
};

// ── フォルダカード ────────────────────────────
const FolderCard = ({ folder, onDelete }) => {
  const [open, setOpen] = useState(false);
  const tree = folder.tree || [];
  const dirs  = tree.filter(n => n.kind === "dir");
  const files = tree.filter(n => n.kind === "file");

  return (
    <div style={{
      background: "#13151e", border: "1px solid #1e2130",
      borderRadius: 10, padding: "16px 18px",
      borderLeft: "3px solid #06b6d4",
      transition: "transform .15s",
    }}
    onMouseEnter={e => e.currentTarget.style.transform = "translateY(-1px)"}
    onMouseLeave={e => e.currentTarget.style.transform = "translateY(0)"}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: ".95rem", color: "#e0e4f0" }}>
            📁 {folder.root_name || "フォルダ不明"}
          </div>
          <div style={{ fontSize: ".78rem", color: "#06b6d4", marginTop: 2 }}>
            {folder.summary}
          </div>
        </div>
        <button onClick={() => onDelete("folder", folder.id)} style={{
          background: "none", border: "1px solid #ef444440", color: "#ef4444",
          borderRadius: 6, padding: "3px 9px", fontSize: ".72rem",
          cursor: "pointer", fontFamily: "inherit",
        }}>消す</button>
      </div>

      <div style={{ marginTop: 8, display: "flex", gap: 12 }}>
        <span style={{ fontSize: ".75rem", color: "#5a6070" }}>📂 {dirs.length}フォルダ</span>
        <span style={{ fontSize: ".75rem", color: "#5a6070" }}>📄 {files.length}ファイル</span>
      </div>

      {tree.length > 0 && (
        <>
          <button onClick={() => setOpen(v => !v)} style={{
            background: "none", border: "none", color: "#4a5060",
            fontSize: ".72rem", cursor: "pointer", marginTop: 6, fontFamily: "inherit",
          }}>{open ? "▲ 閉じる" : "▼ ツリーを見る"}</button>
          {open && (
            <div style={{
              marginTop: 4, background: "#0a0c12", borderRadius: 6,
              padding: "8px 10px", maxHeight: 200, overflowY: "auto",
            }}>
              {tree.map((node, i) => {
                const depth = (node.path.match(/\//g) || []).length;
                return (
                  <div key={i} style={{
                    fontSize: ".72rem", color: node.kind === "dir" ? "#06b6d4" : "#7080a0",
                    paddingLeft: depth * 12, lineHeight: 1.7,
                    fontFamily: "monospace",
                  }}>
                    {node.kind === "dir" ? "📂" : "📄"} {node.path.split("/").pop()}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      <div style={{ fontSize: ".68rem", color: "#3a3f50", marginTop: 8, textAlign: "right" }}>
        {folder.created_at?.slice(0, 16).replace("T", " ")}
      </div>
    </div>
  );
};

const Info = ({ icon, v }) => (
  <span style={{ fontSize: ".76rem", color: "#7080a0" }}>
    {icon} {v}
  </span>
);

// ── メイン ────────────────────────────────────
export default function MemoryManager() {
  const [tab, setTab]       = useState("jobs");
  const [jobs, setJobs]     = useState([]);
  const [folders, setFolders] = useState([]);
  const [busy, setBusy]     = useState(false);
  const [fetched, setFetched] = useState(false);
  const [toast, showToast]  = useToast();

  const fetchAll = async () => {
    try {
      const [jr, fr] = await Promise.all([
        fetch(`${API}/jobs`).then(r => r.json()),
        fetch(`${API}/folders`).then(r => r.json()),
      ]);
      setJobs(jr.jobs || []);
      setFolders(fr.folders || []);
      setFetched(true);
    } catch {
      showToast("取得失敗。バックエンドを確認してください。", "err");
    }
  };

  const handleFiles = async files => {
    setBusy(true);
    let jobCount = 0, folderCount = 0, skipCount = 0;

    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      try {
        const res  = await fetch(`${API}/ocr-screenshot`, { method: "POST", body: form });
        const data = await res.json();
        if      (data.type === "job")              jobCount++;
        else if (data.type === "folder_structure") folderCount++;
        else                                       skipCount++;
      } catch {
        showToast(`エラー: ${file.name}`, "err");
      }
    }

    setBusy(false);
    const parts = [];
    if (jobCount)    parts.push(`求人 ${jobCount}件`);
    if (folderCount) parts.push(`フォルダ構成 ${folderCount}件`);
    if (skipCount)   parts.push(`スキップ ${skipCount}件`);
    if (parts.length) {
      showToast(`登録完了: ${parts.join(" / ")}`);
      await fetchAll();
    }
  };

  const handleDelete = async (type, id) => {
    if (!window.confirm("この記憶を完全に消しますか？")) return;
    try {
      await fetch(`${API}/record/${type}/${id}`, { method: "DELETE" });
      if (type === "job")    setJobs(p => p.filter(j => j.id !== id));
      if (type === "folder") setFolders(p => p.filter(f => f.id !== id));
      showToast("記憶を消しました。");
    } catch {
      showToast("削除失敗。", "err");
    }
  };

  const handleDeleteAll = async () => {
    const all = tab === "jobs" ? jobs : folders;
    if (!all.length) return;
    if (!window.confirm(`${tab === "jobs" ? "求人" : "フォルダ構成"}の記憶をすべて消しますか？`)) return;
    for (const r of all) await handleDelete(tab === "jobs" ? "job" : "folder", r.id);
    showToast("すべての記憶を消しました。");
  };

  const list = tab === "jobs" ? jobs : folders;

  return (
    <>
      {/* 🌟 グローバルなCSS破壊を防ぐため、アニメーションのみに限定 */}
      <style>{`
        @keyframes fade { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }
        @keyframes slide { from { opacity:0; transform:translateX(16px); } to { opacity:1; transform:none; } }
      `}</style>

      {/* 🌟 全体の背景色とフォントカラーをコンポーネント内に限定して適用 */}
      <div style={{ background: "#0d0f16", color: "#c8cde0", minHeight: "100%", fontFamily: "'Helvetica Neue', Arial, sans-serif" }}>
        <div style={{ maxWidth: 880, margin: "0 auto", padding: "32px 20px" }}>

          {/* ヘッダー */}
          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: "1.35rem", fontWeight: 800, color: "#e8eaf0" }}>
              🧠 スクリーンショット記憶
            </h1>
            <p style={{ fontSize: ".8rem", color: "#4a5060", marginTop: 4 }}>
              求人・フォルダ構成を自動判別して保存します
            </p>
          </div>

          {/* ドロップゾーン */}
          <DropZone onFiles={handleFiles} busy={busy} />

          {/* コントロール */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "18px 0 14px" }}>
            <button onClick={fetchAll} style={{
              background: "#4f8ef7", color: "#fff", border: "none",
              borderRadius: 7, padding: "7px 16px", fontSize: ".82rem",
              cursor: "pointer", fontFamily: "inherit", fontWeight: 700,
            }}>一覧を更新</button>

            {list.length > 0 && (
              <button onClick={handleDeleteAll} style={{
                background: "none", border: "1px solid #ef444440", color: "#ef4444",
                borderRadius: 7, padding: "7px 14px", fontSize: ".78rem",
                cursor: "pointer", fontFamily: "inherit", marginLeft: "auto",
              }}>全記憶を消す</button>
            )}
          </div>

          {/* タブ */}
          <div style={{ display: "flex", gap: 4, marginBottom: 16,
                        borderBottom: "1px solid #1e2130", paddingBottom: 8 }}>
            <Tab label="求人" count={jobs.length} active={tab === "jobs"}
                 onClick={() => setTab("jobs")} />
            <Tab label="フォルダ構成" count={folders.length} active={tab === "folders"}
                 onClick={() => setTab("folders")} />
          </div>

          {/* 一覧 */}
          {!fetched ? (
            <div style={{ textAlign: "center", color: "#3a3f50", padding: "40px 0", fontSize: ".85rem" }}>
              「一覧を更新」で読み込みます
            </div>
          ) : list.length === 0 ? (
            <div style={{ textAlign: "center", color: "#3a3f50", padding: "40px 0" }}>
              <div style={{ fontSize: "1.8rem", marginBottom: 8 }}>📭</div>
              <div style={{ fontSize: ".82rem" }}>まだ保存された記憶はありません</div>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 14 }}>
              {list.map((item, i) => (
                <div key={item.id} style={{ animation: `fade .25s ease ${i * .04}s both` }}>
                  {tab === "jobs"
                    ? <JobCard job={item} onDelete={handleDelete} />
                    : <FolderCard folder={item} onDelete={handleDelete} />
                  }
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* トースト */}
      {toast && (
        <div style={{
          position: "fixed", bottom: 20, right: 20, zIndex: 9999,
          background: toast.type === "err" ? "#1e0f0f" : "#0d1e18",
          border: `1px solid ${toast.type === "err" ? "#ef444450" : "#10b98150"}`,
          color: toast.type === "err" ? "#ef4444" : "#10b981",
          borderRadius: 9, padding: "10px 16px", fontSize: ".82rem", fontWeight: 600,
          animation: "slide .2s ease", boxShadow: "0 6px 24px rgba(0,0,0,.4)",
        }}>
          {toast.type === "err" ? "⚠️ " : "✓ "}{toast.msg}
        </div>
      )}
    </>
  );
}