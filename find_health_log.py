import os
import requests

def list_databases():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN missing")
        return

    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "filter": {
            "value": "database",
            "property": "object"
        },
        "page_size": 100
    }
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        print(f"Error searching: {res.text}")
        return
        
    data = res.json()
    print(f"Found {len(data['results'])} databases:")
    for db in data['results']:
        title = "Untitled"
        if db.get("title") and len(db["title"]) > 0:
            title = db["title"][0]["plain_text"]
        print(f"- [{title}] ID: {db['id']}")
        
if __name__ == "__main__":
    list_databases()
