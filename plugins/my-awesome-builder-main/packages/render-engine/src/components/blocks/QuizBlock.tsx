/**
 * QuizBlock.tsx
 *
 * Interactive quiz block with three modes:
 *  - choice:        Multiple-choice question — user selects one answer
 *  - flashcard:     Front/back flip card for self-study
 *  - instant-check: Fill-in-the-blank with immediate correctness feedback
 */

'use client';

import React, { useState, useId } from 'react';
// import type { BlockProps } from '../../config/theme-definitions';
export interface BlockProps {
  animationLevel?: 'none' | 'low' | 'medium' | 'high';
  className?: string;
}
// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type QuizVariant = 'choice' | 'flashcard' | 'instant-check';

export interface QuizOption {
  id: string;
  label: string;
  /** Whether this option is the correct answer */
  correct?: boolean;
}

export interface QuizQuestion {
  /** Question prompt */
  question: string;
  /** Used in choice and instant-check variants */
  options?: QuizOption[];
  /** Answer shown on flashcard back or after instant-check */
  answer?: string;
  /** Optional explanation shown after answering */
  explanation?: string;
  /** Fill-in-the-blank template: use {{blank}} to mark the gap */
  template?: string;
}

export interface QuizContent {
  /** Block heading */
  heading?: string;
  questions: QuizQuestion[];
}

export interface QuizBlockProps extends Omit<BlockProps, 'content' | 'variant'> {
  variant: QuizVariant;
  content: QuizContent;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function animEntrance(level: BlockProps['animationLevel']): string {
  return level === 'none' ? '' : 'animate-entrance';
}
function animScaleIn(level: BlockProps['animationLevel']): string {
  return level === 'none' ? '' : 'animate-scale-in';
}

// ─────────────────────────────────────────────────────────────────────────────
// Variant: choice
// ─────────────────────────────────────────────────────────────────────────────

const ChoiceQuiz: React.FC<{
  question: QuizQuestion;
  index: number;
  animationLevel: BlockProps['animationLevel'];
}> = ({ question, index, animationLevel }) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const id = useId();

  const handleSelect = (optionId: string) => {
    if (!submitted) setSelected(optionId);
  };

  const handleSubmit = () => {
    if (selected) setSubmitted(true);
  };

  const handleReset = () => {
    setSelected(null);
    setSubmitted(false);
  };

  const isCorrect = submitted && question.options?.find((o) => o.id === selected)?.correct;

  return (
    <div className={`card mb-6 ${animEntrance(animationLevel)}`} aria-label={`Question ${index + 1}`}>
      <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--color-text-muted)' }}>
        Question {index + 1}
      </p>
      <p className="text-lg font-semibold mb-5" style={{ color: 'var(--color-text)' }}
         id={`${id}-question`}>
        {question.question}
      </p>

      <ul role="radiogroup" aria-labelledby={`${id}-question`} className="space-y-3">
        {question.options?.map((opt) => {
          let stateClass = '';
          if (submitted) {
            if (opt.correct) stateClass = 'correct';
            else if (opt.id === selected) stateClass = 'incorrect';
          } else if (opt.id === selected) {
            stateClass = 'selected';
          }

          return (
            <li key={opt.id}>
              <button
                type="button"
                role="radio"
                aria-checked={selected === opt.id}
                disabled={submitted}
                onClick={() => handleSelect(opt.id)}
                className={`quiz-option w-full text-left px-4 py-3 text-sm ${stateClass}`}
              >
                <span
                  className="inline-flex items-center justify-center w-6 h-6 rounded-full border mr-3 text-xs font-bold"
                  style={{
                    borderColor: 'var(--color-border)',
                    backgroundColor: selected === opt.id ? 'var(--color-primary)' : 'transparent',
                    color: selected === opt.id ? '#fff' : 'var(--color-text-muted)',
                  }}
                  aria-hidden="true"
                >
                  {opt.id.toUpperCase()}
                </span>
                {opt.label}
              </button>
            </li>
          );
        })}
      </ul>

