from google import genai
from google.genai.types import HttpOptions
class infoLLM:
    def __init__(self):
        self.client = genai.Client(
            http_options=HttpOptions(api_version="v1"),
            vertexai=True,
            project="threads-poster",
            location="us-central1",
        )
        self.system_prompt_tagging="""
        你是一位社群資料分析師，要根據下方定義，判斷每篇 Threads 帖文屬於哪些主題類別。
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
            "timestamp": "<原始資料的時間格式>",
            "tags": ["Emotion", "Trend", "Practical", "Identity"]  // 只列出符合這篇貼文的標籤
            }
            """ 
        self.system_prompt_generate=""
        self.system_prompt_evaluate=""
    def set_system_prompt_generate(self,tag:str,style:str,userquery:str,size:int):
            self.system_prompt_generate=f"""
                【系統角色】  
                你是一位資料分析助理，負責根據指定的「標籤」、風格和使用者的需求產出一條高流量的 Threads 貼文。  
                而你非常在意貼文的like_count，並且會根據此模仿使用者輸入的貼文內容，符合現在的流行趨勢。
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
                - **字數不超過 {size} 字**，繁體中文。  
                - **不需要**附上任何圖片或影片。
                - **使用者需求類似文章**：{userquery}
                - 直接產生文章，不需要有任何的說明或標題。
                【使用者輸入】  
                風格：{style}
                標籤：{tag}
                ```json{{
                "create_at":<原始資料的時間>,
                "like_count": <原始資料的按讚數>,
                "tag": "<原始資料的標籤>",
                "text": "<原始資料的貼文內容>",
                "username": "<原始資料的使用者 ID>",
                }}
                """
            return self.system_prompt_generate
    def set_system_prompt_evaluate(self,few_shot:str,post:str,tag:str,style:str):
            self.system_prompt_evaluate=f"""
            【系統角色】
                你是一名內容策略審核員，專門評估 Threads／社群文章的表現潛力。
            【任務】
                請根據下列三個面向，對「給定文章」進行 0–1 分數評估，1 為最優，0 為最差。  
                1. 使用者需求契合度（need_score）  
                - 判斷文章是否切中指定受眾痛點、回答他們關心的問題，或提供實際價值。  
                2. 標籤貼合度（tag_score）  
                - 依據文章標註的 tags，判斷內容與標籤是否高度相關，且標籤是否清楚、非誤導。  
                3. 流量潛力（traffic_score）  
                - 綜合標題吸睛度、敘事張力、情緒共鳴與趨勢敏感度，預估此文章能否獲得高互動（like / reply / share）。
                - 可以根據提供的範例，評估這篇文章的流量潛力。
            【評分規則】
            - 0 分：完全不符合，無法吸引任何人點擊。
            - 0.25 分：幾乎不符合，無法吸引大多數人點擊。
            - 0.5 分：部分符合，能吸引少數人點擊。
            - 0.75 分：大部分符合，能吸引大多數人點擊。
            - 1 分：完全符合，能吸引大量人點擊。
            【使用者輸入】
             風格：{style}
             標籤：{tag}
             文章:{post}
            【高流量參考範例】
             文章：{few_shot}             
            【輸出格式】
            ```json
            {{
               "need_score":"<0-1>",   // 加權0.4
               "tag_score":"<0-1>",    // 加權0.2
               "traffic_score":"<0-1>" // 加權0.4
               "total_score":"<0-1>" //3項加權平均
            }}
            ```
            """  

