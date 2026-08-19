// MultipleChoiceBlock.jsx
import React, { useState, useMemo } from 'react';

/**
 * props (block.props から展開されて渡ってくる):
 *   - mode: "addition" | "subtraction" | "multiplication" | "combination" | "same_angle_shape"
 *   - label: string
 *   - kind: "text" | "angle_shape"
 *   - problems:
 *       kind === "text"        -> { question: string, choices: string[], correct_index: number }[]
 *       kind === "angle_shape" -> { reference: {angle,rotation}, choices: {angle,rotation}[], correct_index: number }[]
 *   - onOptionSelect: (payload) => void
 */

function AngleGlyph({ angle, rotation, size = 90, highlight = false }) {
  const cx = size / 2;
  const cy = size / 2;
  const length = size * 0.4;

  const toPoint = (deg) => {
    const rad = (deg * Math.PI) / 180;
    return { x: cx + length * Math.cos(rad), y: cy - length * Math.sin(rad) };
  };

  const p1 = toPoint(rotation);
  const p2 = toPoint(rotation + angle);

  return (
    <svg width={size} height={size} className={highlight ? 'drop-shadow' : ''}>
      <circle cx={cx} cy={cy} r={3} fill="currentColor" className="text-slate-400" />
      <line x1={cx} y1={cy} x2={p1.x} y2={p1.y} stroke="currentColor" strokeWidth={3} className="text-slate-700 dark:text-slate-200" />
      <line x1={cx} y1={cy} x2={p2.x} y2={p2.y} stroke="currentColor" strokeWidth={3} className="text-slate-700 dark:text-slate-200" />
    </svg>
  );
}

export default function MultipleChoiceBlock({ mode, label, kind = 'text', problems = [], onOptionSelect }) {
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState('idle'); // idle | running | finished
  const [startedAt, setStartedAt] = useState(null);
  const [questionStartedAt, setQuestionStartedAt] = useState(null);
  const [finishedAt, setFinishedAt] = useState(null);
  const [selected, setSelected] = useState(null); // 現在の問題で選んだ選択肢index
  const [log, setLog] = useState([]); // { correct: bool, reactionMs: number }

  const currentProblem = problems[index];
  const isLastProblem = index === problems.length - 1;

  const start = () => {
    setStatus('running');
    const now = Date.now();
    setStartedAt(now);
    setQuestionStartedAt(now);
    setIndex(0);
    setSelected(null);
    setLog([]);
    setFinishedAt(null);
  };

  const choose = (choiceIndex) => {
    if (status !== 'running' || selected !== null) return;

    setSelected(choiceIndex);
    const now = Date.now();
    const isCorrect = choiceIndex === currentProblem.correct_index;
    const reactionMs = now - (questionStartedAt || now);

    setLog((prev) => [...prev, { correct: isCorrect, reactionMs }]);

    setTimeout(() => {
      if (isLastProblem) {
        setStatus('finished');
        setFinishedAt(Date.now());
      } else {
        setIndex((prev) => prev + 1);
        setSelected(null);
        setQuestionStartedAt(Date.now());
      }
    }, 500); // 正誤を一瞬見せてから次へ
  };

  const stats = useMemo(() => {
    if (!startedAt || log.length === 0) return null;

    const endTime = finishedAt || Date.now();
    const elapsedSec = Math.max(0.1, (endTime - startedAt) / 1000);

    const correctCount = log.filter((l) => l.correct).length;
    const accuracy = Math.round((correctCount / log.length) * 100);
    const avgReactionSec = Math.round((log.reduce((s, l) => s + l.reactionMs, 0) / log.length / 1000) * 10) / 10;
    const questionsPerMin = Math.round((log.length / elapsedSec) * 60 * 10) / 10;

    return {
      elapsedSec: Math.round(elapsedSec * 10) / 10,
      accuracy,
      avgReactionSec,
      questionsPerMin,
      answered: log.length,
    };
  }, [startedAt, finishedAt, log]);

  const sendResultToChat = () => {
    if (!stats || !onOptionSelect) return;
    onOptionSelect({
      type: 'multiple_choice_result',
      message: `四択結果報告: mode=${mode} 正解率=${stats.accuracy}% 平均反応=${stats.avgReactionSec}秒 速度=${stats.questionsPerMin}問/分`,
    });
  };

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-4 bg-white dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">{label || '四択問題'}</div>
        <div className="text-xs text-slate-400">
          {status === 'running' ? `${index + 1} / ${problems.length}` : `${problems.length}問`}
        </div>
      </div>

      {status === 'idle' && (
        <button onClick={start} className="px-4 py-2 rounded bg-slate-800 text-white text-sm hover:bg-slate-700">
          開始する
        </button>
      )}

      {status === 'running' && currentProblem && kind === 'text' && (
        <div className="space-y-3">
          <div className="font-mono text-lg">{currentProblem.question}</div>
          <div className="grid grid-cols-2 gap-2">
            {currentProblem.choices.map((choice, i) => {
              let style = 'border-slate-300 dark:border-slate-600';
              if (selected !== null) {
                if (i === currentProblem.correct_index) style = 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950';
                else if (i === selected) style = 'border-red-500 bg-red-50 dark:bg-red-950';
              }
              return (
                <button
                  key={i}
                  onClick={() => choose(i)}
                  disabled={selected !== null}
                  className={`px-3 py-2 rounded border text-sm font-mono ${style}`}
                >
                  {choice}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {status === 'running' && currentProblem && kind === 'angle_shape' && (
        <div className="space-y-4">
          <div className="text-xs text-slate-400">この角度と同じ角度の図形を選んでください</div>
          <div className="flex justify-center">
            <div className="text-slate-700 dark:text-slate-200">
              <AngleGlyph angle={currentProblem.reference.angle} rotation={currentProblem.reference.rotation} size={110} highlight />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {currentProblem.choices.map((choice, i) => {
              let style = 'border-slate-300 dark:border-slate-600';
              if (selected !== null) {
                if (i === currentProblem.correct_index) style = 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950';
                else if (i === selected) style = 'border-red-500 bg-red-50 dark:bg-red-950';
              }
              return (
                <button
                  key={i}
                  onClick={() => choose(i)}
                  disabled={selected !== null}
                  className={`flex items-center justify-center py-2 rounded border ${style}`}
                >
                  <AngleGlyph angle={choice.angle} rotation={choice.rotation} size={80} />
                </button>
              );
            })}
          </div>
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
              <div className="text-xl font-bold text-slate-800 dark:text-slate-100">{stats.avgReactionSec}s</div>
              <div className="text-xs text-slate-400">平均反応時間</div>
            </div>
            <div className="rounded bg-slate-50 dark:bg-slate-800 p-3">
              <div className="text-xl font-bold text-slate-800 dark:text-slate-100">{stats.questionsPerMin}</div>
              <div className="text-xs text-slate-400">問/分</div>
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={start} className="px-4 py-2 rounded bg-slate-800 text-white text-sm hover:bg-slate-700">
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