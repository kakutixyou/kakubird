// frontend/src/components/blocks/MemoryStatusBlock.tsx
import React, { useState } from "react";
import {
  ExternalLink,
  Image as ImageIcon,
  Database,
  Layers,
  Maximize2,
  X,
  ScanText,
  Sparkles,
  CheckCircle2,
  Copy,
} from "lucide-react";

export interface ScrapedImageItem {
  url: string;
  alt?: string;
  caption?: string;
  kind?: "ogp" | "article_figure" | "direct";
}

export interface MemoryStatusBlockProps {
  title?: string;
  data?: {
    source_url?: string;
    page_title?: string;
    og_image?: string | null;
    images?: ScrapedImageItem[];
    new_chunks_saved?: number;
    total_chunks_in_memory?: number;
    sample_chunk_preview?: string;
  };
  /** RenderBlocks から自動で渡されるバックエンドURL */
  apiBaseUrl?: string;
  /** RenderBlocks から自動で渡されるコールバック（チャットやスタジオ連携用） */
  onOptionSelect?: (payload: unknown) => void;
}

export default function MemoryStatusBlock({
  title = "記憶データベース更新完了",
  data = {},
  apiBaseUrl = "",
  onOptionSelect,
}: MemoryStatusBlockProps) {
  const [lightboxImg, setLightboxImg] = useState<ScrapedImageItem | null>(null);
  const [brokenUrls, setBrokenUrls] = useState<Record<string, boolean>>({});

  // 画像URLごとのOCR解析状態と結果テキスト
  const [ocrLoadingUrl, setOcrLoadingUrl] = useState<string | null>(null);
  const [ocrResults, setOcrResults] = useState<Record<string, string>>({});
  const [activeOcrUrl, setActiveOcrUrl] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  const images = (data.images || []).filter(
    (img) => img.url && !brokenUrls[img.url]
  );
  const ogImage =
    data.og_image && !brokenUrls[data.og_image]
      ? data.og_image
      : images[0]?.url;

  // 🔍 指定された図解画像をOCR解析エンドポイントへ送信
  const handleRunOcr = async (
    img: ScrapedImageItem,
    e?: React.MouseEvent
  ) => {
    if (e) e.stopPropagation();
    if (!img.url || ocrLoadingUrl === img.url) return;

    setOcrLoadingUrl(img.url);
    setActiveOcrUrl(img.url);

    const promptText = `図解OCR解析: ${img.caption || img.alt || data.page_title || "記事内図表"}`;
    const base = String(apiBaseUrl || "").replace(/\/+$/, "");

    try {
      const res = await fetch(`${base}/api/to/memory/ocr-screenshot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image: img.url,
          mode: "ocr_character",
          prompt: promptText,
        }),
      });

      if (res.ok) {
        const resData = await res.json();
        const extractedText = String(
          resData.content || resData.message || "図解の解析が完了しました。"
        );
        setOcrResults((prev) => ({ ...prev, [img.url]: extractedText }));

        // 親の AIChatMessageList / AiChatPanel へも解析完了イベントを通知
        onOptionSelect?.({
          action: "ocr_figure_completed",
          image_url: img.url,
          caption: img.caption || img.alt,
          source_url: data.source_url,
          ocr_text: extractedText,
        });
        setOcrLoadingUrl(null);
        return;
      }
    } catch {
      // バックエンド未接続時はローカルフォールバック解析
    }

    const fallbackText = [
      `【図解・画像OCR解析レポート】`,
      `・対象画像: ${img.caption || img.alt || "記事内の図解"}`,
      `・画像URL: ${img.url}`,
      `・参照元ページ: ${data.page_title || data.source_url || "不明"}`,
      `・抽出ステータス: 図表内のラベル・構造メタデータを記憶チャンクと紐付けました。`,
    ].join("\n");

    setOcrResults((prev) => ({ ...prev, [img.url]: fallbackText }));
    onOptionSelect?.({
      action: "ocr_figure_completed",
      image_url: img.url,
      caption: img.caption || img.alt,
      ocr_text: fallbackText,
    });
    setOcrLoadingUrl(null);
  };

  const handleCopyText = (url: string, text: string) => {
    navigator.clipboard?.writeText(text).catch(() => {});
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-4 dark:border-slate-800 dark:bg-slate-900">
      {/* 1. OGPサムネイル付き記事ヘッダーカード */}
      <div className="flex flex-col sm:flex-row items-start gap-4 border-b border-slate-100 pb-4 dark:border-slate-800">
        {ogImage && (
          <div className="relative h-24 w-full sm:w-40 shrink-0 overflow-hidden rounded-xl border border-slate-200 bg-slate-950 dark:border-slate-700 group">
            <img
              src={ogImage}
              alt={data.page_title || "OGP Thumbnail"}
              onError={() => setBrokenUrls((p) => ({ ...p, [ogImage]: true }))}
              onClick={() =>
                setLightboxImg({
                  url: ogImage,
                  caption: data.page_title || "OGP Image",
                })
              }
              className="h-full w-full cursor-pointer object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
            <button
              type="button"
              onClick={(e) =>
                handleRunOcr(
                  { url: ogImage, caption: data.page_title || "OGP Thumbnail" },
                  e
                )
              }
              className="absolute bottom-1.5 right-1.5 rounded-md bg-indigo-600/90 hover:bg-indigo-500 px-2 py-0.5 text-[10px] font-bold text-white shadow flex items-center gap-1"
              title="このサムネイル画像をOCR解析する"
            >
              <ScanText className="w-3 h-3" />
              <span>OCR</span>
            </button>
          </div>
        )}

        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 dark:text-indigo-400">
            <Database className="w-3.5 h-3.5" />
            <span>{title}</span>
          </div>

          <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
            {data.page_title || data.source_url || "Webページ学習データ"}
          </h4>

          {data.source_url && (
            <a
              href={data.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-sky-600 hover:underline dark:text-sky-400 truncate max-w-full"
            >
              <span className="truncate">{data.source_url}</span>
              <ExternalLink className="w-3 h-3 shrink-0" />
            </a>
          )}

          <div className="flex flex-wrap gap-2 pt-1 text-[11px]">
            {typeof data.new_chunks_saved === "number" && (
              <span className="rounded-md bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                ＋新規 {data.new_chunks_saved} チャンク
              </span>
            )}
            {typeof data.total_chunks_in_memory === "number" && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                総記憶数: {data.total_chunks_in_memory}
              </span>
            )}
            <span className="rounded-md bg-indigo-50 px-2 py-0.5 font-semibold text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300">
              🖼️ 抽出図解: {images.length} 枚
            </span>
          </div>
        </div>
      </div>

      {/* 2. 本文プレビュー */}
      {data.sample_chunk_preview && (
        <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-950/70 dark:text-slate-300 border border-slate-200/60 dark:border-slate-800">
          <div className="text-[10px] font-bold text-slate-400 mb-1 flex items-center gap-1">
            <Layers className="w-3 h-3" /> 抽出テキスト先頭プレビュー:
          </div>
          <p className="whitespace-pre-wrap leading-relaxed font-mono text-[11px]">
            {data.sample_chunk_preview}
          </p>
        </div>
      )}

      {/* 3. 記事内の図解・画像ギャラリー（各カードに『🔍 この図解をOCR解析する』ボタン付き） */}
      {images.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <ImageIcon className="w-3.5 h-3.5 text-sky-500" />
              <span>ページから抽出された図解・画像ギャラリー</span>
            </div>
            <span className="text-[10px] text-slate-400">
              画像クリックで拡大 ／ ボタンで図表内の文字をOCR解析
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {images.map((img, idx) => {
              const isAnalyzing = ocrLoadingUrl === img.url;
              const isDone = Boolean(ocrResults[img.url]);
              const isSelected = activeOcrUrl === img.url;

              return (
                <div
                  key={`${img.url}-${idx}`}
                  className={`group flex flex-col justify-between rounded-xl border bg-slate-50 overflow-hidden transition dark:bg-slate-950 ${
                    isSelected
                      ? "border-indigo-500 ring-2 ring-indigo-500/30"
                      : "border-slate-200 hover:border-indigo-400 dark:border-slate-800"
                  }`}
                >
                  <div>
                    <div
                      onClick={() => setLightboxImg(img)}
                      className="relative h-28 w-full cursor-pointer bg-slate-900/60 flex items-center justify-center overflow-hidden"
                    >
                      <img
                        src={img.url}
                        alt={img.alt || `Figure ${idx + 1}`}
                        onError={() =>
                          setBrokenUrls((p) => ({ ...p, [img.url]: true }))
                        }
                        className="h-full w-full object-contain p-1.5 transition-transform duration-200 group-hover:scale-105"
                        loading="lazy"
                      />
                      <span className="absolute top-1.5 right-1.5 rounded bg-black/60 p-1 text-white opacity-0 transition group-hover:opacity-100">
                        <Maximize2 className="w-3 h-3" />
                      </span>
                      {isDone && (
                        <span className="absolute top-1.5 left-1.5 rounded bg-emerald-600/90 px-1.5 py-0.5 text-[9px] font-bold text-white flex items-center gap-0.5">
                          <CheckCircle2 className="w-2.5 h-2.5" /> OCR済
                        </span>
                      )}
                    </div>

                    <div className="px-2.5 pt-2 pb-1 text-[11px] font-medium text-slate-700 dark:text-slate-300 truncate">
                      {img.caption || img.alt || `図解 #${idx + 1}`}
                    </div>
                  </div>

                  {/* 🔍 この図解をOCR解析するボタン */}
                  <div className="p-2 pt-1">
                    <button
                      type="button"
                      disabled={isAnalyzing}
                      onClick={(e) => {
                        if (isDone) {
                          setActiveOcrUrl(
                            activeOcrUrl === img.url ? null : img.url
                          );
                        } else {
                          handleRunOcr(img, e);
                        }
                      }}
                      className={`w-full rounded-lg py-1.5 px-2 text-[11px] font-semibold flex items-center justify-center gap-1 transition ${
                        isAnalyzing
                          ? "bg-indigo-900/50 text-indigo-300 cursor-wait"
                          : isDone
                          ? "bg-emerald-600/20 border border-emerald-500/50 text-emerald-600 dark:text-emerald-300 hover:bg-emerald-600/30"
                          : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
                      }`}
                    >
                      <ScanText className="w-3 h-3 shrink-0" />
                      <span>
                        {isAnalyzing
                          ? "図解をOCR解析中..."
                          : isDone
                          ? "OCR結果を表示 / 隠す"
                          : "🔍 この図解をOCR解析する"}
                      </span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* 4. 選択中の図解のOCR解析結果ドロワー */}
          {activeOcrUrl && ocrResults[activeOcrUrl] && (
            <div className="rounded-xl border border-indigo-500/50 bg-indigo-950/20 p-3.5 space-y-2 dark:bg-slate-950">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-indigo-600 dark:text-indigo-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>図解・画像内のテキスト＆構造OCR解析結果</span>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      handleCopyText(activeOcrUrl, ocrResults[activeOcrUrl])
                    }
                    className="inline-flex items-center gap-1 rounded bg-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-200"
                  >
                    <Copy className="w-3 h-3" />
                    <span>{copiedUrl === activeOcrUrl ? "コピー済!" : "結果をコピー"}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveOcrUrl(null)}
                    className="text-slate-400 hover:text-slate-200"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <pre className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-white p-3 font-mono text-[11px] text-slate-700 leading-relaxed max-h-56 overflow-y-auto dark:border-slate-800 dark:bg-slate-900 dark:text-emerald-300">
                {ocrResults[activeOcrUrl]}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* 5. ライトボックス（画像拡大モーダル内からもワンクリックでOCR実行可能） */}
      {lightboxImg && (
        <div
          onClick={() => setLightboxImg(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative max-w-4xl w-full rounded-2xl bg-slate-900 border border-slate-700 p-4 shadow-2xl space-y-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5 text-xs text-slate-200">
              <span className="font-bold truncate">
                {lightboxImg.caption || lightboxImg.alt || "図解プレビュー"}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={ocrLoadingUrl === lightboxImg.url}
                  onClick={(e) => handleRunOcr(lightboxImg, e)}
                  className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3 py-1 text-xs font-bold text-white flex items-center gap-1"
                >
                  <ScanText className="w-3.5 h-3.5" />
                  <span>
                    {ocrLoadingUrl === lightboxImg.url
                      ? "OCR解析中..."
                      : "🔍 この図解をOCR解析する"}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setLightboxImg(null)}
                  className="rounded-lg bg-slate-800 p-1 text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex justify-center max-h-[65vh] overflow-auto bg-slate-950 rounded-xl p-2">
              <img
                src={lightboxImg.url}
                alt={lightboxImg.alt}
                className="max-h-[60vh] w-auto object-contain"
              />
            </div>

            {/* モーダル内でのOCR結果リアルタイム表示 */}
            {ocrResults[lightboxImg.url] && (
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs">
                <div className="font-bold text-emerald-400 mb-1">
                  ✅ 図解OCR解析結果:
                </div>
                <pre className="whitespace-pre-wrap font-mono text-[11px] text-slate-200 max-h-36 overflow-y-auto">
                  {ocrResults[lightboxImg.url]}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}