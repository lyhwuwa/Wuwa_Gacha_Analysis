import streamlit as st
import pandas as pd
import io
import altair as alt

st.set_page_config(
    page_title="鸣潮 · 唤取终端",
    page_icon="〰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 鸣潮风格视觉主题（纯 CSS，不依赖外部素材）---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

    :root {
        --ww-bg: #080b10; --ww-panel: rgba(17, 23, 31, .88);
        --ww-line: rgba(112, 226, 231, .20); --ww-cyan: #70e2e7;
        --ww-cyan-soft: #bdfcff; --ww-gold: #e7c675;
        --ww-text: #edf5f6; --ww-muted: #8e9ba7;
    }
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        color: var(--ww-text);
        background:
            radial-gradient(circle at 78% 8%, rgba(30, 160, 170, .13), transparent 28rem),
            radial-gradient(circle at 10% 78%, rgba(231, 198, 117, .055), transparent 24rem),
            linear-gradient(135deg, rgba(112, 226, 231, .025) 25%, transparent 25%) 0 0 / 36px 36px,
            linear-gradient(315deg, rgba(112, 226, 231, .018) 25%, transparent 25%) 0 0 / 36px 36px,
            var(--ww-bg);
    }
    [data-testid="stHeader"] { background: rgba(8, 11, 16, .55); }
    [data-testid="stToolbar"] { right: 1.5rem; }
    .block-container { max-width: 1320px; padding-top: 2.2rem; padding-bottom: 4rem; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #10161e 0%, #0b0f15 100%);
        border-right: 1px solid var(--ww-line);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
    [data-testid="stSidebar"] h3 {
        color: #dce8eb !important;
        font-size: 1.32rem;
        font-weight: 700;
        letter-spacing: .035em;
        text-shadow: 0 0 16px rgba(112, 226, 231, .10);
    }
    [data-testid="stSidebar"] h2 {
        color: var(--ww-cyan-soft) !important;
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: .10em;
        text-shadow: 0 0 12px rgba(112, 226, 231, .12);
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #94a6ae !important;
        opacity: 1;
        font-size: .90rem;
        font-weight: 500;
        line-height: 1.75;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] span {
        color: #94a6ae !important;
        opacity: 1;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label p {
        color: #b9c6cc !important;
        font-size: .94rem;
        font-weight: 600;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span {
        color: #dce5e8 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small {
        color: #8799a2 !important;
    }

    .ww-hero {
        position: relative; overflow: hidden; min-height: 190px;
        padding: 34px 38px; margin: 0 0 22px;
        border: 1px solid rgba(112, 226, 231, .28); border-left: 3px solid var(--ww-cyan);
        border-radius: 4px 20px 4px 20px;
        background: linear-gradient(115deg, rgba(18, 28, 37, .96), rgba(8, 13, 18, .82));
        box-shadow: 0 16px 55px rgba(0, 0, 0, .35), inset 0 0 45px rgba(112, 226, 231, .035);
    }
    .ww-hero::before {
        content: "〰 ︿ 〰︿〰 ︿ 〰︿〰"; position: absolute; right: -15px; top: 9px;
        color: rgba(112, 226, 231, .10); font-size: 80px; font-weight: 300;
        letter-spacing: -18px; transform: rotate(-5deg); white-space: nowrap;
    }
    .ww-hero::after {
        content: "KURO WAVE / RESONANCE ARCHIVE"; position: absolute; right: 28px; bottom: 18px;
        color: rgba(189, 252, 255, .32); font-size: 10px; letter-spacing: .24em;
    }
    .ww-eyebrow { color: var(--ww-cyan); font-size: 11px; font-weight: 700; letter-spacing: .28em; text-transform: uppercase; }
    .ww-title {
        margin: 8px 0 6px; color: #f7ffff; font-size: clamp(34px, 5vw, 58px);
        font-weight: 600; line-height: 1; letter-spacing: .08em;
        text-shadow: 0 0 26px rgba(112, 226, 231, .18);
    }
    .ww-title span { color: var(--ww-cyan); font-weight: 300; }
    .ww-subtitle { color: var(--ww-muted); font-size: 13px; letter-spacing: .06em; }
    .ww-status {
        display: inline-flex; align-items: center; gap: 8px; margin-top: 20px; padding: 6px 12px;
        color: #c8f7ea; font-size: 11px; letter-spacing: .08em;
        border: 1px solid rgba(103, 229, 190, .25); border-radius: 999px;
        background: rgba(57, 179, 141, .08);
    }
    .ww-status::before {
        content: ""; width: 6px; height: 6px; border-radius: 50%;
        background: #67e5be; box-shadow: 0 0 10px #67e5be;
    }
    .ww-section {
        display: flex; align-items: center; gap: 12px; margin: 28px 0 14px;
        color: var(--ww-text); font-size: 15px; font-weight: 600; letter-spacing: .1em;
    }
    .ww-section::before {
        content: ""; width: 24px; height: 2px;
        background: linear-gradient(90deg, var(--ww-cyan), transparent);
        box-shadow: 0 0 8px rgba(112, 226, 231, .5);
    }
    .ww-section small { color: var(--ww-muted); font-size: 10px; font-weight: 400; letter-spacing: .16em; }
    [data-testid="stAlert"] {
        color: #c8d6dc; border: 1px solid rgba(112, 226, 231, .16);
        border-radius: 3px 12px 3px 12px; background: rgba(16, 28, 36, .72);
    }
    [data-testid="stMetric"] {
        position: relative; min-height: 118px; padding: 18px 20px; overflow: hidden;
        border: 1px solid rgba(112, 226, 231, .16); border-radius: 3px 14px 3px 14px;
        background: linear-gradient(145deg, rgba(25, 33, 43, .92), rgba(13, 18, 25, .94));
        box-shadow: inset 0 1px rgba(255,255,255,.025), 0 10px 30px rgba(0,0,0,.16);
    }
    [data-testid="stMetric"]::after {
        content: ""; position: absolute; right: -22px; bottom: -22px; width: 70px; height: 70px;
        border: 1px solid rgba(112, 226, 231, .14); border-radius: 50%;
        box-shadow: 0 0 0 10px rgba(112, 226, 231, .025);
    }
    [data-testid="stMetricLabel"] { color: var(--ww-muted); font-size: 12px; letter-spacing: .05em; }
    [data-testid="stMetricValue"] { color: var(--ww-cyan-soft); font-size: 30px; font-weight: 500; }
    [data-testid="stDataFrame"] {
        overflow: hidden; border: 1px solid rgba(112, 226, 231, .18);
        border-radius: 3px 14px 3px 14px; box-shadow: 0 12px 34px rgba(0, 0, 0, .2);
    }
    .stButton > button, .stDownloadButton > button {
        min-height: 42px; color: #dffbfc; font-weight: 600; letter-spacing: .05em;
        border: 1px solid rgba(112, 226, 231, .32); border-radius: 2px 10px 2px 10px;
        background: linear-gradient(110deg, rgba(38, 93, 99, .48), rgba(22, 32, 41, .92));
        transition: all .2s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        color: white; border-color: var(--ww-cyan); box-shadow: 0 0 20px rgba(112, 226, 231, .14);
        transform: translateY(-1px);
    }
    [data-testid="stFileUploaderDropzone"] {
        border: 1px dashed rgba(112, 226, 231, .28); border-radius: 3px 12px 3px 12px;
        background: rgba(112, 226, 231, .035);
    }
    hr { border-color: rgba(112, 226, 231, .12) !important; }
    .ww-legend { display: flex; flex-wrap: wrap; gap: 10px; margin: 9px 0 6px; }
    .ww-chip {
        padding: 5px 10px; color: #bec9ce; font-size: 11px;
        border: 1px solid rgba(255,255,255,.08); border-radius: 999px; background: rgba(255,255,255,.025);
    }
    .ww-chip b { margin-right: 5px; }
    .ww-green b { color: #67e5be; } .ww-gold b { color: var(--ww-gold); } .ww-red b { color: #ff7882; }
    @media (max-width: 760px) {
        .block-container { padding: 1.2rem .9rem 3rem; }
        .ww-hero { min-height: 170px; padding: 28px 24px; }
        .ww-hero::after { display: none; } .ww-title { font-size: 34px; }
    }
</style>
""", unsafe_allow_html=True)

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
    st.markdown("### 〰 共鸣数据终端")
    st.caption("RESONANCE DATA CONSOLE / LOCAL")
    st.divider()
    st.header("01 · 记录接入")
    st.caption("导入旧记录后，系统会自动合并并去除重复项。")
    uploaded_file = st.file_uploader("接入本地记录 (.xlsx / .csv)", type=["xlsx", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): imported_df = pd.read_csv(uploaded_file)
            else: imported_df = pd.read_excel(uploaded_file)
            if '是否UP?' in imported_df.columns: imported_df = imported_df.rename(columns={'是否UP?': '是UP?'})
            st.session_state.raw_data = merge_records(st.session_state.raw_data, imported_df)
            st.success("记录接入成功 · 数据已完成同步")
        except Exception as e:
            st.error(f"文件读取失败: {e}")

    st.markdown("---")
    st.header("02 · 记录封存")
    st.caption("将当前唤取记录导出为 Excel，方便长期保存。")
    if not st.session_state.raw_data.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.raw_data.to_excel(writer, index=False, sheet_name='抽卡记录')
        excel_data = output.getvalue()
        
        st.download_button(
            label="↓ 封存为 Excel",
            data=excel_data,
            file_name="鸣潮抽卡永久备份.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    
    if st.button("清空当前终端", width="stretch"):
        st.session_state.raw_data = pd.DataFrame(columns=['时间', '角色名', '是UP?', '抽数'])
        st.rerun()

# --- 主界面 ---
st.markdown("""
<div class="ww-hero">
    <div class="ww-eyebrow">Wuthering Waves · Convene Archive</div>
    <div class="ww-title">唤取<span>终端</span></div>
    <div class="ww-subtitle">共鸣者唤取记录 / 概率轨迹 / 欧非分析</div>
    <div class="ww-status">本地解析核心 ONLINE</div>
</div>
""", unsafe_allow_html=True)

st.info("**终端指引**　直接在下方新增唤取记录，或从左侧接入已有 Excel / CSV。所有统计均在当前会话中完成。")
st.markdown('<div class="ww-section">唤取记录录入 <small>CONVENE LOG INPUT</small></div>', unsafe_allow_html=True)

edited_df = st.data_editor(
    st.session_state.raw_data,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "时间": st.column_config.TextColumn("记录时间（可选）"),
        "角色名": st.column_config.TextColumn("共鸣者", required=True),
        "是UP?": st.column_config.SelectboxColumn("限定共鸣者？", options=["是", "否"], required=True),
        "抽数": st.column_config.NumberColumn("唤取次数", min_value=1, max_value=80, required=True, format="%d")
    },
    key="data_editor",
    height=250
)
st.session_state.raw_data = edited_df

st.divider()

if not edited_df.empty and not edited_df['角色名'].isna().all():
    res_df, m = calculate_stats(edited_df)
    if m:
        st.markdown('<div class="ww-section">数据概览 <small>RESONANCE OVERVIEW</small></div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("五星共鸣者", m["总出金"])
        c2.metric("小保底不歪率", m["不歪率"])
        c3.metric("平均出金", f'{m["平均出金"]} 抽')
        
        cost = m["UP平均花费"]
        delta_color = "normal"
        if cost <= 65: delta_color = "off"
        elif cost >= 74: delta_color = "inverse"
        c4.metric("限定平均成本", f"{cost} 抽", delta_color=delta_color)
        
        st.divider()
        
        # ================= 可视化图表区 =================
        st.markdown('<div class="ww-section">限定共鸣者成本轨迹 <small>CONVENE COST TRACE</small></div>', unsafe_allow_html=True)
        
        up_df = res_df[res_df['是UP?'] == '是'].copy()
        
        if not up_df.empty:
            up_df['获取序号'] = range(1, len(up_df) + 1)
            up_df['展示名'] = up_df['获取序号'].astype(str) + ". " + up_df['角色名']
            
            def get_color(cost):
                if pd.isna(cost): return '#66727c'
                if cost <= 65: return '#67e5be'
                elif cost <= 73: return '#e7c675'
                else: return '#ff7882'
                
            up_df['柱子颜色'] = up_df['实际花费'].apply(get_color)
            
            base = alt.Chart(up_df).encode(
                x=alt.X(
                    '实际花费:Q', title='实际唤取次数（含大保底前的歪）',
                    scale=alt.Scale(domain=[0, 160]),
                    axis=alt.Axis(grid=True, gridColor='#22313a', tickColor='#40525c', domain=False)
                ),
                y=alt.Y(
                    '展示名:N', title='',
                    sort=alt.EncodingSortField(field="获取序号", order="ascending"),
                    axis=alt.Axis(domain=False, ticks=False, labelPadding=10)
                )
            )

            bars = base.mark_bar(cornerRadiusEnd=3, height=18).encode(
                color=alt.Color('柱子颜色:N', scale=None),
                tooltip=[
                    alt.Tooltip('角色名', title='共鸣者'),
                    alt.Tooltip('实际花费', title='实际成本'),
                    alt.Tooltip('保底类型', title='唤取结果')
                ]
            )

            labels = base.mark_text(
                align='left', baseline='middle', dx=7,
                color='#dcecef', fontSize=12, fontWeight=600
            ).encode(text=alt.Text('实际花费:Q', format='.0f'))

            chart = (bars + labels).properties(
                height=max(200, len(up_df) * 45)
            ).configure_axis(
                labelColor='#b8c5cb', titleColor='#72838c',
                labelFontSize=12, titleFontSize=12
            ).configure_view(
                stroke=None
            ).configure(
                background='transparent'
            )
            
            st.altair_chart(chart, width="stretch")
            st.markdown("""
            <div class="ww-legend">
                <span class="ww-chip ww-green"><b>◆</b>声频契合 ≤ 65 抽</span>
                <span class="ww-chip ww-gold"><b>◆</b>标准区间 66–73 抽</span>
                <span class="ww-chip ww-red"><b>◆</b>高耗共鸣 ≥ 74 抽</span>
            </div>
            """, unsafe_allow_html=True)
            st.caption("大保底成本会计入此前歪出的抽数，因此可能超过 80 抽。")
        else:
            st.info("暂未检测到限定共鸣者记录，成本轨迹等待同步。")
        # ======================================================

        st.markdown('<div class="ww-section">详细解析日志 <small>ANALYSIS ARCHIVE</small></div>', unsafe_allow_html=True)
        st.dataframe(res_df, width="stretch")
else:
    st.markdown("""
    <div style="padding:42px 20px;text-align:center;border:1px dashed rgba(112,226,231,.16);border-radius:3px 14px 3px 14px;color:#667782;background:rgba(112,226,231,.018)">
        <div style="font-size:28px;color:rgba(112,226,231,.32);margin-bottom:8px">〰 ◇ 〰</div>
        等待首条唤取记录接入
    </div>
    """, unsafe_allow_html=True)
