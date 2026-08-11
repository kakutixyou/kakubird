import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// ─────────────────────────────────────────────────────────────────────────────
// Animation class helpers
// ─────────────────────────────────────────────────────────────────────────────
function getEntranceClass(level) {
    if (level === 'none')
        return '';
    return 'animate-entrance';
}
function getSlideUpClass(level) {
    if (level === 'none')
        return '';
    return 'animate-slide-up';
}
function getHoverClass(level) {
    if (level === 'none')
        return '';
    return 'animate-hover-lift';
}
function getStaggerClass(level) {
    if (level === 'none' || level === 'low')
        return '';
    return 'stagger-children';
}
const Badge = ({ label }) => (_jsx("span", { className: "inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-widest mb-4 border border-[var(--color-primary)] text-[var(--color-primary)] bg-[rgba(var(--color-primary-rgb,37,99,235),0.08)]", children: label }));
const CtaGroup = ({ ctaLabel, ctaHref = '#', secondaryLabel, secondaryHref = '#', animationLevel, }) => (_jsxs("div", { className: `flex flex-wrap items-center gap-4 mt-8 ${getStaggerClass(animationLevel)}`, children: [ctaLabel && (_jsxs("a", { href: ctaHref, className: `btn-primary btn-lg ${getHoverClass(animationLevel)}`, children: [ctaLabel, _jsx("svg", { className: "w-4 h-4", fill: "none", viewBox: "0 0 24 24", stroke: "currentColor", strokeWidth: 2, children: _jsx("path", { strokeLinecap: "round", strokeLinejoin: "round", d: "M9 5l7 7-7 7" }) })] })), secondaryLabel && (_jsx("a", { href: secondaryHref, className: `btn-outline btn-lg ${getHoverClass(animationLevel)}`, children: secondaryLabel }))] }));
// ─────────────────────────────────────────────────────────────────────────────
// Variant: center-title
// ─────────────────────────────────────────────────────────────────────────────
const CenterTitleHero = ({ content, animationLevel, className = '' }) => (_jsxs("section", { className: `block-wrapper relative overflow-hidden ${className}`, "aria-label": "Hero section", children: [_jsx("div", { "aria-hidden": "true", className: "pointer-events-none absolute inset-0 flex items-center justify-center", children: _jsx("div", { className: "w-[800px] h-[600px] rounded-full opacity-20 blur-3xl", style: {
                    background: 'radial-gradient(circle, var(--color-primary) 0%, var(--color-accent) 60%, transparent 100%)',
                } }) }), _jsxs("div", { className: `page-container relative z-10 flex flex-col items-center text-center ${getStaggerClass(animationLevel)}`, children: [content.badge && _jsx(Badge, { label: content.badge }), _jsx("h1", { className: `heading-xl max-w-4xl text-5xl md:text-6xl lg:text-7xl ${getSlideUpClass(animationLevel)}`, children: content.title }), content.subtitle && (_jsx("p", { className: `mt-4 text-xl md:text-2xl font-semibold text-[var(--color-secondary)] ${getSlideUpClass(animationLevel)}`, children: content.subtitle })), content.description && (_jsx("p", { className: `body-lg mt-6 max-w-2xl ${getEntranceClass(animationLevel)}`, children: content.description })), _jsx(CtaGroup, { ctaLabel: content.ctaLabel, ctaHref: content.ctaHref, secondaryLabel: content.secondaryCtaLabel, secondaryHref: content.secondaryCtaHref, animationLevel: animationLevel })] })] }));
