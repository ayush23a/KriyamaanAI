# Kriyamaan UI — Next.js + TypeScript Research Workspace

Production-quality conversational Agentic RAG frontend for Kriyamaan, designed with a warm editorial light theme, conversation-first progressive disclosure, and integration with the Kriyamaan FastAPI runtime.

## Visual Design System
- **Theme**: Warm ivory (`#FAF8F5`), white, and charcoal text (`#1C1917` / `#44403C`).
- **Primary Accent**: Muted Terracotta (`#C25E43`).
- **Success Accent**: Muted Olive (`#5F7143`).
- **Surface**: Subtle glassmorphism (`backdrop-blur-md bg-white/88 border border-stone-200/85`).
- **Icons**: Lucide SVG icons exclusively.

## Core Features
1. **Conversation-First Workspace**:
   - Distinct user messages and assistant editorial typography.
   - Markdown rendering with syntax-highlighted code blocks and copy buttons.
   - Expandable Verified Evidence drawer with score attribution and citations (`[1]`, `[2]`).
   - Progressive live statuses: *Searching your knowledge...*, *Searching the web...*, *Checking evidence...*, *Preparing answer...*
   - Stop generation, regenerate response, and edit user query.
2. **Execution Inspector (Right Drawer)**:
   - Live telemetry: prompt & completion tokens, latency, cost ($USD), semantic cache status.
   - Agent iterations and monotonic budget meters.
   - Structured step-by-step event replay.
   - Evidence judge assessment details.
3. **Collapsible Sidebar**:
   - Conversations grouped by **Today**, **Yesterday**, and **Older**.
   - Search filter for conversations.
   - Live backend health status pill with dependency diagnostic popover.
   - Mobile responsive drawer.
4. **Knowledge Library**:
   - Drag-and-drop ingestion of PDF, DOCX, TXT, MD, HTML.
   - Real-time indexing status, chunk counts, SHA-256 digests.
   - Document inspection and deletion.
5. **Explicit Long-Term Memory**:
   - User-approved memories categorized by User Preferences, Domain Facts, and Project Directives.
   - CRUD management linked to principal memory namespaces.
6. **Agent Settings**:
   - Monotonic budgets: Max retrieval iterations, max tool calls, latency budgets, max output tokens.
   - Response mode (Concise vs. Detailed).
   - Web search fallback toggle.
   - Developer diagnostics.

## Running Locally

```bash
# Navigate to UI directory
cd kriyaman_ui

# Install dependencies (with Bun or npm)
bun install
# or
npm install

# Run development server (on port 3000)
bun run dev
# or
npm run dev

# Build for production
bun run build
```

## Backend Configuration
The UI connects to the FastAPI backend via `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000/api/v1`), which can also be adjusted on the fly in the in-app Settings panel.

