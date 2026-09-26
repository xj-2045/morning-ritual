#!/usr/bin/env python3
"""
Generate morning briefing HTML in the standard format.
Combines: session recap + calendar + kanban + newsletters into one HTML file.

Usage: python3 generate_morning_html.py
Reads: .tmp/digest.json, calendar-projects/<Month YYYY>.md,
       .tmp/calendar.json (Google Calendar list_events output),
       .tmp/session_recap.json (optional)
Writes: .claude/skills/morning/morning-ritual.html
"""

import json
import re
from pathlib import Path
import html as html_lib
from datetime import datetime, timedelta

# Domain color mapping (for kanban board styling)
DOMAIN_COLORS = {
    'Immigration': '#fff8f0',
    'Career': '#f0f8ff',
    'Writing': '#f0fff4',
    'Family': '#fff5f7',
    'Health': '#fffaf0',
    'Reading': '#f5f3ff',
    'Build': '#f9f9f9',
    'Admin': '#f5f5f5',
}

DOMAIN_BG_COLORS = {
    'Immigration': '#fef5f1',
    'Career': '#e8f4ff',
    'Writing': '#e8ffe8',
    'Family': '#ffe8f5',
    'Health': '#fff5e8',
    'Reading': '#f5f0ff',
    'Build': '#f0f0f0',
    'Admin': '#eeeeee',
}

def parse_kanban_markdown(markdown_path):
    """Parse kanban markdown and extract tasks by domain and week."""
    if not markdown_path.exists():
        return {}, [], []

    content = markdown_path.read_text()
    weeks = {}
    week_order = []

    # Split by week sections
    week_pattern = r'## Week of (.+?)\n\n\*\*Focus\*\*: .+?\n\n(.*?)(?=## Week of|## Recurring|$)'
    week_matches = re.finditer(week_pattern, content, re.DOTALL)

    for match in week_matches:
        week_title = match.group(1)
        week_content = match.group(2)
        week_order.append(week_title)
        weeks[week_title] = {}

        # Extract domains and tasks within this week
        domain_pattern = r'### (.+?)\n(.*?)(?=###|## |$)'
        domain_matches = re.finditer(domain_pattern, week_content, re.DOTALL)

        for dmatch in domain_matches:
            domain = dmatch.group(1).strip()
            tasks_text = dmatch.group(2).strip()

            # Extract task items (both checked and unchecked)
            tasks = []
            task_pattern = r'- \[.\] (.+?)(?:\n|$)'
            task_matches = re.finditer(task_pattern, tasks_text)

            for tmatch in task_matches:
                task = tmatch.group(1).strip()
                if not task.startswith('['):  # Skip links and other artifacts
                    tasks.append(task)

            if tasks:
                weeks[week_title][domain] = tasks

    return weeks, week_order, list(DOMAIN_COLORS.keys())

def build_kanban_html(weeks, week_order, all_domains):
    """Build kanban table HTML from parsed data."""
    if not weeks:
        return '<h3>📊 Monthly Kanban Board</h3><p>No kanban data available.</p>'

    # Start table
    html = '''        <h3>📊 Monthly Kanban Board</h3>
        <div style="margin-top: 16px; overflow-x: auto; border: 1px solid #ddd; border-radius: 6px; background: white;">
          <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
            <thead>
              <tr style="background: #f0f0f0; border-bottom: 2px solid #ddd;">
                <th style="padding: 10px 12px; text-align: left; font-weight: 600; width: 110px;">Domain</th>
'''

    # Add week headers
    for week in week_order:
        html += f'                <th style="padding: 10px 12px; text-align: left; font-weight: 600; width: 140px;">{week}</th>\n'

    html += '''              </tr>
            </thead>
            <tbody>
'''

    # Add domain rows (only for domains that have tasks in at least one week)
    domains_with_tasks = set()
    for week_data in weeks.values():
        domains_with_tasks.update(week_data.keys())

    for domain in sorted(domains_with_tasks):
        bg_color = DOMAIN_COLORS.get(domain, '#f9f9f9')
        cell_color = DOMAIN_BG_COLORS.get(domain, '#f0f0f0')

        html += f'''              <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px 12px; font-weight: 600; background: {bg_color};">{domain}</td>
'''

        for week in week_order:
            tasks = weeks.get(week, {}).get(domain, [])
            if tasks:
                task_html = '<ul style="margin: 0; padding-left: 18px; font-size: 12px;">'
                for task in tasks[:3]:  # Limit to 3 tasks per cell
                    task_html += f'<li>{task}</li>'
                task_html += '</ul>'
            else:
                task_html = ''

            html += f'                <td style="padding: 10px 12px; background: {cell_color};">{task_html}</td>\n'

        html += '              </tr>\n'

    html += '''            </tbody>
          </table>
        </div>
'''

    return html

