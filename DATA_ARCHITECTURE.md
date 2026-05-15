# Morning Ritual — Data Architecture

## System Overview

```mermaid
graph TB
    subgraph sources["📊 Data Sources"]
        gmail["📧 Gmail<br/>Forum Tab<br/>19+ newsletters"]
        calendar["📅 Google Calendar<br/>Next 7 days<br/>Events + Deadlines"]
        markdown["📝 Month Markdown<br/>May 2026.md<br/>Domain Tasks"]
    end

    subgraph platforms["🔌 Platforms & Credentials"]
        mcp_gmail["Gmail MCP<br/>OAuth<br/>No token storage"]
        mcp_cal["Calendar MCP<br/>OAuth<br/>No token storage"]
        resend["Resend API<br/>.env file<br/>RESEND_API_KEY"]
    end

    subgraph processing["⚙️ Processing Pipeline"]
        digest_skill["newsletter-digest Skill<br/>Fetch 19 emails<br/>Parallel analysis"]
        fetch_cal["Fetch Calendar<br/>Read Markdown"]
        parse_md["Parse Markdown<br/>Regex extraction<br/>7 domains"]
        python_gen["generate_morning_html.py<br/>Merge data<br/>Render HTML"]
    end

    subgraph outputs["📦 Outputs"]
        html["✅ morning-ritual.html<br/>40KB static file<br/>All data baked in"]
        email["✉️ Email Digest<br/>via Resend API<br/>3k/month free"]
        archive["📂 Archive Copy<br/>morning-YYYY-MM-DD.html<br/>Historical tracking"]
    end

    subgraph browser["🌐 Display Layer"]
        open["macOS: open command<br/>Default browser<br/>Instant load"]
        display["5 Sections:<br/>Session Recap<br/>Calendar<br/>Kanban<br/>Coffee Card<br/>Newsletters"]
    end

    gmail -->|search_threads<br/>category:forums<br/>newer_than:1d| mcp_gmail
    calendar -->|list_events<br/>startTime - endTime| mcp_cal
    markdown -->|Auto-detect<br/>$(date '+%b %Y')| fetch_cal

    mcp_gmail -->|19+ emails| digest_skill
    mcp_cal -->|Today + 7 days| fetch_cal
    fetch_cal -->|Kanban data<br/>Colors + Tasks| parse_md

    digest_skill -->|Analyzed JSON<br/>+ HTML| python_gen
    parse_md -->|Domain matrix<br/>3 weeks × 7 domains| python_gen
    python_gen -->|Generate| html

    html -->|Send via curl| resend
    resend -->|SMTP| email

    html -->|cp dated copy| archive
    html -->|File path| open
    open -->|Zero API calls| display

    style sources fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style platforms fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style processing fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style outputs fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style browser fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style html fill:#4caf50,color:#fff,stroke-width:3px
    style display fill:#2196f3,color:#fff,stroke-width:3px
```

## Data Flow Details

### 1. **Data Sources**

#### Gmail — Newsletter Inbox
- **Query**: `category:forums newer_than:1d` (past 24 hours)
- **Count**: 19+ newsletters from Substack, newsletters.com, etc.
- **MCP Tool**: `search_threads()` → `get_thread()` with `FULL_CONTENT`
- **Output**: Plain text body + sender + subject

#### Google Calendar — Context Window
- **Time Range**: Today at 00:00 → +7 days at 23:59
- **Fields**: Event name, time, duration, attendees
- **MCP Tool**: `list_events()` with ISO 8601 timestamps
- **Output**: Structured calendar events

#### Month Markdown — Strategic Planning
- **Path**: `calendar-projects/May 2026.md` (auto-detected)
- **Format**: 
  ```markdown
  ## Week of May 11-17
  ### Immigration
  - [ ] Task 1
  - [ ] Task 2
  ```
- **Parsing**: Regex extraction by domain and week
- **Output**: Dict of {domain: {week: [tasks]}}

---

### 2. **Processing Pipeline**

#### Step 1: Newsletter Digest (30–45 seconds)
- `/newsletter-digest` skill invoked
- Spawns 5 `newsletter-analyzer` subagents in batches
- Each analyzes one email → JSON (sender, summary_html, key_stats, original_link)
- Writes to `.tmp/digest.json` (array of analyzed newsletters)
- Sends digest email via Resend API

**Critical**: Step 0 deletes all `.tmp/` cache before starting fresh fetch.

#### Step 2: Fetch Calendar + Markdown (3–5 seconds)
- Parallel execution:
  - Google Calendar MCP: `list_events(startTime, endTime)`
  - File read: `Path('calendar-projects/May 2026.md').read_text()`

#### Step 3: Parse Kanban (1–2 seconds)
- Regex patterns extract week sections and domains
- Build 2D matrix: {week: {domain: [tasks]}}
- Match domain names to color palette (7 colors)

