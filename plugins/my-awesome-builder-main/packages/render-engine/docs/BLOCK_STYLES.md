# Block Styles Reference

Complete mapping of all 30 block types × 3 variants with their primary Tailwind utility classes and CSS custom-property usage.

> **Reading the table:** The "Tailwind classes" column lists the *wrapper/outer-element* classes. Inner elements use component classes defined in `styles/components.css` (e.g. `.card`, `.glass-card`, `.btn-primary`).

---

## hero

### center-title
```
flex flex-col items-center text-center py-24 px-6
```
Inner: `heading-xl text-5xl md:text-6xl lg:text-7xl`, `body-lg max-w-2xl`, `btn-primary btn-lg`

### left-image
```
grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center py-16 px-6
```
Inner: `heading-xl text-4xl md:text-5xl`, image `rounded-2xl shadow-2xl`

### full-background
```
relative min-h-screen flex items-center overflow-hidden
```
Inner: overlay `absolute inset-0 bg-gradient-to-r from-black/75`, content `relative z-10`

---

## split_hero

### image-right
```
grid grid-cols-1 lg:grid-cols-2 gap-10 items-center py-16 px-6
```

### image-left
```
grid grid-cols-1 lg:grid-cols-2 gap-10 items-center py-16 px-6
[&>img]:order-first lg:[&>img]:order-last
```

### alternate
```
flex flex-col gap-20 py-16 px-6
[&>section:nth-child(even)]:flex-row-reverse
```

---

## info_cards

### flat
```
grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
```
Card: `.card` → `bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6`

### glass
```
grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
```
Card: `.glass-card` → `backdrop-blur-md bg-white/8 border border-white/15 rounded-xl p-6`

### bordered
```
grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
```
Card: `.bordered-card` → `border-2 border-[var(--color-primary)] rounded-xl p-6`

---

## timeline

### vertical
```
relative pl-8 space-y-10
```
Connector: `absolute left-3.5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary to-accent`
Dot: `absolute -left-4 w-8 h-8 rounded-full border-2 border-primary`

### horizontal
```
flex overflow-x-auto gap-0 pb-4 min-w-max
```
Each item: `relative flex flex-col items-center w-48`

### minimal
```
space-y-6
```
Each item: `flex items-start gap-5`, number badge `w-10 h-10 rounded-full bg-primary/10 text-primary`

---

## quiz

### choice
```
space-y-6 max-w-2xl mx-auto
```
Option: `.quiz-option` → `card cursor-pointer px-4 py-3`, states `.selected`, `.correct`, `.incorrect`

### flashcard
```
space-y-6 max-w-md mx-auto
```
Flip wrapper: `[perspective:1000px]`, front/back: `[backface-visibility:hidden]`, back: `rotateY(180deg)`

### instant-check
```
space-y-6 max-w-2xl mx-auto
```
Input: `.input-base`, feedback: `bg-green-500/10 text-green-700` or `bg-red-500/10 text-red-700`

---

## section_header

### simple
```
mb-10
```
Inner: `heading-lg`, `body-lg mt-3`

### decorated
```
mb-10 text-center
```
Inner: `section-label` (with `::before` line), `heading-lg`, gradient underline `h-1 w-16 bg-gradient-to-r from-primary to-accent mx-auto mt-3`

### full-width
```
w-full py-12 px-6 bg-[var(--color-surface)]
```
Inner: `page-container flex items-center justify-between`

---

## anchor_nav

### horizontal
```
flex overflow-x-auto gap-2 py-3 sticky top-0 bg-[var(--color-bg)] z-40
```
Link: `px-4 py-1.5 rounded-full text-sm font-medium transition-colors`

### vertical
```
flex flex-col gap-1 sticky top-20
```
Link: `px-3 py-2 rounded-lg text-sm font-medium`

### floating
```
fixed bottom-6 right-6 z-50
```
Trigger: `btn-icon glass-card`

---

## sidebar_index

### simple
```
space-y-1 text-sm
```
Link: `block px-3 py-1.5 rounded text-[var(--color-text-muted)] hover:text-primary`

### numbered
```
space-y-1 text-sm counter-reset-[section]
```
Item: `flex gap-2 items-start`, counter badge `text-xs font-bold text-primary`

