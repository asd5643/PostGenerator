import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CLIENT_SECRET_FILE = 'config/credentials.json'
TOKEN_FILE = 'config/token.json'
SPREADSHEET_ID = '1NSOFeBnaBfyIprtL0YjhxIbbl7BYkZ2wemza78aL8yU' # 這是你的試算表 ID
SHEET_NAME = '工作表1'
def get_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def store_posts(posts: list[dict], spreadsheet_id: str = SPREADSHEET_ID, sheet_name: str = SHEET_NAME):
    creds = get_creds()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    # 準備要寫入的數據
    values = []
    for post in posts:
        row = [
            post.get("username",""),
            post.get("text",""),
            post.get("like_count",0),
            post.get("reply_count",0),
            post.get("id",""),
            post.get("Emotion",""),
            post.get("Trend",""),
            post.get("Practical",""),
            post.get("Identity",""),
            post.get("Visual",""),
            post.get("Other",""),
            post.get("reasoning",""),
        ]
        values.append(row)

    if not values:
        print("沒有要寫入的貼文。")
        return

    res = sheet.values().append(
        spreadsheetId=spreadsheet_id,
        range=sheet_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()
    print(f"{res.get('updates').get('updatedCells')} 個單元格已寫入。")

def fetch_all_posts(spreadsheet_id: str = SPREADSHEET_ID, sheet_name: str = SHEET_NAME) -> list[dict]:
    """讀取整張試算表，回傳 list of dict（第一列為欄位名稱）。"""
    creds = get_creds()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    # 讀取 A 到 L 欄（最多 12 欄），第一列當 headers
    RANGE = f"{sheet_name}!A:L"
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=RANGE).execute()
    rows = result.get('values', [])
    if not rows:
        return []
    headers = rows[0]
    posts = []
    for row in rows[1:]:
        # 把每行填到 dict，沒填的欄位設為空字串
        post = { headers[i]: row[i] if i < len(row) else "" 
                 for i in range(len(headers)) }
        posts.append(post)
    return posts

def get_posts_by_label(label: str, spreadsheet_id: str = SPREADSHEET_ID, sheet_name: str = SHEET_NAME) -> list[dict]:
    """
    根據 label（例如 "Emotion"、"Trend"）取出所有該欄位值為 "true" 的貼文。
    回傳該貼文的 dict 清單。
    """
    all_posts = fetch_all_posts(spreadsheet_id, sheet_name)
    filtered = []
    for post in all_posts:
        # 將標籤值小寫比對 "true" 或 "1"
        val = post.get(label, "").strip().lower()
        if val in ("true", "1", "yes"):
            filtered.append(post)
    return filtered
def get_posts_by_label(label: str, spreadsheet_id: str = SPREADSHEET_ID, sheet_name: str = SHEET_NAME) -> list[dict]:
    """
    根據 label（例如 "Emotion"、"Trend"）取出所有該欄位值為 "true" 的貼文。
    回傳該貼文的 dict 清單。
    """
    all_posts = fetch_all_posts(spreadsheet_id, sheet_name)
    filtered = []
    for post in all_posts:
        # 將標籤值小寫比對 "true" 或 "1"
        val = post.get(label, "").strip().lower()
        if val in ("true", "1", "yes"):
            filtered.append(post)
    return filtered
def get_posts_by_userid(user_id: str, spreadsheet_id: str = SPREADSHEET_ID, sheet_name: str = SHEET_NAME) -> list[dict]:
    """
    取出所有欄位user_id吻合的貼文。
    回傳該貼文的 dict 清單。
    """
    all_posts = fetch_all_posts(spreadsheet_id, sheet_name)
    filtered = []
    for post in all_posts:
        # 將標籤值小寫比對 "true" 或 "1"
        if post.get(user_id, "") in [user_id,"@"+user_id]:
            filtered.append(post)
    return filtered

if __name__ == "__main__":
    print("測試：寫入一筆 mock 貼文")
    # 示範：先寫入一筆 mock，然後讀出 Emotion 標籤為 true 的所有貼文
    #print(json.dumps(emo_posts, ensure_ascii=False, indent=2))