# ── CALENDAR ──────────────────────────────────────────────────────────────────

def load_calendar_events(path=Path('.tmp/calendar.json'), days_ahead=7):
    """Read Google Calendar events (list_events output) and split into today / upcoming."""
    if not path.exists():
        return [], []
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return [], []
    events = payload.get('events', []) if isinstance(payload, dict) else payload

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    window_end = (now + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
    today, upcoming, seen = [], [], set()

    for ev in events:
        start = ev.get('start', {})
        dt_str = start.get('dateTime', '')
        date_str = (dt_str or start.get('date', ''))[:10]
        title = ev.get('summary', '(No title)')
        if not date_str or (date_str, title) in seen or not (today_str <= date_str <= window_end):
            continue
        seen.add((date_str, title))

        time_str = 'All day'
        if dt_str:
            try:
                time_str = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).astimezone().strftime('%H:%M')
            except ValueError:
                time_str = ''
        item = {'date': date_str, 'time': time_str, 'title': title}
        (today if date_str == today_str else upcoming).append(item)

    today.sort(key=lambda e: e['time'])
    upcoming.sort(key=lambda e: (e['date'], e['time']))
    return today, upcoming


def build_calendar_html(events):
    today, upcoming = events
    def items(evs, with_date):
        if not evs:
            return '          <li style="color:#999;">No events</li>\n'
        out = ''
        for e in evs:
            label = datetime.fromisoformat(e['date']).strftime('%b %-d') + ' — ' if with_date else ''
            out += f"          <li>{label}{e['time']} — {html_lib.escape(e['title'])}</li>\n"
        return out
    return f"""
        <h3>Today ({datetime.now().strftime('%b %-d')})</h3>
        <ul>
{items(today, False)}        </ul>
        <h3>Upcoming</h3>
        <ul>
{items(upcoming, True)}        </ul>
"""


# ── SESSION RECAP ─────────────────────────────────────────────────────────────

def load_session_recap(path=Path('.tmp/session_recap.json')):
    """Optional: [{"topic": str, "desc": str, "tokens": int}, ...] written by Claude from session history."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return sorted(data, key=lambda t: t.get('tokens', 0), reverse=True)[:5]


def _fmt_tokens(n):
    return f'{n / 1000:.1f}K' if n >= 1000 else str(n)


def build_session_recap_html(topics):
    if not topics:
        return '        <p style="color:#999;">No session recap yet — write .tmp/session_recap.json to populate.</p>\n'
    top = max(t.get('tokens', 0) for t in topics) or 1
    total = sum(t.get('tokens', 0) for t in topics)
    rows = ''
    for i, t in enumerate(topics, 1):
        tokens = t.get('tokens', 0)
        rows += f"""            <tr>
              <td><div class="recap-rank">#{i}</div></td>
              <td>
                <div class="recap-topic-name">{html_lib.escape(t.get('topic', ''))}</div>
                <div class="recap-topic-desc">{html_lib.escape(t.get('desc', ''))}</div>
              </td>
              <td>
                <div class="recap-bar-cell">
                  <div class="recap-bar-container">
                    <div class="recap-bar-fill" style="width: {round(tokens / top * 100)}%;">{_fmt_tokens(tokens)}</div>
                  </div>
                  <div class="recap-token-label">{_fmt_tokens(tokens)}</div>
                </div>
              </td>
            </tr>
