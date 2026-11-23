// frontend/src/components/blocks/RecruitReportBlock.jsx
import React, { useState } from 'react';

export default function RecruitReportBlock({ block, onAppendData }) {
  // 追加情報の入力状態管理
  const [additionalText, setAdditionalText] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);

  const data = block?.props?.data;

  // 完全にデータがない場合は初期ローディング
  if (!data) {
    return (
      <div className="animate-pulse p-6 bg-slate-100 rounded-xl border border-slate-200">
        <div className="h-6 bg-slate-300 rounded w-1/3 mb-4"></div>
        <div className="h-4 bg-slate-300 rounded w-1/2 mb-2"></div>
        <div className="h-4 bg-slate-300 rounded w-2/3"></div>
      </div>
    );
  }

  const {
    company = {},
    offer_summary = {},
    recruitment_text_analysis = {},
    ai_analysis = {}
  } = data;

  // 総合評価ラベルのデザイン判定
  const getLabelStyle = (label) => {
    switch (label) {
      case 'white': return { text: '✨ 優良求人の可能性大', classes: 'bg-emerald-100 text-emerald-700' };
      case 'gray_to_white': return { text: '👍 比較的安全・要確認', classes: 'bg-blue-100 text-blue-700' };
      case 'gray': return { text: '⚠️ 注意・要警戒', classes: 'bg-yellow-100 text-yellow-700' };
      case 'gray_to_black': return { text: '🚨 かなり危険', classes: 'bg-orange-100 text-orange-700' };
      case 'black': return { text: '☠️ ブラック・SESリスク大', classes: 'bg-red-100 text-red-700' };
      default: return { text: '🔍 情報不足・解析中', classes: 'bg-slate-100 text-slate-700' };
    }
  };

  const labelStyle = getLabelStyle(ai_analysis.overall_label);
  const formatMoney = (amount) => amount ? `${amount / 10000}万円` : '不明';

  const ScoreBar = ({ label, score, colorClass }) => (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="font-mono text-slate-500">{score != null ? score : '--'}/100</span>
      </div>
      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
        <div 
          className={`h-2 rounded-full transition-all duration-1000 ${colorClass} ${score == null ? 'w-0' : ''}`} 
          style={{ width: `${Math.min(Math.max(score || 0, 0), 100)}%` }}
        ></div>
      </div>
    </div>
  );

  // 追加情報送信ハンドラ
  const handleAppendSubmit = async () => {
    if (!additionalText.trim()) return;
    setIsUpdating(true);
    
    // 親コンポーネント(ChatUIなど)に送信処理を委譲
    if (onAppendData) {
      await onAppendData(additionalText);
    }
    
    setAdditionalText('');
    setIsUpdating(false);
  };

  return (
    <div className={`w-full font-sans bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm transition-opacity ${isUpdating ? 'opacity-60' : 'opacity-100'}`}>
      
      {/* 1. ヘッダー部 */}
      <div className="p-5 border-b border-slate-100 bg-slate-50/50">
        <div className="flex justify-between items-start gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800">
              {company.name || '企業名解析中...'}
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {company.industry || '業種不明'} | {company.location || '勤務地不明'}
            </p>
          </div>
          <div className={`px-3 py-1.5 rounded-lg border text-sm font-bold shadow-sm ${labelStyle.classes}`}>
            {isUpdating ? '🔄 更新中...' : labelStyle.text}
          </div>
        </div>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 左カラム */}
        <div className="space-y-6">
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 border-b pb-2">💰 条件サマリー</h3>
            <ul className="text-sm space-y-2 text-slate-600">
              <li><span className="font-medium mr-2">給与目安:</span> 
                {formatMoney(offer_summary.salary_range?.min)} 
                {offer_summary.salary_range?.max ? ` 〜 ${formatMoney(offer_summary.salary_range.max)}` : ' 〜上限不明'}
              </li>
              <li><span className="font-medium mr-2">残業目安:</span> 月 {offer_summary.work_style?.average_overtime_hours ?? '?'} 時間</li>
              <li><span className="font-medium mr-2">リモート:</span> {offer_summary.work_style?.remote_possible ? '🟢 可能' : '🔴 記載なし/不可'}</li>
            </ul>
          </div>

          {/* 🌟 新規追加: 求められるスキル */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 border-b pb-2">🛠 求められるスキル</h3>
            <div className="flex flex-wrap gap-2">
              {offer_summary.required_skills?.length > 0 ? (
                offer_summary.required_skills.map((skill, i) => (
                  <span key={i} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded border border-blue-100">
                    {skill}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-400">記載が見つかりません</span>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 border-b pb-2">🧠 AI分析コメント</h3>
            <ul className="text-sm space-y-2 text-slate-600 list-disc list-inside">
              {ai_analysis.analysis_comment?.length > 0 
                ? ai_analysis.analysis_comment.map((c, i) => <li key={i}>{c}</li>)
                : <li className="text-slate-400">分析データが不足しています</li>}
            </ul>
          </div>
        </div>

        {/* 右カラム */}
        <div className="space-y-6">
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 border-b pb-2">📊 テキスト解析スコア</h3>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-3">
              <ScoreBar label="ワークライフバランス" score={recruitment_text_analysis.work_life_balance_score} colorClass="bg-blue-500" />
              <ScoreBar label="技術成長環境" score={recruitment_text_analysis.technical_growth_score} colorClass="bg-emerald-500" />
              <ScoreBar label="成長圧力（プレッシャー）" score={recruitment_text_analysis.growth_pressure_score} colorClass="bg-orange-500" />
              <ScoreBar label="SES・客先常駐リスク" score={recruitment_text_analysis.ses_risk_score} colorClass="bg-red-500" />
              <ScoreBar label="抽象表現（ごまかし）" score={recruitment_text_analysis.abstract_expression_score} colorClass="bg-purple-500" />
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 border-b pb-2">🏷️ 検知キーワード</h3>
            <div className="flex flex-wrap gap-2">
              {recruitment_text_analysis.detected_patterns?.map((pattern, i) => (
                <span key={i} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded border flex items-center gap-1">
                  {pattern.word} <span className="text-[10px] text-slate-400">{pattern.count}回</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 🌟 追加入力UI (パターンAの要) */}
      <div className="p-5 border-t border-slate-100 bg-indigo-50/30">
        <h3 className="text-sm font-bold text-indigo-800 mb-2">🔍 情報を追加して分析を深める</h3>
        <p className="text-xs text-indigo-600/70 mb-3">
          企業の採用ページのURL、募集要項の詳細、またはネットの口コミなどを貼り付けると、AIが上記のJSONスコアを更新します。
        </p>
        <div className="flex gap-2">
          <textarea
            className="w-full h-10 min-h-[40px] max-h-[120px] p-2 text-sm border border-indigo-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
            placeholder="ここにテキストやURLをペースト..."
            value={additionalText}
            onChange={(e) => setAdditionalText(e.target.value)}
            disabled={isUpdating}
          />
          <button
            onClick={handleAppendSubmit}
            disabled={!additionalText.trim() || isUpdating}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors shrink-0"
          >
            {isUpdating ? '分析中...' : '追加分析'}
          </button>
        </div>
      </div>

    </div>
  );
}