from flask import Flask, request
import requests
import os
from datetime import datetime

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
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

SYSTEM_PROMPT = """你是 WE Media 的客服助理「小威」，請用繁體中文、友善專業的語氣回覆客戶。回覆保持簡潔，每則不超過 200 字。

【公司介紹】WE Media 是您的自媒體神隊友，專注於短影音代操與品牌 IP 打造。核心優勢：超過 1000 部影音產製經驗，累積觀看數突破 3000 萬，400+ 集 Podcast 製作，IG 粉絲最高紀錄 10 萬+，支援分期付款。

【服務內容】一條龍短影音代操：人設打造、企劃選題、腳本撰寫、拍攝剪輯、圖文內容、數據優化、全域分發。額外服務：AI 影片製作、線上課程平台（母公司提供）、Podcast 製作、精準廣告投放。

【短影音代操報價】方案A金融業集團：每期10支短影音+8篇圖文，NT$204,000（開案預付68,000/每期68,000）。方案B金融業個人/單位：每期8支短影音+8篇圖文，NT$264,000（開案預付88,000/每期88,000）。其他產業依需求客製報價。價格未含5%營業稅。

【AI影片報價】基礎方案：30秒內3場景NT$4,000。每增加5秒+$500，每增加1場景+$500，含2次小幅修改。加價：超過1次改稿+$500/次，急件3天內+30-50%，客製腳本+$1,500。

【合作流程】第1-2個月啟動期：人設建立、選題腳本、拍攝剪輯。第3-5個月曝光期：持續產製上架、數據優化、結案報告。150天內實現品牌轉型。

【成功案例】醫療業沈耿仲醫師：觀看數成長40倍。傳統業sNug襪子叔叔：流量翻倍。財金T大理財筆記：0粉首支破14萬觀看。Podcast懦夫救星：單支500萬觀看。

【回覆原則】問報價說明方案A和B並邀請留聯絡方式。問AI影片說明$4,000起。問諮詢提供Email：WEmedia@wemediastudios.com。無法回答說「幫您轉給專人，請留下聯絡方式」。"""

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
        requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=data)
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
            requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json={
                "parent": {"database_id": NOTION_CUST_DB},
                "properties": {
                    "用戶名稱": {"title": [{"text": {"content": user_name}}]},
                    "用戶ID": {"rich_text": [{"text": {"content": user_id}}]},
                    "首次互動時間": {"rich_text": [{"text": {"content": now}}]},
                    "最後互動時間": {"rich_text": [{"text": {"content": now}}]},
                    "互動次數": {"number": 1}
                }
            })
    except Exception as e:
        print(f"更新客戶資料失敗: {e}")

def reply_to_user(reply_token, message):
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"},
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": message}]}
    )

def ask_openai(user_message):
    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 500
        }
    )
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

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
                    ai_reply = ask_openai(user_msg)
                    reply_to_user(reply_token, ai_reply)
                    log_conversation(user_id, user_name, user_msg, ai_reply)
                    update_customer(user_id, user_name)
                except Exception as e:
                    print(f"處理訊息失敗: {e}")
                    reply_to_user(reply_token, "抱歉，目前系統忙碌中，請稍後再試。")
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
