import os
import requests
import json

def fixed_widget():
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
                "object": "block", 
                "type": "callout",
                "callout": {
                    "rich_text": [
                        { "text": { "content": "📅 우유의 한 달" }, "annotations": { "bold": True } },
                        { "text": { "content": "\n\n(이곳에 캘린더를 만들어주세요!)" }, "annotations": { "italic": True, "color": "gray" } }
                    ],
                    "icon": { "emoji": "🗓️" },
                    "color": "gray_background"
                },
                "children": [
                     {
                        "object": "block", "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                { "text": { "content": "👇 " } },
                                { "text": { "content": "설정 방법", "annotations": { "bold": True } } },
                                { "text": { "content": "\n1. 이 블록 안을 클릭하고 " } },
                                { "text": { "content": "/linked", "annotations": { "code": True } } },
                                { "text": { "content": " 입력 → '데이터베이스의 링크된 보기' 선택" } },
                                { "text": { "content": "\n2. " } },
                                { "text": { "content": "Health Log", "annotations": { "bold": True, "color": "blue" } } },
                                { "text": { "content": " 선택" } },
                                { "text": { "content": "\n3. 생성된 표의 옵션(...) → 레이아웃 → " } },
                                { "text": { "content": "캘린더", "annotations": { "bold": True } } },
                                { "text": { "content": " 선택" } },
                                { "text": { "content": "\n4. 속성: 모두 숨김 / 페이지 열기: 중앙에서 열기" } }
                            ]
                        }
                    }
                ]
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
    fixed_widget()
