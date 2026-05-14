# `/morning` Ritual — Daily Context Loading (Sequential Newsletter-First)

**Duration**: ~50-80 seconds (all data fetched + HTML opens)  
**Frequency**: Daily at 7:00 AM  
**Purpose**: Run newsletter-digest first to completion, then fetch calendar + tasks, generate complete briefing HTML with all data baked in, open immediately

---

## Architecture: Sequential Workflow

**Newsletter first (~30-50s)**: Fetch, analyze, and send newsletter digest. Verify output file exists.

**Then calendar + tasks (~3-5s)**: Fetch Google Calendar + read month markdown in parallel.

**Then HTML + open (~3-5s)**: Generate complete HTML with all data included. Open in browser immediately with everything ready.

---

## Workflow

### Step 0: Delete & Clear (Always First)

Delete the existing `morning-ritual.html` and all newsletter cache to guarantee fresh content.

```bash
rm -f "./.claude/skills/morning/morning-ritual.html"
rm -f "./.tmp/newsletter_digest_"*.html
rm -rf "./.tmp/emails/" \
        "./.tmp/analyzed/" \
        "./.tmp/digest.json" \
        "./.tmp/resend_payload.json"
DATE=$(date +%Y-%m-%d)
rm -f "./calendar-projects/morning/morning-${DATE}.html"
```

---

### Step 1: Run Newsletter-Digest (Blocking, Sequential)

Invoke the `/newsletter-digest` skill **synchronously** and wait for it to complete.

```
Skill(skill: newsletter-digest)
```

**Critical**: Do NOT use `run_in_background: true`. This must complete before proceeding.

**After the skill finishes**, verify the output file exists:
```bash
DATE=$(date +%Y-%m-%d)
ls -la "./.tmp/newsletter_digest_${DATE}.html"
```

**If the file does NOT exist:**
- Abort the morning ritual
- Tell the user: "Newsletter digest failed. Check .env for Resend credentials. Skipping /morning."
- Exit (do NOT proceed to Step 2)

**If the file EXISTS:**
- Proceed to Step 2 immediately

---

### Step 2: Fetch Calendar + Read Tasks (Parallel)

In ONE message, launch both data sources simultaneously:

**2a. Fetch Google Calendar (today + next 7 days):**
```
mcp__claude_ai_Google_Calendar__list_events:
  startTime: today at 00:00:00 (ISO 8601, e.g., 2026-05-13T00:00:00)
  endTime: today+7 days at 23:59:59 (ISO 8601, e.g., 2026-05-20T23:59:59)
  timeZone: [User's timezone, e.g., America/Los_Angeles]
```

Also fetch a 5-day lookback window:
```
  startTime: today-5 days at 00:00:00
  endTime: today at 23:59:59
```

**2b. Read current month's task file (auto-detected):**
```bash
MONTH_FILE="./calendar-projects/$(date '+%b %Y').md"
cat "$MONTH_FILE"
```

**Display progress in chat:**
```
☕ Morning context loading...
  → Newsletter digest: ✅ sent
  → Calendar: loading...
  → Tasks: loading...
```

---

### Step 3: Write Complete HTML (All Data Baked In)

Once Step 2 completes (calendar + tasks fetched), write the complete `morning-ritual.html` with all data baked in.

**Use the Python script to generate HTML:**
```bash
# Convert calendar events to JSON and pipe to script
python3 ./.claude/skills/morning/scripts/generate_morning_html.py <<< '$(jq -n --argjson events "[...]" '$events')'
```

The script handles:
1. Parsing the month markdown file to extract all domains and tasks
2. Building the kanban board table with color-coded domain rows
3. Extracting newsletter HTML from `.tmp/newsletter_digest_YYYY-MM-DD.html`
4. Formatting calendar events by date (today vs. upcoming)
5. Generating complete HTML with all sections

The generated HTML includes:

**Output:** A fully-rendered morning-ritual.html file with:
- Header with fresh timestamp (day of week, date, time)
- Section 1: Today's events + Upcoming week events
- Section 2: Monthly kanban board (7 domains × 3 weeks, color-coded)
- Section 3: Quick link section
- Section 4: Newsletter digest table with 19+ analyzed newsletters

The script reads from:
- `./calendar-projects/[Month] [Year].md` — for kanban data
- `./.tmp/newsletter_digest_YYYY-MM-DD.html` — for newsletter table
- Calendar events passed from Step 2 — for today/upcoming events

All data is baked into a single static HTML file (~40KB) that opens instantly.

---

### Step 4: Archive Dated Copy

```bash
DATE=$(date +%Y-%m-%d)
cp "./.claude/skills/morning/morning-ritual.html" \
   "./calendar-projects/morning/morning-${DATE}.html"
```

---

### Step 5: Open HTML in Chrome

Use Chrome DevTools MCP to navigate:

