import os
import sys
from datetime import datetime
import requests
import json

# 설정 (사용자가 직접 수정하거나 환경 변수로 설정)
# NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "YOUR_NOTION_TOKEN_HERE")
# PAGE_ID = os.environ.get("NOTION_PAGE_ID", "YOUR_PAGE_ID_HERE")

def calculate_age(birth_date_str):
    """
    생년월일(YYYY-MM-DD)을 입력받아 현재 나이를 'X년 X개월 X일차' 형식으로 반환합니다.
    """
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    today = datetime.now()
    
    # 만 나이 계산 로직이 아님. 단순 기간 계산 (X년 X개월 X일째)
    # relativedelta를 사용하면 더 정확하지만, 표준 라이브러리만 사용하기 위해 직접 계산
    
    years = today.year - birth_date.year
    months = today.month - birth_date.month
    days = today.day - birth_date.day
    
    if days < 0:
        months -= 1
        # 이전 달의 날짜 수 가져오기
        first_day_of_this_month = today.replace(day=1)
        # last_month_last_day = (first_day_of_this_month - birth_date.resolution).day # resolution removed
        
        import calendar
        prev_month_year = today.year if today.month > 1 else today.year - 1
        prev_month = today.month - 1 if today.month > 1 else 12
        _, prev_month_days = calendar.monthrange(prev_month_year, prev_month)
        days += prev_month_days

    if months < 0:
        years -= 1
        months += 12
        
    # 일차 계산 (태어난 날부터 며칠째인지)
    total_days = (today - birth_date).days + 1
    
    return years, months, days, total_days

def get_rich_text_objects(years, months, days, total_days):
    """
    모노톤 디자인을 적용한 하나의 Equation Text 객체를 반환합니다.
    디자인: \textsf{\huge {years}} \textsf{\small Y} \quad \textsf{\huge {months}} \textsf{\small M} \quad \color{gray}\textsf{\small (D+{total_days})}
    """
    equation_content = (
        f"\\textsf{{\\huge {years}}} \\textsf{{\\small Y}} \\quad "
        f"\\textsf{{\\huge {months}}} \\textsf{{\\small M}} \\quad "
        f"\\color{{gray}}\\textsf{{\\small (D+{total_days})}}"
    )

    return [
        {
            "type": "equation",
            "equation": {
                "expression": equation_content
            }
        }
    ]

def update_notion_block(token, block_id, rich_text_list):
    """
    Notion API를 사용하여 블록의 내용을 업데이트합니다.
    rich_text_list: get_rich_text_objects()에서 반환된 리스트
    """
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 콜아웃 블록 업데이트 페이로드
    payload = {
        "callout": {
            "rich_text": rich_text_list
        }
    }
    
    response = requests.patch(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("성공적으로 업데이트되었습니다!")
        return True
    else:
        print(f"업데이트 실패: {response.status_code}")
        print(response.text)
        return False

def get_first_callout_block(token, page_id):
    """
    페이지의 블록 자식들을 조회하여 첫 번째 콜아웃 블록의 ID를 반환합니다.
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"블록 조회 실패: {response.status_code}")
        print(response.text)
        return None
        
    data = response.json()
    for block in data.get("results", []):
        if block.get("type") == "callout":
            return block.get("id")
            
    return None

def create_callout_block(token, page_id, rich_text_list):
    """
    페이지에 새로운 콜아웃 블록을 추가합니다.
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "children": [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": rich_text_list,
                    "icon": {
                        "emoji": "🐶"
                    }
                }
            }
        ]
    }
    
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("새로운 콜아웃 블록이 생성되었습니다!")
        return True
    else:
        print(f"블록 생성 실패: {response.status_code}")
        print(response.text)
        return False

def main():
    # 우유의 생년월일
    OOYU_BIRTHDAY = "2013-09-30"
    
    # 나이 계산
    years, months, days, total_days = calculate_age(OOYU_BIRTHDAY)
    rich_text_list = get_rich_text_objects(years, months, days, total_days)
    
    print(f"우유의 현재 나이: {years}년 {months}개월 {days}일차 (D+{total_days})")
    
    # 노션 설정 확인
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("\n[알림] Notion 토큰 또는 페이지 ID가 설정되지 않았습니다.")
        print("환경 변수 'NOTION_TOKEN'과 'NOTION_PAGE_ID'를 설정해야 실제로 노션에 업데이트됩니다.")
        return

    # 페이지 내 첫 번째 콜아웃 블록 찾기
    print("페이지에서 콜아웃 블록을 찾는 중...")
    block_id = get_first_callout_block(token, page_id)
    
    if block_id:
        print(f"콜아웃 블록 발견: {block_id}")
        update_notion_block(token, block_id, rich_text_list)
    else:
        print("페이지 최상단에서 콜아웃 블록을 찾을 수 없습니다.")
        print("새로운 콜아웃 블록을 생성합니다...")
        create_callout_block(token, page_id, rich_text_list)

if __name__ == "__main__":
    main()
