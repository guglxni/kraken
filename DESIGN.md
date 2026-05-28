# DESIGN.md — KRAKEN Visual + UX Design System

> Design language for the Captain's Bridge UI. Inspired by Stripe's tasteful illustration aesthetic, not Sea-of-Thieves cosplay. The maritime theme is present but restrained.

---

## Brand identity

**Name:** KRAKEN
**Tagline:** One SQL query. Every system. Every voyage.
**Voice:** Serious tool, evocative wrapper. Confident, factual, never cute.

### Logo
A stylized tentacle forming a SQL `JOIN` symbol (⨝). The tentacle wraps around the symbol from the lower-left, suggesting both "creature reaching across systems" and "operator joining tables."

### Naming layer (UI surfaces)
- **Captain's Bridge** — the home dashboard
- **Spyglass** — the natural-language query bar
- **Reef Map** — the live causal graph
- **Voyage Studio** — the visual JOIN editor
- **Coral Playground** — the SQL REPL
- **Voyage Log** — the table of past executions
- **Bench-O-Bot** — the comparison harness panel
- **Anchor** — the human-approval gate for write actions
- **Reef Memory** — the vector-search learning layer
- **Crow's Nest** — the live trace view (Langfuse spans)
- **Ship's Log** — the kraken.findings Parquet store

These names appear in the UI. The technical labels (SQL, JOIN, agent, query, voyage) appear in tooltips and developer-facing surfaces.

### What we don't use
- Pirate slang ("Ahoy", "Matey", "Yarr")
- Skull emojis
- Treasure chest imagery
- Compass rose flourishes (functional compasses are fine; decorative are not)
- Bottle-and-message metaphors
- "Walking the plank" language for errors

---

## Color palette

### Primary
- **Deep ocean:** `#0B1F33` — primary background
- **Kraken ink:** `#0E0E12` — text on light, deepest backgrounds
- **Bioluminescence:** `#00D4A8` — primary accent, success states, active edges in Reef Map

### Secondary
- **Warning coral:** `#FF6B6B` — error states, critical alerts
- **Lagoon:** `#5EEAD4` — secondary accent, hover states
- **Sandstone:** `#F4E8D1` — light surfaces, cards on dark background
- **Mist:** `#F8FAFC` — page background in light mode

### Functional
- **Success:** `#10B981`
- **Warning:** `#F59E0B`
- **Error:** `#EF4444`
- **Info:** `#3B82F6`

### Reef Map node colors (by source type)
- **Code (GitHub, GitLab):** `#6366F1` (indigo)
- **Errors (Sentry):** `#EF4444` (red)
- **Metrics (Datadog, Grafana, CloudWatch):** `#F59E0B` (amber)
- **Incidents (PagerDuty, incident.io):** `#DC2626` (deep red)
- **Communication (Slack, Gmail):** `#10B981` (green)
- **Customers (Intercom, Stripe):** `#8B5CF6` (purple)
- **Projects (Linear, Jira, ClickUp):** `#3B82F6` (blue)
- **Docs (Notion, Confluence):** `#64748B` (slate)
- **Security (OSV):** `#F97316` (orange)
- **Self (kraken.findings):** `#00D4A8` (bioluminescence)

### Reef Map edge colors (by relationship strength)
- **Strong (foreign key match):** `#00D4A8` solid 2px
- **Medium (inferred join):** `#5EEAD4` dashed 2px
- **Weak (semantic similarity):** `#5EEAD4` dotted 1px

---

## Typography

### Fonts
- **UI:** Inter (variable, weights 400/500/600/700)
- **SQL/Code:** JetBrains Mono (variable, weights 400/500/700)
- **Display (h1 only):** Inter at 800 with -2% letter-spacing

### Scale (Tailwind units)
- **Display:** text-5xl (48px) — Captain's Bridge welcome only
- **H1:** text-3xl (30px) — page titles
- **H2:** text-2xl (24px) — section headers
- **H3:** text-xl (20px) — card titles
- **Body:** text-base (16px) — default
- **Small:** text-sm (14px) — metadata, captions
- **Tiny:** text-xs (12px) — timestamps, badges

### Line heights
- Display: 1.1
- Headers: 1.2
- Body: 1.6
- Code: 1.5

---

## Layout

