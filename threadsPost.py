import json
import requests

class ThreadsAPI:
    def __init__(self):
        with open('config/threadsAPI.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        self.access_token = cfg['access_token']
        self.user_id =cfg['user_id']
    def _create_media_container(self,text=None, media_type="TEXT", image_url=None, video_url=None):
        url = f"https://graph.threads.net/v1.0/{self.user_id}/threads"
        params = {
                "access_token": self.access_token,
                "media_type": media_type,
            }
        if text:
            params["text"] = text
        if media_type == "IMAGE" and image_url:
            params["image_url"] = image_url
        if media_type == "VIDEO" and video_url:
            params["video_url"] = video_url
        resp = requests.post(url, params=params)
        resp.raise_for_status()
        creation_id = resp.json().get("id")
        return creation_id
    
    def _publish_media(self, creation_id):
        url = f"https://graph.threads.net/v1.0/{self.user_id}/threads_publish"
        params = {
            "access_token": self.access_token,
            "creation_id": creation_id,
        }
        resp = requests.post(url, params=params)
        resp.raise_for_status()
        post_id = resp.json().get("id")
        return post_id
    
    def publish_text(self, text):
        creation_id = self._create_media_container(text=text, media_type="TEXT")
        post_id = self._publish_media(creation_id)
        print("發文成功！")
        return post_id