// ─────────────────────────────────────────────────────────────────────────────
// Variant: left-image  (text left, image right)
// ─────────────────────────────────────────────────────────────────────────────
const LeftImageHero = ({ content, animationLevel, className = '' }) => (_jsx("section", { className: `block-wrapper ${className}`, "aria-label": "Hero section", children: _jsxs("div", { className: "page-container grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center", children: [_jsxs("div", { className: `flex flex-col ${getStaggerClass(animationLevel)}`, children: [content.badge && _jsx(Badge, { label: content.badge }), _jsx("h1", { className: `heading-xl text-4xl md:text-5xl ${getSlideUpClass(animationLevel)}`, children: content.title }), content.subtitle && (_jsx("p", { className: `mt-3 text-xl font-semibold text-[var(--color-secondary)] ${getSlideUpClass(animationLevel)}`, children: content.subtitle })), content.description && (_jsx("p", { className: `body-lg mt-5 ${getEntranceClass(animationLevel)}`, children: content.description })), _jsx(CtaGroup, { ctaLabel: content.ctaLabel, ctaHref: content.ctaHref, secondaryLabel: content.secondaryCtaLabel, secondaryHref: content.secondaryCtaHref, animationLevel: animationLevel })] }), content.imageUrl && (_jsxs("div", { className: `relative flex items-center justify-center ${getEntranceClass(animationLevel)}`, children: [_jsx("div", { "aria-hidden": "true", className: "absolute inset-0 rounded-3xl opacity-20 blur-2xl", style: { background: 'radial-gradient(circle, var(--color-primary), transparent 70%)' } }), _jsx("img", { src: content.imageUrl, alt: content.imageAlt ?? content.title, className: "relative z-10 w-full max-w-lg rounded-2xl shadow-2xl object-cover", loading: "eager" })] }))] }) }));
// ─────────────────────────────────────────────────────────────────────────────
// Variant: full-background
// ─────────────────────────────────────────────────────────────────────────────
const FullBackgroundHero = ({ content, animationLevel, className = '' }) => (_jsxs("section", { className: `relative min-h-screen flex items-center overflow-hidden ${className}`, "aria-label": "Hero section", children: [content.imageUrl && (_jsxs(_Fragment, { children: [_jsx("img", { src: content.imageUrl, alt: "", "aria-hidden": "true", className: "absolute inset-0 w-full h-full object-cover", loading: "eager" }), _jsx("div", { "aria-hidden": "true", className: "absolute inset-0", style: {
                        background: 'linear-gradient(to right, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.4) 60%, transparent 100%)',
                    } })] })), !content.imageUrl && (_jsx("div", { "aria-hidden": "true", className: "absolute inset-0", style: {
                background: 'var(--gradient-hero, linear-gradient(135deg, var(--color-bg) 0%, var(--color-surface) 100%))',
            } })), _jsxs("div", { className: `page-container relative z-10 flex flex-col max-w-3xl section-padding ${getStaggerClass(animationLevel)}`, children: [content.badge && _jsx(Badge, { label: content.badge }), _jsx("h1", { className: `text-4xl md:text-5xl lg:text-6xl font-bold leading-tight text-white ${getSlideUpClass(animationLevel)}`, style: { color: content.imageUrl ? '#fff' : 'var(--color-text)' }, children: content.title }), content.subtitle && (_jsx("p", { className: `mt-4 text-xl font-semibold ${getSlideUpClass(animationLevel)}`, style: { color: content.imageUrl ? 'rgba(255,255,255,0.85)' : 'var(--color-secondary)' }, children: content.subtitle })), content.description && (_jsx("p", { className: `mt-5 text-lg leading-relaxed max-w-xl ${getEntranceClass(animationLevel)}`, style: { color: content.imageUrl ? 'rgba(255,255,255,0.75)' : 'var(--color-text-muted)' }, children: content.description })), _jsx(CtaGroup, { ctaLabel: content.ctaLabel, ctaHref: content.ctaHref, secondaryLabel: content.secondaryCtaLabel, secondaryHref: content.secondaryCtaHref, animationLevel: animationLevel })] })] }));
// ─────────────────────────────────────────────────────────────────────────────
// Main export
// ─────────────────────────────────────────────────────────────────────────────
/**
 * HeroBlock — renders the appropriate hero variant based on the `variant` prop.
 *
 * @example
 * <HeroBlock
 *   variant="center-title"
 *   theme="future-purple"
 *   animationLevel="high"
 *   content={{ title: "Learn Anything", ctaLabel: "Get Started", ctaHref: "/start" }}
 * />
 */
export const HeroBlock = (props) => {
    switch (props.variant) {
        case 'left-image':
            return _jsx(LeftImageHero, { ...props });
        case 'full-background':
            return _jsx(FullBackgroundHero, { ...props });
        case 'center-title':
        default:
            return _jsx(CenterTitleHero, { ...props });
    }
};
export default HeroBlock;
