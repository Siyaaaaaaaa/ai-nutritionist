import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
from PIL import Image
import json
import re
import pandas as pd
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="Snap & Fit Pro", page_icon="🥗", layout="centered")

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🥗 Snap & Fit: AI 营养分析师 (云端版)")

# --- 2. 安全配置 (Gemini) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

# --- 3. 建立 Google Sheets 连接 ---
# 这一步会自动去 Secrets 里找 [connections.gsheets] 的配置
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库连接失败: {e}")
    st.stop()

# --- 4. 核心功能函数 ---
def analyze_image(img):
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = """
    你是一位专业的营养师。请分析这张图片。
    任务：严格输出为 JSON 格式，Key是食物名，Value是热量数字(kcal)。
    示例：{"米饭": 200, "红烧肉": 450}
    """
    try:
        response = model.generate_content([prompt, img])
        return response.text
    except:
        return None

# --- 5. 界面交互 ---
uploaded_file = st.file_uploader("📸 上传午餐照片", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, use_container_width=True)
    
    # 使用 Session State 防止点击保存按钮时页面刷新导致数据丢失
    if 'analyzed_data' not in st.session_state:
        st.session_state.analyzed_data = None

    if st.button("🔍 开始分析"):
        with st.spinner("AI 正在计算..."):
            raw_text = analyze_image(image)
            if raw_text:
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    st.session_state.analyzed_data = json.loads(match.group(0))
    
    # 如果有分析结果，显示结果和保存按钮
    if st.session_state.analyzed_data:
        data = st.session_state.analyzed_data
        total_cal = sum(data.values())
        
        col1, col2 = st.columns(2)
        col1.metric("🔥 总热量", f"{total_cal} kcal")
        col2.write(data)
        
        # --- 保存到云端 ---
        if st.button("💾 记录到 Google Sheets"):
            try:
                # 1. 读取现有数据
                existing_data = conn.read(worksheet="Sheet1", usecols=list(range(3)), ttl=0)
                
                # 2. 准备新的一行数据
                new_row = pd.DataFrame([{
                    "日期": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "食物清单": json.dumps(data, ensure_ascii=False),
                    "总热量": total_cal
                }])
                
                # 3. 合并并更新
                updated_data = pd.concat([existing_data, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_data)
                
                st.success("✅ 已成功保存到云端数据库！")
                st.balloons()
            except Exception as e:
                st.error(f"保存失败: {e}")