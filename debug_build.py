import json
from build_calendar import generate_interactive_html

# Mock Data
mock_data = {
    "2026-02-02": [{"id": "123", "title": "Test Entry", "emoji": "🧪", "display": "🧪 Test Entry"}]
}

try:
    print("Attempting to generate HTML...")
    html_content = generate_interactive_html(mock_data)
    with open("test_index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("SUCCESS: test_index.html created.")
except Exception as e:
    print(f"FAILURE: {e}")
