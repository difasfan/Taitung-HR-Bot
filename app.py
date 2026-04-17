import streamlit as st
import pandas as pd
import google.generativeai as genai

# ==========================================
# 1. 初始化設定與 API 鑰匙
# ==========================================
st.set_page_config(page_title="臺東縣府差勤小助手 (Gemini AI版)", page_icon="🤖")

# ⚠️ 請務必將下方引號內的文字換成你申請到的 Google Gemini API Key
GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# 選擇 Gemini 模型 (使用 latest 確保抓到最新支援的版本，避免 404 錯誤)
model = genai.GenerativeModel('gemini-3-flash-preview')

# ==========================================
# 2. 讀取法規資料庫 (真實讀取 Excel 版)
# ==========================================
@st.cache_data
def load_data():
    try:
        # 讀取你剛剛用程式生成的 rules.xlsx 檔案
        df = pd.read_excel("rules.xlsx")
        return df
    except FileNotFoundError:
        # 如果找不到檔案，在網頁上顯示紅色錯誤提示
        st.error("⚠️ 找不到 `rules.xlsx` 檔案！請確認 Excel 檔案與 app.py 放在同一個資料夾中。")
        # 回傳一個空的表格，避免程式整個當機
        return pd.DataFrame(columns=["Source", "Keywords", "Title", "Answer"])

df = load_data()

# ==========================================
# 3. 網頁介面設計
# ==========================================
st.title("🤖 臺東縣府差勤小助手 (Gemini AI版)")
st.info("💡 您可以像聊天一樣問我問題，例如：\n* 「我最近壓力很大想請假，有什麼假可以請？」\n* 「我是新來的約聘人員，做滿一年後會有幾天年假？」")
st.divider()

user_query = st.text_input("請描述您的問題：", placeholder="請輸入您的問題...")

# ==========================================
# 4. AI 檢索與回覆邏輯 (RAG 核心)
# ==========================================
if user_query:
    if df.empty:
        st.warning("目前法規資料庫為空，請先確認 rules.xlsx 檔案已準備好喔！")
    else:
        with st.spinner('🤖 正在為您翻閱法規並整理答案中，請稍候...'):
            
            # 步驟 A：把資料庫裡的法規全部整理成一段純文字，當作「參考書」給 AI 看
            all_rules_text = ""
            for index, row in df.iterrows():
                all_rules_text += f"【法規來源】：{row['Source']} / 【規定內容】：{row['Answer']}\n"

            # 步驟 B：建立給 Gemini 的提示詞 (Prompt) -> 設定角色與回答規則
            prompt = f"""
            你是一位專業、親切的臺東縣政府人事處客服人員。
            請「僅根據」以下提供的【法規資料】來回答同仁的【問題】。
            回答時請保持語氣友善，並盡量列點說明以利閱讀。
            如果提供的法規資料中無法回答該問題，請誠實回答：「抱歉，目前的法規資料庫未包含此規定，建議您直接洽詢人事室承辦人員。」，絕對不可以自己編造法規或加入外部資訊。

            【法規資料】：
            {all_rules_text}

            【同仁的問題】：
            {user_query}
            """

            # 步驟 C：呼叫 Gemini 產生回答
            try:
                response = model.generate_content(prompt)
                
                # 步驟 D：將結果顯示給使用者
                st.success("✨ AI 智能回覆：")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"連線發生錯誤，請確認您的電腦有網路，且 API Key 設定正確。錯誤詳情：{e}")

# ==========================================
# 5. 側邊欄：顯示系統狀態
# ==========================================
with st.sidebar:
    st.header("📚 系統狀態")
    st.success("🟢 Gemini AI 引擎已準備就緒")
    st.write("目前已載入法規數量：", len(df), "條")
    
    # 如果有讀取到資料，將不重複的法規名稱列出來
    if not df.empty:
        with st.expander("查看已收錄法規清單"):
            sources = df["Source"].unique()
            for s in sources:
                st.caption(f"- {s}")
