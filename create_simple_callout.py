import os
import requests
import json

def create_simple_callout():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Try fully explicit structure
    payload = {
        "children": [
            {
                "object": "block", 
                "type": "callout",
                "callout": {
                    "rich_text": [
                        { 
                            "type": "text",
                            "text": { "content": "📅 우유의 한 달" }, 
                            "annotations": { "bold": True } 
                        },
                        { 
                            "type": "text",
                            "text": { "content": "\n\n(이곳에 캘린더를 만들어주세요!)" }, 
                            "annotations": { "italic": True, "color": "gray" } 
                        }
                    ],
                    "icon": { "type": "emoji", "emoji": "🗓️" },
                    "color": "gray_background"
                }
            }
        ]
    }
    
    # Not including children yet.
    
    print("--- Sending Payload ---")
    print(json.dumps(payload, indent=2))
    
    res = requests.patch(url, headers=headers, json=payload)
    print("\n--- Response ---")
    print(f"Status: {res.status_code}")
    print(res.text)
    
    if res.status_code == 200:
        results = res.json().get("results", [])
        if results:
            return results[0].get("id")
    return None

if __name__ == "__main__":
    create_simple_callout()
