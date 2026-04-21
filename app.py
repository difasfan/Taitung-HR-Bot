import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# ==========================================
# 1. 初始化設定與 API 鑰匙
# ==========================================
st.set_page_config(page_title="臺東縣府差勤小助手 (聊天室版)", page_icon="💬")

try:
    GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("⚠️ 無法讀取 API Key！請確認已在 Streamlit Secrets 中設定。")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# 【自訂模型備援名單】
MODEL_LIST = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite-001",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite"
]

# ==========================================
# 2. 讀取法規資料庫
# ==========================================
@st.cache_data
def load_data():
    try:
        return pd.read_excel("rules.xlsx")
    except Exception:
        return pd.DataFrame(columns=["Source", "Keywords", "Title", "Answer"])

df = load_data()

# ==========================================
# 3. 聊天室「記憶卡」初始化
# ==========================================
# 如果網頁剛打開，還沒有記憶，就幫它建一個空的記憶清單
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 放入第一句歡迎詞
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "您好！我是臺東縣府差勤小助手👋 \n請隨時問我差勤相關問題，或是延續我們剛剛的話題喔！"
    })

# ==========================================
# 4. 網頁介面 (側邊欄與標題)
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統設定與資訊")
    st.write(f"📚 已收錄法規：{len(df)} 條")
    
    # 增加一個「清除對話」的按鈕
    if st.button("🗑️ 清除對話紀錄 (開啟新話題)"):
        st.session_state.messages = []
        st.rerun() # 重新整理網頁

st.title("💬 臺東縣府差勤小助手")
st.caption("支援連續對話記憶與多模型自動備援")
st.divider()

# ==========================================
# 5. 繪製歷史對話泡泡
# ==========================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 6. 接收新問題與 AI 處理邏輯
# ==========================================
# st.chat_input 是底部的對話輸入框
if user_query := st.chat_input("請輸入您的問題，例如：請問喪假規定..."):
    
    # A. 把同仁的新問題顯示在畫面上，並存入記憶卡
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    # B. 準備打包給 AI 的法規資料
    if df.empty:
        st.error("請先準備 rules.xlsx 檔案。")
    else:
        all_rules_text = ""
        for _, row in df.iterrows():
            all_rules_text += f"【法規】：{row['Source']} / 【規定】：{row['Answer']}\n"
            
        # 整理最近的「歷史對話」給 AI 看 (取最近 6 句，避免塞太多廢話)
        history_context = ""
        recent_messages = st.session_state.messages[-7:-1] # 排除剛剛輸入的最新問題
        for m in recent_messages:
            speaker = "同仁" if m["role"] == "user" else "小助手"
            history_context += f"{speaker}：{m['content']}\n"

        # C. 撰寫終極考卷 (Prompt)
        prompt = f"""
        你是一位專業、親切的臺東縣政府人事處客服人員。
        請「僅根據」以下提供的【法規資料】來回答問題。若法規中找不到答案，請回答：「抱歉，目前的法規資料庫未包含此規定，建議您洽詢人事室。」
        
        【法規資料】：
        {all_rules_text}
        
        【歷史對話紀錄】(請參考上下文，以理解同仁的最新問題)：
        {history_context}
        
        【同仁的最新問題】：
        {user_query}
        """

        # D. 呼叫 AI 並顯示回覆 (含多模型備援)
        with st.chat_message("assistant"):
            message_placeholder = st.empty() # 建立一個空位來放回答或警告
            message_placeholder.markdown("🤖 思考中...")
            
            success = False
            for model_name in MODEL_LIST:
                try:
                    current_model = genai.GenerativeModel(model_name)
                    response = current_model.generate_content(prompt)
                    
                    # 成功取得回答，顯示出來
                    message_placeholder.markdown(response.text)
                    
                    # 將 AI 的回答存入記憶卡
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    success = True
                    break 
                
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "Quota" in error_msg:
                        message_placeholder.warning(f"💡 伺服器忙碌中 ({model_name})，自動切換備援引擎...")
                        time.sleep(1)
                        continue 
                    else:
                        message_placeholder.error(f"連線發生非預期錯誤：{e}")
                        break
            
            if not success:
                message_placeholder.error("❌ 抱歉，所有 AI 引擎額度暫時用罄，請稍後幾分鐘再試。")