import os
import requests
import json

def create_calendar_widget():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("Error: Notion credentials missing.")
        return

    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Step 1: Create the container Callout
    print("Creating Calendar Widget (Container)...")
    payload = {
        "children": [
            {
                "object": "block", 
                "type": "callout",
                "callout": {
                    "rich_text": [
                        { "type": "text", "text": { "content": "📅 우유의 한 달" }, "annotations": { "bold": True } },
                        { "type": "text", "text": { "content": "\n\n(이곳에 캘린더를 만들어주세요!)" }, "annotations": { "italic": True, "color": "gray" } }
                    ],
                    "icon": { "type": "emoji", "emoji": "🗓️" },
                    "color": "gray_background"
                }
            }
        ]
    }
    
    callout_id = None
    res = requests.patch(url, headers=headers, json=payload)
    if res.status_code == 200:
        results = res.json().get("results", [])
        if results:
            callout_id = results[0].get("id")
            print(f"Widget Container created. ID: {callout_id}")
    else:
        print(f"Failed to create widget container: {res.text}")
        return

    # Step 2: Append Instructions inside the Callout
    if callout_id:
        print("Appending Instructions...")
        child_url = f"https://api.notion.com/v1/blocks/{callout_id}/children"
        child_payload = {
            "children": [
                {
                    "object": "block", "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            { "type": "text", "text": { "content": "👇 " } },
                            { "type": "text", "text": { "content": "설정 방법" }, "annotations": { "bold": True } },
                            { "type": "text", "text": { "content": "\n1. 이 블록 안을 클릭하고 " } },
                            { "type": "text", "text": { "content": "/linked" }, "annotations": { "code": True } },
                            { "type": "text", "text": { "content": " 입력 → '데이터베이스의 링크된 보기' 선택" } },
                            { "type": "text", "text": { "content": "\n2. " } },
                            { "type": "text", "text": { "content": "Health Log" }, "annotations": { "bold": True, "color": "blue" } },
                            { "type": "text", "text": { "content": " 선택" } },
                            { "type": "text", "text": { "content": "\n3. 생성된 표의 옵션(...) → 레이아웃 → " } },
                            { "type": "text", "text": { "content": "캘린더" }, "annotations": { "bold": True } },
                            { "type": "text", "text": { "content": " 선택" } },
                            { "type": "text", "text": { "content": "\n4. 속성: 모두 숨김 / 페이지 열기: 중앙에서 열기" } }
                        ]
                    }
                }
            ]
        }
        c_res = requests.patch(child_url, headers=headers, json=child_payload)
        if c_res.status_code == 200:
            print("Instructions appended successfully.")
        else:
            print(f"Failed to append instructions: {c_res.text}")

if __name__ == "__main__":
    create_calendar_widget()
