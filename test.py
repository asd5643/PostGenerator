
from Threads import Threads_scraper
import json
import asyncio
from threadsPost import ThreadsAPI
from threadsRealdatabase import fetch_top_query, delete_posts, store_posts_to_firestore
from vectorDatabase import vectorDatabase as db
from infoLLM import infoLLM
index=db("threads")
def add_data_into_pinecone():
   with open('config/threadsUser.json','r',encoding='utf-8') as f:
         cfg = json.load(f)
   threads=Threads_scraper(username=cfg['username'])
   threads.filter_setting(gclike=100)
   posts=(asyncio.run(
         threads.Top_crawl(batch=1)
      ))
   posts=json.loads(threads.getJosn(posts))
   ai=infoLLM()
   results =[]
   for post in posts['posts']:
      payload=ai.system_prompt_tagging+"\n貼文列表:\n"+json.dumps(post, ensure_ascii=False, indent=1)
      response =ai.client.models.generate_content(
         model="gemini-2.0-flash-001",
         contents=payload,
         config={'response_mime_type': 'application/json'}
      )
      sigle_batch = json.loads(response.text)
      results.append(sigle_batch)
   index.store_embeddings_with_tag(posts=results)


query=input("希望產生的文章內容短敘述")
Label =list(map(str.strip, input("請輸入要查詢的標籤（用空格分隔）：").split()))
index.set_filter(tags=Label, min_likes=1000, within_days=7)
query_result=index.query(query=query, top_k=3)
print(query_result)
def generate_post(query_result:dict,Label:str):
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
   類別：{Label}
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
   project_id="threads-poster"
   location="us-central1"
   client = genai.Client(
      http_options=HttpOptions(api_version="v1"),
      vertexai=True,
      project=project_id,
      location=location,
   )
   results =[]
   for post in query_result:
      payload=system_prompt_generate.format(Label=Label)+json.dumps(post, ensure_ascii=False, indent=1)
      response = client.models.generate_content(
         model="gemini-2.0-flash-001",
         contents=payload,
         config={'response_mime_type': 'application/json'}
      )
      sigle_batch = json.loads(response.text)
      results.append(sigle_batch)
   return results
