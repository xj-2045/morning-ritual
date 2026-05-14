# Morning Ritual — Technical Architecture

## Overview

The Morning Ritual is a fully-automated daily briefing system that consolidates newsletters, calendar events, and monthly task planning into a single HTML artifact. It runs at 7:00 AM daily, requiring ~60–80 seconds total.

---

## Components

### **1. Skills**

#### `/morning` — Orchestrator
- Entry point: runs daily or on-demand
- Coordinates Steps 0–5 sequentially
- Waits for newsletter-digest completion before proceeding
- Invokes Python script to generate HTML
- Calls Chrome DevTools MCP to open browser

**File**: `.claude/skills/morning/SKILL.md`

#### `/newsletter-digest` — Newsletter Collection & Analysis
- Fetches emails from Gmail Forum tab (category:forums, newer_than:1d)
- Spawns 19 parallel subagents (`newsletter-analyzer`) in batches of 5–7
- Batching reduces file I/O contention; actually runs **faster** than all-at-once (30–45s vs. 50–65s)
- Analyzes each email: extracts summary, key stats, and source link
- Sends HTML digest to user inbox via Resend API
- Outputs: `newsletter_digest_YYYY-MM-DD.html`

**File**: `.claude/skills/newsletter-digest/SKILL.md`

### **2. MCP Servers**

#### **Gmail (claude.ai integration)**
- `search_threads`: query:category:forums, newer_than:1d, pageSize:50
- `get_thread`: fetch full content for each thread (FULL_CONTENT format)
- No OAuth setup needed; uses claude.ai's built-in Gmail MCP

#### **Google Calendar (claude.ai integration)**
- `list_events`: fetches today + next 7 days + past 5 days (for retrospective context)
- Returns structured event data: title, time, date
- No OAuth setup needed; uses claude.ai's built-in Google Calendar MCP

#### **Chrome DevTools MCP**
- `navigate_page`: opens morning-ritual.html in Chrome browser
- Configured in ~/.claude/settings.json
- Optional; can manually open file if not available

---

## Data Pipeline

### **Step 0: Cache Cleanup**
```bash
rm -rf .tmp/emails/ .tmp/analyzed/ .tmp/digest.json
rm -f .tmp/newsletter_digest_*.html .tmp/resend_payload.json
```
Ensures fresh data each run; prevents stale data being served.

### **Step 1: Newsletter Digest (Blocking)**
Calls `/newsletter-digest` skill:
```
Skill(skill: newsletter-digest)
```
Waits for completion. Produces:
- `newsletter_digest_YYYY-MM-DD.html` (table with 19+ rows, 5 columns)
- Email sent to user inbox via Resend API

### **Step 2: Fetch Calendar + Markdown (Parallel)**
Two MCP calls + one file read in parallel:
- **2a**: Google Calendar list_events (today + 7 days + past 5 days)
- **2b**: Read month markdown (auto-detected: `calendar-projects/[Month] [Year].md`)

### **Step 3: Generate HTML**
Python script: `.claude/skills/morning/scripts/generate_morning_html.py`

**Input**: 
- Calendar events (JSON)
- Month markdown (text)
- Newsletter HTML file (extracted from .tmp/)

**Processing**:
1. Parse month markdown using regex:
   - Find "## Week of [DATE]" sections
   - Extract "### [Domain]" subsections
   - Collect "- [ ] task" items into 7×3 matrix (domains × weeks)
2. Extract newsletter HTML:
   - Regex: `<tbody>(.*?)</tbody>` 
   - Preserves full HTML structure, styles, links
3. Format calendar events:
   - Separate today's events from upcoming
   - Parse ISO 8601 timestamps into HH:MM format
4. Generate complete HTML:
   - Header with fresh timestamp (day of week, date, time)
   - Section 1: Today + Upcoming week + Kanban board
   - Section 2: Quick-link section
   - Section 3: Newsletter table
   - Footer with generation timestamp

**Output**: `morning-ritual.html` (~40KB, static HTML)

### **Step 4: Archive Dated Copy**
```bash
cp .claude/skills/morning/morning-ritual.html \
   calendar-projects/morning/morning-YYYY-MM-DD.html
```
Creates a timestamped archive for auditing/replay.

### **Step 5: Open in Browser**
Chrome DevTools MCP:
```
navigate_page:
  url: file:///path/to/project/.claude/skills/morning/morning-ritual.html
```

---

## Kanban Board Generation

The Python script parses the month markdown to extract a kanban matrix:

**Structure**:
```
## Week of [Date Range]
**Focus**: ...

### Domain 1
- [ ] Task 1
- [ ] Task 2

### Domain 2
- [ ] Task 3
...

## Week of [Next Date Range]
...
```

**Parser**:
1. Regex to find all "## Week of [DATE]" sections
2. For each week, find all "### [Domain]" subsections
3. Extract "- [ ] task" items (checkbox syntax)
4. Build 7×3 matrix (7 domains, 3 weeks)

**HTML Output**:
- Responsive table with 7 domain rows, 3 week columns
- Color-coded by domain (customizable)
- Tasks rendered as nested `<ul><li>` in each cell
- Empty cells left blank (no "No tasks" placeholder)

**Color Scheme** (customizable):
| Domain | Header | Cell |
|--------|--------|------|
| Domain 1 | #fff8f0 | #fef5f1 |
| Domain 2 | #f0f8ff | #f5faff |
| Domain 3 | #fff5e6 | #fffbf0 |
| Domain 4 | #ffe6f0 | #fff5fa |
| Domain 5 | #e6f5ff | #f0faff |
| Domain 6 | #f0e6ff | #f8f5ff |
| Domain 7 | #e6ffe6 | #f0fff0 |

