import asyncio, json, os
from typing import List, Dict, Optional
from nested_lookup import nested_lookup
from parsel import Selector        # 仍可用來抓第一次的 script
from playwright.async_api import async_playwright

class ThreadsScraper:
    def __init__(self,
                 search_choice: str = "like_count",
                 acc: bool = False,
                 username: Optional[List[str]] = None):
        self.url = "https://www.threads.net/@"
        self.search_choice = search_choice
        self.acc = acc
        self.username = username or []
        self.seen = self._load_seen()

    # ---------- 公用小工具 ----------
    def _load_seen(self):
        try:
            with open("config/existID.json", "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def _save_seen(self):
        with open("config/existID.json", "w", encoding="utf-8") as f:
            json.dump(list(self.seen), f, ensure_ascii=False, indent=1)

    def _parse_post(self, item: Dict) -> Dict:
        """用 jmespath 濾掉肥肉。"""
        import jmespath
        return jmespath.search(
            """
            {
              id: post.id,
              code: post.code,
              text: post.caption.text,
              like_count: post.like_count,
              reply_count: post.text_post_app_info.direct_reply_count,
              username: post.user.username,
              media_urls: post.carousel_media[].image_versions2.candidates[0].url,
              video_urls: post.video_versions[].url
            }
            """,
            item,
        )

    # ---------- 👇 新的抓法 ----------
    async def crawl_user(self, username: str, max_posts: int = 20) -> List[Dict]:
        """回傳單一使用者的貼文（已排序、去重）。"""
        posts: List[Dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # 攔截 /api/graphql 的 response
            async def handle_response(resp):
                if "/api/graphql" not in resp.url:
                    return
                ctype = resp.headers.get("content-type", "")
                if "json" not in ctype:            # 只要 JSON 回應
                    return
                try:
                    body = await resp.json()
                except Exception:
                    return

                # 找所有 thread_items
                for group in nested_lookup("thread_items", body):
                    for item in group:
                        parsed = self._parse_post(item)
                        pid = parsed["id"]
                        if pid in self.seen:
                            continue
                        posts.append(parsed)
                        self.seen.add(pid)
              
            page.on("response", handle_response)
            while len(posts) < max_posts:
                # 進入頁面（把第一批首刷資料也吃掉）
                await page.goto(f"{self.url}{username}", timeout=60_000)

                # 把 hydration script 裏的 thread_items 也撈一下
                selector = Selector(await page.content())
            
                for payload in selector.css("script[type='application/json'][data-sjs]::text").getall():
                    if '"thread_items"' not in payload:
                        continue
                    data = json.loads(payload)
                    for group in nested_lookup("thread_items", data):
                        print("ok1")
                        for item in group:
                            print("ok2")
                            if(len(posts)>=max_posts):
                                print("finish")
                            parsed = self._parse_post(item)
                            pid = parsed["id"]
                            if pid not in self.seen:
                                print("now:",len(posts))
                                posts.append(parsed)
                                self.seen.add(pid)

                # 觸發捲動以便前端送分頁 GraphQL
                print("scrolling...:", len(posts))
                await page.mouse.wheel(0, 8000)              # 一次滑到底
                await page.wait_for_timeout(20000)            # 簡單等待網路靜止
            await page.close()
            await browser.close()

        self._save_seen()
        # 依需求排序
        posts.sort(key=lambda p: p.get(self.search_choice) or 0,
                   reverse=not self.acc)
        return posts[:max_posts]

# --- demo ---
async def demo():
    s = ThreadsScraper(username=["huang.weizhu"])
    result = await s.crawl_user("huang.weizhu", max_posts=30)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(demo())