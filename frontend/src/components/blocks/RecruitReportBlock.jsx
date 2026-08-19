// frontend/src/components/blocks/RecruitReportBlock.jsx
import React from 'react';

export default function RecruitReportBlock({ block }) {
  // 司令塔(AI)から渡されたJSONデータを安全に取り出す
  const data = block?.props?.data;

  if (!data) {
    return (
      <div className="p-4 text-sm text-slate-500 bg-slate-100 rounded-xl dark:bg-slate-800 dark:text-slate-400">
        分析データの読み込みに失敗しました。
      </div>
    );
  }

  // 安全なデータ参照のための分割代入
  const {
    company = {},
    offer_summary = {},
    company_culture = {},
    recruitment_text_analysis = {},
    ai_analysis = {}
  } = data;

  // 総合評価ラベルのデザイン判定
  const getLabelStyle = (label) => {
    switch (label) {
      case 'white':
        return { text: '✨ 優良求人の可能性大', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200' };
      case 'gray_to_white':
        return { text: '👍 比較的安全・要確認', classes: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200' };
      case 'gray':
        return { text: ' 注意・要警戒', classes: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-200' };
      case 'black':
        return { text: '🚨 ブラック・SESリスク大', classes: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border-red-200' };
      default:
        return { text: '🔍 解析中/不明', classes: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400 border-slate-200' };
    }
  };

  const labelStyle = getLabelStyle(ai_analysis.overall_label);

  // 金額フォーマット関数 (例: 4500000 -> 450万円)
  const formatMoney = (amount) => {
    if (!amount) return '不明';
    return `${amount / 10000}万円`;
  };

  // スコアバー描画用コンポーネント
  const ScoreBar = ({ label, score, colorClass }) => (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-slate-600 dark:text-slate-300">{label}</span>
        <span className="font-mono text-slate-500">{score || 0}/100</span>
      </div>
      <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
        <div 
          className={`h-2 rounded-full ${colorClass}`} 
          style={{ width: `${Math.min(Math.max(score || 0, 0), 100)}%` }}
        ></div>
      </div>
    </div>
  );

  return (
    <div className="w-full font-sans bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden shadow-sm">
      
      {/* 
          ヘッダー部: 企業名と総合判定
       */}
      <div className="p-5 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
        <div className="flex justify-between items-start gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
              {company.name || '不明な企業'}
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {company.industry || '業種不明'} | {company.location || '勤務地不明'}
            </p>
          </div>
          <div className={`px-3 py-1.5 rounded-lg border text-sm font-bold shadow-sm ${labelStyle.classes}`}>
            {labelStyle.text}
          </div>
        </div>
        
        {offer_summary.headline && (
          <div className="mt-4 p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
            <p className="text-sm font-bold text-indigo-700 dark:text-indigo-400">
              「 {offer_summary.headline} 」
            </p>
          </div>
        )}
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* 
            左カラム: 基本情報 & AIの評価
         */}
        <div className="space-y-6">
          
          {/* 基本情報 */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 pb-2">
              💰 条件サマリー
            </h3>
            <ul className="text-sm space-y-2 text-slate-600 dark:text-slate-400">
              <li><span className="font-medium mr-2">給与目安:</span> 
                {formatMoney(offer_summary.salary_range?.min)} 
                {offer_summary.salary_range?.max ? ` 〜 ${formatMoney(offer_summary.salary_range.max)}` : ' 〜上限不明'}
              </li>
              <li><span className="font-medium mr-2">残業目安:</span> 月 {offer_summary.work_style?.average_overtime_hours || '?'} 時間</li>
              <li><span className="font-medium mr-2">リモート:</span> {offer_summary.work_style?.remote_possible ? '🟢 可能' : '🔴 不可・不明'}</li>
              <li><span className="font-medium mr-2">案件選択:</span> {offer_summary.work_style?.project_selection ? '🟢 実績あり' : '🔴 記載なし（会社主導の可能性）'}</li>
            </ul>
          </div>

          {/* AIのコメント */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 pb-2">
              🧠 AI分析コメント
            </h3>
            <ul className="text-sm space-y-2 text-slate-600 dark:text-slate-400 list-disc list-inside">
              {ai_analysis.analysis_comment?.map((comment, i) => (
                <li key={i}>{comment}</li>
              ))}
            </ul>
          </div>

          {/* 面談での推奨質問 */}
          <div className="space-y-3 bg-amber-50 dark:bg-amber-900/20 p-4 rounded-xl border border-amber-200 dark:border-amber-800/50">
            <h3 className="text-sm font-bold text-amber-800 dark:text-amber-400 mb-2">
              🎯 面談で確認すべき質問
            </h3>
            <ul className="text-sm space-y-1 text-amber-700 dark:text-amber-500 list-none">
              {ai_analysis.recommendation?.map((rec, i) => (
                <li key={i} className="flex gap-2">
                  <span>☑️</span> <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>

        </div>

        {/* 
            右カラム: スコアリング & パターン
         */}
        <div className="space-y-6">
          
          {/* スコアリング（プログレスバー） */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 pb-2">
              📊 テキスト解析スコア
            </h3>
            <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50 space-y-3">
              <ScoreBar label="ワークライフバランス" score={recruitment_text_analysis.work_life_balance_score} colorClass="bg-blue-500" />
              <ScoreBar label="技術成長環境" score={recruitment_text_analysis.technical_growth_score} colorClass="bg-emerald-500" />
              <ScoreBar label="成長圧力（プレッシャー）" score={recruitment_text_analysis.growth_pressure_score} colorClass="bg-orange-500" />
              <ScoreBar label="SES・客先常駐リスク" score={recruitment_text_analysis.ses_risk_score} colorClass="bg-red-500" />
              <ScoreBar label="抽象的表現の多さ（ごまかし）" score={recruitment_text_analysis.abstract_expression_score} colorClass="bg-purple-500" />
            </div>
          </div>

          {/* 検出キーワードタグ */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 pb-2">
              🏷️ 頻出・警戒キーワード
            </h3>
            <div className="flex flex-wrap gap-2">
              {recruitment_text_analysis.detected_patterns?.map((pattern, i) => (
                <span 
                  key={i} 
                  className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-xs rounded-md border border-slate-200 dark:border-slate-700 flex items-center gap-1"
                >
                  {pattern.word} 
                  <span className="text-[10px] bg-slate-200 dark:bg-slate-700 px-1 rounded text-slate-500">
                    {pattern.count}回
                  </span>
                </span>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}