import os
import requests
import json
from datetime import datetime

def create_pet_database(token, page_id):
    url = "https://api.notion.com/v1/databases"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "parent": {
            "type": "page_id",
            "page_id": page_id
        },
        "icon": {
            "type": "emoji",
            "emoji": "🐾"
        },
        "title": [
            {
                "type": "text",
                "text": {
                    "content": "반려견 정보 (Pet Info)"
                }
            }
        ],
        "properties": {
            # Basic Info
            "이름": {
                "title": {}
            },
            "생일": {
                "date": {}
            },
            "프로필 사진": {
                "files": {}
            },
            
            # Health
            "몸무게 (kg)": {
                "number": {
                    "format": "number"
                }
            },
            "성별": {
                "select": {
                    "options": [
                        {"name": "남아", "color": "blue"},
                        {"name": "여아", "color": "pink"}
                    ]
                }
            },
            "중성화 여부": {
                "checkbox": {}
            },
            "혈액형": {
                "select": {
                    "options": [
                        {"name": "DEA 1.1 -", "color": "gray"},
                        {"name": "DEA 1.1 +", "color": "gray"},
                        {"name": "모름", "color": "default"}
                    ]
                }
            },
            "알레르기": {
                "multi_select": {
                    "options": [
                        {"name": "닭고기", "color": "orange"},
                        {"name": "소고기", "color": "brown"},
                        {"name": "꽃가루", "color": "yellow"}
                    ]
                }
            },
            "마지막 예방접종일": {
                "date": {}
            },
            "동물병원 연락처": {
                "phone_number": {}
            },
            
            # Lifestyle
            "견종": {
                "select": {}
            },
            "동물등록번호": {
                "rich_text": {}
            },
            "마이크로칩 위치": {
                "select": {
                    "options": [
                        {"name": "내장", "color": "green"},
                        {"name": "외장", "color": "blue"}
                    ]
                }
            },
            "옷 사이즈": {
                "select": {
                    "options": [
                        {"name": "S", "color": "default"},
                        {"name": "M", "color": "default"},
                        {"name": "L", "color": "default"},
                        {"name": "XL", "color": "default"},
                        {"name": "2XL", "color": "default"}
                    ]
                }
            },
            "현재 먹는 사료": {
                "rich_text": {}
            },
            "좋아하는 간식": {
                "multi_select": {}
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        db_data = response.json()
        print(f"데이터베이스가 성공적으로 생성되었습니다! ID: {db_data['id']}")
        return db_data['id']
    else:
        print(f"데이터베이스 생성 실패: {response.status_code}")
        print(response.text)
        return None

def add_pet_entry(token, database_id, name, birthday):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "parent": {
            "database_id": database_id
        },
        "properties": {
            "이름": {
                "title": [
                    {
                        "text": {
                            "content": name
                        }
                    }
                ]
            },
            "생일": {
                "date": {
                    "start": birthday
                }
            },
            "성별": {
                "select": {
                    "name": "남아" # Default assumption, user can change
                }
            },
            "중성화 여부": {
                "checkbox": True
            },
            "견종": {
                "select": {
                    "name": "말티즈" # Example default
                }
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"'{name}' 강아지 정보가 추가되었습니다.")
    else:
        print(f"데이터 추가 실패: {response.status_code}")
        print(response.text)

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("Error: NOTION_TOKEN or NOTION_PAGE_ID missing")
        return

    print("반려견 정보 데이터베이스를 생성합니다...")
    db_id = create_pet_database(token, page_id)
    
    if db_id:
        # 우유 정보 기본 추가
        # 기존 설정에서 생일을 가져오면 좋겠지만, 일단 사용자 요청대로 2013-09-30 고정 사용
        add_pet_entry(token, db_id, "우유", "2013-09-30")
        
        # Save DB ID to config for future use? 
        # Actually update_age.py will be updated to find it dynamically or use this ID.
        print("\n[완료] Notion 페이지를 확인해보세요!")

if __name__ == "__main__":
    main()