      {/* Feedback */}
      {submitted && (
        <div
          className={`mt-4 p-4 rounded-lg text-sm ${animScaleIn(animationLevel)}`}
          style={{
            backgroundColor: isCorrect ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)',
            color: isCorrect ? 'var(--color-success,#16a34a)' : 'var(--color-error,#dc2626)',
          }}
          role="status"
          aria-live="polite"
        >
          <span className="font-semibold">{isCorrect ? '✓ Correct!' : '✗ Not quite.'}</span>
          {question.explanation && <p className="mt-1">{question.explanation}</p>}
        </div>
      )}

      {/* Actions */}
      <div className="mt-5 flex gap-3">
        {!submitted ? (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!selected}
            className="btn-primary btn-sm"
          >
            Check Answer
          </button>
        ) : (
          <button type="button" onClick={handleReset} className="btn-outline btn-sm">
            Try Again
          </button>
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Variant: flashcard
// ─────────────────────────────────────────────────────────────────────────────

const Flashcard: React.FC<{
  question: QuizQuestion;
  index: number;
  animationLevel: BlockProps['animationLevel'];
}> = ({ question, index, animationLevel }) => {
  const [flipped, setFlipped] = useState(false);

  return (
    <div className={`mb-6 ${animEntrance(animationLevel)}`}>
      <p className="text-xs font-semibold uppercase tracking-widest mb-2 text-center"
         style={{ color: 'var(--color-text-muted)' }}>
        Card {index + 1}
      </p>

      {/* Flip card container */}
      <div
        className="relative cursor-pointer select-none"
        style={{ perspective: '1000px', minHeight: '200px' }}
        onClick={() => setFlipped((f) => !f)}
        onKeyDown={(e) => e.key === 'Enter' && setFlipped((f) => !f)}
        role="button"
        tabIndex={0}
        aria-pressed={flipped}
        aria-label={flipped ? 'Card back — answer' : 'Card front — question. Press to flip.'}
      >
        <div
          className="relative w-full transition-transform duration-500"
          style={{
            transformStyle: 'preserve-3d',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
          }}
        >
          {/* Front */}
          <div
            className="w-full rounded-2xl p-8 flex flex-col items-center justify-center text-center min-h-[200px]"
            style={{
              backfaceVisibility: 'hidden',
              WebkitBackfaceVisibility: 'hidden',
              backgroundColor: 'var(--color-surface)',
              border: '2px solid var(--color-primary)',
              boxShadow: 'var(--shadow-card)',
            }}
          >
            <span className="text-xs font-semibold uppercase tracking-widest mb-3"
                  style={{ color: 'var(--color-primary)' }}>
              Question
            </span>
            <p className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
              {question.question}
            </p>
            <p className="mt-4 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Click to reveal answer
            </p>
          </div>

          {/* Back */}
          <div
            className="absolute inset-0 rounded-2xl p-8 flex flex-col items-center justify-center text-center"
            style={{
              backfaceVisibility: 'hidden',
              WebkitBackfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
              backgroundColor: 'var(--color-primary)',
              color: '#fff',
              boxShadow: 'var(--shadow-glow)',
            }}
          >
            <span className="text-xs font-semibold uppercase tracking-widest mb-3 opacity-75">
              Answer
            </span>
            <p className="text-lg font-semibold">{question.answer}</p>
            {question.explanation && (
              <p className="mt-3 text-sm opacity-80">{question.explanation}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Variant: instant-check  (fill-in-the-blank)
// ─────────────────────────────────────────────────────────────────────────────

const InstantCheckQuiz: React.FC<{
  question: QuizQuestion;
  index: number;
  animationLevel: BlockProps['animationLevel'];
}> = ({ question, index, animationLevel }) => {
  const [value, setValue] = useState('');
  const [checked, setChecked] = useState(false);
  const id = useId();

  const normalize = (s: string) => s.trim().toLowerCase();
  const isCorrect =
    checked &&
    question.answer != null &&
    normalize(value) === normalize(question.answer);

  const handleCheck = () => { if (value.trim()) setChecked(true); };
  const handleReset = () => { setValue(''); setChecked(false); };

  // Replace {{blank}} with an inline input or the filled value
  const renderTemplate = () => {
    if (!question.template) return null;
    const parts = question.template.split('{{blank}}');
    return (
      <p className="text-base font-medium mb-5 leading-relaxed" style={{ color: 'var(--color-text)' }}>
        {parts[0]}
        {checked ? (
          <span
            className="mx-1 px-2 py-0.5 rounded font-semibold"
            style={{
              backgroundColor: isCorrect ? 'rgba(22,163,74,0.15)' : 'rgba(220,38,38,0.15)',
              color: isCorrect ? 'var(--color-success,#16a34a)' : 'var(--color-error,#dc2626)',
            }}
          >
            {value}
          </span>
        ) : (
          <input
            id={id}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            className="input-base inline-block w-36 mx-1 px-2 py-0.5 text-sm"
            aria-label="Fill in the blank"
            autoComplete="off"
          />
        )}
        {parts[1]}
      </p>
    );
  };

  return (
    <div className={`card mb-6 ${animEntrance(animationLevel)}`}>
      <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--color-text-muted)' }}>
        Question {index + 1}
      </p>

      <p className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
        {question.question}
      </p>

      {question.template ? renderTemplate() : (
        <div className="mb-5">
          <label htmlFor={id} className="label-base">Your answer</label>
          <input
            id={id}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            disabled={checked}
            className="input-base"
            aria-label="Your answer"
            autoComplete="off"
          />
        </div>
      )}

      {checked && (
        <div
          className={`mt-2 p-4 rounded-lg text-sm ${animScaleIn(animationLevel)}`}
          style={{
            backgroundColor: isCorrect ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)',
            color: isCorrect ? 'var(--color-success,#16a34a)' : 'var(--color-error,#dc2626)',
          }}
          role="status"
          aria-live="polite"
        >
          <span className="font-semibold">
            {isCorrect ? '✓ Correct!' : `✗ The answer is: ${question.answer}`}
          </span>
          {question.explanation && <p className="mt-1">{question.explanation}</p>}
        </div>
      )}

      <div className="mt-5 flex gap-3">
        {!checked ? (
          <button type="button" onClick={handleCheck} disabled={!value.trim()} className="btn-primary btn-sm">
            Check
          </button>
        ) : (
          <button type="button" onClick={handleReset} className="btn-outline btn-sm">
            Try Again
          </button>
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

/**
 * QuizBlock — interactive quiz with choice, flashcard, or instant-check modes.
 *
 * @example
 * <QuizBlock
 *   variant="choice"
 *   theme="default"
 *   animationLevel="medium"
 *   content={{
 *     heading: "Knowledge Check",
 *     questions: [{
 *       question: "What hook manages component state in React?",
 *       options: [
 *         { id: "a", label: "useEffect" },
 *         { id: "b", label: "useState", correct: true },
 *         { id: "c", label: "useRef" },
 *       ],
 *       explanation: "useState returns a stateful value and a setter function.",
 *     }],
 *   }}
 * />
 */
export const QuizBlock: React.FC<QuizBlockProps> = ({
  variant, animationLevel, content, className = '',
}) => (
  <section className={`block-wrapper ${className}`} aria-label={content.heading ?? 'Quiz'}>
    <div className="page-container max-w-2xl mx-auto">
      {content.heading && (
        <header className={`section-header ${animEntrance(animationLevel)}`}>
          <h2 className="heading-lg">{content.heading}</h2>
        </header>
      )}

      {content.questions.map((q, idx) => {
        switch (variant) {
          case 'flashcard':
            return <Flashcard key={idx} question={q} index={idx} animationLevel={animationLevel} />;
          case 'instant-check':
            return <InstantCheckQuiz key={idx} question={q} index={idx} animationLevel={animationLevel} />;
          case 'choice':
          default:
            return <ChoiceQuiz key={idx} question={q} index={idx} animationLevel={animationLevel} />;
        }
      })}
    </div>
  </section>
);

export default QuizBlock;
