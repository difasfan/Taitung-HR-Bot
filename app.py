import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# ==========================================
# 1. 初始化設定與 API 鑰匙
# ==========================================
st.set_page_config(page_title="臺東縣府差勤小助手 (智能對話版)", page_icon="💬")

try:
    GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("⚠️ 無法讀取 API Key！請確認已在 Streamlit Secrets 中設定。")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# 【自訂模型備援名單】確保系統穩定不當機
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
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "您好！我是臺東縣府差勤小助手👋 \n請隨時問我差勤相關問題，我會根據最新法規為您解答！"
    })

# ==========================================
# 4. 網頁介面 (側邊欄與標題)
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統設定與資訊")
    st.write(f"📚 已收錄法規：{len(df)} 條")
    
    if st.button("🗑️ 清除對話紀錄 (開啟新話題)"):
        st.session_state.messages = []
        st.rerun()

st.title("💬 臺東縣府差勤小助手")
st.caption("支援連續對話記憶與嚴謹計算邏輯")
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
if user_query := st.chat_input("請輸入您的問題，例如：請問喪假規定..."):
    
    # 顯示同仁的新問題並存入記憶卡
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    if df.empty:
        st.error("請先準備 rules.xlsx 檔案。")
    else:
        # 準備法規資料
        all_rules_text = ""
        for _, row in df.iterrows():
            all_rules_text += f"【法規】：{row['Source']} / 【規定】：{row['Answer']}\n"
            
        # 整理最近的歷史對話 (取最近 6 句)
        history_context = ""
        recent_messages = st.session_state.messages[-7:-1] 
        for m in recent_messages:
            speaker = "同仁" if m["role"] == "user" else "小助手"
            history_context += f"{speaker}：{m['content']}\n"

        # ==========================================
        # 👑 核心防呆考卷 (加入反問機制)
        # ==========================================
        prompt = f"""
        你是一位專業、親切的臺東縣政府人事處客服人員。
        請遵守以下兩大原則來回答問題：
        
        1. 【法規依據】：請「僅根據」以下提供的【法規資料】來回答問題。若法規中找不到答案，請回答：「抱歉，目前的法規資料庫未包含此規定，建議您洽詢人事室。」絕對不可自己編造法規。
        
        2. 【精準計算與反問機制】（非常重要）：如果同仁的問題涉及到天數或金額的「比例計算」（例如：按比例計算隔年休假天數、計算年資等），請你務必先檢查【歷史對話紀錄】與【同仁的最新問題】中，是否已經提供了計算必備的變數（例如：「到職月份日期」或「確切年資」）。
        👉 如果「缺少」這些必備條件，請你「務必先禮貌地反問同仁」以取得確切的月份或日期。
        👉 絕對「不可以」自己假設一個數字（例如假設對方做滿整年、預設12個月、或假設某個日期）來計算。
        
        【法規資料】：
        {all_rules_text}
        
        【歷史對話紀錄】(請參考上下文，以理解同仁的最新問題)：
        {history_context}
        
        【同仁的最新問題】：
        {user_query}
        """

        # 呼叫 AI 並顯示回覆 (多模型備援)
        with st.chat_message("assistant"):
            message_placeholder = st.empty() 
            message_placeholder.markdown("🤖 思考中...")
            
            success = False
            for model_name in MODEL_LIST:
                try:
                    current_model = genai.GenerativeModel(model_name)
                    response = current_model.generate_content(prompt)
                    
                    message_placeholder.markdown(response.text)
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