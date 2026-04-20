import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# ==========================================
# 1. 初始化設定與 API 鑰匙
# ==========================================
st.set_page_config(page_title="臺東縣府差勤小助手 (多機關備援版)", page_icon="🤖")

# 讀取 API Key
try:
    GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("⚠️ 無法讀取 API Key！請確認已在 Streamlit Secrets 中設定。")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# 【自訂模型備援名單】：按優先順序嘗試
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
        df = pd.read_excel("rules.xlsx")
        return df
    except Exception:
        return pd.DataFrame(columns=["Source", "Keywords", "Title", "Answer"])

df = load_data()

# ==========================================
# 3. 網頁介面
# ==========================================
st.title("🤖 臺東縣府差勤小助手")
st.caption("目前系統支援多重 AI 模型自動備援，確保連線穩定")
st.divider()

user_query = st.text_input("請輸入您的問題：", placeholder="例如：請問喪假規定...")

# ==========================================
# 4. 核心邏輯：自動切換模型機制
# ==========================================
if user_query:
    if df.empty:
        st.warning("請先準備 rules.xlsx 檔案。")
    else:
        with st.spinner('🤖 正在尋找最合適的 AI 引擎為您回答...'):
            
            # 準備 Prompt (內容與之前相同)
            all_rules_text = ""
            for _, row in df.iterrows():
                all_rules_text += f"【法規】：{row['Source']} / 【規定】：{row['Answer']}\n"

            prompt = f"""
            你是一位專業的臺東縣政府人事處人員。請僅根據以下法規回答問題。
            若無法回答，請說：「抱歉，目前的法規資料庫未包含此規定，建議您洽詢人事室。」
            
            【法規資料】：
            {all_rules_text}
            【問題】：
            {user_query}
            """

            success = False # 標記是否成功得到答案
            
            # --- 開始輪詢模型名單 ---
            for model_name in MODEL_LIST:
                try:
                    # 動態建立當前嘗試的模型
                    current_model = genai.GenerativeModel(model_name)
                    response = current_model.generate_content(prompt)
                    
                    # 如果成功回答，顯示結果並跳出迴圈
                    st.success(f"✨ AI 智能回覆 (由 {model_name} 提供)：")
                    st.markdown(response.text)
                    success = True
                    break 
                
                except Exception as e:
                    error_msg = str(e)
                    # 如果是額度問題 (429)，則嘗試下一個模型
                    if "429" in error_msg or "Quota" in error_msg:
                        st.warning(f"💡 模型 {model_name} 額度已滿，正在自動切換至下一個備援模型...")
                        time.sleep(1) # 短暫停頓避免請求過快
                        continue # 進入下一個迴圈，嘗試名單中的下一個模型
                    else:
                        st.error(f"連線發生非預期錯誤 ({model_name})：{e}")
                        break
            
            if not success:
                st.error("❌ 抱歉，名單中所有 AI 模型的免費額度皆已用罄，請稍後幾分鐘再試。")

# ==========================================
# 5. 側邊欄狀態
# ==========================================
with st.sidebar:
    st.header("📊 系統資訊")
    st.write("已掛載備援模型數量：", len(MODEL_LIST))
    st.info("優先順序：\n" + "\n".join([f"{i+1}. {m}" for i, m in enumerate(MODEL_LIST)]))
    st.write("已收錄法規數：", len(df))