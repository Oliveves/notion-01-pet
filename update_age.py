import os
import sys
from datetime import datetime
import requests
import json
import time

def calculate_age(birth_date_str):
    """
    생년월일(YYYY-MM-DD)을 입력받아 현재 나이를 'X년 X개월 X일차' 형식으로 반환합니다.
    """
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    today = datetime.now()
    
    years = today.year - birth_date.year
    months = today.month - birth_date.month
    days = today.day - birth_date.day
    
    if days < 0:
        months -= 1
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

def get_age_rich_text(years, months, days, total_days):
    """
     [LINE 2] 나이 정보 (타자기체 + 회색 D+)
     디자인: \texttt{\huge 12} \texttt{\tiny \ 해} \quad \texttt{\huge 3} \texttt{\tiny \ 개월} \hspace{5pt}\color{gray}\mathsf{\scriptsize (D+4503)}
    """
    equation_content = (
        f"\\texttt{{\\huge {years}}} \\texttt{{\\tiny \\ 해}} \\quad "
        f"\\texttt{{\\huge {months}}} \\texttt{{\\tiny \\ 개월}} \\hspace{{5pt}}\\color{{gray}}\\mathsf{{\\scriptsize (D+{total_days})}}"
    )
    return [{
        "type": "equation",
        "equation": {"expression": equation_content}
    }]

def get_season_rich_text(birth_date, pet_name):
    """
    [LINE 3] 계절 정보 + 이모티콘
    디자인: \color{gray} \textsf{\scriptsize 우유와 함께하는 13번째} \color{black} \mathbf{\scriptsize \ 겨울}
    """
    current_year = datetime.now().year
    current_month = datetime.now().month
    birth_year = birth_date.year
    
    # 계절 판별 및 N번째 계산
    if 3 <= current_month <= 5:
        season_name = "봄"
        season_emoji = "🌷"
        nth_season = current_year - birth_year + 1
    elif 6 <= current_month <= 8:
        season_name = "여름"
        season_emoji = "🍉"
        nth_season = current_year - birth_year + 1
    elif 9 <= current_month <= 11:
        season_name = "가을"
        season_emoji = "🪵"
        nth_season = current_year - birth_year + 1
    else:
        season_name = "겨울"
        season_emoji = "🧦"
        season_year = current_year if current_month == 12 else (current_year - 1)
        nth_season = season_year - birth_year + 1
        
    equation_content = (
        f"\\color{{gray}} \\textsf{{\\scriptsize {pet_name}와 함께하는 {nth_season}번째}} \\color{{black}} \\mathbf{{\\scriptsize \\ {season_name}}}"
    )
    
    return [
        {
            "type": "equation",
            "equation": {"expression": equation_content}
        },
        {
            "type": "text",
            "text": {"content": f" {season_emoji}"}
        }
    ]

