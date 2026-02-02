import json
import os
from build_calendar import generate_interactive_html

# Mock Data
mock_data = {
    "2026-02-02": [{"id": "123", "title": "Test Entry", "emoji": "🧪", "display": "🧪 Test Entry"}]
}

print("Generating index.html with mock data...")
html_content = generate_interactive_html(mock_data)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html created manually.")
