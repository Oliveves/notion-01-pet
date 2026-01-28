import os
import requests
import json

def debug_widget():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "children": [
            {
                "object": "block", "type": "callout",
                "callout": {
                    "rich_text": [
                        { "text": { "content": "📅 우유의 한 달", "annotations": { "bold": True } } },
                        { "text": { "content": "\n\n(이곳에 캘린더를 만들어주세요!)", "annotations": { "color": "gray", "italic": True } } }
                    ],
                    "icon": { "emoji": "🗓️" },
                    "color": "gray_background",
                    "children": [
                         {
                            "object": "block", "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{ "text": { "content": "Test Child" } }]
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    print("--- Sending Payload ---")
    print(json.dumps(payload, indent=2))
    
    res = requests.patch(url, headers=headers, json=payload)
    print("\n--- Response ---")
    print(f"Status: {res.status_code}")
    print(res.text)

if __name__ == "__main__":
    debug_widget()
