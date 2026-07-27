import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function animEntrance(level) {
    return level === 'none' ? '' : 'animate-entrance';
}
function animSlideUp(level) {
    return level === 'none' ? '' : 'animate-slide-up';
}
function animHover(level) {
    return level === 'none' ? '' : 'animate-hover-lift';
}
function animStagger(level) {
    return level !== 'none' && level !== 'low' ? 'stagger-children' : '';
}
const colClasses = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
};
// ─────────────────────────────────────────────────────────────────────────────
// Card Icon renderer
// ─────────────────────────────────────────────────────────────────────────────
const CardIcon = ({ icon }) => {
    const isUrl = icon.startsWith('http') || icon.startsWith('/');
    const isSvg = icon.trimStart().startsWith('<svg');
    if (isUrl) {
        return (_jsx("div", { className: "flex items-center justify-center w-12 h-12 rounded-xl mb-4", style: { backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)' }, children: _jsx("img", { src: icon, alt: "", className: "w-7 h-7 object-contain" }) }));
    }
    if (isSvg) {
        // Encode SVG as a data URL for use in <img> so scripts inside the SVG
        // cannot execute (SVG loaded via <img> is sandboxed by the browser).
        const svgDataUrl = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(icon)))}`;
        return (_jsx("div", { className: "flex items-center justify-center w-12 h-12 rounded-xl mb-4", style: { backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)' }, children: _jsx("img", { src: svgDataUrl, alt: "", className: "w-7 h-7 object-contain", "aria-hidden": "true" }) }));
    }
    // Treat as emoji or text character
    return (_jsx("div", { className: "flex items-center justify-center w-12 h-12 rounded-xl mb-4 text-2xl", style: { backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)' }, "aria-hidden": "true", children: icon }));
};
const SingleCard = ({ card, variant, animationLevel }) => {
    const hoverCls = animHover(animationLevel);
    const cardClass = variant === 'glass'
        ? `glass-card ${hoverCls}`
        : variant === 'bordered'
            ? `bordered-card ${hoverCls}`
            : `card ${hoverCls}`;
    return (_jsxs("article", { className: `${cardClass} flex flex-col`, children: [card.icon && _jsx(CardIcon, { icon: card.icon }), _jsxs("div", { className: "flex items-start justify-between gap-2 mb-2", children: [_jsx("h3", { className: "text-lg font-semibold", style: { color: 'var(--color-text)' }, children: card.title }), card.badge && (_jsx("span", { className: "badge-primary shrink-0", children: card.badge }))] }), _jsx("p", { className: "body-base flex-1", children: card.description }), card.linkLabel && (_jsxs("a", { href: card.linkHref ?? '#', className: "mt-4 inline-flex items-center gap-1.5 text-sm font-semibold", style: { color: 'var(--color-primary)' }, children: [card.linkLabel, _jsx("svg", { className: "w-3.5 h-3.5", fill: "none", viewBox: "0 0 24 24", stroke: "currentColor", strokeWidth: 2.5, children: _jsx("path", { strokeLinecap: "round", strokeLinejoin: "round", d: "M9 5l7 7-7 7" }) })] }))] }));
};
// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────
/**
 * InfoCardsBlock — a grid of informational cards.
 *
 * @example
 * <InfoCardsBlock
 *   variant="glass"
 *   theme="future-purple"
 *   animationLevel="high"
 *   content={{
 *     heading: "What you'll learn",
 *     cards: [
 *       { title: "React Basics", description: "Learn JSX and hooks.", icon: "⚛️" },
 *       { title: "TypeScript", description: "Type-safe code.", icon: "🔷" },
 *     ],
 *   }}
 * />
 */
export const InfoCardsBlock = ({ variant, animationLevel, content, className = '', }) => {
    const cols = content.columns ?? 3;
    const gridCols = colClasses[cols] ?? colClasses[3];
    return (_jsx("section", { className: `block-wrapper ${className}`, "aria-label": content.heading ?? 'Info cards', children: _jsxs("div", { className: "page-container", children: [(content.heading || content.subheading) && (_jsxs("header", { className: `section-header-centered ${animEntrance(animationLevel)}`, children: [content.heading && (_jsx("h2", { className: "heading-lg", children: content.heading })), content.subheading && (_jsx("p", { className: "body-lg mt-3 max-w-2xl mx-auto", children: content.subheading }))] })), _jsx("div", { className: `grid ${gridCols} gap-6 ${animStagger(animationLevel)}`, children: content.cards.map((card, idx) => (_jsx(SingleCard, { card: card, variant: variant, animationLevel: animationLevel }, `${card.title}-${idx}`))) })] }) }));
};
export default InfoCardsBlock;
