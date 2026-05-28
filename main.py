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

SYSTEM_PROMPT = """你是 WE Media 的 AI 客服助理「小WE」，請用繁體中文、友善專業的語氣回覆客戶。回覆保持簡潔，每則不超過 200 字。

第一次見面或客人詢問你是誰時，才自我介紹：「您好！我是小WE，WE Media 的 AI 客服助理，很高興為您服務！」其他情況直接回答問題，不要每次都自我介紹。

【公司介紹】WE Media 是您的自媒體神隊友，專注於短影音代操與品牌 IP 打造。核心優勢：超過 1000 部影音產製經驗，累積觀看數突破 3000 萬，400+ 集 Podcast 製作，IG 粉絲最高紀錄 10 萬+，支援分期付款。

【服務內容】一條龍短影音代操：人設打造、企劃選題、腳本撰寫、拍攝剪輯、圖文內容、數據優化、全域分發。額外服務：AI 影片製作、線上課程平台（母公司提供）、Podcast 製作、精準廣告投放。

【短影音代操報價】我們提供短影音代操服務：每期8支短影音+8篇圖文，NT$264,000（開案預付88,000/每期88,000）。其他產業依需求客製報價。價格未含5%營業稅。若不需要圖文內容，每篇圖文可抵800元。

【AI影片報價】
基礎方案：30秒內、3場景以內 = NT$4,000（含2次小幅修改）
加價規則：
- 每增加5秒 +$500（從第31秒起計算）
- 每增加1個場景 +$500
- 超過1次改稿 +$500/次
- 急件（3天內完成）+30%～50%
- 客製腳本撰寫 +$1,500

計算範例：
- 30秒 3場景 = $4,000（基礎價）
- 60秒 3場景 = $4,000 + $3,000（多30秒=6個5秒×$500）= $7,000
- 30秒 5場景 = $4,000 + $1,000（多2個場景×$500）= $5,000
- 60秒 5場景 = $4,000 + $3,000 + $1,000 = $8,000

計算方式：超過30秒的部分，每5秒收$500；超過3個場景的部分，每個場景收$500。

【合作流程】第1-2個月啟動期：人設建立、選題腳本、拍攝剪輯。第3-5個月曝光期：持續產製上架、數據優化、結案報告。150天內實現品牌轉型。

【成功案例】醫療業沈耿仲醫師：觀看數成長40倍。傳統業sNug襪子叔叔：流量翻倍。財金T大理財筆記：0粉首支破14萬觀看。Podcast懦夫救星：單支500萬觀看。

【回覆原則】問報價只說明方案B，絕對不提方案A的任何內容或價格，方案A完全不存在。問AI影片說明$4,000起。問諮詢提供Email：WEmedia@wemediastudios.com。無法回答說「幫您轉給專人，請留下聯絡方式」。"""

def log_conversation(user_id, user_name, user_msg, ai_reply):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "parent": {"database_id": NOTION_CONV_DB},
            "properties": {
                "名稱": {"title": [{"text": {"content": now}}]},
                "用戶ID": {"rich_text": [{"text": {"content": user_id}}]},
                "使用者名稱": {"rich_text": [{"text": {"content": user_name}}]},
                "客戶問題": {"rich_text": [{"text": {"content": user_msg[:2000]}}]},
                "AI回覆": {"rich_text": [{"text": {"content": ai_reply[:2000]}}]}
            }
        }
        res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=data)
        print(f"Notion 對話記錄: {res.status_code} - {res.json().get('object','')}{res.json().get('code','')}{res.json().get('message','')}") 
    except Exception as e:
        import traceback
        print(f"記錄對話失敗: {e}")
        print(traceback.format_exc())

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
        import traceback
        print(f"更新客戶資料失敗: {e}")
        print(traceback.format_exc())

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
    print(f"DEBUG - NOTION_TOKEN: {'OK' if NOTION_TOKEN else 'MISSING'}, CONV_DB: {NOTION_CONV_DB[:8] if NOTION_CONV_DB else 'MISSING'}, CUST_DB: {NOTION_CUST_DB[:8] if NOTION_CUST_DB else 'MISSING'}")
    body = request.get_json()
    if not body:
        return "OK", 200
    for event in body.get("events", []):
        if event.get("type") == "follow":
            reply_token = event.get("replyToken")
            if reply_token:
                reply_to_user(reply_token, "您好！我是小WE，WE Media 的 AI 客服助理，很高興為您服務！\n\n有任何關於短影音代操、AI影片製作或線上課程的問題，歡迎隨時詢問 😊")
            continue
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
