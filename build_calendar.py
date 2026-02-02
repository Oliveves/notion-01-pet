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
    # Map "YYYY-MM-DD" -> List of entries (dicts)
    calendar_data = {}
    
    for page in results:
        props = page.get("properties", {})
        page_id = page.get("id").replace("-", "")
        
        # Find Date Property
        date_candidates = ["날짜", "Date", "증상 발견 일시"]
        date_prop = None
        for key in date_candidates:
            if key in props:
                date_prop = props[key].get("date")
                if date_prop: break
        
        if not date_prop: continue
        date_str = date_prop.get("start")
        if not date_str: continue
        date_str = date_str[:10] # YYYY-MM-DD
        
        # Find Title Property
        title_candidates = ["이름", "Name", "Problem", "제목"]
        title_list = []
        for key in title_candidates:
            if key in props and props[key].get("type") == "title":
                title_list = props[key].get("title", [])
                break
        
        # Fallback if no specific title found, try any title type
        if not title_list:
            for key, val in props.items():
                if val.get("type") == "title":
                    title_list = val.get("title", [])
                    break
                    
        title = "".join([t.get("plain_text", "") for t in title_list])
        if not title: title = "Untitled"
        
        # Icon?
        icon = page.get("icon", {})
        emoji = icon.get("emoji") if icon.get("type") == "emoji" else "📝"
        
        if date_str not in calendar_data:
            calendar_data[date_str] = []
            
        calendar_data[date_str].append({
            "id": page_id,
            "title": title,
            "emoji": emoji,
            "display": f"{emoji} {title}"
        })
        
    return calendar_data

def generate_html(calendar_data):
    # Convert data to JSON for embedding
    json_data = json.dumps(calendar_data, ensure_ascii=False)
    
    # CSS
    css = """
    <style>
        /* Hide scrollbar */
        ::-webkit-scrollbar { display: none; }
        html { -ms-overflow-style: none; scrollbar-width: none; }

        :root {
            --bg-color: #ffffff;
            --text-color: #37352f;
            --grid-border: #e0e0e0;
            --hover-bg: #f7f7f5;
        }
        body {
            font-family: "Courier New", Courier, monospace;
            margin: 0;
            padding: 12px 20px 20px 20px;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            max-width: 600px;
            margin-bottom: 10px;
        }

        h1 { 
            margin: 0; 
            font-size: 1.0em; 
            font-weight: bold; 
            text-align: center;
        }
        
        button {
            border: none;
            background: none;
            cursor: pointer;
            font-size: 1.2em;
            color: #555;
            padding: 0 10px;
        }
        button:hover {
            color: #000;
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
            background-color: #333;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 8px 12px;
            position: absolute;
            z-index: 1000;
            bottom: 125%; 
            left: 50%;
            transform: translateX(-50%);
            width: max-content;
            max-width: 250px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.8em;
            font-weight: normal;
            pointer-events: auto;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            white-space: normal;
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
        }
        .entry-item:last-child {
            margin-bottom: 0;
        }
        
        /* Green Underline for dates with entries */
        .has-entry .day-number {
            border-bottom: 3px solid #81C784;
            padding-bottom: 2px;
            display: inline-block;
            line-height: 1.2;
        }
        
        .day-number {
             pointer-events: none;
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
        <div class="header-container">
            <button id="prevBtn" onclick="changeMonth(-1)">&#10094;</button>
            <h1 id="monthLabel">Month Year</h1>
            <button id="nextBtn" onclick="changeMonth(1)">&#10095;</button>
        </div>
        
        <div class="calendar-grid" id="calendarGrid">
            <!-- Headers -->
            <div class="day-header">Sun</div>
            <div class="day-header">Mon</div>
            <div class="day-header">Tue</div>
            <div class="day-header">Wed</div>
            <div class="day-header">Thu</div>
            <div class="day-header">Fri</div>
            <div class="day-header">Sat</div>
        </div>

        <script>
            // Derived from Notion Data through build_calendar.py
            const calendarData = {json_data};
            
            let currentDate = new Date(); // Defaults to today/current month

            function renderCalendar() {{
                const year = currentDate.getFullYear();
                const month = currentDate.getMonth(); // 0-based
                
                // Update Header
                const monthNames = ["January", "February", "March", "April", "May", "June", 
                                    "July", "August", "September", "October", "November", "December"];
                document.getElementById('monthLabel').innerText = `${{monthNames[month]}} ${{year}}`;
                
                const grid = document.getElementById('calendarGrid');
                
                // Clear old day cells (keep first 7 headers)
                // Using a strategy to remove all elements after the 7th
                while(grid.children.length > 7) {{
                    grid.removeChild(grid.lastChild);
                }}

                // Calculate geometry
                const firstDayObj = new Date(year, month, 1);
                const startDay = firstDayObj.getDay(); // 0(Sun) - 6(Sat)
                
                const lastDayObj = new Date(year, month + 1, 0);
                const daysInMonth = lastDayObj.getDate();

                // Generate Empty Cells for padding
                for(let i=0; i<startDay; i++) {{
                    const div = document.createElement('div');
                    div.className = 'day-cell empty';
                    grid.appendChild(div);
                }}

                // Generate Date Cells
                const today = new Date();
                const isCurrentMonth = (today.getFullYear() === year && today.getMonth() === month);

                for(let d=1; d<=daysInMonth; d++) {{
                    const mStr = String(month + 1).padStart(2, '0');
                    const dStr = String(d).padStart(2, '0');
                    const dateStr = `${{year}}-${{mStr}}-${{dStr}}`;
                    
                    const entries = calendarData[dateStr] || [];
                    
                    const cell = document.createElement('div');
                    let className = 'day-cell';
                    if (isCurrentMonth && d === today.getDate()) className += ' today';
                    if (entries.length > 0) className += ' has-entry';
                    cell.className = className;
                    
                    let innerHtml = `<span class="day-number">${{d}}</span>`;
                    
                    if (entries.length > 0) {{
                        let tipHtml = '<div class="tooltip">';
                        entries.forEach(e => {{
                            tipHtml += `<div class="entry-item">${{e.display}}</div>`;
                        }});
                        tipHtml += '</div>';
                        innerHtml += tipHtml;
                    }} else {{
                        innerHtml += '<div class="tooltip">No Info</div>';
                    }}
                    
                    cell.innerHTML = innerHtml;
                    grid.appendChild(cell);
                }}
            }}

            function changeMonth(delta) {{
                currentDate.setMonth(currentDate.getMonth() + delta);
                renderCalendar();
            }}

            // Start
            renderCalendar();
        </script>
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
