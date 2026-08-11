/**
 * HeroBlock.tsx
 *
 * Hero section block with three variants:
 *  - center-title:      Centered text + CTA, optional background image overlay
 *  - left-image:        Image on the right, text on the left (split hero)
 *  - full-background:   Full-bleed background with overlaid content
 */

import React from 'react';

// Minimal local BlockProps type for HeroBlock; external theme-definitions may be unavailable.
export interface BlockProps {
  animationLevel?: 'none' | 'low' | 'medium' | 'high';
  className?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type HeroVariant = 'center-title' | 'left-image' | 'full-background';

export interface HeroContent {
  /** Main headline */
  title: string;
  /** Optional subheading rendered below the title */
  subtitle?: string;
  /** Body copy / description */
  description?: string;
  /** Primary CTA button label */
  ctaLabel?: string;
  /** Primary CTA URL */
  ctaHref?: string;
  /** Secondary CTA button label */
  secondaryCtaLabel?: string;
  /** Secondary CTA URL */
  secondaryCtaHref?: string;
  /** URL for hero image (used in left-image and full-background variants) */
  imageUrl?: string;
  /** Accessible alt text for the hero image */
  imageAlt?: string;
  /** Optional badge / label shown above the title */
  badge?: string;
}

export interface HeroBlockProps extends Omit<BlockProps, 'content' | 'variant'> {
  variant: HeroVariant;
  content: HeroContent;
}

// ─────────────────────────────────────────────────────────────────────────────
// Animation class helpers
// ─────────────────────────────────────────────────────────────────────────────

function getEntranceClass(level: BlockProps['animationLevel']): string {
  if (level === 'none') return '';
  return 'animate-entrance';
}

function getSlideUpClass(level: BlockProps['animationLevel']): string {
  if (level === 'none') return '';
  return 'animate-slide-up';
}

function getHoverClass(level: BlockProps['animationLevel']): string {
  if (level === 'none') return '';
  return 'animate-hover-lift';
}

function getStaggerClass(level: BlockProps['animationLevel']): string {
  if (level === 'none' || level === 'low') return '';
  return 'stagger-children';
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

interface BadgeProps { label: string; }
const Badge: React.FC<BadgeProps> = ({ label }) => (
  <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-widest mb-4 border border-[var(--color-primary)] text-[var(--color-primary)] bg-[rgba(var(--color-primary-rgb,37,99,235),0.08)]">
    {label}
  </span>
);

interface CtaGroupProps {
  ctaLabel?: string;
  ctaHref?: string;
  secondaryLabel?: string;
  secondaryHref?: string;
  animationLevel: BlockProps['animationLevel'];
}
const CtaGroup: React.FC<CtaGroupProps> = ({
  ctaLabel, ctaHref = '#',
  secondaryLabel, secondaryHref = '#',
  animationLevel,
}) => (
  <div className={`flex flex-wrap items-center gap-4 mt-8 ${getStaggerClass(animationLevel)}`}>
    {ctaLabel && (
      <a
        href={ctaHref}
        className={`btn-primary btn-lg ${getHoverClass(animationLevel)}`}
      >
        {ctaLabel}
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </a>
    )}
    {secondaryLabel && (
      <a
        href={secondaryHref}
        className={`btn-outline btn-lg ${getHoverClass(animationLevel)}`}
      >
        {secondaryLabel}
      </a>
    )}
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// Variant: center-title
// ─────────────────────────────────────────────────────────────────────────────

const CenterTitleHero: React.FC<HeroBlockProps> = ({ content, animationLevel, className = '' }) => (
  <section
    className={`block-wrapper relative overflow-hidden ${className}`}
    aria-label="Hero section"
  >
    {/* Decorative background gradient blob */}
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 flex items-center justify-center"
    >
      <div
        className="w-[800px] h-[600px] rounded-full opacity-20 blur-3xl"
        style={{
          background: 'radial-gradient(circle, var(--color-primary) 0%, var(--color-accent) 60%, transparent 100%)',
        }}
      />
    </div>

    <div className={`page-container relative z-10 flex flex-col items-center text-center ${getStaggerClass(animationLevel)}`}>
      {content.badge && <Badge label={content.badge} />}

      <h1
        className={`heading-xl max-w-4xl text-5xl md:text-6xl lg:text-7xl ${getSlideUpClass(animationLevel)}`}
      >
        {content.title}
      </h1>

      {content.subtitle && (
        <p
          className={`mt-4 text-xl md:text-2xl font-semibold text-[var(--color-secondary)] ${getSlideUpClass(animationLevel)}`}
        >
          {content.subtitle}
        </p>
      )}

      {content.description && (
        <p
          className={`body-lg mt-6 max-w-2xl ${getEntranceClass(animationLevel)}`}
        >
          {content.description}
        </p>
      )}

      <CtaGroup
        ctaLabel={content.ctaLabel}
        ctaHref={content.ctaHref}
        secondaryLabel={content.secondaryCtaLabel}
        secondaryHref={content.secondaryCtaHref}
        animationLevel={animationLevel}
      />
    </div>
  </section>
);

// ─────────────────────────────────────────────────────────────────────────────
// Variant: left-image  (text left, image right)
// ─────────────────────────────────────────────────────────────────────────────

const LeftImageHero: React.FC<HeroBlockProps> = ({ content, animationLevel, className = '' }) => (
  <section
    className={`block-wrapper ${className}`}
    aria-label="Hero section"
  >
    <div className="page-container grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
      {/* Text column */}
      <div className={`flex flex-col ${getStaggerClass(animationLevel)}`}>
        {content.badge && <Badge label={content.badge} />}

        <h1 className={`heading-xl text-4xl md:text-5xl ${getSlideUpClass(animationLevel)}`}>
          {content.title}
        </h1>

        {content.subtitle && (
          <p className={`mt-3 text-xl font-semibold text-[var(--color-secondary)] ${getSlideUpClass(animationLevel)}`}>
            {content.subtitle}
          </p>
        )}

        {content.description && (
          <p className={`body-lg mt-5 ${getEntranceClass(animationLevel)}`}>
            {content.description}
          </p>
        )}

        <CtaGroup
          ctaLabel={content.ctaLabel}
          ctaHref={content.ctaHref}
          secondaryLabel={content.secondaryCtaLabel}
          secondaryHref={content.secondaryCtaHref}
          animationLevel={animationLevel}
        />
      </div>

      {/* Image column */}
      {content.imageUrl && (
        <div
          className={`relative flex items-center justify-center ${getEntranceClass(animationLevel)}`}
        >
          <div
            aria-hidden="true"
            className="absolute inset-0 rounded-3xl opacity-20 blur-2xl"
            style={{ background: 'radial-gradient(circle, var(--color-primary), transparent 70%)' }}
          />
          <img
            src={content.imageUrl}
            alt={content.imageAlt ?? content.title}
            className="relative z-10 w-full max-w-lg rounded-2xl shadow-2xl object-cover"
            loading="eager"
          />
        </div>
      )}
    </div>
  </section>
);

// ─────────────────────────────────────────────────────────────────────────────
// Variant: full-background
// ─────────────────────────────────────────────────────────────────────────────

const FullBackgroundHero: React.FC<HeroBlockProps> = ({ content, animationLevel, className = '' }) => (
  <section
    className={`relative min-h-screen flex items-center overflow-hidden ${className}`}
    aria-label="Hero section"
  >
    {/* Background image + overlay */}
    {content.imageUrl && (
      <>
        <img
          src={content.imageUrl}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover"
          loading="eager"
        />
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            background: 'linear-gradient(to right, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.4) 60%, transparent 100%)',
          }}
        />
      </>
    )}
    {!content.imageUrl && (
      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background: 'var(--gradient-hero, linear-gradient(135deg, var(--color-bg) 0%, var(--color-surface) 100%))',
        }}
      />
    )}

    {/* Content */}
    <div
      className={`page-container relative z-10 flex flex-col max-w-3xl section-padding ${getStaggerClass(animationLevel)}`}
    >
      {content.badge && <Badge label={content.badge} />}

      <h1
        className={`text-4xl md:text-5xl lg:text-6xl font-bold leading-tight text-white ${getSlideUpClass(animationLevel)}`}
        style={{ color: content.imageUrl ? '#fff' : 'var(--color-text)' }}
      >
        {content.title}
      </h1>

      {content.subtitle && (
        <p
          className={`mt-4 text-xl font-semibold ${getSlideUpClass(animationLevel)}`}
          style={{ color: content.imageUrl ? 'rgba(255,255,255,0.85)' : 'var(--color-secondary)' }}
        >
          {content.subtitle}
        </p>
      )}

      {content.description && (
        <p
          className={`mt-5 text-lg leading-relaxed max-w-xl ${getEntranceClass(animationLevel)}`}
          style={{ color: content.imageUrl ? 'rgba(255,255,255,0.75)' : 'var(--color-text-muted)' }}
        >
          {content.description}
        </p>
      )}

      <CtaGroup
        ctaLabel={content.ctaLabel}
        ctaHref={content.ctaHref}
        secondaryLabel={content.secondaryCtaLabel}
        secondaryHref={content.secondaryCtaHref}
        animationLevel={animationLevel}
      />
    </div>
  </section>
);

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
export const HeroBlock: React.FC<HeroBlockProps> = (props) => {
  switch (props.variant) {
    case 'left-image':
      return <LeftImageHero {...props} />;
    case 'full-background':
      return <FullBackgroundHero {...props} />;
    case 'center-title':
    default:
      return <CenterTitleHero {...props} />;
  }
};

export default HeroBlock;
