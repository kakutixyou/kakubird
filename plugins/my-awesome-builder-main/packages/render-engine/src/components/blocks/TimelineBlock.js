import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function animSlideUp(level) {
    return level === 'none' ? '' : 'animate-slide-up';
}
function animEntrance(level) {
    return level === 'none' ? '' : 'animate-entrance';
}
function animStagger(level) {
    return level !== 'none' && level !== 'low' ? 'stagger-children' : '';
}
// ─────────────────────────────────────────────────────────────────────────────
// Variant: vertical
// ─────────────────────────────────────────────────────────────────────────────
const VerticalTimeline = ({ content, animationLevel, className = '', }) => (_jsx("section", { className: `block-wrapper ${className}`, "aria-label": content.heading ?? 'Timeline', children: _jsxs("div", { className: "page-container max-w-3xl mx-auto", children: [(content.heading || content.subheading) && (_jsxs("header", { className: `section-header-centered ${animEntrance(animationLevel)}`, children: [content.heading && _jsx("h2", { className: "heading-lg", children: content.heading }), content.subheading && (_jsx("p", { className: "body-lg mt-3 max-w-2xl mx-auto", children: content.subheading }))] })), _jsxs("ol", { className: `relative pl-8 ${animStagger(animationLevel)}`, "aria-label": "Timeline", children: [_jsx("li", { "aria-hidden": "true", className: "pointer-events-none", children: _jsx("span", { className: "absolute left-3.5 top-0 bottom-0 w-0.5", style: {
                                background: 'linear-gradient(to bottom, var(--color-primary), var(--color-accent))',
                            } }) }), content.entries.map((entry, idx) => (_jsxs("li", { className: `relative mb-10 last:mb-0 ${animSlideUp(animationLevel)}`, children: [_jsx("span", { className: "absolute -left-4 top-1 flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold border-2 z-10", style: {
                                    backgroundColor: entry.featured ? 'var(--color-primary)' : 'var(--color-surface)',
                                    borderColor: 'var(--color-primary)',
                                    color: entry.featured ? 'var(--color-text-inverse, #fff)' : 'var(--color-primary)',
                                    boxShadow: entry.featured ? 'var(--shadow-glow)' : undefined,
                                }, "aria-hidden": "true", children: entry.icon ?? entry.marker }), _jsxs("div", { className: `ml-4 p-5 rounded-xl border transition-all duration-200 ${entry.featured ? 'border-[var(--color-primary)]' : 'border-[var(--color-border)]'}`, style: {
                                    backgroundColor: 'var(--color-surface)',
                                    boxShadow: entry.featured ? 'var(--shadow-glow)' : 'var(--shadow-card)',
                                }, children: [entry.date && (_jsx("time", { className: "block text-xs font-semibold uppercase tracking-wider mb-1", style: { color: 'var(--color-text-muted)' }, children: entry.date })), _jsx("h3", { className: "text-base font-semibold", style: { color: 'var(--color-text)' }, children: entry.title }), entry.description && (_jsx("p", { className: "body-sm mt-1", children: entry.description }))] })] }, `${entry.marker}-${idx}`)))] })] }) }));
