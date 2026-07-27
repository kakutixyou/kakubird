# Block Styles Reference

## 30 Blocks with 3 Variants Each

### Hero Block
- **center-title**: Headline centered, full-width background
- **left-image**: Image on right, text on left
- **full-background**: Full-screen background image

### Split Hero Block
- **image-right**: Image right side, text left
- **image-left**: Image left side, text right
- **alternate**: Alternating image/text layout

### Info Cards Block
- **flat**: Clean card grid
- **glass**: Glassmorphism cards
- **bordered**: Outlined cards

### Timeline Block
- **vertical**: Vertical timeline
- **horizontal**: Horizontal scrollable timeline
- **minimal**: Minimal text-only timeline

### Quiz Block
- **choice**: Multiple choice
- **flashcard**: Flashcard flip
- **instant-check**: Instant feedback quiz

### Section Header Block
- **simple**: Plain heading
- **decorated**: With decorative elements
- **full-width**: Full-width spanning header

### Anchor Nav Block
- **horizontal**: Tab-style horizontal nav
- **vertical**: Sidebar vertical nav
- **floating**: Floating sticky nav

### Sidebar Index Block
- **simple**: Plain list
- **numbered**: Numbered list
- **collapsible**: Collapsible sections

### Two Column Layout Block
- **equal**: Equal 50/50 split
- **sidebar-right**: Main content + right sidebar
- **sidebar-left**: Left sidebar + main content

### Footer Block
- **minimal**: Logo + links
- **rich**: Multi-column footer
- **centered**: Centered single-column footer

### Profile Cards Block
- **portrait**: Vertical portrait cards
- **horizontal**: Horizontal bio cards
- **featured**: Featured large profile

### Step Flow Block
- **numbered**: Numbered steps
- **arrow**: Arrow-connected steps
- **circular**: Circular process diagram

### Table Section Block
- **simple**: Plain table
- **striped**: Alternating row colors
- **comparison**: Feature comparison table

### Definition Box Block
- **simple**: Term + definition
- **highlighted**: Highlighted term
- **card**: Card-style definition

### Quote Panel Block
- **simple**: Plain blockquote
- **large**: Large display quote
- **attributed**: Quote with author attribution

### Code Panel Block
- **simple**: Plain code block
- **terminal**: Terminal-style dark panel
- **highlighted**: Syntax-highlighted code

### Diagram Cards Block
- **grid**: Grid of diagram items
- **flow**: Flow diagram layout
- **feature**: Feature highlight cards

### Accordion FAQ Block
- **simple**: Plain accordion
- **bordered**: Bordered accordion items
- **colored**: Colored header accordion

### Checklist Summary Block
- **simple**: Simple checklist
- **detailed**: Detailed items with descriptions
- **progress**: Progress-tracking checklist

### Image Gallery Block
- **grid**: Fixed grid gallery
- **masonry**: Masonry layout gallery
- **carousel**: Carousel/slider gallery

### Feature Banner Block
- **simple**: Text + CTA banner
- **gradient**: Gradient background banner
- **pattern**: Pattern background banner

### Progress Meter Block
- **bar**: Horizontal progress bar
- **circle**: Circular progress indicator
- **steps**: Step-based progress tracker

### Statistic Circle Block
- **simple**: Simple number display
- **animated**: Animated counting number
- **comparison**: Side-by-side comparison stats

### Comparison Split Block
- **side-by-side**: Two columns side by side
- **overlay**: Overlay comparison
- **table**: Table comparison format

### Spotlight Panel Block
- **centered**: Centered spotlight content
- **split**: Split image + text spotlight
- **hero**: Hero-style spotlight

### Mini Test Block
- **text**: Text answer input
- **fill-blank**: Fill in the blank
- **matching**: Matching pairs exercise

### Download CTA Block
- **button**: Button-style CTA
- **card**: Card-style download CTA
- **banner**: Full-width download banner

### Next Lesson Block
- **simple**: Simple next lesson link
- **preview**: Preview card of next lesson
- **progress**: Progress + next lesson

### Contact Box Block
- **simple**: Simple contact form
- **card**: Card-style contact info
- **sidebar**: Sidebar contact widget

### Final Message Block
- **simple**: Simple closing message
- **celebration**: Celebration/completion message
- **summary**: Course summary + message

---

## Surface Recommendations
Default surfaces per block type are defined in `BLOCK_SURFACE_DEFAULTS` in
`packages/ai-engine/schema_rules.py`. Override per block by adding a `"surface"` field
to the block in the page schema.

Available surfaces: `flat` | `glass` | `neumorphism` | `bordered` | `elevated` | `paper` | `glow` | `frosted-dark`
