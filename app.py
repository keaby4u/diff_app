import streamlit as st
import pandas as pd
from data_diff import read_recipe_excel, compare_recipe_details

st.set_page_config(page_title="配方差异比对工具", layout="wide")
st.title("📊 配方差异比对工具")

st.markdown("""
上传两个 Excel 配方文件（餐厅 + 供应链），系统将对比：
- 是否有相同原料
- 用量是否一致（支持误差容忍）
- 单位是否一致
并展示所有指定附加字段。
""")

col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("📥 上传餐厅配方 Excel", type="xlsx")
with col2:
    file2 = st.file_uploader("📥 上传供应链配方 Excel", type="xlsx")

tolerance = st.slider("⚙️ 用量差异容忍范围（g）", 0.0, 1.0, 0.05, step=0.01)

if file1 and file2:
    try:
        df1 = read_recipe_excel(file1)
        df2 = read_recipe_excel(file2)

        df_diff = compare_recipe_details(df1, df2, tolerance)

        st.success(f"✅ 比对完成，记录总数：{len(df_diff)}")
        st.dataframe(df_diff, use_container_width=True)

        def to_excel(df):
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()

        st.download_button(
            label="📤 下载差异对比结果 Excel",
            data=to_excel(df_diff),
            file_name="配方差异明细.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ 处理过程中出错：{e}")