### collapsible
```
space-y-1 text-sm
```
Group: `disclosure` pattern, icon `chevron-down rotate-180 when-open`

---

## two_column_layout

### equal
```
grid grid-cols-1 lg:grid-cols-2 gap-10
```

### sidebar-right
```
grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-10
```

### sidebar-left
```
grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-10
```

---

## footer

### minimal
```
flex items-center justify-between py-6 px-6
border-t border-[var(--color-border)] text-sm text-[var(--color-text-muted)]
```

### rich
```
grid grid-cols-2 lg:grid-cols-4 gap-8 py-12 px-6
```

### centered
```
flex flex-col items-center gap-6 py-10 px-6 text-center
```

---

## profile_cards

### portrait
```
grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4
```
Card: `.card flex flex-col items-center text-center`, avatar `w-20 h-20 rounded-full`

### horizontal
```
flex flex-col gap-5
```
Card: `.card flex gap-4 items-center`

### featured
```
grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-8 items-center
```

---

## step_flow

### numbered
```
grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8
```
Number: `text-6xl font-black text-primary/20`

### arrow
```
flex flex-wrap items-center justify-center gap-4
```
Arrow: `text-[var(--color-text-muted)]` SVG `w-6 h-6`

### circular
```
flex flex-wrap justify-center gap-8
```
Node: `w-20 h-20 rounded-full border-2 border-primary`

---

## table_section

### simple
```
overflow-x-auto
```
Table: `w-full`, `th` `font-semibold bg-[var(--color-surface-alt)]`

### striped
```
overflow-x-auto [&_tbody_tr:nth-child(even)]:bg-[var(--color-surface-alt)]
```

### comparison
```
overflow-x-auto
```
Tick: `text-green-500`, Cross: `text-red-500`

---

## definition_box

### simple
```
border-l-4 border-[var(--color-primary)] pl-4 py-2
```

### highlighted
```
rounded-xl p-5 bg-[rgba(var(--color-primary-rgb,37,99,235),0.08)]
border border-[var(--color-primary)]/20
```

### card
```
.card
```
Header: `text-xs font-semibold uppercase tracking-wider text-primary`

---

## quote_panel

### simple
```
border-l-4 border-[var(--color-primary)] pl-6 py-2 italic
```

### large
```
text-center py-12 px-6 relative
```
Quote mark: `text-[10rem] leading-none text-primary/10 absolute -top-6 left-6`

### attributed
```
.card flex gap-5
```
Avatar: `w-14 h-14 rounded-full shrink-0`

---

## code_panel

### simple
```
.code-block
```
Header: `.code-block-header`, dots: `.code-dot bg-red-500`, `.code-dot bg-amber-500`, `.code-dot bg-green-500`

### terminal
```
.code-block-terminal
```
Prompt: `text-[#7ee787]` before content

### highlighted
```
.code-block
```
Highlighted line: `bg-[var(--color-primary)]/10 -mx-6 px-6 border-l-2 border-primary`

---

## diagram_cards

### grid
```
grid gap-5 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
```
Card: `.feature-card`

### flow
```
flex flex-wrap items-center justify-center gap-4
```
Connector: SVG arrow `w-8 text-[var(--color-text-muted)]`

### feature
```
grid gap-8 grid-cols-1 sm:grid-cols-2
```
Card: `.card p-8`, icon: `w-16 h-16`

---

## accordion_faq

### simple
```
divide-y divide-[var(--color-border)]
```
Trigger: `flex items-center justify-between w-full py-4 text-left font-semibold`

### bordered
```
space-y-3
```
Item: `rounded-xl border border-[var(--color-border)] overflow-hidden`

### colored
```
space-y-3
```
Open item: `bg-[rgba(var(--color-primary-rgb),0.06)]`

---

## checklist_summary

### simple
```
space-y-3
```
Item: `flex items-center gap-3`, checkbox `w-5 h-5 rounded border-2`

### detailed
```
space-y-4
```
Item: `.card flex gap-4`, description `body-sm mt-1`

### progress
```
space-y-4
```
Progress bar: `.progress-bar-track` + `.progress-bar-fill`

---

## image_gallery

