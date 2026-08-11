// ProofreadingTestBlock.jsx
import React, { useState, useMemo } from 'react';

/**
 * props (block.props から展開されて渡ってくる):
 *   - mode: "proofreading" | "proofreading_hard" | ...
 *   - label: string
 *   - fields: { key: string, label: string }[]  表示項目と順序(名前/性別/生年月日/住所1/住所2/電話番号/アドレス/備考)
 *   - problems: { left: object, correct: object, error_fields: string[] }[]
 *   - onOptionSelect: (payload) => void  結果をチャットに送り返したいときに使う
 */
export default function ProofreadingTestBlock({ mode, label, fields = [], problems = [], onOptionSelect }) {
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState('idle'); // idle | running | finished
  const [startedAt, setStartedAt] = useState(null);
  const [finishedAt, setFinishedAt] = useState(null);

  const [checkedFields, setCheckedFields] = useState({}); // { fieldKey: boolean } 今の問題分
  const [judgeLog, setJudgeLog] = useState([]); // 問題ごとの正誤詳細

  const currentProblem = problems[index];
  const isLastProblem = index === problems.length - 1;

  const start = () => {
    setStatus('running');
    setStartedAt(Date.now());
    setIndex(0);
    setCheckedFields({});
    setJudgeLog([]);
    setFinishedAt(null);
  };

  const toggleField = (key) => {
    setCheckedFields((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const commitCurrentAnswer = () => {
    if (!currentProblem) return;

    const errorSet = new Set(currentProblem.error_fields);
    let correctJudgements = 0;

    fields.forEach(({ key }) => {
      const userSaysDiff = !!checkedFields[key];
      const actuallyDiff = errorSet.has(key);
      if (userSaysDiff === actuallyDiff) correctJudgements += 1;
    });

    setJudgeLog((prev) => [
      ...prev,
      {
        totalFields: fields.length,
        correctJudgements,
        errorFields: currentProblem.error_fields,
        userCheckedFields: Object.keys(checkedFields).filter((k) => checkedFields[k]),
      },
    ]);

    if (isLastProblem) {
      setStatus('finished');
      setFinishedAt(Date.now());
    } else {
      setIndex((prev) => prev + 1);
      setCheckedFields({});
    }
  };

  const stats = useMemo(() => {
    if (!startedAt || judgeLog.length === 0) return null;

    const endTime = finishedAt || Date.now();
    const elapsedSec = Math.max(0.1, (endTime - startedAt) / 1000);

    const totalFields = judgeLog.reduce((sum, j) => sum + j.totalFields, 0);
    const totalCorrect = judgeLog.reduce((sum, j) => sum + j.correctJudgements, 0);
    const accuracy = totalFields > 0 ? Math.round((totalCorrect / totalFields) * 100) : 100;

    const problemsPerMin = Math.round((judgeLog.length / elapsedSec) * 60 * 10) / 10;
    const secPerProblem = Math.round((elapsedSec / judgeLog.length) * 10) / 10;

    return {
      elapsedSec: Math.round(elapsedSec * 10) / 10,
      accuracy,
      problemsPerMin,
      secPerProblem,
      answered: judgeLog.length,
    };
  }, [startedAt, finishedAt, judgeLog]);

  const sendResultToChat = () => {
    if (!stats || !onOptionSelect) return;
    onOptionSelect({
      type: 'proofreading_result',
      message: `照合結果報告: mode=${mode} 正解率=${stats.accuracy}% 速度=${stats.problemsPerMin}問/分 経過=${stats.elapsedSec}秒`,
    });
  };

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-4 bg-white dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {label || '間違い修正テスト'}
        </div>
        <div className="text-xs text-slate-400">
          {status === 'running' ? `${index + 1} / ${problems.length}` : `${problems.length}問`}
        </div>
      </div>

      {status === 'idle' && (
        <div className="space-y-2">
          <p className="text-xs text-slate-400">
            左側のデータには一部誤りがあります。右側の正しいデータと見比べて、違う項目にチェックを入れてください。
          </p>
          <button
            onClick={start}
            className="px-4 py-2 rounded bg-slate-800 text-white text-sm hover:bg-slate-700"
          >
            開始する
          </button>
        </div>
      )}

      {status === 'running' && currentProblem && (
        <div className="space-y-3">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-xs text-slate-400">
                <th className="text-left font-normal pb-1 w-8"></th>
                <th className="text-left font-normal pb-1">項目</th>
                <th className="text-left font-normal pb-1">チェック対象（左）</th>
                <th className="text-left font-normal pb-1">正データ（右）</th>
              </tr>
            </thead>
            <tbody>
              {fields.map(({ key, label: fieldLabel }) => (
                <tr key={key} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2">
                    <input
                      type="checkbox"
                      checked={!!checkedFields[key]}
                      onChange={() => toggleField(key)}
                    />
                  </td>
                  <td className="py-2 text-slate-500 dark:text-slate-400">{fieldLabel}</td>
                  <td className="py-2 font-mono">{currentProblem.left[key]}</td>
                  <td className="py-2 font-mono text-slate-500 dark:text-slate-400">
                    {currentProblem.correct[key]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <button
            onClick={commitCurrentAnswer}
            className="px-4 py-2 rounded bg-slate-800 text-white text-sm hover:bg-slate-700"
          >
            {isLastProblem ? '回答して終了' : '次の問題へ'}
          </button>
        </div>
      )}

      {status === 'finished' && stats && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="rounded bg-slate-50 dark:bg-slate-800 p-3">
              <div className="text-xl font-bold text-slate-800 dark:text-slate-100">{stats.accuracy}%</div>
              <div className="text-xs text-slate-400">正解率</div>
            </div>
            <div className="rounded bg-slate-50 dark:bg-slate-800 p-3">
              <div className="text-xl font-bold text-slate-800 dark:text-slate-100">{stats.problemsPerMin}</div>
              <div className="text-xs text-slate-400">問/分</div>
            </div>
            <div className="rounded bg-slate-50 dark:bg-slate-800 p-3">
              <div className="text-xl font-bold text-slate-800 dark:text-slate-100">{stats.elapsedSec}s</div>
              <div className="text-xs text-slate-400">所要時間</div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={start}
              className="px-4 py-2 rounded bg-slate-800 text-white text-sm hover:bg-slate-700"
            >
              もう一度
            </button>
            {onOptionSelect && (
              <button
                onClick={sendResultToChat}
                className="px-4 py-2 rounded border border-slate-300 dark:border-slate-600 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                結果をチャットに送る
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}