/**
 * TimelineBlock.tsx
 *
 * Chronological / step-by-step timeline in three layouts:
 *  - vertical:    Classic vertical line with alternating or stacked items
 *  - horizontal:  Scrollable horizontal timeline (great for timelines of events)
 *  - minimal:     Clean numbered list, no connector lines
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

export type TimelineVariant = 'vertical' | 'horizontal' | 'minimal';

export interface TimelineEntry {
  /** Step number, year, or any short label */
  marker: string;
  /** Entry title */
  title: string;
  /** Detailed description */
  description?: string;
  /** Optional ISO date string or display string */
  date?: string;
  /** Optional icon (emoji, SVG, or URL) */
  icon?: string;
  /** Highlight this entry */
  featured?: boolean;
}

export interface TimelineContent {
  /** Section heading */
  heading?: string;
  /** Section subheading */
  subheading?: string;
  entries: TimelineEntry[];
}

export interface TimelineBlockProps extends Omit<BlockProps, 'content' | 'variant'> {
  variant: TimelineVariant;
  content: TimelineContent;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function animSlideUp(level: BlockProps['animationLevel']): string {
  return level === 'none' ? '' : 'animate-slide-up';
}
function animEntrance(level: BlockProps['animationLevel']): string {
  return level === 'none' ? '' : 'animate-entrance';
}
function animStagger(level: BlockProps['animationLevel']): string {
  return level !== 'none' && level !== 'low' ? 'stagger-children' : '';
}

// ─────────────────────────────────────────────────────────────────────────────
// Variant: vertical
// ─────────────────────────────────────────────────────────────────────────────

const VerticalTimeline: React.FC<TimelineBlockProps> = ({
  content, animationLevel, className = '',
}) => (
  <section className={`block-wrapper ${className}`} aria-label={content.heading ?? 'Timeline'}>
    <div className="page-container max-w-3xl mx-auto">
      {(content.heading || content.subheading) && (
        <header className={`section-header-centered ${animEntrance(animationLevel)}`}>
          {content.heading && <h2 className="heading-lg">{content.heading}</h2>}
          {content.subheading && (
            <p className="body-lg mt-3 max-w-2xl mx-auto">{content.subheading}</p>
          )}
        </header>
      )}

      <ol className={`relative pl-8 ${animStagger(animationLevel)}`} aria-label="Timeline">
        {/* Vertical connector */}
        <li aria-hidden="true" className="pointer-events-none">
          <span
            className="absolute left-3.5 top-0 bottom-0 w-0.5"
            style={{
              background: 'linear-gradient(to bottom, var(--color-primary), var(--color-accent))',
            }}
          />
        </li>

        {content.entries.map((entry, idx) => (
          <li
            key={`${entry.marker}-${idx}`}
            className={`relative mb-10 last:mb-0 ${animSlideUp(animationLevel)}`}
          >
            {/* Dot */}
            <span
              className="absolute -left-4 top-1 flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold border-2 z-10"
              style={{
                backgroundColor: entry.featured ? 'var(--color-primary)' : 'var(--color-surface)',
                borderColor: 'var(--color-primary)',
                color: entry.featured ? 'var(--color-text-inverse, #fff)' : 'var(--color-primary)',
                boxShadow: entry.featured ? 'var(--shadow-glow)' : undefined,
              }}
              aria-hidden="true"
            >
              {entry.icon ?? entry.marker}
            </span>

            {/* Card */}
            <div
              className={`ml-4 p-5 rounded-xl border transition-all duration-200 ${
                entry.featured ? 'border-[var(--color-primary)]' : 'border-[var(--color-border)]'
              }`}
              style={{
                backgroundColor: 'var(--color-surface)',
                boxShadow: entry.featured ? 'var(--shadow-glow)' : 'var(--shadow-card)',
              }}
            >
              {entry.date && (
                <time className="block text-xs font-semibold uppercase tracking-wider mb-1"
                      style={{ color: 'var(--color-text-muted)' }}>
                  {entry.date}
                </time>
              )}
              <h3 className="text-base font-semibold" style={{ color: 'var(--color-text)' }}>
                {entry.title}
              </h3>
              {entry.description && (
                <p className="body-sm mt-1">{entry.description}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  </section>
);

// ─────────────────────────────────────────────────────────────────────────────
// Variant: horizontal
// ─────────────────────────────────────────────────────────────────────────────

const HorizontalTimeline: React.FC<TimelineBlockProps> = ({
  content, animationLevel, className = '',
}) => (
  <section className={`block-wrapper ${className}`} aria-label={content.heading ?? 'Timeline'}>
    <div className="page-container">
      {(content.heading || content.subheading) && (
        <header className={`section-header-centered ${animEntrance(animationLevel)}`}>
          {content.heading && <h2 className="heading-lg">{content.heading}</h2>}
          {content.subheading && (
            <p className="body-lg mt-3 max-w-2xl mx-auto">{content.subheading}</p>
          )}
        </header>
      )}

      {/* Scrollable horizontal track */}
      <div className="overflow-x-auto pb-4">
        <ol
          className={`relative flex gap-0 min-w-max ${animStagger(animationLevel)}`}
          aria-label="Timeline"
        >
          {content.entries.map((entry, idx) => (
            <li
              key={`${entry.marker}-${idx}`}
              className={`relative flex flex-col items-center w-48 ${animEntrance(animationLevel)}`}
            >
              {/* Connector line */}
              {idx < content.entries.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute top-4 left-1/2 w-full h-0.5 -translate-y-1/2"
                  style={{ background: 'var(--color-border)', left: '50%' }}
                />
              )}

              {/* Dot */}
              <span
                className="relative z-10 flex items-center justify-center w-9 h-9 rounded-full text-sm font-bold border-2 mb-3"
                style={{
                  backgroundColor: entry.featured ? 'var(--color-primary)' : 'var(--color-surface)',
                  borderColor: 'var(--color-primary)',
                  color: entry.featured ? 'var(--color-text-inverse, #fff)' : 'var(--color-primary)',
                }}
                aria-hidden="true"
              >
                {entry.icon ?? entry.marker}
              </span>

              {/* Label */}
              <div className="text-center px-2">
                {entry.date && (
                  <time className="block text-xs font-semibold uppercase tracking-wider mb-0.5"
                        style={{ color: 'var(--color-text-muted)' }}>
                    {entry.date}
                  </time>
                )}
                <p className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                  {entry.title}
                </p>
                {entry.description && (
                  <p className="text-xs mt-1 leading-snug" style={{ color: 'var(--color-text-muted)' }}>
                    {entry.description}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  </section>
);

// ─────────────────────────────────────────────────────────────────────────────
// Variant: minimal
// ─────────────────────────────────────────────────────────────────────────────

const MinimalTimeline: React.FC<TimelineBlockProps> = ({
  content, animationLevel, className = '',
}) => (
  <section className={`block-wrapper ${className}`} aria-label={content.heading ?? 'Timeline'}>
    <div className="page-container max-w-2xl mx-auto">
      {(content.heading || content.subheading) && (
        <header className={`section-header ${animEntrance(animationLevel)}`}>
          {content.heading && <h2 className="heading-lg">{content.heading}</h2>}
          {content.subheading && (
            <p className="body-lg mt-3">{content.subheading}</p>
          )}
        </header>
      )}

      <ol className={`space-y-6 ${animStagger(animationLevel)}`} aria-label="Timeline">
        {content.entries.map((entry, idx) => (
          <li
            key={`${entry.marker}-${idx}`}
            className={`flex items-start gap-5 ${animSlideUp(animationLevel)}`}
          >
            {/* Number badge */}
            <span
              className="shrink-0 flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold"
              style={{
                backgroundColor: 'rgba(var(--color-primary-rgb,37,99,235),0.1)',
                color: 'var(--color-primary)',
              }}
              aria-hidden="true"
            >
              {entry.icon ?? entry.marker}
            </span>

            <div className="flex-1 pt-1">
              {entry.date && (
                <time className="block text-xs font-semibold uppercase tracking-wider mb-0.5"
                      style={{ color: 'var(--color-text-muted)' }}>
                  {entry.date}
                </time>
              )}
              <h3 className="text-base font-semibold" style={{ color: 'var(--color-text)' }}>
                {entry.title}
              </h3>
              {entry.description && (
                <p className="body-sm mt-1">{entry.description}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  </section>
);

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
export const TimelineBlock: React.FC<TimelineBlockProps> = (props) => {
  switch (props.variant) {
    case 'horizontal':
      return <HorizontalTimeline {...props} />;
    case 'minimal':
      return <MinimalTimeline {...props} />;
    case 'vertical':
    default:
      return <VerticalTimeline {...props} />;
  }
};

export default TimelineBlock;