### grid
```
grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4
```
Image: `rounded-xl object-cover aspect-square`

### masonry
```
columns-2 sm:columns-3 lg:columns-4 gap-3
```
Image: `w-full rounded-xl mb-3 break-inside-avoid`

### carousel
```
flex overflow-x-auto snap-x snap-mandatory gap-4 pb-2
```
Item: `shrink-0 snap-center w-64 sm:w-80`

---

## feature_banner

### simple
```
flex items-center gap-6 rounded-xl p-6 bg-[var(--color-surface)]
border border-[var(--color-border)]
```

### gradient
```
rounded-2xl p-8 overflow-hidden relative
background: var(--gradient-primary)
```

### pattern
```
rounded-2xl p-8 overflow-hidden relative bg-alexandros-pattern
```

---

## progress_meter

### bar
```
space-y-3
```
Track: `.progress-bar-track`, fill: `.progress-bar-fill`

### circle
```
flex flex-wrap gap-6 justify-center
```
SVG ring: `stroke-dasharray`, `stroke-dashoffset`

### steps
```
flex items-center gap-0
```
Step: `w-8 h-8 rounded-full border-2`, connector: `flex-1 h-0.5`

---

## statistic_circle

### simple
```
grid gap-6 grid-cols-2 lg:grid-cols-4
```
Number: `text-4xl font-black text-[var(--color-primary)]`

### animated
```
grid gap-6 grid-cols-2 lg:grid-cols-4
```
Uses `CountUp` animation on intersection observer

### comparison
```
grid gap-8 grid-cols-1 sm:grid-cols-2
```

---

## comparison_split

### side-by-side
```
grid grid-cols-1 sm:grid-cols-2 gap-6
```

### overlay
```
relative overflow-hidden rounded-xl cursor-ew-resize
```
Slider: `absolute inset-y-0 w-0.5 bg-white cursor-ew-resize`

### table
```
overflow-x-auto
```
Header row: `bg-[var(--color-primary)] text-white`

---

## spotlight_panel

### centered
```
flex flex-col items-center text-center gap-4 py-12 px-6
```

### split
```
grid grid-cols-1 lg:grid-cols-2 min-h-[400px]
```
Left: `bg-[var(--color-primary)]`, Right: `bg-[var(--color-surface)]`

### hero
```
relative rounded-2xl overflow-hidden p-10 min-h-[320px] flex items-center
```

---

## mini_test

### text
```
.card max-w-xl mx-auto space-y-4
```
Input: `textarea .input-base rows-4`

### fill-blank
```
.card max-w-xl mx-auto space-y-4
```
Blank input: `.input-base inline-block w-32 mx-1`

### matching
```
grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl mx-auto
```
Drop targets: `rounded-lg border-2 border-dashed border-[var(--color-border)] p-3`

---

## download_cta

### button
```
inline-flex items-center gap-3
```
Icon: `w-5 h-5`, label: `.btn-primary`

### card
```
.card flex gap-4 items-start
```
Thumbnail: `w-16 h-16 rounded-lg object-cover shrink-0`

### banner
```
flex flex-col sm:flex-row items-center justify-between gap-4
rounded-xl p-6 bg-[var(--color-surface-alt)]
```

---

## next_lesson

### simple
```
flex items-center justify-between py-6
border-t border-[var(--color-border)]
```

### preview
```
.card flex gap-5 items-center
```
Thumbnail: `w-20 h-14 rounded-lg object-cover shrink-0`

### progress
```
.card space-y-4
```
Progress bar: `.progress-bar-track` + `.progress-bar-fill`

---

## contact_box

### simple
```
space-y-4
```
Row: `flex items-center gap-3 text-sm`

### card
```
.card space-y-5 max-w-lg mx-auto
```
Fields: `.input-base`, submit: `.btn-primary w-full`

### sidebar
```
.card space-y-3 text-sm
```

---

## final_message

### simple
```
text-center py-12 space-y-4 max-w-xl mx-auto
```

### celebration
```
text-center py-16 space-y-6 relative overflow-hidden
```
Badge: `inline-flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-white`

### summary
```
.card max-w-2xl mx-auto space-y-6
```
Checklist recap: `space-y-2 text-sm`, CTA: `.btn-primary w-full`
