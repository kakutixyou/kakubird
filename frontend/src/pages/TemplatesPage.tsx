// frontend/src/pages/TemplatesPage.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBuilderStore } from '../store/builderStore';
import { generateHtmlString, printAndPdfHtml } from '../utils/exportHtml';

const genId = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

// プレセットテンプレート（初期値）
const INITIAL_TEMPLATES = [
  {
    id: 'tpl-1',
    title: 'ランディングページ',
    description: 'Heroエリアと仕切り、テキストで構成された王道のLP構成です。',
    components: [
      { type: 'hero', props: { title: 'Project "To" v1.0へようこそ', subtitle: '直感的な操作でサイトを構築', ctaText: '始める', bgColor: '#1d4ed8' } },
      { type: 'divider', props: { style: 'solid', color: '#e5e7eb' } },
      { type: 'text', props: { content: 'ここに特徴やアピールポイントを書きます。', align: 'center' } }
    ]
  },
  {
    id: 'tpl-2',
    title: 'お問い合わせフォーム',
    description: '標準的なお問い合わせ用のヘッダーとフォーム入力の構成です。',
    components: [
      { type: 'header', props: { text: 'お問い合わせ', level: 'h1', align: 'center' } },
      { type: 'form', props: { fields: [{ label: 'お名前', type: 'text' }, { label: 'メール', type: 'email' }], submitLabel: '送信する' } }
    ]
  }
];

