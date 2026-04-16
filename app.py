import streamlit as st
import pandas as pd
import io
import altair as alt

st.set_page_config(page_title="鸣潮抽卡分析站 | 纯净本地版", layout="wide")

def merge_records(old_df, new_df):
    """智能合并并去重"""
    if old_df.empty: return new_df
    if new_df.empty: return old_df
    for df in [old_df, new_df]:
        if '时间' not in df.columns: df['时间'] = ""
        df['时间'] = df['时间'].fillna("")
    combined = pd.concat([old_df, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=['角色名', '抽数', '时间'], keep='last').reset_index(drop=True)
    return combined

def calculate_stats(df):
    df_valid = df.dropna(subset=['角色名', '抽数']).copy()
    if df_valid.empty: return pd.DataFrame(), {}
        
    df_valid['抽数'] = pd.to_numeric(df_valid['抽数'], errors='coerce').fillna(0).astype(int)
    
    analysis_data = []
    wasted_pulls = 0
    total_up_cost, total_up_count, win_count, win_opportunity = 0, 0, 0, 0
    
    for _, row in df_valid.iterrows():
        char_name = str(row.get('角色名', '')).strip()
        if not char_name or char_name == 'nan': continue
        
        is_up_raw = row.get('是否UP?', row.get('是UP?', '否'))
        is_up = str(is_up_raw).strip() == '是'
        pulls = int(row['抽数'])
        time_str = row.get('时间', '')
        
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
            "时间": time_str, "角色名": char_name, "是UP?": "是" if is_up else "否", 
            "抽数": pulls, "保底类型": pity_type, "实际花费": current_cost if is_up else None
        })
    
    stats = {
        "总出金": len(df_valid), "UP数": total_up_count, 
        "不歪率": f"{(win_count/win_opportunity*100):.1f}%" if win_opportunity > 0 else "0%",
        "平均出金": round(df_valid['抽数'].mean(), 1) if not df_valid.empty else 0,
        "UP平均花费": round(total_up_cost/total_up_count, 1) if total_up_count > 0 else 0
    }
    return pd.DataFrame(analysis_data), stats

# --- 状态初始化 ---
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame(columns=['时间', '角色名', '是UP?', '抽数'])

# --- 侧边栏 ---
with st.sidebar:
    st.header("📁 第一步：数据导入")
    st.caption("支持导入之前导出的记录，会自动与当前表格合并。")
    uploaded_file = st.file_uploader("导入本地备份 (.xlsx/.csv)", type=["xlsx", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): imported_df = pd.read_csv(uploaded_file)
            else: imported_df = pd.read_excel(uploaded_file)
            if '是否UP?' in imported_df.columns: imported_df = imported_df.rename(columns={'是否UP?': '是UP?'})
            st.session_state.raw_data = merge_records(st.session_state.raw_data, imported_df)
            st.success("文件导入合并成功！")
        except Exception as e:
            st.error(f"文件读取失败: {e}")

    st.markdown("---")
    st.header("💾 第二步：安全导出")
    st.caption("添加完新角色后，随时导出一份最新 Excel 保存到电脑/手机里。")
    if not st.session_state.raw_data.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.raw_data.to_excel(writer, index=False, sheet_name='抽卡记录')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 导出为 Excel (.xlsx)",
            data=excel_data,
            file_name="鸣潮抽卡永久备份.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    
    if st.button("🗑️ 清空面板"):
        st.session_state.raw_data = pd.DataFrame(columns=['时间', '角色名', '是UP?', '抽数'])
        st.rerun()

# --- 主界面 ---
st.title("🌊 鸣潮抽卡数据分析站 (纯净本地版)")
st.info("💡 **使用说明**：你可以在下方表格直接手动双击输入数据，也可以在左侧上传 Excel 导入。一切都在本地计算，绝对安全。")

edited_df = st.data_editor(
    st.session_state.raw_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "时间": st.column_config.TextColumn("出金时间 (可选)"),
        "角色名": st.column_config.TextColumn("角色名", required=True),
        "是UP?": st.column_config.SelectboxColumn("是否UP?", options=["是", "否"], required=True),
        "抽数": st.column_config.NumberColumn("使用抽数", min_value=1, max_value=80, required=True, format="%d")
    },
    key="data_editor",
    height=250
)
st.session_state.raw_data = edited_df

st.divider()

if not edited_df.empty and not edited_df['角色名'].isna().all():
    res_df, m = calculate_stats(edited_df)
    if m:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总出金 (五星总数)", m["总出金"])
        c2.metric("小保底不歪率", m["不歪率"])
        c3.metric("平均出金抽数", m["平均出金"])
        
        cost = m["UP平均花费"]
        delta_color = "normal"
        if cost <= 65: delta_color = "off"
        elif cost >= 74: delta_color = "inverse"
        c4.metric("获得UP平均花费", f"{cost} 抽", delta_color=delta_color)
        
        st.write("---")
        
        # ================= 可视化图表区 =================
        st.subheader("📊 UP角色花费欧非图鉴")
        
        up_df = res_df[res_df['是UP?'] == '是'].copy()
        
        if not up_df.empty:
            up_df['获取序号'] = range(1, len(up_df) + 1)
            up_df['展示名'] = up_df['获取序号'].astype(str) + ". " + up_df['角色名']
            
            def get_color(cost):
                if pd.isna(cost): return '#808080'
                if cost <= 65: return '#28a745'
                elif cost <= 73: return '#ffc107'
                else: return '#dc3545'
                
            up_df['柱子颜色'] = up_df['实际花费'].apply(get_color)
            
            chart = alt.Chart(up_df).mark_bar(cornerRadiusEnd=4, height=20).encode(
                x=alt.X('实际花费:Q', title='花费抽数 (含垫刀)', scale=alt.Scale(domain=[0, 160])),
                y=alt.Y('展示名:N', title='', sort=alt.EncodingSortField(field="获取序号", order="ascending")),
                color=alt.Color('柱子颜色:N', scale=None),
                tooltip=[
                    alt.Tooltip('角色名', title='角色'),
                    alt.Tooltip('实际花费', title='实际花费抽数'),
                    alt.Tooltip('保底类型', title='抽取情况')
                ]
            ).properties(
                height=max(200, len(up_df) * 45)
            ).configure_axis(
                labelFontSize=13,
                titleFontSize=14
            )
            
            st.altair_chart(chart, use_container_width=True)
            st.caption("🟢 **欧皇**：≤ 65 抽 | 🟡 **平庸**：66 - 73 抽 | 🔴 **非酋**：≥ 74 抽 （*注：大保底花费可能超过80抽*）")
        else:
            st.info("尚未获取UP角色，无法生成可视化图鉴。")
        # ======================================================

        st.write("#### 📜 详细分析日志")
        st.dataframe(res_df, use_container_width=True)
