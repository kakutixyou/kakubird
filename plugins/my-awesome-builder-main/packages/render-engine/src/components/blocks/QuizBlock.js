/**
 * QuizBlock.tsx
 *
 * Interactive quiz block with three modes:
 *  - choice:        Multiple-choice question — user selects one answer
 *  - flashcard:     Front/back flip card for self-study
 *  - instant-check: Fill-in-the-blank with immediate correctness feedback
 */
'use client';
import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useState, useId } from 'react';
// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function animEntrance(level) {
    return level === 'none' ? '' : 'animate-entrance';
}
function animScaleIn(level) {
    return level === 'none' ? '' : 'animate-scale-in';
}
// ─────────────────────────────────────────────────────────────────────────────
// Variant: choice
// ─────────────────────────────────────────────────────────────────────────────
const ChoiceQuiz = ({ question, index, animationLevel }) => {
    const [selected, setSelected] = useState(null);
    const [submitted, setSubmitted] = useState(false);
    const id = useId();
    const handleSelect = (optionId) => {
        if (!submitted)
            setSelected(optionId);
    };
    const handleSubmit = () => {
        if (selected)
            setSubmitted(true);
    };
    const handleReset = () => {
        setSelected(null);
        setSubmitted(false);
    };
    const isCorrect = submitted && question.options?.find((o) => o.id === selected)?.correct;
    return (_jsxs("div", { className: `card mb-6 ${animEntrance(animationLevel)}`, "aria-label": `Question ${index + 1}`, children: [_jsxs("p", { className: "text-xs font-semibold uppercase tracking-widest mb-2", style: { color: 'var(--color-text-muted)' }, children: ["Question ", index + 1] }), _jsx("p", { className: "text-lg font-semibold mb-5", style: { color: 'var(--color-text)' }, id: `${id}-question`, children: question.question }), _jsx("ul", { role: "radiogroup", "aria-labelledby": `${id}-question`, className: "space-y-3", children: question.options?.map((opt) => {
                    let stateClass = '';
                    if (submitted) {
                        if (opt.correct)
                            stateClass = 'correct';
                        else if (opt.id === selected)
                            stateClass = 'incorrect';
                    }
                    else if (opt.id === selected) {
                        stateClass = 'selected';
                    }
                    return (_jsx("li", { children: _jsxs("button", { type: "button", role: "radio", "aria-checked": selected === opt.id, disabled: submitted, onClick: () => handleSelect(opt.id), className: `quiz-option w-full text-left px-4 py-3 text-sm ${stateClass}`, children: [_jsx("span", { className: "inline-flex items-center justify-center w-6 h-6 rounded-full border mr-3 text-xs font-bold", style: {
                                        borderColor: 'var(--color-border)',
                                        backgroundColor: selected === opt.id ? 'var(--color-primary)' : 'transparent',
                                        color: selected === opt.id ? '#fff' : 'var(--color-text-muted)',
                                    }, "aria-hidden": "true", children: opt.id.toUpperCase() }), opt.label] }) }, opt.id));
                }) }), submitted && (_jsxs("div", { className: `mt-4 p-4 rounded-lg text-sm ${animScaleIn(animationLevel)}`, style: {
                    backgroundColor: isCorrect ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)',
                    color: isCorrect ? 'var(--color-success,#16a34a)' : 'var(--color-error,#dc2626)',
                }, role: "status", "aria-live": "polite", children: [_jsx("span", { className: "font-semibold", children: isCorrect ? '✓ Correct!' : '✗ Not quite.' }), question.explanation && _jsx("p", { className: "mt-1", children: question.explanation })] })), _jsx("div", { className: "mt-5 flex gap-3", children: !submitted ? (_jsx("button", { type: "button", onClick: handleSubmit, disabled: !selected, className: "btn-primary btn-sm", children: "Check Answer" })) : (_jsx("button", { type: "button", onClick: handleReset, className: "btn-outline btn-sm", children: "Try Again" })) })] }));
};
// ─────────────────────────────────────────────────────────────────────────────
// Variant: flashcard
// ─────────────────────────────────────────────────────────────────────────────
const Flashcard = ({ question, index, animationLevel }) => {
    const [flipped, setFlipped] = useState(false);
    return (_jsxs("div", { className: `mb-6 ${animEntrance(animationLevel)}`, children: [_jsxs("p", { className: "text-xs font-semibold uppercase tracking-widest mb-2 text-center", style: { color: 'var(--color-text-muted)' }, children: ["Card ", index + 1] }), _jsx("div", { className: "relative cursor-pointer select-none", style: { perspective: '1000px', minHeight: '200px' }, onClick: () => setFlipped((f) => !f), onKeyDown: (e) => e.key === 'Enter' && setFlipped((f) => !f), role: "button", tabIndex: 0, "aria-pressed": flipped, "aria-label": flipped ? 'Card back — answer' : 'Card front — question. Press to flip.', children: _jsxs("div", { className: "relative w-full transition-transform duration-500", style: {
                        transformStyle: 'preserve-3d',
                        transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                    }, children: [_jsxs("div", { className: "w-full rounded-2xl p-8 flex flex-col items-center justify-center text-center min-h-[200px]", style: {
                                backfaceVisibility: 'hidden',
                                WebkitBackfaceVisibility: 'hidden',
                                backgroundColor: 'var(--color-surface)',
                                border: '2px solid var(--color-primary)',
                                boxShadow: 'var(--shadow-card)',
                            }, children: [_jsx("span", { className: "text-xs font-semibold uppercase tracking-widest mb-3", style: { color: 'var(--color-primary)' }, children: "Question" }), _jsx("p", { className: "text-lg font-semibold", style: { color: 'var(--color-text)' }, children: question.question }), _jsx("p", { className: "mt-4 text-xs", style: { color: 'var(--color-text-muted)' }, children: "Click to reveal answer" })] }), _jsxs("div", { className: "absolute inset-0 rounded-2xl p-8 flex flex-col items-center justify-center text-center", style: {
                                backfaceVisibility: 'hidden',
                                WebkitBackfaceVisibility: 'hidden',
                                transform: 'rotateY(180deg)',
                                backgroundColor: 'var(--color-primary)',
                                color: '#fff',
                                boxShadow: 'var(--shadow-glow)',
                            }, children: [_jsx("span", { className: "text-xs font-semibold uppercase tracking-widest mb-3 opacity-75", children: "Answer" }), _jsx("p", { className: "text-lg font-semibold", children: question.answer }), question.explanation && (_jsx("p", { className: "mt-3 text-sm opacity-80", children: question.explanation }))] })] }) })] }));
};
// ─────────────────────────────────────────────────────────────────────────────
// Variant: instant-check  (fill-in-the-blank)
// ─────────────────────────────────────────────────────────────────────────────
const InstantCheckQuiz = ({ question, index, animationLevel }) => {
    const [value, setValue] = useState('');
    const [checked, setChecked] = useState(false);
    const id = useId();
    const normalize = (s) => s.trim().toLowerCase();
    const isCorrect = checked &&
        question.answer != null &&
        normalize(value) === normalize(question.answer);
    const handleCheck = () => { if (value.trim())
        setChecked(true); };
    const handleReset = () => { setValue(''); setChecked(false); };
    // Replace {{blank}} with an inline input or the filled value
    const renderTemplate = () => {
        if (!question.template)
            return null;
        const parts = question.template.split('{{blank}}');
        return (_jsxs("p", { className: "text-base font-medium mb-5 leading-relaxed", style: { color: 'var(--color-text)' }, children: [parts[0], checked ? (_jsx("span", { className: "mx-1 px-2 py-0.5 rounded font-semibold", style: {
                        backgroundColor: isCorrect ? 'rgba(22,163,74,0.15)' : 'rgba(220,38,38,0.15)',
                        color: isCorrect ? 'var(--color-success,#16a34a)' : 'var(--color-error,#dc2626)',
                    }, children: value })) : (_jsx("input", { id: id, type: "text", value: value, onChange: (e) => setValue(e.target.value), onKeyDown: (e) => e.key === 'Enter' && handleCheck(), className: "input-base inline-block w-36 mx-1 px-2 py-0.5 text-sm", "aria-label": "Fill in the blank", autoComplete: "off" })), parts[1]] }));
    };
    return (_jsxs("div", { className: `card mb-6 ${animEntrance(animationLevel)}`, children: [_jsxs("p", { className: "text-xs font-semibold uppercase tracking-widest mb-2", style: { color: 'var(--color-text-muted)' }, children: ["Question ", index + 1] }), _jsx("p", { className: "text-lg font-semibold mb-4", style: { color: 'var(--color-text)' }, children: question.question }), question.template ? renderTemplate() : (_jsxs("div", { className: "mb-5", children: [_jsx("label", { htmlFor: id, className: "label-base", children: "Your answer" }), _jsx("input", { id: id, type: "text", value: value, onChange: (e) => setValue(e.target.value), onKeyDown: (e) => e.key === 'Enter' && handleCheck(), disabled: checked, className: "input-base", "aria-label": "Your answer", autoComplete: "off" })] })), checked && (_jsxs("div", { className: `mt-2 p-4 rounded-lg text-sm ${animScaleIn(animationLevel)}`, style: {
                    backgroundColor: isCorrect ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)',
                    color: isCorrect ? 'var(--color-success,#16a34a)' : 'var(--color-error,#dc2626)',
                }, role: "status", "aria-live": "polite", children: [_jsx("span", { className: "font-semibold", children: isCorrect ? '✓ Correct!' : `✗ The answer is: ${question.answer}` }), question.explanation && _jsx("p", { className: "mt-1", children: question.explanation })] })), _jsx("div", { className: "mt-5 flex gap-3", children: !checked ? (_jsx("button", { type: "button", onClick: handleCheck, disabled: !value.trim(), className: "btn-primary btn-sm", children: "Check" })) : (_jsx("button", { type: "button", onClick: handleReset, className: "btn-outline btn-sm", children: "Try Again" })) })] }));
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
export const QuizBlock = ({ variant, animationLevel, content, className = '', }) => (_jsx("section", { className: `block-wrapper ${className}`, "aria-label": content.heading ?? 'Quiz', children: _jsxs("div", { className: "page-container max-w-2xl mx-auto", children: [content.heading && (_jsx("header", { className: `section-header ${animEntrance(animationLevel)}`, children: _jsx("h2", { className: "heading-lg", children: content.heading }) })), content.questions.map((q, idx) => {
                switch (variant) {
                    case 'flashcard':
                        return _jsx(Flashcard, { question: q, index: idx, animationLevel: animationLevel }, idx);
                    case 'instant-check':
                        return _jsx(InstantCheckQuiz, { question: q, index: idx, animationLevel: animationLevel }, idx);
                    case 'choice':
                    default:
                        return _jsx(ChoiceQuiz, { question: q, index: idx, animationLevel: animationLevel }, idx);
                }
            })] }) }));
export default QuizBlock;