export default function TemplatesPage() {
  const navigate = useNavigate();
  const { pages, setPages, setCurrentPage, setComponents } = useBuilderStore();

  // 🛠 開発用エディタ（コントロールパネル）用のステート
  const [selectedPreset, setSelectedPreset] = useState(INITIAL_TEMPLATES[0]);
  const [jsonInput, setJsonInput] = useState(JSON.stringify(INITIAL_TEMPLATES[0].components, null, 2));
  const [customTitle, setCustomTitle] = useState(INITIAL_TEMPLATES[0].title);
  const [jsonError, setJsonError] = useState<string | null>(null);

  // プリセット切り替え時の処理
  const handlePresetChange = (presetId: string) => {
    const target = INITIAL_TEMPLATES.find(t => t.id === presetId);
    if (target) {
      setSelectedPreset(target);
      setCustomTitle(target.title);
      setJsonInput(JSON.stringify(target.components, null, 2));
      setJsonError(null);
    }
  };

  // JSONのバリデーションをかけつつ、データをストアに流し込んでビルダーへ進む共通ロジック
  const launchBuilder = (title: string, rawComponentsJson: any[]) => {
    const newPageId = genId();
    
    const newPage = {
      id: newPageId,
      title: `${title} (新規)`,
      path: `/page-${newPageId.slice(0, 4)}`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const initialComponents = rawComponentsJson.map((c, index) => ({
      id: genId(),
      page_id: newPageId,
      type: c.type,
      order_index: index,
      props: c.props || {},
      styles: c.styles || {},
    }));

    setPages([...pages, newPage as any]);
    setCurrentPage(newPage as any);
    setComponents(initialComponents);

    // 🚀 ビルダー画面へ遷移
    navigate(`/builder/${newPageId}`);
  };

  // 🛠 ツールエディタ：JSONから直接ビルダーを起動
  const handleLaunchWithJson = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      if (!Array.isArray(parsed)) {
        throw new Error('ルート要素はコンポーネントの配列（ [ ... ] ）である必要があります。');
      }
      setJsonError(null);
      launchBuilder(customTitle, parsed);
    } catch (err: any) {
      setJsonError(err.message || 'JSONのパースに失敗しました。カンマや括弧を確認してください。');
    }
  };

  // 🛠 ツールエディタ：その場でPDF/印刷プレビューを走らせる
  const handleDirectPdfTest = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      if (!Array.isArray(parsed)) {
        throw new Error('コンポーネント配列ではありません。');
      }
      setJsonError(null);
      // utilsの印刷エンジンを直接キック
      printAndPdfHtml(parsed);
    } catch (err: any) {
      setJsonError(`PDFテスト失敗: ${err.message}`);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8 text-gray-800">
      
      {/* 上部ヘッダー */}
      <div className="flex justify-between items-center border-b pb-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">テンプレート ＆ テストスタジオ 🎨</h1>
          <p className="text-sm text-gray-500 mt-1">ビルダーへ流し込むモデルの変更、およびPDF機能のフロントエンド単体テストが行えます。</p>
        </div>
        {/* <button 
          onClick={() => navigate('/builder')} 
          className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm transition font-medium"
        >
          キャンバスへ直接行く 🏗
        </button> */}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* =========================================================
            左側・中央：標準テンプレートカード + 他のHTML（ダミー）への遷移
           ========================================================= */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2">プリセットから選ぶ</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {INITIAL_TEMPLATES.map((tpl) => (
              <div key={tpl.id} className="border border-gray-200 rounded-xl p-5 bg-white shadow-sm flex flex-col justify-between">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">{tpl.title}</h3>
                  <p className="text-sm text-gray-500 mt-2 min-h-[40px]">{tpl.description}</p>
                </div>
                <div className="mt-5 space-y-2">
                  <button 
                    onClick={() => launchBuilder(tpl.title, tpl.components)}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg text-sm font-semibold transition"
                  >
                    この構成でビルダーを起動 🚀
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* 🔗 他のHTML構造/シミュレーションページへの遷移セクション */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 mt-6">
            <h3 className="font-bold text-lg text-gray-900">他のHTML・モック環境への遷移</h3>
            <p className="text-xs text-gray-500 mt-1">BookCMSなどのVanilla JS型モックや、データベース、API設定などの他モジュール画面にルーティングを切り替えます。</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
              <button onClick={() => navigate('/databases')} className="p-3 bg-white border rounded-lg text-xs font-medium hover:bg-gray-100 text-center transition">
                🗄️ 生成済みDB管理
              </button>
              <button onClick={() => navigate('/settings-api')} className="p-3 bg-white border rounded-lg text-xs font-medium hover:bg-gray-100 text-center transition">
                🔌 API外部連携設定
              </button>
              <button onClick={() => navigate('/memory')} className="p-3 bg-white border rounded-lg text-xs font-medium hover:bg-gray-100 text-center transition">
                🧠 AIメモリー空間
              </button>
            </div>
          </div>
        </div>

        {/* =========================================================
            右側：モデル変更 ＆ PDF直接テスト用ツールエディタ
           ========================================================= */}
        <div className="bg-gray-900 text-gray-100 p-5 rounded-2xl shadow-xl space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="border-b border-gray-800 pb-2">
              <h2 className="text-lg font-bold text-blue-400 flex items-center gap-1">🛠 開発ツールエディタ</h2>
              <p className="text-xs text-gray-400">流し込むJSONモデルをリアルタイムに書き換えます。</p>
            </div>

            {/* プリセットのクイックインポート */}
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">モデルの土台を選択</label>
              <select 
                value={selectedPreset.id} 
                onChange={(e) => handlePresetChange(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                {INITIAL_TEMPLATES.map(t => (
                  <option key={t.id} value={t.id}>{t.title}</option>
                ))}
              </select>
            </div>

            {/* タイトルカスタム */}
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">ページタイトル</label>
              <input 
                type="text" 
                value={customTitle} 
                onChange={(e) => setCustomTitle(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* JSONコードエディタ領域 */}
            <div className="flex-1 flex flex-col">
              <label className="block text-xs font-semibold text-gray-400 mb-1">HTMLコンポーネントの構造 (JSON型)</label>
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                rows={12}
                className="w-full bg-black text-green-400 font-mono text-xs p-3 rounded border border-gray-800 focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                placeholder='[ { "type": "hero", "props": { ... } } ]'
              />
              {jsonError && (
                <div className="bg-red-950 border border-red-800 text-red-400 p-2 rounded text-[11px] mt-2 whitespace-pre-wrap">
                  ⚠️ {jsonError}
                </div>
              )}
            </div>
          </div>

          {/* テスト実行ボタン群 */}
          <div className="pt-4 border-t border-gray-800 space-y-2">
            <button
              onClick={handleLaunchWithJson}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white py-2.5 rounded-lg text-sm font-bold shadow-md transition"
            >
              このカスタムJSONでビルダー起動 🏗
            </button>
            
            <button
              onClick={handleDirectPdfTest}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-lg text-sm font-semibold transition flex items-center justify-center gap-1"
              title="ビルダーを挟まず、その場でPDF化/印刷ダイアログの挙動を検証"
            >
              直で印刷 / PDF出力をテスト 🖨
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}