```
mcp__plugin_chrome_devtools__navigate_page:
  url: file:///[absolute-path-to-project]/.claude/skills/morning/morning-ritual.html
```

**Tell the user:**
```
✅ Morning briefing complete — all data fresh and ready.
```

---

### Step 6: Announce Complete

```
✅ Morning briefing complete — all fresh data loaded.

Today: [N events]
This week: [N events]
Newsletters: [N analyzed and sent to inbox]

Go build.
```

---

## Monthly File Auto-Detection

The month markdown files are auto-detected based on the current system date:

```bash
$(date '+%b %Y')  # → "May 2026", "Jun 2026", "Jul 2026"
```

Files in calendar-projects: `May 2026.md`, `Jun 2026.md`, `Jul 2026.md`, `Annual-2026.md`

This auto-detection means:
- May 1–31 → reads `May 2026.md`
- June 1–30 → reads `Jun 2026.md` (automatic rollover)
- July 1–31 → reads `Jul 2026.md`

No manual month file detection needed.

---

## Output

You should have:
- ✓ Fresh HTML opened in browser within ~60-80 seconds
- ✓ Today's calendar events visible (Section 1–2)
- ✓ Weekly commitments and Kanban board visible (Section 2)
- ✓ Generated timestamp in header confirming today's date/time
- ✓ Newsletter digest table embedded in Section 4 with all 19+ newsletters
- ✓ All data baked into a single static HTML file (~40KB)

---

## Timing Summary

| Step | What | Duration |
|------|------|----------|
| 0 | Delete & clear | ~0.1s |
| 1 | Run /newsletter-digest (blocking) | ~30-50s |
| 2 | Fetch calendar + read tasks | ~3-5s |
| 3 | Write HTML with all data | ~2s |
| 4 | Archive & open in Chrome | ~1s |
| — | **Briefing ready and visible** | **~50-80s total** |

---

## How to Invoke

Type in Claude:

```
/morning
```

The skill will execute all steps automatically:
1. Delete stale files
2. Launch parallel data fetch
3. Generate fresh HTML
4. Open in browser
5. Inject newsletter when ready

No manual intervention required.

---

## Learnings

**CRITICAL: Kanban board generation**
- The Python script automatically parses the month markdown file to extract all domain sections and tasks
- Domains are color-coded with subtle background tints
- Each domain row shows tasks for all weeks
- Empty cells are left blank if no tasks exist for that domain/week
- The script regex-extracts "## Week of [DATE]" sections and "### [Domain]" subsections, then collects "- [ ] task" items

**Kanban board design choices:**
- Responsive HTML table with overflow-x for mobile viewing
- Domain label widths: 110px; Week column widths: 140px each
- Tasks are listed as nested `<ul><li>` elements in each cell
- Font size: 12px for tasks, 13px for table overall
- Borders: 1px solid #ddd between rows; 2px solid #ddd for header
- Padding: 10px 12px for all cells

**HTML generation is fully automated:**
- Step 3 calls the Python script which reads calendar events (JSON), month markdown, and newsletter HTML
- Script outputs a single 40KB static HTML file that loads instantly
- All data is baked in at generation time — no dynamic loading or spinners needed
- Timestamp in header is fresh proof the HTML is up-to-date
- No external dependencies; script uses only Python standard library

## Verification Checklist

✓ Step 1: Newsletter-digest completes and file exists at `.tmp/newsletter_digest_YYYY-MM-DD.html`  
✓ Step 1: Email sent to configured recipient  
✓ Step 2: Calendar events fetched successfully  
✓ Step 2: Month markdown file read correctly  
✓ Step 3: Python script executes without errors  
✓ Step 3: HTML generated with fresh timestamp in header  
✓ Step 3: Kanban board visible with all 7 domains and weeks populated correctly
✓ Step 3: Newsletter table embedded (19+ newsletters visible)  
✓ Step 5: Page opens in Chrome within ~60-80 seconds  
✓ Running `/morning` again on same day produces fresh HTML with updated events

---

## Troubleshooting

**Newsletter-digest fails or doesn't complete:**
- Check that RESEND_API_KEY, RESEND_FROM, RESEND_TO are all in `.env`
- Verify `.tmp/newsletter_digest_YYYY-MM-DD.html` exists after running
- If missing: newsletter-digest aborted, `/morning` ritual will exit with error message (do NOT proceed to Step 2)

**HTML doesn't open:**
- Verify file path is correct: `./.claude/skills/morning/morning-ritual.html`
- Check directory permissions

**Calendar events missing:**
- Verify Google Calendar MCP is connected (should work by default)
- Check that events actually exist on the target dates

**Month file not found:**
- Verify file exists: `ls ./calendar-projects/$(date '+%b %Y').md`
- Confirm month abbreviation is correct (May, Jun, Jul — not May, June, July)
