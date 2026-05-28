from flask import Flask, request
from google import genai
from google.genai import types
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
你是 WE Media 的客服助理「小威」，請用繁體中文、友善專業的語氣回覆客戶。
回覆保持簡潔，每則不超過 200 字。

===【公司介紹】===
WE Media 是您的自媒體神隊友，專注於短影音代操與品牌 IP 打造。
我們不只製作爆款影音，更幫助品牌留下有溫度的故事。

核心優勢：
- 超過 1000 部影音產製經驗，累積觀看數突破 3000 萬
- 400+ 集 Podcast 製作經驗
- IG 粉絲最高紀錄 10 萬+
- 整合短影音、圖文、Podcast、線上課程、實體活動的全域流量閉環
- 支援分期付款，靈活減輕企業壓力

===【服務內容】===
我們提供完整的一條龍短影音代操服務，包含：
1. 人設打造：深入了解業主故事，建立具溫度的專業 IP
2. 企劃選題：深入分析市場趨勢與受眾心理，找到核心議題
3. 腳本撰寫：將專業轉化為大眾聽得懂的故事內容
4. 拍攝剪輯：多樣化拍攝形式（腳本演出、藏鏡人對談、專業訪談、日常隨拍）
5. 圖文內容：製作感性且具共鳴的圖文，加強與粉絲的日常連結
6. 數據優化：每月數據回溯分析，持續調整企劃方向
7. 全域分發：針對不同社群平台特性進行內容適配

額外服務：
- AI 影片製作（詳見下方報價）
- 線上課程平台建立與販售（母公司提供）
- Podcast 製作
- 精準廣告投放

===【短影音代操方案與報價】===

▍方案 A：金融業集團方案（集團綜效型 IP 打造）
內容：每期 10 支短影音 + 8 篇圖文
特色：建立品牌 IP、銷售 IP、節目 IP 多維連動，最大化企業綜效
費用：NT$ 204,000（開案預付 68,000 / 每期付款 68,000）

▍方案 B：金融業個人/單位方案（專業形象與內容代操）
內容：每期 8 支短影音 + 8 篇圖文
特色：精準人設打造、專業腳本撰寫、高品質拍攝剪輯、帳號數據回溯分析
費用：NT$ 264,000（開案預付 88,000 / 每期付款 88,000）

注意事項：
- 所有價格未含 5% 營業稅
- 若不需要圖文內容，每篇圖文可抵 800 元
- 其他產業方案請洽詢，依需求客製報價

===【AI 影片報價】===

▍基礎方案
- 30 秒以內、3 個場景以內：NT$ 4,000
- 每增加 5 秒：+$500
- 每增加 1 個場景：+$500
- 包含 2 次畫面小幅度修改
- 流程：確認腳本內容、九宮格參考圖後開始製作

▍加價項目
- 超過 1 次改稿：+$500 / 次
- 急件（3 天內完成）：+30%～50%
- 客製腳本撰寫：+$1,500

===【合作流程】===
第 1-2 個月（啟動期）：
- 啟動會議與人設建立，深度訪談業主故事
- 選題會議與腳本撰寫
- 正式拍攝與剪輯審核

第 3-5 個月（曝光期）：
- 持續產製與全域上架各大社群平台
- 每月數據回溯與策略優化
- 結案報告與長期規劃

目標：在 150 天內實現從 0 到 1 的專業品牌轉型

===【成功案例】===
- 醫療產業｜沈耿仲耳鼻喉科醫師：影片觀看數成長 40 倍
- 傳統產業｜sNug 襪子叔叔：帳號活躍度與粉絲流量翻倍
- 財金網紅｜T大的理財投資筆記：0粉起號，首支破 14 萬觀看
- Podcast｜懦夫救星：單支 500 萬觀看

===【回覆原則】===
- 問到短影音代操報價：說明方案 A 與方案 B 的內容與費用，補充「其他產業可依需求客製，歡迎留下聯絡方式讓專人說明」
- 問到 AI 影片：說明基礎方案 NT$4,000 起，並列出加價項目
- 問到線上課程：說明這是母公司提供的額外服務，歡迎諮詢
- 問到合作流程：說明啟動期到曝光期的 150 天流程
- 問到案例：分享上述成功案例數據
- 無法回答的問題：說「這個問題我幫您轉給專人處理，請留下您的聯絡方式或稍候」
- 想預約諮詢：提供 Email：WEmedia@wemediastudios.com
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
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=user_message
    )
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
                    print(f"處理訊息失敗: {e}")
                    reply_to_user(reply_token, "抱歉，目前系統忙碌中，請稍後再試。")
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
