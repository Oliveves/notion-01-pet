import os
import requests
import json

def get_all_blocks(token, page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return []
        
    data = response.json()
    return data.get("results", [])

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("Set NOTION_TOKEN and NOTION_PAGE_ID env vars")
        return

def scan_blocks_recursive(token, block_ids, file_handle, depth=0):
    for block_id in block_ids:
        # Fetch children of this block (or if it's the page, we already have the list)
        # But wait, we need to minimize API calls.
        # Let's just define a function that processes a list of blocks and recurses if needed.
        pass

def process_blocks(token, blocks, file_handle):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    
    for block in blocks:
        block_type = block.get("type")
        block_id = block.get("id")
        
        # Check for equation content in this block
        if block_type in ["callout", "paragraph", "heading_1", "heading_2", "heading_3", "quote", "to_do", "toggle"]:
            rich_text = block.get(block_type, {}).get('rich_text', [])
            for rt in rich_text:
                if rt.get('type') == 'equation':
                    file_handle.write(f"--- FOUND EQUATION IN {block_type.upper()} ({block_id}) ---\n")
                    file_handle.write(rt['equation']['expression'] + "\n")
                    file_handle.write("---------------------------------------------\n")
        
        elif block_type == "equation":
            file_handle.write(f"--- FOUND EQUATION BLOCK ({block_id}) ---\n")
            file_handle.write(block['equation']['expression'] + "\n")
            file_handle.write("---------------------------------------------\n")

        # Recursion for container blocks
        if block.get("has_children"):
            # Only fetch children for layout blocks we expect (columns, toggles) to save time/limits
            if block_type in ["column_list", "column", "toggle", "callout"]:
                url = f"https://api.notion.com/v1/blocks/{block_id}/children"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    children = response.json().get("results", [])
                    process_blocks(token, children, file_handle)

def main():
    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    
    if not token or not page_id:
        print("Set NOTION_TOKEN and NOTION_PAGE_ID env vars")
        return

    # Initial fetch of page blocks
    top_level_blocks = get_all_blocks(token, page_id)
    
    if top_level_blocks:
        with open("all_equations.txt", "w", encoding="utf-8") as f:
            process_blocks(token, top_level_blocks, f)
        print("Equations saved to all_equations.txt")
    else:
        print("No blocks found.")
if __name__ == "__main__":
    main()