"""
    return f"""
        <style>
          .recap-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
          .recap-table thead tr {{ border-bottom: 2px solid #e0e0e0; }}
          .recap-table th {{ text-align: left; padding: 12px 16px; font-size: 13px; font-weight: 600; color: #5f6368; text-transform: uppercase; letter-spacing: 0.5px; }}
          .recap-table td {{ padding: 16px; border-bottom: 1px solid #f1f3f4; vertical-align: middle; }}
          .recap-table tr:hover td {{ background: #f8f9ff; }}
          .recap-rank {{ font-weight: 600; color: #5f6368; font-size: 13px; width: 30px; }}
          .recap-topic-name {{ font-weight: 500; color: #1a73e8; font-size: 14px; margin-bottom: 6px; }}
          .recap-topic-desc {{ font-size: 12px; color: #5f6368; line-height: 1.4; }}
          .recap-bar-cell {{ display: flex; align-items: center; gap: 12px; }}
          .recap-bar-container {{ flex-grow: 1; height: 24px; background: #f1f3f4; border-radius: 4px; overflow: hidden; }}
          .recap-bar-fill {{ height: 100%; background: linear-gradient(90deg, #1a73e8 0%, #4285f4 100%); display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 12px; font-weight: 600; }}
          .recap-token-label {{ min-width: 75px; text-align: right; font-weight: 600; color: #202124; font-size: 14px; }}
          .recap-stats-row {{ display: flex; gap: 32px; margin-top: 20px; padding: 16px; background: #f8f9fa; border-radius: 6px; font-size: 14px; }}
          .recap-stat {{ flex: 1; }}
          .recap-stat-label {{ color: #5f6368; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
          .recap-stat-value {{ font-size: 18px; font-weight: 600; color: #202124; }}
        </style>
        <h3>💻 Session Recap — Top {len(topics)} Topics</h3>
        <table class="recap-table">
          <thead>
            <tr>
              <th style="width: 8%;">Rank</th>
              <th style="width: 50%;">Topic</th>
              <th style="width: 42%;">Tokens Used</th>
            </tr>
          </thead>
          <tbody>
{rows}          </tbody>
        </table>
        <div class="recap-stats-row">
          <div class="recap-stat">
            <div class="recap-stat-label">Total Tokens</div>
            <div class="recap-stat-value">{_fmt_tokens(total)}</div>
          </div>
          <div class="recap-stat">
            <div class="recap-stat-label">Topics Grouped</div>
            <div class="recap-stat-value">{len(topics)}</div>
          </div>
          <div class="recap-stat">
            <div class="recap-stat-label">Avg Tokens/Topic</div>
            <div class="recap-stat-value">{_fmt_tokens(total // len(topics))}</div>
          </div>
        </div>
"""


def generate_morning_html():
    today = datetime.now().strftime('%Y-%m-%d')
    day_name = datetime.now().strftime('%A')

    # Read digest data
    digest_path = Path('.tmp/digest.json')
    if not digest_path.exists():
        print("❌ Error: .tmp/digest.json not found")
        return False

    with open(digest_path) as f:
        digest_data = json.load(f)

    # Build newsletter table rows (full HTML detail format)
    newsletter_rows = ""
    for i, item in enumerate(digest_data, 1):
        sender = item.get('sender', 'Unknown')
        summary_html = item.get('summary_html', '<span></span>')
        stats = item.get('key_stats', [])
        link = item.get('original_link', '')

        # Build stats list HTML
        stats_html = ""
        if stats:
            stats_html = '<ul>' + ''.join([f'<li style="margin-bottom:4px;color:#5f6368;">{stat}</li>' for stat in stats]) + '</ul>'

        link_cell = f'<a href="{link}" target="_blank" style="display:inline-block;color:#1a73e8;text-decoration:none;font-size:18px;">🔗</a>' if link else ''

        newsletter_rows += f'''          <tr>
            <td class="sender">{sender}</td>
            <td class="summary">{summary_html}</td>
            <td class="stats">{stats_html}</td>
            <td class="icon-cell">{link_cell}</td>
            <td class="icon-cell">✉️</td>
          </tr>
'''

    session_recap = build_session_recap_html(load_session_recap())
    today_events = build_calendar_html(load_calendar_events())

    # Parse kanban markdown dynamically
    month_name = datetime.now().strftime('%b %Y')
    kanban_path = Path(f'calendar-projects/{month_name}.md')
    weeks, week_order, all_domains = parse_kanban_markdown(kanban_path)
    kanban_html = build_kanban_html(weeks, week_order, all_domains)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Morning Ritual</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }}
    .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .header {{ background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 40px; text-align: center; }}
    .header h1 {{ font-size: 36px; margin-bottom: 12px; }}
    .header p {{ font-size: 16px; opacity: 0.9; }}
    .generated-at {{ font-size: 12px; opacity: 0.7; font-family: 'Monaco', monospace; margin-top: 12px; }}
    .content {{ padding: 40px; }}
    .section {{ margin-bottom: 30px; padding: 24px; background: #f9f9f9; border-left: 4px solid #3498db; border-radius: 8px; }}
    .section-title {{ font-size: 24px; font-weight: 600; margin-bottom: 16px; color: #2c3e50; }}
    .section h3 {{ font-size: 16px; font-weight: 600; margin-top: 16px; margin-bottom: 8px; color: #34495e; }}
    .section ul {{ list-style: none; padding-left: 0; }}
    .section li {{ padding: 8px 0 8px 20px; position: relative; line-height: 1.6; }}
    .section li:before {{ content: "→"; position: absolute; left: 0; color: #3498db; font-weight: bold; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
    thead {{ background: #ecf0f1; border-bottom: 2px solid #bdc3c7; }}
    th {{ padding: 12px; text-align: left; font-weight: 600; color: #2c3e50; }}
    tbody tr {{ border-bottom: 1px solid #ecf0f1; }}
    tbody tr:hover {{ background: #f9f9f9; }}
    td {{ padding: 12px; color: #555; }}
    .sender {{ font-weight: 600; color: #2980b9; }}
    .summary {{ width: 45%; }}
    .summary span {{ font-weight: 700; display: block; margin-bottom: 6px; }}
    .summary ul {{ margin: 0; padding-left: 16px; font-size: 12px; }}
    .summary li {{ margin-bottom: 4px; }}
    .stats {{ width: 20%; }}
    .stats ul {{ margin: 0; padding-left: 16px; font-size: 12px; }}
    .stats li {{ margin-bottom: 3px; color: #666; }}
    .icon-cell {{ text-align: center; width: 40px; }}
    .icon-cell a {{ color: #2980b9; text-decoration: none; font-size: 16px; }}
    .footer {{ padding: 16px 40px; background: #ecf0f1; border-top: 1px solid #bdc3c7; text-align: center; font-size: 12px; color: #666; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🌅 Morning Ritual</h1>
      <p>Grounded in your north star</p>
      <p class="generated-at">{day_name}, {today} · Generated at {datetime.now().strftime('%I:%M %p')}</p>
    </div>

    <div class="content">
      <div class="section">
        <div class="section-title">💻 Session Recap (Past 5 Days)</div>
{session_recap}
      </div>

      <div class="section">
        <div class="section-title">📅 This Week</div>
{today_events}
{kanban_html}
      </div>

      <div class="section">
        <div class="section-title">☕ Wall Street Journal</div>
        <div style="margin-top: 20px; text-align: center; padding: 24px; background: linear-gradient(135deg, #fef9f3 0%%, #f5f1eb 100%%); border-radius: 8px;">
          <div style="font-size: 48px; margin-bottom: 16px; animation: float 3s ease-in-out infinite;">☕</div>
          <p style="font-size: 16px; font-weight: 500; color: #34495e; margin: 0;">20 minutes with coffee and the WSJ.</p>
          <p style="font-size: 14px; color: #7f8c8d; margin: 8px 0 0 0;">Time always well spent.</p>
        </div>
        <style>
          @keyframes float {{
            0%%, 100%% {{ transform: translateY(0px); }}
            50%% {{ transform: translateY(-8px); }}
          }}
        </style>
      </div>

      <div class="section">
        <div class="section-title">📬 Newsletters & Digest</div>
        <p style="margin-bottom: 16px; color: #666;">{len(digest_data)} newsletters analyzed and delivered to your inbox.</p>
        <table>
          <thead>
            <tr>
              <th>Sender</th>
              <th class="summary">Summary</th>
              <th class="stats">Key Stats</th>
              <th class="icon-cell">Link</th>
              <th class="icon-cell">Gmail</th>
            </tr>
          </thead>
          <tbody>
{newsletter_rows}          </tbody>
        </table>
      </div>
    </div>

    <div class="footer">
      Morning Briefing — {today} | All data fresh · Go build.
    </div>
  </div>
</body>
</html>
"""

    # Write both the main file and archive
    main_path = Path('.claude/skills/morning/morning-ritual.html')
    main_path.write_text(html)

    archive_dir = Path('calendar-projects/morning')
    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / f'morning-{today}.html'
    archive_path.write_text(html)

    return True

if __name__ == '__main__':
    if generate_morning_html():
        print("✅ Morning HTML generated successfully")
    else:
        print("❌ Failed to generate morning HTML")
