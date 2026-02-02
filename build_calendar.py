import os
import requests
import json
import datetime
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
        emoji = icon.get("emoji") if icon and icon.get("type") == "emoji" else "📝"
        
        if date_str not in calendar_data:
            calendar_data[date_str] = []
            
        calendar_data[date_str].append({
            "id": page_id,
            "title": title,
            "emoji": emoji,
            "display": f"{emoji} {title}"
        })
        
    return calendar_data

def generate_interactive_html(calendar_data):
    # Pass data as JSON
    data_json = json.dumps(calendar_data)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Milk's Month</title>
        <style>
            ::-webkit-scrollbar {{ display: none; }}
            html {{ -ms-overflow-style: none; scrollbar-width: none; }}
            
            :root {{
                --bg-color: #ffffff;
                --text-color: #37352f;
                --grid-border: #e0e0e0;
                --hover-bg: #f7f7f5;
                /* Pet Theme Colors */
                --today-bg: #edf9ee;
                --today-text: #1b5e20;
                --underline-color: #81C784;
            }}
            body {{
                font-family: "Courier New", Courier, monospace;
                margin: 0;
                padding: 12px 20px 20px 20px;
                background-color: var(--bg-color);
                color: var(--text-color);
                display: flex;
                flex-direction: column;
                align-items: center;
                user-select: none;
            }}
            
            .header-container {{
                display: flex;
                justify-content: flex-start; /* Align left */
                align-items: center;
                gap: 15px; /* Space between title and buttons */
                width: 100%;
                max-width: 600px;
                margin-bottom: 10px;
            }}
            
            h1 {{
                margin: 0;
                font-size: 0.9em; 
                font-weight: bold; 
                text-align: left;
            }}
            
            .nav-btn {{
                background: none;
                border: 1px solid transparent;
                cursor: pointer;
                font-family: "Courier New", Courier, monospace;
                font-size: 0.5em; /* Adjusted to 0.5em as requested */
                color: #999;
                padding: 0 1px; /* Tighter spacing */
                border-radius: 4px;
                transition: color 0.2s, background 0.2s;
            }}
            .nav-btn:hover {{
                color: #333;
                background: #f0f0f0;
            }}
            
            .calendar-grid {{
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 8px;
                width: 100%;
                max-width: 600px;
            }}
            
            .day-header {{
                text-align: center;
                font-size: 0.8em;
                color: #999;
                padding-bottom: 8px;
            }}
            
            .day-cell {{
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
            }}
            
            .day-cell:hover {{
                background: var(--hover-bg);
                z-index: 10;
            }}
            
            .day-cell.empty {{
                background: transparent;
                box-shadow: none;
                cursor: default;
            }}
            
            .day-cell.today {{
                background: var(--today-bg);
                color: var(--today-text);
                box-shadow: 0 0 0 1px var(--today-text);
            }}

            .tooltip {{
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
                max-width: 300px;
                opacity: 0;
                transition: opacity 0.3s;
                font-size: 0.8em;
                font-weight: normal;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                white-space: normal;
            }}
            
            .tooltip::after {{
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #333 transparent transparent transparent;
            }}
            
            .day-cell:hover .tooltip {{
                visibility: visible;
                opacity: 1;
            }}
            
            .entry-item {{ margin-bottom: 4px; }}
            .entry-item:last-child {{ margin-bottom: 0; }}

            .has-entry .day-number {{
                border-bottom: 3px solid var(--underline-color);
                padding-bottom: 2px;
                display: inline-block;
                line-height: 1.2;
            }}
            .day-number {{ pointer-events: none; }}

            .nav-container {
                display: flex;
                align-items: center;
                gap: 2px;
            }
        </style>
    </head>
    <body>
        <div class="header-container">
            <h1 id="monthLabel">Loading...</h1>
            <div class="nav-container">
                <button class="nav-btn" id="prevBtn">◀</button>
                <button class="nav-btn" id="nextBtn">▶</button>
            </div>
        </div>
        
        <div class="calendar-grid" id="calendarGrid">
            <!-- Headers and Days inserted by JS -->
        </div>

        <script>
            const eventData = {data_json};
            let currentDate = new Date(); // Defaults to today on client side

            const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

            function renderCalendar() {{
                const year = currentDate.getFullYear();
                const month = currentDate.getMonth(); // 0-11
                
                // Update Header
                const monthName = monthNames[month];
                document.getElementById('monthLabel').innerText = `${year} ${monthName}`;
                
                // Calculate Grid
                const firstDay = new Date(year, month, 1);
                const lastDay = new Date(year, month + 1, 0); // Last day of current month
                
                const numDays = lastDay.getDate();
                const startDayOfWeek = firstDay.getDay(); // 0 (Sun) - 6 (Sat)
                
                const grid = document.getElementById('calendarGrid');
                grid.innerHTML = ''; // Clear previous
                
                // Day Headers
                const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
                days.forEach(d => {{
                    const el = document.createElement('div');
                    el.className = 'day-header';
                    el.innerText = d;
                    grid.appendChild(el);
                }});
                
                // Empty cells before start
                for (let i = 0; i < startDayOfWeek; i++) {{
                    const el = document.createElement('div');
                    el.className = 'day-cell empty';
                    grid.appendChild(el);
                }}
                
                // Days
                const today = new Date();
                const isCurrentMonth = (today.getFullYear() === year && today.getMonth() === month);
                const todayDate = today.getDate();
                
                for (let d = 1; d <= numDays; d++) {{
                    const cell = document.createElement('div');
                    cell.className = 'day-cell';
                    
                    // construct YYYY-MM-DD string with padding
                    const mStr = String(month + 1).padStart(2, '0');
                    const dStr = String(d).padStart(2, '0');
                    const dateKey = `${{year}}-${{mStr}}-${{dStr}}`;
                    
                    const entries = eventData[dateKey] || [];
                    
                    if (isCurrentMonth && d === todayDate) {{
                        cell.classList.add('today');
                    }}
                    
                    if (entries.length > 0) {{
                        cell.classList.add('has-entry');
                        
                        // Create Tooltip
                        let tooltipContent = '';
                        entries.forEach(e => {{
                            tooltipContent += `<div class="entry-item">${{e.display}}</div>`;
                        }});
                        
                        const tooltip = document.createElement('div');
                        tooltip.className = 'tooltip';
                        tooltip.innerHTML = tooltipContent;
                        cell.appendChild(tooltip);
                    }} else {{
                         const tooltip = document.createElement('div');
                         tooltip.className = 'tooltip';
                         tooltip.innerText = 'No Info';
                         cell.appendChild(tooltip);
                    }}
                    
                    const numSpan = document.createElement('span');
                    numSpan.className = 'day-number';
                    numSpan.innerText = d;
                    cell.appendChild(numSpan);
                    
                    grid.appendChild(cell);
                }}
            }}

            // Event Listeners
            document.getElementById('prevBtn').addEventListener('click', () => {{
                currentDate.setMonth(currentDate.getMonth() - 1);
                renderCalendar();
            }});
            
            document.getElementById('nextBtn').addEventListener('click', () => {{
                currentDate.setMonth(currentDate.getMonth() + 1);
                renderCalendar();
            }});
            
            // Initial Render
            renderCalendar();
        </script>
    </body>
    </html>
    """
    return html

def main():
    token = os.environ.get("NOTION_TOKEN")
    # Health Log ID (Pet)
    db_id = "2f50d907-031e-800a-82db-e4ca63b42e6e"
    
    if not token:
        print("Notion token missing.")
        # Try to read locally if missing (optional fallback?)
        # For now, just exit or similar
        sys.exit(1)
        
    print("Fetching Notion data...")
    raw_data = fetch_health_log(token, db_id)
    print(f"Fetched {len(raw_data)} entries.")
    
    print("Parsing data...")
    calendar_data = parse_data(raw_data)
    
    print("Generating HTML...")
    html_content = generate_interactive_html(calendar_data)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("index.html created successfully.")

if __name__ == "__main__":
    main()
