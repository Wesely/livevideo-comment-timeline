import streamlit as st
import requests
import csv
import time
import logging
import re
from datetime import datetime
import pytz
import os
import pandas as pd

# 設置 logging 基本配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 頁面名稱與對應的長期存取權杖字典
FACEBOOK_LONG_TERM_TOKEN_DICT = {
    "Vannise": "EAAHlt6ZBwJk8BO6jpnUYPuLTkYXxFZCnWy9fttLmIsPd1S1MtVgyR9zmeZBNQzFwrL4zF8TdxMHc3u8ClDxoaXO1P7IZBZCIh95X5jvum2162ksYYqvaYTdYeEkvBmoQL0acBtN4HHfH82ZA2ZCwaxWa5QZASUTLGYNZBUEzckzex2Lth1tZADRE7la8oeyZAy9dUic",
    "Vannise不斷電": "EAAHlt6ZBwJk8BO3uxEcRtHTBs73Lq2mwfAZCuSlJ8furlyCwICWpQltijcV75jqqCNA02C3Ub5r4sxQTJworTZC5G1xilqZAxg52Vkl8GmSwBsZBlb9D0r4AQjK5Gj0LktEvDWyvCEqfYriqaCnpEm87rAcu4xL6D8Iz5qn9ZBHTpZCvLj2AnBlvCUkQpKALHI8kQQ5vPzBZBt4ZBgGvYKzJF85Fk"
}

# Streamlit 介面設定
st.set_page_config(page_title="Facebook Token Selector & Comment Fetcher", page_icon="💬")
st.title("💬 Facebook Token Selector & Comment Fetcher")

# 新增下拉式選單讓使用者選擇頁面名稱
selected_page = st.selectbox(
    "請選擇 Facebook 頁面名稱",
    options=list(FACEBOOK_LONG_TERM_TOKEN_DICT.keys())
)

# 根據使用者選擇的頁面名稱，從字典中取出對應的 token
access_token = FACEBOOK_LONG_TERM_TOKEN_DICT[selected_page]

# 顯示選擇的頁面名稱和對應的 access token
st.write(f"選擇的頁面名稱: {selected_page}")
st.write(f"對應的 Access Token: {access_token}")

# 獲取當天日期並格式化為 YYYY-MM-DD
today = datetime.now().strftime("%Y-%m-%d")

# 使用者輸入，檔案名稱預設為當天日期
STREAM_NAME = st.text_input("請輸入檔案名稱 (例如: 2024-10-16-不斷電.早):", f"{today}-不斷電")
VIDEO_ID = st.text_input("請輸入 Facebook 影片 ID:", "1543222116619760")

# 動態設定檔案名稱
filename = f"{STREAM_NAME}-留言.csv"

# 檢查檔案是否存在，不存在則建立檔案
if not os.path.exists(filename):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['created_time', 'user_name', 'user_id', 'message', 'comment_id', 'item_id'])  # CSV header
    logging.info(f"檔案 {filename} 不存在，已自動建立")

def extract_item_id(message):
    if "+1" in message:
        match = re.search(r'(\d{4})', message)
        if match:
            return match.group(1)
    return ""

def convert_to_taiwan_time(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S%z")
    taiwan_tz = pytz.timezone("Asia/Taipei")
    taiwan_time = utc_time.astimezone(taiwan_tz)
    return taiwan_time.strftime("%Y-%m-%d %H:%M:%S")

def fetch_comments(api_url, filename):
    page_count = 0
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        while api_url:
            try:
                response = requests.get(api_url)
                if response.status_code != 200:
                    logging.error(f"Error fetching data: {response.status_code}")
                    break
                
                data = response.json()
                
                page_comments = []
                for comment in data.get('data', []):
                    created_time = comment.get('created_time')
                    message = comment.get('message')
                    user_name = comment.get('from', {}).get('name', 'Unknown')
                    user_id = comment.get('from', {}).get('id', 'Unknown')
                    comment_id = comment.get('id')

                    # 將 UTC 時間轉換為台灣時間
                    taiwan_time = convert_to_taiwan_time(created_time)

                    # 提取 item_id
                    item_id = extract_item_id(message)

                    page_comments.append([taiwan_time, user_name, user_id, message, comment_id, item_id])
                
                writer.writerows(page_comments)
                
                page_count += 1
                logging.info(f"抓取到第 {page_count} 頁，已寫入 {len(page_comments)} 條留言")
                
                api_url = data.get('paging', {}).get('next')

                time.sleep(1)
            
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                break

# 在 Streamlit 中執行留言抓取功能
if st.button("開始抓取留言"):
    if not access_token or not VIDEO_ID:
        st.error("請確保已選擇頁面和輸入影片 ID")
    else:
        st.info("開始抓取留言，請稍等...")
        initial_url = f"https://graph.facebook.com/v20.0/{VIDEO_ID}/comments?limit=1000&access_token={access_token}"
        fetch_comments(initial_url, filename)
        st.success(f"留言已成功抓取並儲存至 {filename}")

        # 讀取 CSV 並顯示
        df = pd.read_csv(filename)
        st.dataframe(df)

        # 提供下載按鈕
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="下載留言 CSV",
            data=csv,
            file_name=filename,
            mime='text/csv',
        )
