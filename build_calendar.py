import os
import requests
import json
import datetime
import calendar
import sys

# Force UTF-8 encoding for stdout/stderr to handle emojis on all platforms
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def fetch_health_log(token, db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Filter for this month? Or just fetch everything and filter in python?
    # Fetching simplified for now.
    payload = { "page_size": 100 }
    
    results = []
    has_more = True
    start_cursor = None
    
    while has_more:
        if start_cursor: payload["start_cursor"] = start_cursor
        
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code != 200:
            print(f"Error fetching DB: {res.text}")
            break
            
        data = res.json()
        results.extend(data.get("results", []))
        has_more = data.get("has_more")
        start_cursor = data.get("next_cursor")
        
    return results

def parse_data(results):
    # Map "YYYY-MM-DD" -> List of entries
    calendar_data = {}
    
    for page in results:
        props = page.get("properties", {})
        
        # Date
        date_prop = props.get("날짜", {}).get("date", {})
        if not date_prop: continue
        date_str = date_prop.get("start")
        if not date_str: continue
        
        # Title (Name)
        title_list = props.get("이름", {}).get("title", [])
        title = "".join([t.get("plain_text", "") for t in title_list])
        if not title: title = "Untitled"
        
        # Icon?
        icon = page.get("icon", {})
        emoji = icon.get("emoji") if icon.get("type") == "emoji" else "📝"
        
        if date_str not in calendar_data:
            calendar_data[date_str] = []
            
        calendar_data[date_str].append(f"{emoji} {title}")
        
    return calendar_data

def generate_html(calendar_data):
    # Current Month
    today = datetime.date.today()
    year = today.year
    month = today.month
    
    cal = calendar.Calendar(firstweekday=6) # Sunday start
    month_days = cal.monthdayscalendar(year, month)
    
    month_name = datetime.date(year, month, 1).strftime("%B %Y")
    
    # CSS
    css = """
    <style>
        /* Hide scrollbar for Chrome, Safari and Opera */
        ::-webkit-scrollbar {
            display: none;
        }
        /* Hide scrollbar for IE, Edge and Firefox */
        html {
            -ms-overflow-style: none;  /* IE and Edge */
            scrollbar-width: none;  /* Firefox */
        }

        :root {
            --bg-color: #ffffff;
            --text-color: #37352f;
            --grid-border: #e0e0e0;
            --hover-bg: #f7f7f5;
        }
        body {
            font-family: "Courier New", Courier, monospace; /* Typewriter font */
            margin: 0;
            padding: 12px 20px 20px 20px; /* Slightly increased top padding */
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { 
            margin-top: 0;
            margin-bottom: 10px; 
            font-size: 0.9em; 
            font-weight: bold; 
            width: 100%;
            max-width: 600px;
            text-align: left;
        }
        
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            width: 100%;
            max-width: 600px;
        }
        
        .day-header {
            text-align: center;
            font-size: 0.8em;
            color: #999;
            padding-bottom: 8px;
        }
        
        .day-cell {
            aspect-ratio: 1 / 1;
            border-radius: 8px;
            background: #fff;
            box-shadow: 0 0 0 1px var(--grid-border);
            position: relative;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .day-cell:hover {
            background: var(--hover-bg);
            z-index: 10;
        }
        
        .day-cell.empty {
            background: transparent;
            box-shadow: none;
            cursor: default;
        }
        
        .today {
            background: #edf9ee;
            color: #1b5e20;
            box-shadow: 0 0 0 1px #1b5e20;
        }
        
        /* Tooltip */
        .tooltip {
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 8px 12px;
            position: absolute;
            z-index: 100;
            bottom: 125%; /* Position above */
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.8em;
            font-weight: normal;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .tooltip::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #333 transparent transparent transparent;
        }
        
        .day-cell:hover .tooltip {
            visibility: visible;
            opacity: 1;
        }
        
        .entry-item {
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* Valid Entry Indicator dot */
        /* Valid Entry Indicator dot */
        .has-entry::after {
            content: '';
            position: absolute;
            bottom: 6px;
            width: 4px;
            height: 4px;
            background-color: #eb5757;
            border-radius: 50%;
        }
        
        /* Link styling */
        .day-link {
            text-decoration: none;
            color: inherit;
            display: flex;
            width: 100%;
            height: 100%;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
    </style>
    """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Milk's Month</title>
        {css}
    </head>
    <body>
        <h1>{month_name}</h1>
        <div class="calendar-grid">
            <div class="day-header">Sun</div>
            <div class="day-header">Mon</div>
            <div class="day-header">Tue</div>
            <div class="day-header">Wed</div>
            <div class="day-header">Thu</div>
            <div class="day-header">Fri</div>
            <div class="day-header">Sat</div>
    """
    
    # Database URL (Hardcoded for now as it matches db_id)
    # db_id = "2f50d907-031e-800a-82db-e4ca63b42e6e"
    db_url = "https://www.notion.so/2f50d907031e800a82dbe4ca63b42e6e"

    for week in month_days:
        for day in week:
            if day == 0:
                html += '<div class="day-cell empty"></div>'
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                entries = calendar_data.get(date_str, [])
                
                classes = "day-cell"
                if date_str == str(today): classes += " today"
                if entries: classes += " has-entry"
                
                tooltip_html = ""
                if entries:
                    content_html = "".join([f'<div class="entry-item">{e}</div>' for e in entries])
                    tooltip_html = f'<div class="tooltip">{content_html}</div>'
                elif day > 0:
                     tooltip_html = f'<div class="tooltip">No Info</div>'

                html += f"""
                <div class="{classes}">
                    <a href="{db_url}" class="day-link" target="_top">
                        {day}
                        {tooltip_html}
                    </a>
                </div>
                """
                
    html += """
        </div>
    </body>
    </html>
    """
    return html

def main():
    token = os.environ.get("NOTION_TOKEN")
    # Health Log ID
    db_id = "2f50d907-031e-800a-82db-e4ca63b42e6e"
    
    if not token:
        print("Notion token missing.")
        sys.exit(1)
        
    print("Fetching Notion data...")
    raw_data = fetch_health_log(token, db_id)
    print(f"Fetched {len(raw_data)} entries.")
    
    print("Parsing data...")
    calendar_data = parse_data(raw_data)
    
    print("Generating HTML...")
    html_content = generate_html(calendar_data)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("index.html created successfully.")

if __name__ == "__main__":
    main()
