from google import genai 
from google.genai.types import HttpOptions
from Threads import Threads_scraper
from threadsStore import store_posts, get_posts_by_label
import json
import asyncio
from threadsPost import ThreadsAPI
from threadsRealdatabase import fetch_top_query, delete_posts, store_posts_to_firestore
with open('config/threadsUser.json','r',encoding='utf-8') as f:
        cfg = json.load(f)
threads=Threads_scraper(username=cfg['username'])
threads.filter_setting(gclike=100)
posts=(asyncio.run(
        threads.Top_crawl(batch=1)
    ))
posts=json.loads(threads.getJosn(posts))

system_prompt_tagging="""你是一位社群資料分析師，要根據下方定義，判斷每篇 Threads 帖文屬於哪些主題類別。
【主題類別定義】
1. Emotion – 情緒共鳴  
   - 真實抒發壓力、低潮、幽默自嘲等，目的在引發共鳴或安慰。  
2. Trend – 潮流參與  
   - 跟風梗、熱門 hashtag／挑戰、即時時事評論、迷因。  
3. Practical – 實用知識  
   - 生活小技巧、工具／清單推薦、速讀式教學、職場或戀愛洞察。  
4. Identity – 身分認同／圈層梗  
   - 只對特定族群有梗：#大學生 #工程師日常 #社畜心聲…"
【標註規則】
- 一篇貼文可屬於「多個」類別，從 Emotion、Trend、Practical、Identity 這四類中，找出所有符合此貼文的標籤 
- 先找**主導**類別；若同時符合其他類別，再額外標註。  
【輸出格式（JSON）】
```json
{
  "id": "<原始資料的唯一 ID>",
  "username": "<原始資料的使用者 ID>",
  "text": "<原始資料的貼文內容>",
  "like_count": <原始資料的按讚數>,
  "reply_count": <原始資料的回覆數>,
  "timestamp": "<原始資料的時間 ISO 8601 格式>",
  "tags": ["Emotion", "Trend", "Practical", "Identity"]  // 只列出符合這篇貼文的標籤
}
"""
project_id="threads-poster"
location="us-central1"
client = genai.Client(
    http_options=HttpOptions(api_version="v1"),
    vertexai=True,
    project=project_id,
    location=location,
)
results =[]
for post in posts['posts']:
   payload=system_prompt_tagging+"\n貼文列表:\n"+json.dumps(post, ensure_ascii=False, indent=1)
   response = client.models.generate_content(
      model="gemini-2.0-flash-001",
      contents=payload,
      config={'response_mime_type': 'application/json'}
   )
   sigle_batch = json.loads(response.text)
   results.append(sigle_batch)

store_posts_to_firestore(results)


category = input("請輸入要產生的類別文章：")

while category not in ["Emotion","Trend","Practical","Identity","Visual"]:
   print("請輸入正確的類別：Emotion｜Trend｜Practical｜Identity｜Visual")
   category = input("請輸入要產生的類別文章：")   
posts=fetch_top_query(limit=10,label=category,days_keep=7)

system_prompt_generate=f"""
【系統角色】  
你是一位資料分析助理，負責根據指定的「類別」產出一條高流量的 Threads 貼文。  
而你非常在意貼文的like_count，並且會根據此調整貼文內容，符合現在的流行趨勢。
注意產生內容不需要圖影加以輔助，適合由全文字的發文型式呈現。
[任務]
你將會收到好幾則 user message，每則裡面都是一段 JSON 陣列（examples chunk）。  
請**暫時不要**回應任何東西，直到最後收到一則，
{{"command": "analyze", "category": "<類別>"}}
- 請**模仿下方「參考貼文模式」**的風格與結構，但要用全新的內容。  
- 以第一人稱帶入場景
- 文章結構要包含：  
  1. **吸睛開頭**：一句勾起好奇／共鳴的文字  
  2. **核心亮點**：緊扣「類別」主題、融入足夠細節  
  3. **不用產生hashtag**
- **字數不超過 100 字**，繁體中文。  
- **不需要**附上任何圖片或影片。
- 直接產生文章，不需要有任何的說明或標題。
【使用者輸入】  
類別：{category}
```json{{
  "id": "<原始資料的唯一 ID>",
  "username": "<原始資料的使用者 ID>",
  "text": "<原始資料的貼文內容>",
  "like_count": <原始資料的按讚數>,
  "reply_count": <原始資料的回覆數>,
  "timestmp":<原始資料的時間>,
  "Emotion": true/false,
  "Trend": true/false,
  "Practical": true/false,
  "Identity": true/false,
  "Other": true/false
}}
"""
messages = [
    {"role": "system", "content": system_prompt_generate}
]
def clean_post_json(post):
    """清理一筆 post，適合輸出成 JSON"""
    ts = post.get("timestamp")
    if hasattr(ts, 'isoformat'):
        ts = ts.isoformat()

    return {
        "id": post.get("id", ""),
        "username": post.get("username", ""),
        "text": (post.get("text", "") or "").replace("\n", " "),
        "like_count": post.get("like_count", 0),
        "reply_count": post.get("reply_count", 0),
        "timestamp": ts
    }
# 2. 分批加入每則範例
for post in posts:
    
    messages.append({
        "role": "user",
        "content": json.dumps({"examples": [clean_post_json(post)]}, ensure_ascii=False)
    })
messages.append({
    "role": "user",
    "content": json.dumps({"command": "analyze", "category": category}, ensure_ascii=False)
})
chat = client.chats.create(
    model="gemini-2.0-flash-001",
)
response = chat.send_message(json.dumps(messages,ensure_ascii=False))
print("生成的貼文：")
print(response.text)
verify = input("請問要發佈嗎？(y/n)").lower()
if verify == "y":
    threadsAPI = ThreadsAPI()
    post_id = threadsAPI.publish_text(response.text)
    print(f"發文成功！貼文 ID: {post_id}")
else:
   print("已取消發文。")


