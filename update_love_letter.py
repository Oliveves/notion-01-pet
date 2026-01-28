import os
import requests
import json
import random
import sys

# Force UTF-8 for stdout/stderr to handle emojis on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def get_random_love_letter(token, db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Fetch all entries (assuming not more than 100 for now, or pagination if needed)
    # For a simple randomizer, one page is enough to start.
    payload = { "page_size": 100 }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Failed to query database: {response.status_code} {response.text}")
            return None
            
        results = response.json().get("results", [])
        if not results:
            print("No entries found in Love Letter database.")
            return None
            
        # Pick random
        choice = random.choice(results)
        page_id = choice.get("id")
        
        # Try to get page content (children)
        child_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        child_res = requests.get(child_url, headers=headers)
        
        lines = []
        if child_res.status_code == 200:
            blocks = child_res.json().get("results", [])
            for block in blocks:
                if block.get("type") == "paragraph":
                    text_list = block.get("paragraph", {}).get("rich_text", [])
                    plain_text = "".join([t.get("plain_text", "") for t in text_list])
                    if plain_text.strip():
                        lines.append(plain_text)
        
        # If body is empty, fallback to title
        if not lines:
            props = choice.get("properties", {})
            title_prop = props.get("하고싶은 말", {}).get("title", [])
            if title_prop:
                text = "".join([t.get("plain_text", "") for t in title_prop])
                lines.append(text)
            else:
                 return "사랑해" # Fallback
        
        # Return the list of lines directly
        return lines
        
    except Exception as e:
        print(f"Error getting love letter: {e}")
        return None

def find_or_create_target_blocks(token, page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    heading_id = None
    callout_id = None
    
    # Scan page
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        blocks = res.json().get("results", [])
        for i, block in enumerate(blocks):
            if block.get("type") == "heading_1":
                txt = "".join([t.get("plain_text", "") for t in block.get("heading_1", {}).get("rich_text", [])])
                if "Love letter" in txt or "Love Letter" in txt:
                    heading_id = block.get("id")
                    # Check next block for callout
                    if i + 1 < len(blocks) and blocks[i+1].get("type") == "callout":
                        callout_id = blocks[i+1].get("id")
                    break
    
    # Create if missing
    if not heading_id:
        print("Creating 'Love Letter' section...")
        # We append to the bottom for now, or top if preferred. Let's append to bottom.
        payload = {
            "children": [
                {
                    "object": "block", "type": "heading_1",
                    "heading_1": { "rich_text": [{ "text": { "content": "💌 Love Letter" } }] }
                },
                {
                    "object": "block", "type": "callout",
                    "callout": {
                        "rich_text": [{ "text": { "content": "Loading..." } }],
                        "icon": { "emoji": "💝" }
                    }
                }
            ]
        }
        res = requests.patch(url, headers=headers, json=payload)
        if res.status_code == 200:
            new_blocks = res.json().get("results", [])
            if len(new_blocks) >= 2:
                callout_id = new_blocks[1].get("id")
        else:
            print(f"Failed to create section: {res.text}")
            
    elif not callout_id:
        print("Found header but missing Callout. Creating Callout...")
        # Append callout after heading? 
        # API doesn't easily support "insert after ID" directly in 'append' endpoint without re-ordering.
        # But 'append' adds to end. 
        # For simplicity, let's just add it to the end of page if not found immediately after.
        # Or better, just add it to the end of page.
        payload = {
            "children": [
                {
                    "object": "block", "type": "callout",
                    "callout": {
                        "rich_text": [{ "text": { "content": "Loading..." } }],
                        "icon": { "emoji": "💝" }
                    }
                }
            ]
        }
        res = requests.patch(url, headers=headers, json=payload)
        if res.status_code == 200:
            callout_id = res.json().get("results", [])[0].get("id")
            
    return callout_id

def get_child_block_id(token, parent_id):
    url = f"https://api.notion.com/v1/blocks/{parent_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        results = res.json().get("results", [])
        if results:
            return results[0].get("id"), results[0].get("type")
    return None, None

def update_equation_block(token, block_id, block_type, lines):
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # Format each line individually
    # Each line format: \texttt{\scriptsize \color{green}{TEXT}}
    formatted_lines = [f"\\texttt{{\\scriptsize \\color{{green}}{{{line}}}}}" for line in lines]
    
    # Join with \\ and add vertical spacing [-0.1em]
    # Python string needs \\\\ for LaTeX \\
    lines_joined = " \\\\[-0.1em] ".join(formatted_lines)
    
    # Just raw lines joined, no wrapper environment as requested
    latex_content = lines_joined
    
    payload = {
        block_type: { # e.g. "paragraph"
            "rich_text": [
                {
                    "type": "equation",
                    "equation": { "expression": latex_content }
                }
            ]
        }
    }
    
    res = requests.patch(url, headers=headers, json=payload)
    if res.status_code == 200:
        print("Block updated successfully.")
    else:
        print(f"Failed to update block: {res.text}")

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    db_id = "2f60d907-031e-8085-80ae-eb6323149741" 
    
    # Existing Green Callout ID found by scan
    target_callout_id = "2f60d907-031e-802d-b5b2-f985d454c290"
    
    if not token or not page_id:
        print("Error: Notion credentials missing.")
        return

    print("Fetching random love letter...")
    lines = get_random_love_letter(token, db_id)
    if not lines:
        return
    print(f"Selected: {lines}")
    
    print(f"Finding child block of {target_callout_id}...")
    child_id, child_type = get_child_block_id(token, target_callout_id)
    
    if child_id and child_type:
        print(f"Updating child block {child_id} ({child_type})...")
        update_equation_block(token, child_id, child_type, lines)
    else:
        print("Could not find child block to update.")

if __name__ == "__main__":
    main()
