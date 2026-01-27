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

def get_rich_text_objects(years, months, days, total_days, birth_date, pet_name):
    """
    타자기 폰트(\texttt) 디자인을 유지하며, 현재 계절에 맞춰 {nth}번째 {Season} 문구를 적용합니다.
    """
    current_year = datetime.now().year
    current_month = datetime.now().month
    birth_year = birth_date.year
    
    # 계절 판별 및 N번째 계산
    # 3-5: 봄 / 6-8: 여름 / 9-11: 가을 / 12,1,2: 겨울
    if 3 <= current_month <= 5:
        season_name = "봄"
        # 봄은 그 해의 연도로 계산
        nth_season = current_year - birth_year + 1
    elif 6 <= current_month <= 8:
        season_name = "여름"
        nth_season = current_year - birth_year + 1
    elif 9 <= current_month <= 11:
        season_name = "가을"
        nth_season = current_year - birth_year + 1
    else:
        season_name = "겨울"
        # 1, 2월은 작년 겨울 시즌에 포함되므로 보정
        season_year = current_year if current_month == 12 else (current_year - 1)
        nth_season = season_year - birth_year + 1
    
    equation_content = (
        f"\\texttt{{\\huge {years}}} \\texttt{{\\tiny \\ 해}} \\quad "
        f"\\texttt{{\\huge {months}}} \\texttt{{\\tiny \\ 개월}} \\quad "
        f"\\color{{gray}}\\texttt{{\\small (D+{total_days})}} \\quad "
        f"\\texttt{{\\scriptsize {pet_name}와 함께한 {nth_season}번째 {season_name}}}"
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

def load_config():
    """
    config.json 파일에서 설정을 읽어옵니다. 없으면 기본값을 반환합니다.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    default_config = {
        "pet_name": "우유",
        "birthday": "2013-09-30"
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # 기본값에 사용자 설정 덮어쓰기
                default_config.update(user_config)
                print("config.json 설정을 로드했습니다.")
        except Exception as e:
            print(f"config.json 로드 중 오류 발생: {e}")
            print("기본 설정을 사용합니다.")
    else:
        print("config.json이 없어 기본 설정을 사용합니다.")
        
    return default_config

def get_config_from_notion(token, page_id):
    """
    Notion 페이지의 블록들을 스캔하여 설정값을 읽어옵니다.
    지원 형식:
    - 이름: OOO
    - 생일: YYYY-MM-DD
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Notion 설정 읽기 실패: {response.status_code}")
        return {}
        
    config = {}
    data = response.json()
    
    for block in data.get("results", []):
        # 텍스트가 있는 블록 타입들 확인 (paragraph, heading 등)
        text_content = ""
        block_type = block.get("type")
        
        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "callout", "quote", "toggle"]:
            rich_texts = block.get(block_type, {}).get("rich_text", [])
            text_content = "".join([t.get("text", {}).get("content", "") for t in rich_texts])
            
        # 설정 파싱
        if "이름:" in text_content:
            try:
                config["pet_name"] = text_content.split("이름:")[1].strip()
                print(f"Notion에서 이름 발견: {config['pet_name']}")
            except:
                pass
                
        if "생일:" in text_content:
            try:
                config["birthday"] = text_content.split("생일:")[1].strip()
                print(f"Notion에서 생일 발견: {config['birthday']}")
            except:
                pass
                
    return config

def ensure_settings_block(token, page_id):
    """
    페이지에 설정값을 입력할 수 있는 Toggle 블록이 있는지 확인하고, 없으면 생성합니다.
    """
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # 1. 기존 블록 확인
    get_response = requests.get(url, headers=headers)
    if get_response.status_code == 200:
        data = get_response.json()
        for block in data.get("results", []):
            if block.get("type") == "toggle":
                rich_text = block.get("toggle", {}).get("rich_text", [])
                text_content = "".join([t.get("text", {}).get("content", "") for t in rich_text])
                if "설정" in text_content:
                    print("기존 설정 블록을 찾았습니다.")
                    return

    # 2. 없으면 생성
    print("설정 블록이 없습니다. 새로 생성합니다...")
    payload = {
        "children": [
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "⚙️ 설정 (이곳을 클릭하여 이름과 생일을 수정하세요)"
                            }
                        }
                    ]
                },
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        # 기본값은 config.json이나 코드의 기본값을 따름
                                        "content": "이름: 우유" 
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "생일: 2013-09-30"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "위 내용을 수정하면 다음 업데이트 시 반영됩니다."
                                    }
                                }
                            ],
                            "icon": {
                                "emoji": "💡"
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    post_response = requests.patch(url, headers=headers, json=payload)
    if post_response.status_code == 200:
        print("설정 블록을 성공적으로 생성했습니다.")
    else:
        print(f"설정 블록 생성 실패: {post_response.status_code}")
        print(post_response.text)

def main():
    # 노션 설정 확인 (환경변수)
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("\n[알림] Notion 토큰 또는 페이지 ID가 설정되지 않았습니다.")
        print("환경 변수 'NOTION_TOKEN'과 'NOTION_PAGE_ID'를 설정해야 실제로 노션에 업데이트됩니다.")
        return

    # 1. config.json 로드 (기본값)
    config = load_config()
    
    # 2. Notion 페이지에서 설정 로드 (덮어쓰기)
    # 먼저 설정 블록이 있는지 확인하고 없으면 만듦 (사용자 편의)
    ensure_settings_block(token, page_id)
    
    try:
        print("Notion 페이지에서 설정을 찾고 있습니다...")
        notion_config = get_config_from_notion(token, page_id)
        if notion_config:
            print("Notion에서 새로운 설정을 발견하여 적용합니다.")
            config.update(notion_config)
    except Exception as e:
        print(f"Notion 설정 읽기 중 오류: {e}")

    pet_name = config.get("pet_name")
    birth_date_str = config.get("birthday")
    
    # 나이 계산
    try:
        years, months, days, total_days = calculate_age(birth_date_str)
        birth_date_obj = datetime.strptime(birth_date_str, "%Y-%m-%d")
        rich_text_list = get_rich_text_objects(years, months, days, total_days, birth_date_obj, pet_name)
        
        print(f"[{pet_name}]의 현재 나이: {years}년 {months}개월 {days}일차 (D+{total_days})")
        print(f"생일: {birth_date_str}")
        
    except ValueError as e:
        print(f"오류: 생일 형식이 잘못되었습니다 ({birth_date_str}). YYYY-MM-DD 형식이어야 합니다.")
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
