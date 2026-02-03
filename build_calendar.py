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

def find_health_log_id(token):
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "query": "Health Log",
        "filter": {
            "value": "database",
            "property": "object"
        },
        "page_size": 1
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                found_id = results[0]["id"]
                print(f"Observed 'Health Log' ID: {found_id}")
                return found_id
    except Exception as e:
        print(f"Error searching for DB: {e}")
        
    return None

def parse_data(raw_data):
    # Map "YYYY-MM-DD" -> List of entries (dicts)
    calendar_data = {}
    
    for page in raw_data:
        props = page.get("properties", {})
        page_id = page.get("id").replace("-", "")
        
        # 1. Smart Date Discovery
        date_str = None
        
        # Priority A: Look for type "date"
        for key, val in props.items():
            if val.get("type") == "date":
                date_obj = val.get("date")
                if date_obj:
                    date_str = date_obj.get("start")
                break
        
        # Priority B: Look for "created_time" (system property is root level, but sometimes aliases exist)
        # Actually page["created_time"] is always available at root.
        if not date_str:
            # Check if user wants to use Created Time property
            for key, val in props.items():
                if val.get("type") == "created_time":
                    date_str = val.get("created_time")
                    break

        # Priority C: Fallback to Page Created Time if absolutely no date property found
        if not date_str:
            date_str = page.get("created_time")

        if not date_str: continue 
        date_str = date_str[:10] # YYYY-MM-DD
        
        # 2. Smart Title Discovery
        title = "Untitled"
        for key, val in props.items():
            if val.get("type") == "title":
                title_list = val.get("title", [])
                if title_list:
                    title = "".join([t.get("plain_text", "") for t in title_list])
                break
                
        # 3. Icon
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

def generate_interactive_html(calendar_data, error_message=None):
    # Pass data as JSON
    data_json = json.dumps(calendar_data)
    
    # Determine header text
    header_text = "Loading..."
    if error_message:
        header_text = error_message
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Milk's Month</title>
        <style>
            /* ... (keep existing CSS) ... */
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
                color: { 'red' if error_message else 'inherit' }; /* Highlight error */
            }}
            /* v2.1 Debug Probe */
            
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

            .nav-container {{
                display: flex;
                align-items: center;
                gap: 2px;
            }}
        </style>
    </head>
    <body>
        <div class="header-container">
            <h1 id="monthLabel">{header_text}</h1>
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
                
                // Update Header if no error
                const currentTitle = document.getElementById('monthLabel').innerText;
                const isError = currentTitle.startsWith("Error") || 
                                currentTitle.startsWith("Token") || 
                                currentTitle.startsWith("Keys") || 
                                currentTitle.startsWith("No Data") ||
                                currentTitle.startsWith("Fetch");
                                
                if (!isError) {{
                     const monthName = monthNames[month];
                     document.getElementById('monthLabel').innerText = `${{year}} ${{monthName}}`;
                }}
                
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
    
    raw_data = []
    error_msg = None
    
    if not token:
        print("WARNING: Notion token missing. Generating empty calendar.")
        error_msg = "Token Missing"
    else:
        # Dynamically find Health Log ID
        db_id = find_health_log_id(token)
        
        if not db_id:
            print("ERROR: 'Health Log' database not found.")
            error_msg = "Health Log DB Not Found"
        else:
            print(f"Using Database ID: {db_id}")
            print("Fetching Notion data...")
            try:
                raw_data = fetch_health_log(token, db_id)
                print(f"Fetched {len(raw_data)} entries.")
                if not raw_data:
                     print("DEBUG: Database is empty or no permissions to view children.")
                     error_msg = "No Data Found (Empty DB)"
                
            except Exception as e:
                print(f"Error executing fetch: {e}")
                error_msg = f"Fetch Error: {str(e)[:20]}..."

    print("Parsing data...")
    calendar_data = parse_data(raw_data)
    
    # DEBUG: If raw data exists but calendar is empty, it's a parsing issue.
    # Show the available keys to the user.
    if not error_msg and raw_data and not calendar_data:
        first_props = raw_data[0].get("properties", {}).keys()
        props_str = ", ".join(first_props)
        print(f"DEBUG: Parse failed. Available keys: {props_str}")
        error_msg = f"Keys: {props_str[:50]}..." # Truncate for header
    
    print("Generating HTML...")
    html_content = generate_interactive_html(calendar_data, error_msg)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("index.html created successfully.")

if __name__ == "__main__":
    main()
