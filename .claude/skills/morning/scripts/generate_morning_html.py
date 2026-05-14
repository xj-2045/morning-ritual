#!/usr/bin/env python3
"""Generate morning-ritual.html with all data baked in: calendar, kanban, newsletters."""

import re
import json
import pathlib
from datetime import datetime, timedelta

BASE_DIR = pathlib.Path("/Users/xjz/Desktop/XJ Personal OS")

# Domain color scheme
DOMAIN_COLORS = {
    "Immigration": {"header": "#fff8f0", "cell": "#fef5f1"},
    "Career": {"header": "#f0f8ff", "cell": "#f5faff"},
    "Writing": {"header": "#fff5e6", "cell": "#fffbf0"},
    "Family": {"header": "#ffe6f0", "cell": "#fff5fa"},
    "Health": {"header": "#e6f5ff", "cell": "#f0faff"},
    "Reading": {"header": "#f0e6ff", "cell": "#f8f5ff"},
    "Build": {"header": "#e6ffe6", "cell": "#f0fff0"},
}

def parse_month_markdown(month_file):
    """Parse month markdown to extract kanban data."""
    text = month_file.read_text()

    # Find all week sections
    weeks = []
    week_pattern = r"## Week of ([\w\s\-]+)\n\n\*\*Focus\*\*: (.+?)\n\n(.*?)(?=## Week of|## Recurring|## Monthly|$)"

    for match in re.finditer(week_pattern, text, re.DOTALL):
        week_name = match.group(1).strip()
        focus = match.group(2).strip()
        week_content = match.group(3)

        domains = {}
        domain_pattern = r"### ([\w]+)\n(.*?)(?=###|\Z)"

        for domain_match in re.finditer(domain_pattern, week_content, re.DOTALL):
            domain = domain_match.group(1).strip()
            domain_content = domain_match.group(2)

            # Extract tasks (checkbox items)
            tasks = []
            task_pattern = r"- \[.\] (.+?)(?:\n|$)"
            for task_match in re.finditer(task_pattern, domain_content):
                task = task_match.group(1).strip()
                # Clean up links and extra formatting
                task = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", task)
                tasks.append(task)

            if tasks:
                domains[domain] = tasks

        weeks.append({"name": week_name, "focus": focus, "domains": domains})

    return weeks

def build_kanban_html(weeks_data):
    """Build kanban table HTML from parsed week data."""
    # Collect all domains
    all_domains = ["Immigration", "Career", "Writing", "Family", "Health", "Reading", "Build"]

    # Extract week names (May 11-17, May 18-24, May 25-31)
    week_names = [w["name"] for w in weeks_data]

    html = '<h3>Monthly Kanban Board</h3>\n'
    html += '<div style="margin-top: 16px; overflow-x: auto; border: 1px solid #ddd; border-radius: 6px; background: white;">\n'
    html += '  <table style="width: 100%; font-size: 13px; border-collapse: collapse;">\n'

    # Header
    html += '    <thead>\n'
    html += '      <tr style="background: #f0f0f0; border-bottom: 2px solid #ddd;">\n'
    html += '        <th style="padding: 10px 12px; text-align: left; font-weight: 600; width: 110px;">Domain</th>\n'
    for week in week_names:
        html += f'        <th style="padding: 10px 12px; text-align: left; font-weight: 600; width: 140px;">{week}</th>\n'
    html += '      </tr>\n'
    html += '    </thead>\n'

    # Body
    html += '    <tbody>\n'

    for domain in all_domains:
        header_color = DOMAIN_COLORS[domain]["header"]
        cell_color = DOMAIN_COLORS[domain]["cell"]

        html += f'      <tr style="border-bottom: 1px solid #eee;">\n'
        html += f'        <td style="padding: 10px 12px; font-weight: 600; background: {header_color};">{domain}</td>\n'

        for week_data in weeks_data:
            tasks = week_data["domains"].get(domain, [])
            html += f'        <td style="padding: 10px 12px; background: {cell_color};">'

            if tasks:
                html += '<ul style="margin: 0; padding-left: 18px; font-size: 12px;">'
                for task in tasks:
                    html += f'<li>{task}</li>'
                html += '</ul>'

            html += '</td>\n'

        html += '      </tr>\n'

    html += '    </tbody>\n'
    html += '  </table>\n'
    html += '</div>\n'

    return html

def extract_newsletter_html(newsletter_file):
    """Extract tbody from newsletter HTML file."""
    if not newsletter_file.exists():
        return ""

    text = newsletter_file.read_text()
    match = re.search(r'<tbody>(.*?)</tbody>', text, re.DOTALL)
    return match.group(1) if match else ""

