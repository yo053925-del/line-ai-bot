from flask import Flask, request
import google.generativeai as genai
import requests
import os

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

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
                try:
                    ai_reply = ask_gemini(user_msg)
                    reply_to_user(reply_token, ai_reply)
                except Exception as e:
                    reply_to_user(reply_token, "抱歉，目前系統忙碌中，請稍後再試。")
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
