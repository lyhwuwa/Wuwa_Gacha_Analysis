import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="鸣潮抽卡分析站", layout="wide")

def calculate_stats(df):
    # 清理掉还没填完的空行
    df_valid = df.dropna(subset=['角色名', '抽数']).copy()
    if df_valid.empty:
        return pd.DataFrame(), {}
        
    df_valid['抽数'] = pd.to_numeric(df_valid['抽数'], errors='coerce').fillna(0).astype(int)
    
    analysis_data = []
    wasted_pulls = 0
    total_up_cost = 0
    total_up_count = 0
    win_count = 0
    win_opportunity = 0
    
    for _, row in df_valid.iterrows():
        char_name = str(row.get('角色名', '')).strip()
        if not char_name or char_name == 'nan': continue
        
        # 兼容列名
        is_up_raw = row.get('是否UP?', row.get('是UP?', '否'))
        is_up = str(is_up_raw).strip() == '是'
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
            
        analysis_data.append({
            "角色名": char_name, 
            "是UP?": "是" if is_up else "否", 
            "抽数": pulls, 
            "保底类型": pity_type, 
            "实际花费": current_cost if is_up else None
        })
    
    stats = {
        "总出金": len(df_valid), "UP数": total_up_count, 
        "不歪率": f"{(win_count/win_opportunity*100):.1f}%" if win_opportunity > 0 else "0%",
        "平均出金": round(df_valid['抽数'].mean(), 1) if not df_valid.empty else 0,
        "UP平均花费": round(total_up_cost/total_up_count, 1) if total_up_count > 0 else 0
    }
    return pd.DataFrame(analysis_data), stats

# 初始化数据状态
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame(columns=['角色名', '是UP?', '抽数'])

# --- 侧边栏 ---
with st.sidebar:
    st.header("📁 批量导入")
    uploaded_file = st.file_uploader("上传 CSV 记录 (可选)", type="csv")
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8-sig")
        imported_df = pd.read_csv(io.StringIO(content))
        if '是否UP?' in imported_df.columns:
            imported_df = imported_df.rename(columns={'是否UP?': '是UP?'})
        cols_to_keep = [c for c in ['角色名', '是UP?', '抽数'] if c in imported_df.columns]
        st.session_state.raw_data = imported_df[cols_to_keep]
        st.success("导入成功！右侧表格已更新。")
        
    st.markdown("---")
    if st.button("🗑️ 清空所有数据"):
        st.session_state.raw_data = pd.DataFrame(columns=['角色名', '是UP?', '抽数'])
        st.rerun()

# --- 主界面 ---
st.title("🌊 鸣潮抽卡数据分析站")

st.write("### 📝 数据录入区")
st.info("💡 **操作提示**：除了上传文件，你还可以直接在下面表格的**空白行**输入数据。支持批量复制粘贴，修改后自动计算。")

# 强大的可编辑数据表
edited_df = st.data_editor(
    st.session_state.raw_data,
    num_rows="dynamic", # 允许动态增加/删除行
    use_container_width=True,
    column_config={
        "角色名": st.column_config.TextColumn("角色名 (必填)", required=True),
        "是UP?": st.column_config.SelectboxColumn("是否为UP角色?", options=["是", "否"], required=True),
        "抽数": st.column_config.NumberColumn("使用抽数", min_value=1, max_value=80, required=True, format="%d")
    },
    key="data_editor"
)

# 将编辑后的数据保存下来
st.session_state.raw_data = edited_df

st.divider()

# --- 结果展示 ---
st.write("### 📊 欧非分析结果")
if not edited_df.empty and not edited_df['角色名'].isna().all():
    res_df, m = calculate_stats(edited_df)
    if m:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总出金 (五星总数)", m["总出金"])
        c2.metric("小保底不歪率", m["不歪率"])
        c3.metric("平均出金抽数", m["平均出金"])
        
        # 加上一点欧非颜色提示
        cost = m["UP平均花费"]
        delta_color = "normal"
        if cost < 60: delta_color = "off"
        elif cost > 100: delta_color = "inverse"
        c4.metric("获得UP平均花费 (含歪)", f"{cost} 抽", delta_color=delta_color)
        
        st.write("#### 📜 抽卡明细追溯")
        st.dataframe(res_df, use_container_width=True)
else:
    st.warning("表格暂时没有有效数据，请在上方录入你的第一金！")