---

## Subagents

### `newsletter-analyzer`
**Role**: Analyze a single newsletter email  
**Model**: Claude Sonnet (best quality for summarization)  
**Tools**: Read, Write (no MCP access)  
**Input**: `.tmp/emails/email_N.json` with full email body  
**Output**: `.tmp/analyzed/analyzed_N.json` with:
```json
{
  "sender": "Newsletter Name",
  "date": "YYYY-MM-DD",
  "summary_html": "<span style=...>TYPE</span><ul>...</ul>",
  "key_stats": ["stat 1", "stat 2", ...],
  "original_link": "https://..."
}
```

**Batching Pattern**:
- Spawn 5–7 subagents per batch
- Wait for all to complete (receive task-notification messages)
- Spawn next batch
- Total 19 emails across 3–4 batches
- **Why**: All-at-once spawning (19 agents) causes file I/O contention. Batching reduces system load and actually runs **faster** (30–45s vs. 50–65s)

---

## Configuration

### **Required Environment Variables**
Set in `.env`:
```bash
RESEND_API_KEY=re_xxxx...           # From resend.com/api-keys
RESEND_FROM=onboarding@resend.dev   # Or verified custom domain
RESEND_TO=your-email@example.com    # Recipient email
```

### **Month Markdown Location**
Auto-detected by system date:
```
calendar-projects/[Month] [Year].md
# Examples:
calendar-projects/May 2026.md
calendar-projects/Jun 2026.md
```

### **Output Locations**
```
.claude/skills/morning/morning-ritual.html         # Live briefing
.tmp/newsletter_digest_YYYY-MM-DD.html            # Newsletter HTML
.tmp/emails/email_N.json                          # Raw email JSON
.tmp/analyzed/analyzed_N.json                     # Analyzed results
calendar-projects/morning/morning-YYYY-MM-DD.html # Archive
```

---

## Performance

| Phase | Duration | Bottleneck |
|-------|----------|-----------|
| Delete cache | <1s | Local I/O |
| Newsletter digest | 30–50s | Gmail API + subagent spawn |
| Calendar + markdown fetch | 3–5s | Google Calendar API |
| HTML generation | <100ms | Python script (CPU only) |
| Browser open | ~10s | Chrome startup |
| **Total** | **60–80s** | Newsletter fetch |

**Optimization notes:**
- Newsletter is the critical path; all other phases overlap or complete quickly
- Batching subagents (vs. all-at-once) reduces from 50–65s to 30–45s
- HTML generation is negligible (<100ms); could be further optimized with templating
- Browser open time depends on OS/hardware; typically ~10s

---

## Error Handling

### **If Newsletter Digest Fails**
- Step 1 aborts; `/morning` exits with error message
- No HTML generated (prevents stale news)
- User must fix Resend credentials and retry

### **If Calendar Fetch Fails**
- Step 2 continues with empty calendar
- Month markdown still loads
- HTML renders with empty calendar section (kanban board still visible)

### **If Month Markdown Missing**
- Kanban board omitted from HTML
- All other sections render normally
- No crash; graceful degradation

### **If Newsletter HTML Malformed**
- Newsletter section left blank
- Other sections render normally
- User can manually check inbox

---

## Testing Checklist

- [ ] Newsletter digest file exists: `.tmp/newsletter_digest_YYYY-MM-DD.html`
- [ ] Email sent to RESEND_TO address
- [ ] Calendar events fetched (should see today + upcoming week)
- [ ] Month markdown parsed (kanban board visible in HTML)
- [ ] HTML timestamp matches current date/time
- [ ] Newsletter table embeds all 19+ newsletters
- [ ] Kanban board shows all 7 domains (even if empty cells)
- [ ] Browser opens within 80 seconds of running `/morning`
- [ ] Running `/morning` again same day produces new HTML (Step 0 deletion works)

---

## Future Optimizations

1. **Batch MCP calls**: Fetch multiple calendar events in single call (vs. 1 per thread)
2. **Pipeline analysis**: Start analyzing batch 2 while fetching batch 3
3. **Template caching**: Pre-compile HTML template (save ~10ms)
4. **Async subagent spawning**: Don't wait for full batch before spawning next (save ~5s)
5. **Weekly/Monthly rituals**: Same architecture, extends to summary/forecasting

---

## Security Notes

- **No credentials in code**: All API keys via environment variables
- **No credential storage**: Uses MCP OAuth (Gmail, Google Calendar)
- **Resend API key**: Stored in .env, never logged or exposed
- **Month markdown**: Plain text, contains task names only (no sensitive data)
- **Output HTML**: Static file, no embedded credentials or secrets
- **GitHub-safe**: All files can be committed except `.env` (add to .gitignore)

---

## Privacy & Personal Data

This system is designed to protect your personal information:

- **No personal details in code** — all examples use generic domain names (Domain 1, Domain 2, etc.)
- **No email addresses hardcoded** — configured via `.env` (excluded from version control)
- **No file paths exposed** — all paths are relative or configurable
- **No task content published** — month markdown is never committed to version control
- **No credentials exposed** — .env is in .gitignore by default

When sharing this codebase:
- Never commit `.env` file
- Never commit personal month markdown files
- Never include example tasks with sensitive information
- Always use generic domain names in documentation