### Captain's Bridge (home page)
```
┌─────────────────────────────────────────────────────────────┐
│  [logo]  Captain's Bridge                       [user menu] │ 64px topbar
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │                     │  │                              │  │
│  │   Voyage Library    │  │     Risk Heatmap             │  │
│  │   (Tremor grid of   │  │     (Tremor BarList from V7) │  │
│  │   8 voyage cards)   │  │                              │  │
│  │                     │  │                              │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                         ││
│  │            Spyglass (chat input)                        ││
│  │  ┌───────────────────────────────────────────────────┐  ││
│  │  │ Ask anything across your systems...               │  ││
│  │  └───────────────────────────────────────────────────┘  ││
│  │                                                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Voyage Log (last 10 runs)                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Tremor table: voyage name | when | sources | cost │ ⋯  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Spyglass + Reef Map (active voyage)
```
┌─────────────────────────────────────────────────────────────┐
│  [logo]  Voyage: Why is Acme churning?         [back]       │
├──────────────────────────┬──────────────────────────────────┤
│                          │                                  │
│   Spyglass (chat)        │   Reef Map (causal graph)        │
│                          │                                  │
│   You: Why is Acme       │   [animated React Flow graph]    │
│        churning?         │                                  │
│                          │       gmail.messages             │
│   Quartermaster:         │             │                    │
│   Routing to Purser...   │             ▼                    │
│                          │       intercom.contacts          │
│   Purser:                │             │                    │
│   [generative UI card]   │             ▼                    │
│   Customer: Acme Corp    │       stripe.subscriptions       │
│   MRR: $240,000          │             │                    │
│   Root cause: PR #4521   │       ...                        │
│   in dashboard-api       │                                  │
│                          │                                  │
│   Suggested actions:     │   ┌─────────────────────────┐    │
│   [Reply via Gmail]      │   │ Bench-O-Bot panel       │    │
│   [Page on-call]         │   │ Coral: 9s, $0.04        │    │
│   [Rollback PR]          │   │ Direct: 47s, $0.14      │    │
│   [Create Linear ticket] │   └─────────────────────────┘    │
│                          │                                  │
└──────────────────────────┴──────────────────────────────────┘
```

### Voyage Studio (visual JOIN editor)
```
┌─────────────────────────────────────────────────────────────┐
│  [logo]  Voyage Studio                       [save] [export]│
├──────────┬──────────────────────────────────┬───────────────┤
│          │                                  │               │
│ Sources  │   Canvas (React Flow)            │  SQL Output   │
│          │                                  │  (monaco)     │
│ github   │   ┌──────────┐  ┌──────────┐     │               │
│ sentry   │   │ github   │──│ sentry   │     │  SELECT       │
│ slack    │   │ .pulls   │  │ .issues  │     │    p.title,   │
│ datadog  │   └──────────┘  └──────────┘     │    COUNT(s.id)│
│ pagerduty│         │                        │  FROM         │
│ linear   │         ▼                        │    github     │
│ ...      │   ┌──────────┐                   │    .pulls p   │
│          │   │ datadog  │                   │  JOIN         │
│ Custom:  │   │ .metrics │                   │    sentry     │
│ + osv    │   └──────────┘                   │    .issues s  │
│ + gmail  │                                  │  ON ...       │
│          │                                  │               │
│ [drag]   │                                  │  [run] [test] │
└──────────┴──────────────────────────────────┴───────────────┘
```

---

## Component library (shadcn/ui + Tremor)

### Always use
- **Buttons:** shadcn/ui Button. Variants: default (bioluminescence), secondary (sandstone), destructive (warning coral), ghost (transparent), outline.
- **Cards:** shadcn/ui Card with Tremor decorations for data density.
- **Tables:** Tremor Table with @tanstack/react-table headless logic.
- **Charts:** Tremor (BarList, LineChart, AreaChart, DonutChart, Tracker).
- **Inputs:** shadcn/ui Input + Textarea + Select.
- **Dialogs:** shadcn/ui Dialog for confirmations, Sheet for side panels.
- **Tooltips:** shadcn/ui Tooltip on every truncated value.
- **Toasts:** shadcn/ui Sonner for transient notifications.
- **Forms:** react-hook-form + zod, NOT formik or final-form.

### Specialized
- **Reef Map:** React Flow (xyflow) with custom node renderers per source type.
- **SQL Editor:** monaco-editor with our LSP backend for Coral schema autocomplete.
- **Generative UI cards (in chat):** CopilotKit's `useCopilotAction` renderer.
- **Live trace view:** Langfuse embedded UI in an iframe.
- **Voyage cards (home grid):** Tremor Card with hover animation.

### Never build from scratch
- Buttons, inputs, selects (shadcn/ui)
- Tables (Tremor + @tanstack/react-table)
- Charts (Tremor)
- Modals (shadcn/ui Dialog)
- Toast notifications (Sonner)

---

## Animation principles

### Reef Map animations
- Edges draw with 300ms ease-out per hop in the JOIN chain
- New nodes fade-in over 200ms
- Idle nodes have a subtle 4-second pulse animation
- Active query edges have a flowing gradient animation (bioluminescence → lagoon → bioluminescence)
- Click animations: 150ms scale to 1.05 then back to 1.0

### Spyglass chat animations
- Tokens stream at native speed; no artificial delays
- Generative UI cards slide-in from below with 300ms ease-out
- Tool call badges (Coral SQL fired) appear instantly; spinner animation while running

### Loading states
- Use Tremor's skeleton loaders, never spinners on full-page loads
- Spinners only inside buttons during action execution
- Shimmer animation on skeletons (2-second cycle)

### What we don't animate
- Page transitions (none — instant)
- Modal entries (instant fade, no slide)
- Tab switches (instant)
- Hover states beyond color change (no scale, no shadow lift)

---

## Iconography

- **Lucide React** for all icons. Consistent stroke width 1.5px.
- **No custom icons** except the KRAKEN logo.
- **Always pair icons with text labels** for accessibility. Icon-only buttons require Tooltip.

### Semantic mapping (consistent across the app)
- **Voyage:** `Compass`
- **Source:** `Database`
- **Agent:** `Bot`
- **Finding:** `Lightbulb`
- **Plan:** `ListTodo`
- **Query:** `Search`
- **Run:** `Play`
- **Save:** `Save`
- **Edit:** `Pencil`
- **Delete:** `Trash2`
- **Approve (Anchor):** `Anchor`
- **Reject:** `X`
- **External link:** `ExternalLink`
- **Settings:** `Settings`
- **Help:** `HelpCircle`

---

## Accessibility

- WCAG 2.1 AA compliance baseline
- All interactive elements keyboard-navigable
- Focus rings visible (Tailwind `focus-visible:ring-2 ring-bioluminescence`)
- ARIA labels on all icon-only buttons
- Color contrast ratios ≥ 4.5:1 for text
- Reef Map has a text-table fallback view for screen readers
- All animations respect `prefers-reduced-motion`

---

## Empty states

Every list, table, and dashboard has a meaningful empty state with:
1. A relevant Lucide icon (not the page's title icon)
2. A one-line headline
3. A one-line description
4. A primary action button if applicable

### Examples
- **No voyages yet:** "Set sail" / "Run your first voyage to populate the log" / [Run Hot Deploy]
- **No findings yet:** "The crow's nest is empty" / "Specialists haven't written any findings yet" / no button
- **No sources connected:** "Drop anchor first" / "Connect at least one source to start querying" / [Connect Source]

---

## Error states

- **Network errors:** Inline alert at the top of the affected component with retry button
- **Coral query errors:** Inline alert below the Spyglass input with the offending SQL truncated and a "view in trace" link
- **LLM API errors:** Toast notification with fallback path explanation ("Anthropic rate-limited, falling back to OpenAI")
- **Source spec auth errors:** Modal prompting reconnection with clear OAuth flow

### Never do
- Browser `alert()` calls
- Generic "Something went wrong" with no actionable detail
- Errors that disappear before the user can read them (toasts < 5s)

---

## Demo-specific polish

These are required for the demo and tested during the polish phase:

1. **Reef Map hand-tuned layout** for the hero demo. Pre-position nodes so they don't tangle.
2. **Pre-recorded fallback video** in case live demo fails. Captioned "showing pre-recorded demo due to network issue."
3. **All sources pre-connected** before recording. No OAuth flows during the demo.
4. **Loading state durations capped** — anything over 3 seconds gets a skeleton with progress hint.
5. **Cursor visible** in screen recording so reviewers can follow the click path.
6. **Browser zoomed to 110%** for readability on small projector screens.

---

## Mobile + responsive

The Captain's Bridge is **desktop-first**. Mobile is out of scope for the hackathon. Tablet (768-1024px) gets a degraded layout:
- Spyglass + Reef Map stack vertically instead of side-by-side
- Voyage Studio canvas hidden; only source list and SQL output visible
- Voyage Library grid becomes a single column

Below 768px: a "best viewed on desktop" notice with a link to the read-only demo video.

---

## Dark mode

KRAKEN is **dark mode by default** (deep ocean background). Light mode is supported for the documentation site (Astro) only. The main app does not have a light mode for the hackathon.

---

## Storybook (stretch)

If time permits during the polish phase, ship a Storybook with the key components:
- Voyage Card
- Reef Map (with sample data)
- Spyglass message types (user, agent, generative UI card)
- Bench-O-Bot comparison panel

Storybook is judged-favorable evidence of design rigor. Worth the time investment if the polish phase is on track.

---

## Inspiration references

- **Linear** for the chrome density and information architecture
- **Stripe** for the illustration restraint and color palette discipline
- **Vercel** for the developer-tool feel
- **Replit** for the playground UX
- **dbt Cloud** for the lineage visualization conventions
- **Resolve.ai** for incident-graph design language (study, don't copy)

We are NOT inspired by:
- Datadog (visually overloaded)
- Jira (cluttered, dated)
- Slack (chat-centric, wrong category)
- Notion (too text-heavy for an operations tool)