def format_calendar_events(events, date_filter=None):
    """Format calendar events into HTML list items."""
    html_items = []

    for event in events:
        start = event.get("start", {})
        start_time = start.get("dateTime", start.get("date", ""))
        summary = event.get("summary", "Untitled")

        if not start_time:
            continue

        try:
            # Parse ISO format
            if "T" in start_time:
                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M")
            else:
                dt = datetime.fromisoformat(start_time)
                time_str = "All day"
        except:
            time_str = ""

        if time_str:
            html_items.append(f"<li>{time_str} — {summary}</li>")
        else:
            html_items.append(f"<li>{summary}</li>")

    return "\n          ".join(html_items)

def generate_html(calendar_events, newsletter_html):
    """Generate complete morning ritual HTML."""
    now = datetime.now()
    today = now.strftime("%A, %Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # Parse today's events
    today_events = []
    upcoming_events = []

    for event in calendar_events:
        start = event.get("start", {})
        start_time = start.get("dateTime", start.get("date", ""))

        if not start_time:
            continue

        try:
            if "T" in start_time:
                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(start_time)
                dt = dt.replace(hour=0, minute=0, second=0)
        except:
            continue

        event_copy = event.copy()
        event_copy["_datetime"] = dt

        if dt.date() == now.date():
            today_events.append(event_copy)
        else:
            upcoming_events.append(event_copy)

    today_events.sort(key=lambda e: e.get("_datetime", now))

    today_list = format_calendar_events(today_events) or "<li>No events scheduled</li>"
    upcoming_list = ""

    for event in upcoming_events[:10]:
        dt = event["_datetime"]
        date_str = dt.strftime("%b %d")
        summary = event.get("summary", "Untitled")
        upcoming_list += f'<li>{date_str} — {summary}</li>\n          '

    if not upcoming_list.strip():
        upcoming_list = "<li>No upcoming events</li>"

    # Month kanban
    month_file = BASE_DIR / "calendar-projects" / f"{now.strftime('%b %Y')}.md"
    kanban_html = ""
    if month_file.exists():
        weeks_data = parse_month_markdown(month_file)
        kanban_html = build_kanban_html(weeks_data)

    # Complete HTML
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
      <p class="generated-at">{today} · Generated at {time_str} AM</p>
    </div>

    <div class="content">
      <div class="section">
        <div class="section-title">📅 This Week</div>
        <h3>Today ({now.strftime("%b %d")})</h3>
        <ul>
          {today_list}
        </ul>
        <h3>Upcoming ({(now + timedelta(days=1)).strftime("%b %d")}-{(now + timedelta(days=7)).strftime("%d")})</h3>
        <ul>
          {upcoming_list}
        </ul>
        {kanban_html}
      </div>

      <div class="section">
        <div class="section-title">📰 Wall Street Journal</div>
        <p>Take 15 minutes to read today's news.</p>
        <a href="https://messages.google.com/web/conversations" target="_blank" style="display:inline-block;margin-top:12px;padding:10px 16px;background:#2980b9;color:white;text-decoration:none;border-radius:6px;font-size:14px;">Open Google Messages</a>
      </div>

      <div class="section">
        <div class="section-title">📬 Newsletters & Digest</div>
        <p style="margin-bottom: 16px; color: #666;">Newsletters analyzed and delivered to your inbox.</p>
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
            {newsletter_html}
          </tbody>
        </table>
      </div>
    </div>

    <div class="footer">
      Morning Briefing — {now.strftime("%Y-%m-%d")} | All data fresh · Go build.
    </div>
  </div>
</body>
</html>"""

    return html

if __name__ == "__main__":
    import sys

    # Read calendar events from stdin (JSON)
    calendar_json = sys.stdin.read().strip()
    try:
        events = json.loads(calendar_json) if calendar_json else []
    except json.JSONDecodeError:
        events = []

    # Extract newsletter HTML
    newsletter_file = BASE_DIR / ".tmp" / f"newsletter_digest_{datetime.now().strftime('%Y-%m-%d')}.html"
    newsletter_html = extract_newsletter_html(newsletter_file)

    # Generate HTML
    html = generate_html(events, newsletter_html)

    # Write to file
    output_file = BASE_DIR / ".claude" / "skills" / "morning" / "morning-ritual.html"
    output_file.write_text(html)

    print(f"✓ Generated {output_file}")
