import os
import sys
from datetime import datetime, timedelta, timezone
import requests
import json
import time

KST = timezone(timedelta(hours=9))

def calculate_age(birth_date_str):
    """
    생년월일(YYYY-MM-DD)을 입력받아 현재 나이를 'X년 X개월 X일차' 형식으로 반환합니다.
    """
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").replace(tzinfo=KST)
    # Use KST
    today = datetime.now(KST)
    
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
    current_year = datetime.now(KST).year
    current_month = datetime.now(KST).month
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
                    # Age Block: "D+" 혹은 "해", "개월" 등이 포함된 수식
                    # Also check for LaTeX structure if text is messed up
                    if ("D+" in full_content or "\\huge" in full_content) and found_blocks["age"] is None:
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

def ensure_settings_block(token, page_id, default_name="우유", default_birthday="2013-09-30"):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = { 
        "Authorization": f"Bearer {token}", 
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # Step 1: Check existing block
    existing_block_id = None
    needs_update = False
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        for b in res.json().get("results", []):
            if b.get("type") == "toggle":
                # Check contents
                rich_text = b.get("toggle", {}).get("rich_text", [])
                txt = "".join([t.get("plain_text", "") for t in rich_text])
                if "설정" in txt:
                    existing_block_id = b.get("id")
                    # Check if it has the new fields (e.g. check children or assume based on content if we could read children here)
                    # To be safe, we can read children or just rely on a force update if we can't confirm.
                    # Let's read the children of this block to check for "성별"
                    child_url = f"https://api.notion.com/v1/blocks/{existing_block_id}/children"
                    c_res = requests.get(child_url, headers=headers)
                    if c_res.status_code == 200:
                        c_txt = ""
                        for c in c_res.json().get("results", []):
                            if c.get("type") in ["paragraph", "callout"]:
                                c_rts = c.get(c.get("type"), {}).get("rich_text", [])
                                c_txt += "".join([t.get("plain_text", "") for t in c_rts])
                        
                        if "성별:" not in c_txt:
                            print("Old settings block found. Updating schema...")
                            needs_update = True
                        else:
                            return # Already up to date
                    break

    if existing_block_id and needs_update:
        # Delete old block
        del_url = f"https://api.notion.com/v1/blocks/{existing_block_id}"
        requests.delete(del_url, headers=headers)
        print("Deleted old settings block.")

    # Step 2: Create the Toggle Block
    payload_parent = {
        "children": [
            {
                "object": "block", "type": "toggle",
                "toggle": { 
                    "rich_text": [{ "type": "text", "text": { "content": "⚙️ 설정 (클릭하여 반려견 정보 입력)" } }] 
                }
            }
        ]
    }
    response = requests.patch(url, headers=headers, json=payload_parent)
    if response.status_code != 200:
        print(f"Failed to create settings parent block: {response.text}")
        return

    # Get the new block ID
    new_blocks = response.json().get("results", [])
    if not new_blocks:
        print("Created block but got no results?")
        return
        
    toggle_block_id = new_blocks[0].get("id")
    print(f"Settings block created ({toggle_block_id}). Adding content...")
    
    # Step 3: Add children to the new Toggle Block
    # List of fields to add
    fields = [
        f"이름: {default_name}",
        f"생일: {default_birthday}",
        "견종: ",
        "성별: ",
        "중성화 여부: ",
        "몸무게 (kg): ",
        "동물등록번호: ",
        "마이크로칩 위치: ",
        "옷 사이즈: ",
        "현재 먹는 사료: ",
        "좋아하는 간식: ",
        "혈액형: ",
        "알레르기: ",
        "마지막 예방접종일: ",
        "동물병원 연락처: "
    ]
    
    children_payload = []
    for field in fields:
        children_payload.append({
            "object": "block", "type": "paragraph",
            "paragraph": { "rich_text": [{ "type": "text", "text": { "content": field } }] }
        })
    
    # Add help callout
    children_payload.append({
        "object": "block", "type": "callout", 
        "callout": { 
            "rich_text": [{ "type": "text", "text": { "content": "내용을 자유롭게 수정하세요. (이름, 생일은 자동 반영)" } }], 
            "icon": { "type": "emoji", "emoji": "💡" } 
        } 
    })

    url_children = f"https://api.notion.com/v1/blocks/{toggle_block_id}/children"
    
    # Batch add (Note: Notion allows up to 100 children per request, we have ~16 so it fits)
    payload_children = { "children": children_payload }
    
    resp_child = requests.patch(url_children, headers=headers, json=payload_children)
    if resp_child.status_code != 200:
        print(f"Failed to add children to settings block: {resp_child.text}")
    else:
        print("Settings content added successfully.")

def get_config_from_database(token, page_id):
    """
    페이지 내의 '반려견 정보' 데이터베이스를 찾아서 첫 번째 항목의 이름과 생일을 반환합니다.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # 1. 페이지의 자식 중 데이터베이스 찾기
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    db_id = None
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            for block in response.json().get("results", []):
                if block.get("type") == "child_database":
                    # 제목 확인
                    if "반려견 정보" in block.get("child_database", {}).get("title", ""):
                        db_id = block.get("id")
                        print(f"반려견 정보 데이터베이스 발견: {db_id}")
                        break
    except Exception as e:
        print(f"DB 검색 실패: {e}")
        
    if not db_id:
        # DB가 없으면 기존 방식(텍스트 파싱)이나 기본값 사용
        return {}
        
    # 2. 데이터베이스 쿼리
    query_url = f"https://api.notion.com/v1/databases/{db_id}/query"
    try:
        # 첫 번째 페이지만 가져옴
        q_response = requests.post(query_url, headers=headers, json={"page_size": 1})
        if q_response.status_code == 200:
            results = q_response.json().get("results", [])
            if results:
                page = results[0]
                props = page.get("properties", {})
                
                config = {}
                
                # 이름 (Title)
                name_prop = props.get("이름", {}).get("title", [])
                if name_prop:
                    config["pet_name"] = name_prop[0].get("plain_text", "")
                    
                # 생일 (Date)
                date_prop = props.get("생일", {}).get("date", {})
                if date_prop:
                    config["birthday"] = date_prop.get("start", "")
                    
                print(f"DB에서 설정 로드: {config}")
                return config
                
    except Exception as e:
        print(f"DB 쿼리 실패: {e}")
        
    return {}

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("Error: Notion Token or Page ID missing.")
        return

    config = load_config()
    
    # 1. DB에서 설정 로드 (기본값)
    print("Notion 데이터베이스에서 설정을 확인합니다...")
    db_config = get_config_from_database(token, page_id)
    if db_config:
        config.update(db_config)
    
    # 2. 텍스트 설정 블록 확인 (현재 값 읽기)
    print("텍스트 설정 블록을 확인합니다...")
    notion_config = get_config_from_notion(token, page_id)
    if notion_config:
        print(f"텍스트 설정 발견: {notion_config}")
        config.update(notion_config)
        
    # 3. 설정 블록 보장 (스키마 업데이트 및 생성)
    # 읽어온 최신 config 값을 사용하여 블록을 재생성하거나 업데이트함
    current_name = config.get("pet_name", "우유")
    current_birthday = config.get("birthday", "2013-09-30")
    
    ensure_settings_block(token, page_id, current_name, current_birthday)

    pet_name = config.get("pet_name")
    birth_date_str = config.get("birthday")
    print(f"최종 설정: {pet_name}, {birth_date_str}")
    
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
