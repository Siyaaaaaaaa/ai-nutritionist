import streamlit as st
from google import genai
from PIL import Image
import json
import re
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="Snap & Fit", page_icon="🥗", layout="centered")

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("🥗 Snap & Fit: AI 营养分析师")
st.write("上传你的午餐照片，AI 帮你算热量！")

# --- 2. 安全配置 ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)
except:
    st.error("请先在 Streamlit Secrets 中配置 GOOGLE_API_KEY")
    st.stop()

# --- 3. 核心功能函数 ---
def analyze_image(img):
    """调用 Gemini 2.0 Flash 识别食物并返回 JSON"""
    prompt = """
    你是一位专业的营养师。请分析这张图片。
    任务：
    1. 识别图中所有的食物项。
    2. 估算每项食物的大致热量(kcal)。
    3. 严格输出为 JSON 格式，Key是食物名，Value是热量数字。不要包含任何其他文字或解释。
    示例格式：{"米饭": 200, "红烧肉": 450, "青菜": 50}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img]
        )
        return response.text
    except Exception as e:
        st.error(f"AI 思考出错: {e}")
        return None

# --- 4. 界面交互 ---
uploaded_file = st.file_uploader("📸 请上传食物照片", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="你的午餐", use_container_width=True)
    
    if st.button("🔍 开始分析热量"):
        with st.spinner("AI 正在计算卡路里..."):
            raw_text = analyze_image(image)
            
            if raw_text:
                # --- 数据清洗 (Regex) ---
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                
                if match:
                    json_str = match.group(0)
                    try:
                        data = json.loads(json_str)
                        total_cal = sum(data.values())
                        
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("🔥 总热量", f"{total_cal} kcal")
                        with col2:
                            st.write("📋 **详细清单:**")
                            st.write(data)
                        
                        st.bar_chart(data)
                        
                    except json.JSONDecodeError:
                        st.error("AI 返回的数据格式无法解析，请重试。")
                else:
                    st.error("未找到有效的 JSON 数据。")