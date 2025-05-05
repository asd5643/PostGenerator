from infoLLM import infoLLM 
from Threads import Threads_scraper as ts
from vectorDatabase import vectorDatabase as db
from threadsPost import ThreadsAPI
import json
import asyncio
class Workflow:
    def __init__(self):
        with open('config/threadsUser.json','r',encoding='utf-8') as f:
            cfg = json.load(f)
        self.threads=ts(username=cfg["username"])
        self.ai=infoLLM()
        self.database=db("threads")
        self.set_filter()
    def tagging_new_scrape_posts_into_pinecone(self):
        self.threads.filter_setting(gclike=1000)
        posts=(asyncio.run(
        self.threads.Top_crawl(batch=1)
        ))
        posts=json.loads(self.threads.getJosn(posts))
        results =[]
        for post in posts['posts']:
            payload=self.ai.system_prompt_tagging+"\n貼文列表:\n"+json.dumps(post, ensure_ascii=False, indent=1)
            response =self.ai.client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=payload,
                config={'response_mime_type': 'application/json'}
            )
            sigle_batch = json.loads(response.text)
            results.append(sigle_batch)
        self.database.store_embeddings_with_tag(posts=results)
    def set_filter(self, tags: list[str] = None, min_likes: int = 1000, within_days: int = 30):
        self.database.set_filter(tags=tags, min_likes=min_likes, within_days=within_days)
    def _query(self, userquery: str, top_k: int = 10) -> list[dict]:
        filter = self.database.filter.build()
        emdQuery = self.database.embed([userquery])[0]
        response = self.database.index.query(
            vector=emdQuery,
            top_k=top_k,
            include_metadata=True,
            namespace="threads",
            filter=filter
        )
        return response["matches"]
    def generate_post(self,userquery:str,style:str,size:int,tag:str)->str:
        self.set_filter(tags=[style])
        rsp=self._query(userquery=userquery)
        self.ai.set_system_prompt_generate(style=style,userquery=userquery,size=size,tag=tag)
        messages = [
            {"role": "system", "content":self.ai.system_prompt_generate}
        ]
        for post in rsp:
            messages.append({"role": "user", "content": post["metadata"]})
        messages.append({
            "role": "user",
            "content": json.dumps({"command": "analyze", "category": style}, ensure_ascii=False)
        })
        chat = self.ai.client.chats.create(
            model="gemini-2.0-flash-001",
        )
        return chat.send_message(json.dumps(messages,ensure_ascii=False)).text
    def evaluate_post(self,userquery:str,post:str,tag:str,style:str)->str:
        self.set_filter(tags=[style])
        rsp=self._query(userquery=userquery)
        few_shot=rsp[0]["metadata"]["text"]
        self.ai.set_system_prompt_evaluate(post=post,few_shot=few_shot,tag=tag,style=style)
        response =self.ai.client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=self.ai.system_prompt_evaluate,
                config={'response_mime_type': 'application/json'}
        )
        score = json.loads(response.text)
        return float(score['total_score']) 
    def work_flow(self,userquery:str,style:str,size:int,fetch:bool,tag:str)->str:
        if(fetch):
            self.tagging_new_scrape_posts_into_pinecone()
        score=0
        post=""
        while score<0.7:
            post=self.generate_post(tag=tag,userquery=userquery,style=style,size=size)
            score=self.evaluate_post(userquery=userquery,post=post,tag=tag,style=style)
            print(f"目前評分：{score} \n 文章：{post}")
        verify = input("請問要發佈嗎？(y/n)").lower()
        if verify == "y":
            threadsAPI = ThreadsAPI()
            post_id = threadsAPI.publish_text(post)
            print(f"發文成功！貼文 ID: {post_id}")
        else:
            print("已取消發文。")

if __name__ == "__main__":
    workflow = Workflow()
    userquery = input("請輸入要產生的文章內容短敘述:")
    category = input("請輸入要產生的類別文章：")
    tag = input("請輸入要使用的標籤")
    while category not in ["Emotion","Trend","Practical","Identity"]:
        print("請輸入正確的類別：Emotion｜Trend｜Practical｜Identity")
        category = input("請輸入要產生的類別文章：")   
    size=int(input("請輸入要產生的文章字數："))
    fetch = input("是否需要抓取資料？(y/n)").lower() == "y"
    workflow.work_flow(userquery=userquery,style=category,size=size,fetch=fetch,tag=tag)
       
                

        




    
