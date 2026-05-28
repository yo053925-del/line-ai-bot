from flask import Flask, request
import google.generativeai as genai
import requests
import os
from datetime import datetime

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_CONV_DB = os.environ.get("NOTION_CONV_DB")
NOTION_CUST_DB = os.environ.get("NOTION_CUST_DB")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

SYSTEM_PROMPT = """
你是一間短影音代操公司的客服助理，請用繁體中文、友善專業的語氣回覆。

我們的服務包括：
- 短影音代操（企劃、腳本、拍攝、剪輯全包）
- AI 影片製作服務
- 專案 PM 管理
- 線上課程平台建立與販售（母公司提供）

回覆原則：
- 問到具體報價：回答「依專案規模與需求而定，歡迎留下聯絡方式讓專人為您報價」
- 問到合作流程：說明從諮詢到交付約 4–6 週
- 問到案例作品：說「歡迎私訊索取作品集，我們會盡快提供」
- 無法回答的問題：說「這個問題我幫您轉給專人處理，請稍候」
- 每則回覆不超過 150 字，保持簡潔
"""

def log_conversation(user_id, user_name, user_msg, ai_reply):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "parent": {"database_id": NOTION_CONV_DB},
            "properties": {
                "時間": {"title": [{"text": {"content": now}}]},
                "用戶ID": {"rich_text": [{"text": {"content": user_id}}]},
                "用戶名稱": {"rich_text": [{"text": {"content": user_name}}]},
                "客戶問題": {"rich_text": [{"text": {"content": user_msg}}]},
                "AI回覆": {"rich_text": [{"text": {"content": ai_reply}}]}
            }
        }
        requests.post(
            "https://api.notion.com/v1/pages",
            headers=NOTION_HEADERS,
            json=data
        )
    except Exception as e:
        print(f"記錄對話失敗: {e}")

def update_customer(user_id, user_name):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        res = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_CUST_DB}/query",
            headers=NOTION_HEADERS,
            json={"filter": {"property": "用戶ID", "rich_text": {"equals": user_id}}}
        )
        results = res.json().get("results", [])
        if results:
            page_id = results[0]["id"]
            count = results[0]["properties"]["互動次數"]["number"] + 1
            requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=NOTION_HEADERS,
                json={"properties": {
                    "最後互動時間": {"rich_text": [{"text": {"content": now}}]},
                    "互動次數": {"number": count}
                }}
            )
        else:
            data = {
                "parent": {"database_id": NOTION_CUST_DB},
                "properties": {
                    "用戶名稱": {"title": [{"text": {"content": user_name}}]},
                    "用戶ID": {"rich_text": [{"text": {"content": user_id}}]},
                    "首次互動時間": {"rich_text": [{"text": {"content": now}}]},
                    "最後互動時間": {"rich_text": [{"text": {"content": now}}]},
                    "互動次數": {"number": 1}
                }
            }
            requests.post(
                "https://api.notion.com/v1/pages",
                headers=NOTION_HEADERS,
                json=data
            )
    except Exception as e:
        print(f"更新客戶資料失敗: {e}")

def reply_to_user(reply_token, message):
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=body
    )

def ask_gemini(user_message):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )
    response = model.generate_content(user_message)
    return response.text

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    if not body:
        return "OK", 200
    for event in body.get("events", []):
        if event.get("type") == "message":
            if event["message"].get("type") == "text":
                user_msg = event["message"]["text"]
                reply_token = event["replyToken"]
                user_id = event["source"].get("userId", "unknown")
                user_name = "未知用戶"
                try:
                    profile_res = requests.get(
                        f"https://api.line.me/v2/bot/profile/{user_id}",
                        headers={"Authorization": f"Bearer {LINE_TOKEN}"}
                    )
                    if profile_res.status_code == 200:
                        user_name = profile_res.json().get("displayName", "未知用戶")
                except:
                    pass
                try:
                    ai_reply = ask_gemini(user_msg)
                    reply_to_user(reply_token, ai_reply)
                    log_conversation(user_id, user_name, user_msg, ai_reply)
                    update_customer(user_id, user_name)
                except Exception as e:
                    reply_to_user(reply_token, "抱歉，目前系統忙碌中，請稍後再試。")
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