#### Step 4: Render HTML (<100ms)
- Read `.tmp/digest.json`
- Insert newsletter rows into table template
- Build kanban HTML table with color-coded cells
- Embed session recap (fixated format)
- Generate complete HTML with fresh timestamp

---

### 3. **Outputs**

#### Primary Output: morning-ritual.html
- **Size**: ~40KB static HTML file
- **Location**: `.claude/skills/morning/morning-ritual.html`
- **Sections**:
  1. **Session Recap** — Top 5 topics (fixated format, 💻 emoji)
  2. **Calendar** — Today + Upcoming
  3. **Kanban Board** — 7 domains × 3 weeks
  4. **Coffee Card** — Floating ☕ animation
  5. **Newsletter Digest** — Full HTML table (19 rows)

#### Secondary Output: Email Digest
- **Recipient**: `RESEND_TO` from `.env`
- **Subject**: `Newsletter Digest — YYYY-MM-DD`
- **Body**: Subset of morning-ritual.html (newsletter table only)
- **API**: Resend (curl POST, no Python urllib — avoids macOS cert issues)

#### Archive: Dated Copy
- **Location**: `calendar-projects/morning/morning-YYYY-MM-DD.html`
- **Purpose**: Historical tracking (compare yesterday's vs. today's briefing)

---

### 4. **Display Layer**

#### Opening the File
- **Command**: `open .claude/skills/morning/morning-ritual.html`
- **Why macOS `open` instead of Chrome DevTools MCP**:
  - Uses system default browser (no lock conflicts)
  - Avoids Chrome DevTools MCP contention
  - Simpler, faster, more reliable

#### Browser Load Time
- **Zero additional API calls** (all data baked into HTML)
- **Instant render** (<100ms after browser opens)
- **Timestamp proof** — "Generated at HH:MM PM" shows data is fresh

---

## Platform & Credential Architecture

### OAuth Connections (No Storage)
| Platform | MCP Tool | Credentials | Scope |
|----------|----------|-------------|-------|
| Gmail | search_threads, get_thread | OAuth | Read-only Forum tab |
| Google Calendar | list_events | OAuth | Read-only events |

**Note**: Both use claude.ai integration — no token files stored locally.

### API Keys (Environment Variables)
| Service | Key | Storage | Scope |
|---------|-----|---------|-------|
| Resend | RESEND_API_KEY | `.env` file | Send emails from verified sender |
| Resend | RESEND_FROM | `.env` file | Sender email (must be verified in dashboard) |
| Resend | RESEND_TO | `.env` file | Recipient email address |

**Important**: `.env` is in `.gitignore` — never committed.

---

## Performance Breakdown

| Phase | Duration | Critical Path? | Notes |
|-------|----------|---|---|
| Newsletter fetch + analyze | 30–45s | ✅ YES | Bottleneck: subagent batching (5-7 per wave) |
| Calendar + markdown read | 3–5s | — | Parallel with newsletter analysis |
| Kanban parsing | 1–2s | — | Regex extraction |
| HTML generation | <100ms | — | Python string templating |
| Browser open + render | ~10s | — | OS startup time |
| **Total** | **~60–80s** | — | End-to-end, daily execution |

---

## Data Validation & Safety

### Sanitization Checklist for GitHub Publishing
- ✅ Remove absolute paths (replace with `$HOME` or relative paths)
- ✅ Remove personal emails (use `your-email@example.com`)
- ✅ Remove API keys (move to `.env`, add to `.gitignore`)
- ✅ Remove domain names (use examples like `example.com`)
- ✅ Remove task examples (use placeholders)
- ✅ Documentation-only: no secrets in markdown files

### Security Notes
- **No credentials in code**: Only `.env` file (excluded via `.gitignore`)
- **MCP OAuth**: All tokens managed by claude.ai — not stored locally
- **Resend API**: Called via curl (system cert store), not Python urllib
- **HTML injection risk**: Newsletter HTML is user-controlled → consider sanitizing in production

---

## Extending This System

Same architecture scales to:
- **Weekly review** — aggregate 7 daily mornings → plan next week
- **Monthly review** — consolidate 4 weeks → adjust quarterly targets
- **Quarterly planning** — assess progress → refine annual vision

All share the same:
- Data source abstraction (Gmail, Calendar, Markdown)
- MCP orchestration pattern
- Python HTML generation
- Static file output

---

## Troubleshooting Data Flow

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Newsletter digest fails | Resend API error | Check RESEND_API_KEY, verify sender domain |
| Kanban blank | Markdown format | Verify `## Week of` and `### Domain` sections |
| Calendar events missing | API permissions | Confirm Google Calendar OAuth scope |
| HTML doesn't open | File permissions | `chmod +x morning-ritual.html` or check path |
| Old data appears | Cache not cleared | Ensure Step 0 deletes `.tmp/` before fetch |

---

**Last Updated**: May 15, 2026  
**Script Version**: generate_morning_html.py (with kanban parsing, fixated session recap, coffee card)
