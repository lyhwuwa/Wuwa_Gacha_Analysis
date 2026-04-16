import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="鸣潮抽卡分析站", layout="wide")

def calculate_stats(df):
    df['抽数'] = pd.to_numeric(df['抽数'], errors='coerce').fillna(0)
    analysis_data = []
    wasted_pulls = 0
    total_up_cost = 0
    total_up_count = 0
    win_count = 0
    win_opportunity = 0
    
    for _, row in df.iterrows():
        char_name = str(row['角色名'])
        is_up = str(row['是否UP?']).strip() == '是' or str(row['是UP?']).strip() == '是'
        pulls = int(row['抽数'])
        pity_type, current_cost = "", 0

        if is_up:
            total_up_count += 1
            if wasted_pulls > 0:
                pity_type, current_cost = "强娶 (大保底)", pulls + wasted_pulls
                wasted_pulls = 0
            else:
                pity_type, current_cost = "运气 (小保底)", pulls
                win_count += 1
                win_opportunity += 1
            total_up_cost += current_cost
        else:
            pity_type, wasted_pulls = "歪了", wasted_pulls + pulls
            win_opportunity += 1
            
        analysis_data.append({"角色名": char_name, "是UP?": "是" if is_up else "否", "抽数": pulls, "保底类型": pity_type, "实际花费": current_cost if is_up else None})
    
    stats = {
        "总出金": len(df), "UP数": total_up_count, 
        "不歪率": f"{(win_count/win_opportunity*100):.1f}%" if win_opportunity > 0 else "0%",
        "平均出金": round(df['抽数'].mean(), 1),
        "UP平均花费": round(total_up_cost/total_up_count, 1) if total_up_count > 0 else 0
    }
    return pd.DataFrame(analysis_data), stats

st.title("🌊 鸣潮抽卡数据分析站")

# 文件上传功能
uploaded_file = st.file_uploader("点击上传你的抽卡记录 CSV 文件", type="csv")

if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['角色名', '是UP?', '抽数'])

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8-sig")
    st.session_state.data = pd.read_csv(io.StringIO(content))
    st.success("文件导入成功！")

if not st.session_state.data.empty:
    res_df, m = calculate_stats(st.session_state.data)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总出金", m["总出金"])
    c2.metric("不歪率", m["不歪率"])
    c3.metric("平均出金", m["平均出金"])
    c4.metric("UP平均成本", m["UP平均花费"])
    st.dataframe(res_df, use_container_width=True)