// ─────────────────────────────────────────────────────────────────────────────
// Variant: horizontal
// ─────────────────────────────────────────────────────────────────────────────
const HorizontalTimeline = ({ content, animationLevel, className = '', }) => (_jsx("section", { className: `block-wrapper ${className}`, "aria-label": content.heading ?? 'Timeline', children: _jsxs("div", { className: "page-container", children: [(content.heading || content.subheading) && (_jsxs("header", { className: `section-header-centered ${animEntrance(animationLevel)}`, children: [content.heading && _jsx("h2", { className: "heading-lg", children: content.heading }), content.subheading && (_jsx("p", { className: "body-lg mt-3 max-w-2xl mx-auto", children: content.subheading }))] })), _jsx("div", { className: "overflow-x-auto pb-4", children: _jsx("ol", { className: `relative flex gap-0 min-w-max ${animStagger(animationLevel)}`, "aria-label": "Timeline", children: content.entries.map((entry, idx) => (_jsxs("li", { className: `relative flex flex-col items-center w-48 ${animEntrance(animationLevel)}`, children: [idx < content.entries.length - 1 && (_jsx("span", { "aria-hidden": "true", className: "absolute top-4 left-1/2 w-full h-0.5 -translate-y-1/2", style: { background: 'var(--color-border)', left: '50%' } })), _jsx("span", { className: "relative z-10 flex items-center justify-center w-9 h-9 rounded-full text-sm font-bold border-2 mb-3", style: {
                                    backgroundColor: entry.featured ? 'var(--color-primary)' : 'var(--color-surface)',
                                    borderColor: 'var(--color-primary)',
                                    color: entry.featured ? 'var(--color-text-inverse, #fff)' : 'var(--color-primary)',
                                }, "aria-hidden": "true", children: entry.icon ?? entry.marker }), _jsxs("div", { className: "text-center px-2", children: [entry.date && (_jsx("time", { className: "block text-xs font-semibold uppercase tracking-wider mb-0.5", style: { color: 'var(--color-text-muted)' }, children: entry.date })), _jsx("p", { className: "text-sm font-semibold", style: { color: 'var(--color-text)' }, children: entry.title }), entry.description && (_jsx("p", { className: "text-xs mt-1 leading-snug", style: { color: 'var(--color-text-muted)' }, children: entry.description }))] })] }, `${entry.marker}-${idx}`))) }) })] }) }));
// ─────────────────────────────────────────────────────────────────────────────
// Variant: minimal
// ─────────────────────────────────────────────────────────────────────────────
const MinimalTimeline = ({ content, animationLevel, className = '', }) => (_jsx("section", { className: `block-wrapper ${className}`, "aria-label": content.heading ?? 'Timeline', children: _jsxs("div", { className: "page-container max-w-2xl mx-auto", children: [(content.heading || content.subheading) && (_jsxs("header", { className: `section-header ${animEntrance(animationLevel)}`, children: [content.heading && _jsx("h2", { className: "heading-lg", children: content.heading }), content.subheading && (_jsx("p", { className: "body-lg mt-3", children: content.subheading }))] })), _jsx("ol", { className: `space-y-6 ${animStagger(animationLevel)}`, "aria-label": "Timeline", children: content.entries.map((entry, idx) => (_jsxs("li", { className: `flex items-start gap-5 ${animSlideUp(animationLevel)}`, children: [_jsx("span", { className: "shrink-0 flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold", style: {
                                backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)',
                                color: 'var(--color-primary)',
                            }, "aria-hidden": "true", children: entry.icon ?? entry.marker }), _jsxs("div", { className: "flex-1 pt-1", children: [entry.date && (_jsx("time", { className: "block text-xs font-semibold uppercase tracking-wider mb-0.5", style: { color: 'var(--color-text-muted)' }, children: entry.date })), _jsx("h3", { className: "text-base font-semibold", style: { color: 'var(--color-text)' }, children: entry.title }), entry.description && (_jsx("p", { className: "body-sm mt-1", children: entry.description }))] })] }, `${entry.marker}-${idx}`))) })] }) }));
// ─────────────────────────────────────────────────────────────────────────────
// Main export
// ─────────────────────────────────────────────────────────────────────────────
/**
 * TimelineBlock — chronological entries in vertical, horizontal, or minimal layout.
 *
 * @example
 * <TimelineBlock
 *   variant="vertical"
 *   theme="default"
 *   animationLevel="medium"
 *   content={{
 *     heading: "Course Roadmap",
 *     entries: [
 *       { marker: "1", title: "Introduction", description: "Get familiar with the basics." },
 *       { marker: "2", title: "Core Concepts", description: "Deep dive into theory.", featured: true },
 *     ],
 *   }}
 * />
 */
export const TimelineBlock = (props) => {
    switch (props.variant) {
        case 'horizontal':
            return _jsx(HorizontalTimeline, { ...props });
        case 'minimal':
            return _jsx(MinimalTimeline, { ...props });
        case 'vertical':
        default:
            return _jsx(VerticalTimeline, { ...props });
    }
};
export default TimelineBlock;
