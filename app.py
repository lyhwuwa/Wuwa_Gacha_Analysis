import streamlit as st
import pandas as pd
import hashlib
import altair as alt

from gacha_model import MEAN_GOLD, MEAN_UP
from record_analysis import (empty_records, normalize_records, merge_records, analyze_records, read_backup, export_backup)
from simulation_ui import render_simulator, number, themed

st.set_page_config(
    page_title="鸣潮 · 唤取终端",
    page_icon="〰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 鸣潮风格视觉主题（纯 CSS，不依赖外部素材）---
st.markdown("""
<style>

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


# Keep only committed record data in session state; the editor is applied explicitly.
for key, value in {
    "raw_data": empty_records(), "editor_version": 0, "upload_version": 0,
    "tail_pity": 0, "initial_guaranteed": False, "workspace": "抽卡记录",
    "last_import": None,
}.items():
    st.session_state.setdefault(key, value)


def clear_records():
    st.session_state.raw_data = empty_records()
    st.session_state.editor_version += 1
    st.session_state.upload_version += 1
    st.session_state.last_import = None
    st.session_state.tail_pity = 0
    st.session_state.initial_guaranteed = False


def use_history(pulls, pity, guaranteed, message):
    st.session_state.queued_simulation = dict(pulls=pulls, pity=pity, guaranteed=guaranteed, message=message)
    st.session_state.workspace = "概率模拟"


with st.sidebar:
    st.markdown("### 〰 共鸣数据终端")
    st.caption("RESONANCE DATA CONSOLE / LOCAL")
    st.divider()
    st.header("01 · 记录接入")
    st.caption("支持旧版 Excel / CSV。请按同一限定角色卡池的时间顺序记录，保底跨期继承。")
    uploaded = st.file_uploader("接入本地记录 (.xlsx / .csv)", type=["xlsx", "csv"], key=f"import_{st.session_state.upload_version}")
    if uploaded is not None:
        fingerprint = hashlib.sha256(uploaded.getvalue()).hexdigest()
        if fingerprint != st.session_state.last_import:
            try:
                imported, settings = read_backup(uploaded.getvalue(), uploaded.name)
                was_empty = st.session_state.raw_data.empty
                st.session_state.raw_data = merge_records(st.session_state.raw_data, imported)
                st.session_state.editor_version += 1
                st.session_state.last_import = fingerprint
                if was_empty:
                    st.session_state.update(settings)
                elif settings:
                    st.info("记录已合并。当前垫抽和记录起点沿用现有设置，请在下方核对。")
                st.success("记录已接入；重复导入不会再次累加。")
            except Exception as exc:
                st.error(f"文件读取失败：{exc}")
    st.header("02 · 保底状态")
    st.number_input("当前垫抽（末尾未出金）", min_value=0, max_value=78, step=1, key="tail_pity")
    st.checkbox("记录起点已处于大保底", key="initial_guaranteed")
    st.caption("起点默认0垫抽、小保底。若历史不完整，请谨慎解读累计成本与分位。当前垫抽属于已经投入的抽数。")
    st.header("03 · 记录封存")
    if not st.session_state.raw_data.empty or st.session_state.tail_pity:
        st.download_button("↓ 封存为 Excel", export_backup(st.session_state.raw_data, st.session_state.tail_pity, st.session_state.initial_guaranteed),
                           "鸣潮抽卡永久备份.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", key="backup_excel")
        st.caption("Excel 同时保存原始记录、当前垫抽和记录起点状态。请应用编辑后再导出。")
    st.button("清空当前终端", width="stretch", on_click=clear_records)

st.markdown("""
<div class="ww-hero">
    <div class="ww-eyebrow">Wuthering Waves · Convene Archive</div>
    <div class="ww-title">唤取<span>终端</span></div>
    <div class="ww-subtitle">真实记录 / 概率模拟 / 同预算对比</div>
    <div class="ww-status">本地解析核心 ONLINE</div>
</div>
""", unsafe_allow_html=True)
st.radio("工作区", ["抽卡记录", "概率模拟"], horizontal=True, key="workspace", label_visibility="collapsed")
res_df, metrics = analyze_records(st.session_state.raw_data, int(st.session_state.tail_pity), st.session_state.initial_guaranteed)

if st.session_state.workspace == "概率模拟":
    render_simulator(metrics)
else:
    st.info("**终端指引**　每行是一条出金记录，抽数是距上次出金的间隔（跨卡池继承的垫抽也计入）。按从早到晚排列，修改后点击“应用记录并更新统计”。")
    st.markdown('<div class="ww-section">唤取记录录入 <small>CONVENE LOG INPUT</small></div>', unsafe_allow_html=True)
    with st.form("record_editor_form"):
        edited = st.data_editor(
            st.session_state.raw_data, num_rows="dynamic", width="stretch", hide_index=True,
            column_order=["时间", "角色名", "是UP?", "抽数"],
            column_config={
                "时间": st.column_config.TextColumn("记录时间（可选）"),
                "角色名": st.column_config.TextColumn("共鸣者", required=True),
                "是UP?": st.column_config.SelectboxColumn("限定共鸣者？", options=["是", "否"], required=True),
                "抽数": st.column_config.NumberColumn("唤取次数", min_value=1, max_value=80, step=1, required=True, format="%d"),
            }, key=f"record_editor_{st.session_state.editor_version}", height=250)
        if st.form_submit_button("应用记录并更新统计", type="primary"):
            st.session_state.raw_data = normalize_records(edited)
            st.session_state.editor_version += 1
            st.rerun()
    for warning in metrics["问题"]:
        st.warning(warning)
    if metrics["总出金"] or metrics["当前垫抽"]:
        st.markdown('<div class="ww-section">数据概览 <small>RESONANCE OVERVIEW</small></div>', unsafe_allow_html=True)
        a, b, c, d = st.columns(4)
        a.metric("五星共鸣者", metrics["总出金"])
        b.metric("限定UP数", metrics["UP数"])
        c.metric("小保底不歪率", f'{metrics["不歪率"]:.1%}' if metrics["不歪率"] is not None else "—")
        d.metric("平均出金间隔", f'{number(metrics["平均出金"], 1)} 抽')
        a, b, c, d = st.columns(4)
        a.metric("累计实际投入", f'{metrics["总投入"]:,} 抽')
        b.metric("已完成UP平均成本", f'{number(metrics["UP平均花费"], 1)} 抽')
        c.metric("总投入÷UP数", f'{number(metrics["预算每UP"], 1)} 抽')
        d.metric("尚未完成的UP投入", f'{metrics["未完成UP投入"]} 抽')
        st.caption(f'完整UP周期包含此前的歪；末尾未出UP的投入另列，包含未完成周期中的非UP金及当前垫抽。模型长期参考：每金{MEAN_GOLD:.2f}抽，每UP {MEAN_UP:.2f}抽。')
        st.caption(f'下一次出金：{"必定为UP（大保底）" if metrics["下次大保底"] else "50/50（小保底）"}。')
        a, b = st.columns(2)
        a.button("用我的总抽数对比模拟", type="primary", disabled=not metrics["可对比"], width="stretch",
                 on_click=use_history, kwargs=dict(pulls=max(1, metrics["总投入"]), pity=0, guaranteed=metrics["起始大保底"],
                                                   message="已载入记录总投入；下方将叠加真实UP数和出金数。"))
        b.button("从当前保底状态继续模拟", disabled=bool(metrics["问题"]), width="stretch",
                 on_click=use_history, kwargs=dict(pulls=1700, pity=metrics["当前垫抽"], guaranteed=metrics["下次大保底"],
                                                   message="已载入当前垫抽和大小保底。这里的抽数是未来新增投入，可自行调整。"))
        if metrics["总投入"] > 100000:
            st.caption("当前模型单次最多计算100,000抽；历史记录统计不受此限。")
        up_df = res_df[res_df["是UP?"] == "是"].copy()
        st.markdown('<div class="ww-section">限定共鸣者成本轨迹 <small>CONVENE COST TRACE</small></div>', unsafe_allow_html=True)
        if not up_df.empty:
            up_df["获取序号"] = range(1, len(up_df) + 1)
            up_df["展示名"] = up_df["获取序号"].astype(str) + ". " + up_df["角色名"]
            up_df["柱子颜色"] = up_df["实际花费"].map(lambda cost: "#67e5be" if cost <= 65 else "#e7c675" if cost <= 73 else "#ff7882")
            base = alt.Chart(up_df).encode(
                x=alt.X("实际花费:Q", title="完整UP周期投入（含此前的歪）", scale=alt.Scale(domain=[0, max(160, float(up_df["实际花费"].max()) + 10)])),
                y=alt.Y("展示名:N", title="", sort=alt.EncodingSortField(field="获取序号", order="ascending")))
            bars = base.mark_bar(cornerRadiusEnd=3, height=18).encode(color=alt.Color("柱子颜色:N", scale=None), tooltip=["角色名:N", "实际花费:Q", "保底类型:N"])
            labels = base.mark_text(align="left", baseline="middle", dx=7, color="#dcecef").encode(text=alt.Text("实际花费:Q", format=".0f"))
            reference = alt.Chart(pd.DataFrame({"长期均值": [MEAN_UP]})).mark_rule(color="#70e2e7", strokeDash=[4, 4]).encode(x="长期均值:Q", tooltip=alt.Tooltip("长期均值:Q", format=".2f"))
            st.altair_chart(themed((bars + labels + reference).properties(height=max(200, len(up_df) * 40))), width="stretch")
            st.caption("颜色沿用原成本分段：≤65抽、66–73抽、≥74抽；虚线为模型长期每UP均值81.15抽。颜色不是统计显著性的判断。")
        else:
            st.info("尚未获得UP；未完成周期的投入继续累计，不会记成0抽/UP。")
        st.markdown('<div class="ww-section">详细解析日志 <small>ANALYSIS ARCHIVE</small></div>', unsafe_allow_html=True)
        st.dataframe(res_df, width="stretch", hide_index=True)
        st.download_button("导出详细解析 CSV", res_df.to_csv(index=False).encode("utf-8-sig"), "鸣潮抽卡解析.csv", "text/csv")
    else:
        st.markdown("""<div style="padding:36px 20px;text-align:center;border:1px dashed rgba(112,226,231,.16);border-radius:3px 14px;color:#8e9ba7">等待首条唤取记录接入；也可以切换到“概率模拟”直接体验1700抽。</div>""", unsafe_allow_html=True)
