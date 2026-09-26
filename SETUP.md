# Morning Ritual — Configuration & Setup Guide

Complete step-by-step guide to set up the morning ritual system.

## Prerequisites

- Claude Code (local or web)
- Gmail account with newsletters in the Forum tab
- Google Calendar
- Resend API account (https://resend.com, free tier: 3k emails/month)

## Step 1: Set Up Resend API

1. Go to https://resend.com and sign up (free tier available)
2. Navigate to **API Keys** section
3. Copy your API key (starts with `re_...`)
4. Note your sender email:
   - For testing: use `onboarding@resend.dev` (works out of the box)
   - For production: verify a custom domain in Resend dashboard

## Step 2: Create `.env` File

Create a file at the root of your project with:

```bash
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM=onboarding@resend.dev
RESEND_TO=your-email@example.com
```

**Important**: 
- Never commit `.env` to GitHub (it's in `.gitignore`)
- Keep API keys private
- Use absolute email addresses (no aliases)

## Step 3: Create Month Markdown File

Create a file at `calendar-projects/[Month] [Year].md` (e.g., `May 2026.md`):

```markdown
# [Month] [Year] — Strategic Planning

## Week of [Date Range]

**Focus**: Strategic priorities for this week.

### Domain 1
- [ ] Task A
- [ ] Task B

### Domain 2
- [ ] Task C
- [ ] Task D

### Domain 3
- [ ] Task E

## Week of [Next Date Range]

**Focus**: Continuation of strategic execution.

### Domain 1
- [ ] Task F
- [ ] Task G
```

**Key format rules**:
- `## Week of [DATE]` — defines a week block
- `**Focus**: [text]` — week focus statement
- `### [Domain Name]` — domain label (can be any name you choose)
- `- [ ] [task]` — checkbox item (task)
- Empty domains are OK (just omit the `### [Domain]` section)

**Default domains** (7 total, customizable):
- Domain 1, Domain 2, Domain 3, Domain 4, Domain 5, Domain 6, Domain 7

You can customize these domain names in the Python script.

## Step 4: Verify Gmail Forum Tab

1. Open Gmail
2. Click on the "Forum" tab (or label) in the left sidebar
3. You should see newsletters from mailing lists
4. The `/newsletter-digest` skill will automatically fetch from here

**Note**: Gmail auto-categorizes newsletters into the Forum tab. No manual filtering needed.

## Step 5: Verify Google Calendar

1. Open Google Calendar
2. Confirm events are showing for today + next 7 days
3. The `/morning` ritual will fetch these automatically via MCP

**Note**: Google Calendar MCP is built into Claude. No additional OAuth setup needed.

## Step 6: Run `/morning` for the First Time

In Claude Code, type:

```
/morning
```

**Expected output** (60–80 seconds):
1. Newsletter digest fetched and analyzed (~30–50s)
2. Calendar events fetched (~3–5s)
3. HTML generated with kanban board (<100ms)
4. Browser opens with complete briefing (~10s)

**Check for**:
- ✓ HTML file exists at `.claude/skills/morning/morning-ritual.html` (46–50KB)
- ✓ Email received in inbox with newsletter digest
- ✓ Browser shows today's date in header
- ✓ Kanban board visible with 7 domains and 3 weeks
- ✓ Newsletter table has 19+ rows

## Troubleshooting

### "Newsletter digest failed"
- Check RESEND_API_KEY in `.env` (copy from https://resend.com/api-keys)
- Check RESEND_FROM — if using custom domain, verify it in Resend dashboard
- Check RESEND_TO — must be verified email (check Resend contacts)
- Verify you haven't exceeded 3k emails/month free tier limit

### "Calendar events missing"
- Confirm events exist in Google Calendar for today + next 7 days
- Check that Google Calendar MCP is connected (should be automatic)

### "Month markdown not found"
- Verify file exists: `ls calendar-projects/$(date '+%b %Y').md`
- Check month abbreviation (May, Jun, Jul — not May, June, July)
- Confirm file has at least one "## Week of" section

### "HTML doesn't open in browser"
- Check file path is correct in your SKILL.md configuration
- Try opening the HTML file manually
- If Chrome DevTools MCP unavailable, manually open the file

### "Kanban board is blank"
- Check month markdown file exists and has content
- Verify format: `### [Domain Name]` followed by `- [ ] task` items
- Confirm file has proper markdown syntax

## Daily Workflow

**Every morning at 7:00 AM** (or anytime):

1. Type `/morning` in Claude
2. Wait ~60–80 seconds
3. Fresh briefing opens in browser
4. Review today's schedule + weekly priorities + newsletter summaries
5. Go build

**That's it.** No manual email checking, calendar review, or task consolidation needed.

## Customization

### Change Resend sender
1. Update `RESEND_FROM` in `.env`
2. Verify domain in Resend dashboard if custom domain
3. Re-run `/morning`

### Change digest recipient
1. Update `RESEND_TO` in `.env` with new email
2. Verify email in Resend dashboard
3. Re-run `/morning`

### Customize domain names
Edit `.claude/skills/morning/scripts/generate_morning_html.py`:
- Find `all_domains = [...]` list (~line 61)
- Replace domain names (e.g., `"Domain 1"` → `"MyCustomDomain"`)
- Update your month markdown to match these names

### Change month markdown location
Edit `.claude/skills/morning/SKILL.md`:
- Look for month markdown path variable
- Replace with custom path and format

## Performance Optimization

**If newsletter digest is slow (>50s)**:
- Reduce number of newsletters: archive old ones in Gmail
- Check network latency to API endpoints

**If HTML generation is slow (>500ms)**:
- Usually <100ms; if slower, check disk I/O
- Try re-running; first run may have overhead

**If browser opens slowly (>15s)**:
- Chrome startup time depends on OS/hardware
- Pre-open Chrome before running `/morning` (saves ~3–5s)

## Next Steps

1. Run `/morning` daily at 7:00 AM (can be automated via cron)
2. Extend to weekly review (similar architecture, different data)
3. Extend to monthly forecasting (seasonal planning, goal review)

---

**Setup time: ~5 minutes. Ongoing maintenance: zero.**
