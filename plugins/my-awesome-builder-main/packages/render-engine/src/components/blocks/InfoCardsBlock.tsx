/**
 * InfoCardsBlock.tsx
 *
 * Displays a grid of information cards in three visual styles:
 *  - flat:     Clean white/surface cards with subtle shadow
 *  - glass:    Frosted-glass effect (ideal for dark/purple themes)
 *  - bordered: Outline cards with primary-colour border
 */

import React from 'react';
// import type { BlockProps } from '../../config/theme-definitions';
export interface BlockProps {
  animationLevel?: 'none' | 'low' | 'medium' | 'high';
  className?: string;
}
// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type InfoCardsVariant = 'flat' | 'glass' | 'bordered';

export interface InfoCard {
  /** Short card heading */
  title: string;
  /** Body text */
  description: string;
  /** Icon: any valid emoji, SVG string, or URL */
  icon?: string;
  /** Optional badge label */
  badge?: string;
  /** Optional link */
  linkLabel?: string;
  linkHref?: string;
}

export interface InfoCardsContent {
  /** Section heading (optional) */
  heading?: string;
  /** Section subheading */
  subheading?: string;
  /** Array of card data */
  cards: InfoCard[];
  /** Number of columns override (auto by default) */
  columns?: 2 | 3 | 4;
}

export interface InfoCardsBlockProps extends Omit<BlockProps, 'content' | 'variant'> {
  variant: InfoCardsVariant;
  content: InfoCardsContent;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function animEntrance(level: BlockProps['animationLevel']): string {
  return level === 'none' ? '' : 'animate-entrance';
}
function animSlideUp(level: BlockProps['animationLevel']): string {
  return level === 'none' ? '' : 'animate-slide-up';
}
function animHover(level: BlockProps['animationLevel']): string {
  return level === 'none' ? '' : 'animate-hover-lift';
}
function animStagger(level: BlockProps['animationLevel']): string {
  return level !== 'none' && level !== 'low' ? 'stagger-children' : '';
}

const colClasses: Record<number, string> = {
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
};

// ─────────────────────────────────────────────────────────────────────────────
// Card Icon renderer
// ─────────────────────────────────────────────────────────────────────────────

const CardIcon: React.FC<{ icon: string }> = ({ icon }) => {
  const isUrl = icon.startsWith('http') || icon.startsWith('/');
  const isSvg = icon.trimStart().startsWith('<svg');

  if (isUrl) {
    return (
      <div className="flex items-center justify-center w-12 h-12 rounded-xl mb-4"
           style={{ backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)' }}>
        <img src={icon} alt="" className="w-7 h-7 object-contain" />
      </div>
    );
  }

  if (isSvg) {
    // Encode SVG as a data URL for use in <img> so scripts inside the SVG
    // cannot execute (SVG loaded via <img> is sandboxed by the browser).
    const svgDataUrl = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(icon)))}`;
    return (
      <div
        className="flex items-center justify-center w-12 h-12 rounded-xl mb-4"
        style={{ backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)' }}
      >
        <img src={svgDataUrl} alt="" className="w-7 h-7 object-contain" aria-hidden="true" />
      </div>
    );
  }

  // Treat as emoji or text character
  return (
    <div
      className="flex items-center justify-center w-12 h-12 rounded-xl mb-4 text-2xl"
      style={{ backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)' }}
      aria-hidden="true"
    >
      {icon}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Individual card variants
// ─────────────────────────────────────────────────────────────────────────────

interface SingleCardProps {
  card: InfoCard;
  variant: InfoCardsVariant;
  animationLevel: BlockProps['animationLevel'];
}

const SingleCard: React.FC<SingleCardProps> = ({ card, variant, animationLevel }) => {
  const hoverCls = animHover(animationLevel);

  const cardClass =
    variant === 'glass'
      ? `glass-card ${hoverCls}`
      : variant === 'bordered'
      ? `bordered-card ${hoverCls}`
      : `card ${hoverCls}`;

  return (
    <article className={`${cardClass} flex flex-col`}>
      {card.icon && <CardIcon icon={card.icon} />}

      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
          {card.title}
        </h3>
        {card.badge && (
          <span className="badge-primary shrink-0">{card.badge}</span>
        )}
      </div>

      <p className="body-base flex-1">{card.description}</p>

      {card.linkLabel && (
        <a
          href={card.linkHref ?? '#'}
          className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold"
          style={{ color: 'var(--color-primary)' }}
        >
          {card.linkLabel}
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </a>
      )}
    </article>
  );
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
export const InfoCardsBlock: React.FC<InfoCardsBlockProps> = ({
  variant,
  animationLevel,
  content,
  className = '',
}) => {
  const cols = content.columns ?? 3;
  const gridCols = colClasses[cols] ?? colClasses[3];

  return (
    <section
      className={`block-wrapper ${className}`}
      aria-label={content.heading ?? 'Info cards'}
    >
      <div className="page-container">
        {/* Section header */}
        {(content.heading || content.subheading) && (
          <header className={`section-header-centered ${animEntrance(animationLevel)}`}>
            {content.heading && (
              <h2 className="heading-lg">{content.heading}</h2>
            )}
            {content.subheading && (
              <p className="body-lg mt-3 max-w-2xl mx-auto">{content.subheading}</p>
            )}
          </header>
        )}

        {/* Card grid */}
        <div className={`grid ${gridCols} gap-6 ${animStagger(animationLevel)}`}>
          {content.cards.map((card, idx) => (
            <SingleCard
              key={`${card.title}-${idx}`}
              card={card}
              variant={variant}
              animationLevel={animationLevel}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export default InfoCardsBlock;