def scan_page_for_targets(token, page_id):
    """
    페이지 전체를 스캔하여 대상 블록(나이, 계절)을 찾습니다.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    
    found_blocks = {"age": None, "season": None}
    
    # BFS 방식으로 탐색 (Queue)
    queue = [page_id] # 시작은 페이지 아이디
    visited = set()
    
    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        
        # 자식 블록 가져오기
        url = f"https://api.notion.com/v1/blocks/{current_id}/children"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                continue
            
            blocks = response.json().get("results", [])
            
            for block in blocks:
                b_type = block.get("type")
                b_id = block.get("id")
                
                # 내용 검사 (수식 포함 여부 확인)
                content_str = ""
                full_content = ""
                if b_type in ["paragraph", "heading_1", "heading_2", "heading_3", "callout", "quote", "toggle"]:
                    rich_text = block.get(b_type, {}).get("rich_text", [])
                    # Plain text 추출
                    plain_text = "".join([t.get("plain_text", "") for t in rich_text])
                    # Equation expression 추출 (수식 내부 텍스트 확인용)
                    equation_text = ""
                    for rt in rich_text:
                        if rt.get("type") == "equation":
                            equation_text += rt.get("equation", {}).get("expression", "")
                    
                    full_content = plain_text + equation_text
                    
                    # 시그니처 매칭
                    # Age Block: "D+" 혹은 "해", "개월" 등이 포함된 수식 (user specific: D+)
                    if "D+" in full_content and found_blocks["age"] is None:
                        print(f"Found Age Block: {b_id}")
                        found_blocks["age"] = b_id
                        
                    # Season Block: "함께하는" or "함께한"
                    if ("함께하는" in full_content or "함께한" in full_content) and found_blocks["season"] is None:
                        print(f"Found Season Block: {b_id}")
                        found_blocks["season"] = b_id
                
                # 더 깊이 탐색할 블록들 큐에 추가
                if block.get("has_children"):
                    queue.append(b_id)
                    
            if found_blocks["age"] and found_blocks["season"]:
                break
                
        except Exception as e:
            print(f"Error scanning block {current_id}: {e}")
            continue
            
    return found_blocks

def update_notion_block_content(token, block_id, rich_text_list, block_type="paragraph"):
    """
    특정 블록의 내용을 업데이트합니다.
    """
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 블록 타입에 맞춰 페이로드 생성
    if block_type == "callout":
         payload = { "callout": { "rich_text": rich_text_list } }
    else:
         # 기본적으로 paragraph로 취급
         payload = { "paragraph": { "rich_text": rich_text_list } }

    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        return True
    else:
        print(f"Update failed for {block_id}: {response.text}")
        return False

def get_config_from_notion(token, page_id):
    """
    Notion 페이지의 블록들을 스캔하여 설정값을 읽어옵니다. (이름, 생일)
    """
    config = {}
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = { "Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28" }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200: return {}
        data = response.json()
        
        results = data.get("results", [])
        
        for block in results:
            b_type = block.get("type")
            text = ""
            if b_type in ["paragraph", "toggle", "callout", "heading_1", "heading_2", "heading_3"]:
                 rich_texts = block.get(b_type, {}).get("rich_text", [])
                 text = "".join([t.get("plain_text", "") for t in rich_texts])
            
            if "이름:" in text: config["pet_name"] = text.split("이름:")[1].strip()
            if "생일:" in text: config["birthday"] = text.split("생일:")[1].strip()
            
            if b_type == "toggle" and "설정" in text:
                 t_url = f"https://api.notion.com/v1/blocks/{block['id']}/children"
                 t_res = requests.get(t_url, headers=headers)
                 if t_res.status_code == 200:
                     t_children = t_res.json().get("results", [])
                     for child in t_children:
                         c_type = child.get("type")
                         c_text = ""
                         if c_type in ["paragraph", "callout"]:
                             rts = child.get(c_type, {}).get("rich_text", [])
                             c_text = "".join([t.get("plain_text", "") for t in rts])
                         
                         if "이름:" in c_text: config["pet_name"] = c_text.split("이름:")[1].strip()
                         if "생일:" in c_text: config["birthday"] = c_text.split("생일:")[1].strip()
                         
    except Exception as e:
        print(f"Config scan error: {e}")
        
    return config

def load_config():
    config = { "pet_name": "우유", "birthday": "2013-09-30" }
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    return config

def ensure_settings_block(token, page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = { 
        "Authorization": f"Bearer {token}", 
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        for b in res.json().get("results", []):
            if b.get("type") == "toggle":
                txt = "".join([t.get("plain_text", "") for t in b.get("toggle", {}).get("rich_text", [])])
                if "설정" in txt: return

    print("Creating settings block...")
    payload = {
        "children": [
            {
                "object": "block", "type": "toggle",
                "toggle": { "rich_text": [{ "text": { "content": "⚙️ 설정 (이곳을 클릭하여 이름과 생일을 수정하세요)" } }] },
                "children": [
                    { "object": "block", "type": "paragraph", "paragraph": { "rich_text": [{ "text": { "content": "이름: 우유" } }] } },
                    { "object": "block", "type": "paragraph", "paragraph": { "rich_text": [{ "text": { "content": "생일: 2013-09-30" } }] } },
                    { "object": "block", "type": "callout", "callout": { "rich_text": [{ "text": { "content": "수정 후 다음 업데이트에 반영됩니다." } }], "icon": { "emoji": "💡" } } }
                ]
            }
        ]
    }
    requests.patch(url, headers=headers, json=payload)

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("Error: Notion Token or Page ID missing.")
        return

    config = load_config()
    ensure_settings_block(token, page_id)
    notion_config = get_config_from_notion(token, page_id)
    config.update(notion_config)
    
    pet_name = config.get("pet_name")
    birth_date_str = config.get("birthday")
    print(f"Config: {pet_name}, {birth_date_str}")
    
    try:
        years, months, days, total_days = calculate_age(birth_date_str)
        birth_date_obj = datetime.strptime(birth_date_str, "%Y-%m-%d")
    except Exception as e:
        print(f"Date Error: {e}")
        return

    print("Scanning page for target blocks (Smart Find)...")
    targets = scan_page_for_targets(token, page_id)
    
    age_block_id = targets["age"]
    season_block_id = targets["season"]
    
    if not age_block_id or not season_block_id:
        print(f"Could not find targets. Age: {age_block_id}, Season: {season_block_id}")
        print("Required Signatures: 'D+' (Age), '함께하는' (Season)")
        return

    # Update Blocks
    age_rich_text = get_age_rich_text(years, months, days, total_days)
    if update_notion_block_content(token, age_block_id, age_rich_text, "paragraph"):
        print("Updated Age Block successfully.")
        
    season_rich_text = get_season_rich_text(birth_date_obj, pet_name)
    if update_notion_block_content(token, season_block_id, season_rich_text, "paragraph"):
        print("Updated Season Block successfully.")

if __name__ == "__main__":
    main()
