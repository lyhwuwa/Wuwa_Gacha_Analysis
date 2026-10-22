"""Streamlit views shared by standalone simulation and actual-record comparison."""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from gacha_model import (MEAN_GOLD, MEAN_UP, PROBABILITIES, exact_expectations,
                         percentile_interval, sample_account, simulate)


def number(value, digits=2):
    return "—" if value is None else f"{value:,.{digits}f}"


def themed(chart):
    return chart.configure_axis(labelColor="#b8c5cb", titleColor="#8e9ba7", gridColor="#22313a").configure_view(stroke=None).configure(background="transparent")


def distribution_chart(counts, expectation, title, actual=None):
    values, frequencies = np.unique(counts, return_counts=True)
    df = pd.DataFrame({"数量": values, "账号占比": frequencies / len(counts)})
    bars = alt.Chart(df).mark_bar(color="#70e2e7", opacity=0.72, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("数量:Q", title=title, axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("账号占比:Q", title="账号比例", axis=alt.Axis(format=".0%")),
        tooltip=[alt.Tooltip("数量:Q", format=".0f"), alt.Tooltip("账号占比:Q", format=".2%")])
    lines = [{"位置": expectation, "参考": "精确期望"}]
    if actual is not None:
        lines.append({"位置": actual, "参考": "我的记录"})
    rule = alt.Chart(pd.DataFrame(lines)).mark_rule(strokeWidth=2, strokeDash=[5, 4]).encode(
        x="位置:Q", color=alt.Color("参考:N", scale=alt.Scale(domain=["精确期望", "我的记录"], range=["#e7c675", "#ff7882"]), legend=alt.Legend(title=None, orient="top")),
        tooltip=["参考:N", alt.Tooltip("位置:Q", format=".2f")])
    return themed((bars + rule).properties(height=300))


def record_comparison(stats, result, theory):
    if not stats or not stats["可对比"]:
        return False
    if not (result["pulls"] == stats["总投入"] and result["pity"] == 0 and result["guaranteed"] == stats["起始大保底"]):
        return False
    st.markdown("#### 我的记录与相同预算对比")
    a, b, c = st.columns(3)
    a.metric("我的UP数", stats["UP数"], f'{stats["UP数"] - theory["up"]:+.2f} vs 期望')
    b.metric("我的出金数", stats["总出金"], f'{stats["总出金"] - theory["gold"]:+.2f} vs 期望')
    lo, hi = percentile_interval(result["up_counts"], stats["UP数"])
    c.metric("UP数量分位区间", f"{lo:.1%}–{hi:.1%}")
    st.caption("分位区间下界是UP数比你少的账号比例，上界还包含与你相同的账号。这里只比较相同预算的模型样本。")
    st.caption("若记录并非从已知保底状态开始、只导入了部分历史，或特意在出金时停止记录，这一对比只能作参照；抽卡后的实际机制不会因分位高低而改变。")
    return True


def render_simulator(stats=None):
    st.markdown("### 概率模拟实验室")
    st.caption("使用提供的79抽出金曲线及50/50大小保底规则，按实际抽取次数计算。")
    defaults = {"sim_pulls": 1700, "sim_trials": 100000, "sim_pity": 0,
                "sim_guaranteed": False, "sim_seed": 20261022, "sim_sample_index": 0}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    queued = st.session_state.pop("queued_simulation", None)
    if queued:
        st.session_state.update({"sim_pulls": queued["pulls"], "sim_pity": queued["pity"],
                                 "sim_guaranteed": queued["guaranteed"]})
        st.info(queued["message"])
    with st.form("simulation_controls"):
        a, b, c = st.columns(3)
        a.number_input("每账号总抽数", min_value=1, max_value=100000, step=1, key="sim_pulls")
        b.selectbox("模拟账号数", [1000, 10000, 100000], key="sim_trials", format_func=lambda x: f"{x:,} 个")
        c.number_input("起始垫抽", min_value=0, max_value=78, step=1, key="sim_pity")
        a, b = st.columns(2)
        a.checkbox("开局大保底（下次金必UP）", key="sim_guaranteed")
        b.number_input("随机种子", min_value=0, max_value=4294967295, step=1, key="sim_seed")
        run = st.form_submit_button("运行模拟", type="primary")
    if run or queued or "simulation_result" not in st.session_state:
        try:
            with st.spinner("计算精确期望并模拟独立账号…"):
                result = simulate(int(st.session_state.sim_pulls), int(st.session_state.sim_trials),
                                  int(st.session_state.sim_pity), bool(st.session_state.sim_guaranteed), int(st.session_state.sim_seed))
                st.session_state.simulation_result = result
                st.session_state.sim_sample_index = 0
        except ValueError as e:
            st.error(str(e))
            return
    result = st.session_state.simulation_result
    theory = exact_expectations(result["pulls"], result["pity"], result["guaranteed"])
    st.caption(f'当前结果：{result["pulls"]:,}抽 × {result["trials"]:,}个账号 · 起始垫抽{result["pity"]} · {"大" if result["guaranteed"] else "小"}保底 · 种子{result["seed"]}')
    a, b, c, d = st.columns(4)
    a.metric("平均UP数量 · 精确", number(theory["up"]))
    b.metric("平均出金数 · 精确", number(theory["gold"]))
    c.metric("预算÷期望UP数", f'{number(theory["cost_up"])} 抽')
    d.metric("长期完整UP周期", f"{MEAN_UP:.2f} 抽")
    st.caption(f'模拟核验：平均UP {result["up_mean"]:.4f}（标准误{result["up_se"]:.4f}），平均出金 {result["gold_mean"]:.4f}（标准误{result["gold_se"]:.4f}）。长期每金{MEAN_GOLD:.2f}抽。')
    overlay = record_comparison(stats, result, theory)
    view = st.radio("观察分布", ["UP数量", "出金数"], horizontal=True, key="sim_distribution")
    up_view = view == "UP数量"
    counts = result["up_counts" if up_view else "gold_counts"]
    actual = stats["UP数" if up_view else "总出金"] if overlay else None
    st.altair_chart(distribution_chart(counts, theory["up" if up_view else "gold"], view, actual), width="stretch")
    q05, median, q95 = np.quantile(counts, [0.05, 0.5, 0.95], method="inverted_cdf")
    a, b, c, d = st.columns(4)
    a.metric("中位数", f"{median:.0f} 个")
    b.metric("第5–95百分位", f"{q05:.0f}–{q95:.0f} 个")
    target = c.number_input("目标数量（至少）", min_value=0, max_value=100000, value=20, step=1, key="sim_target")
    d.metric("模拟达标概率", f"{np.mean(counts >= target):.2%}")
    st.caption("百分位范围描述账号之间的波动；它不是平均值的置信区间。")
    with st.expander("一个模拟账号的出金记录", expanded=False):
        if st.button("再模拟一个账号", key="sim_another"):
            st.session_state.sim_sample_index += 1
        sample_seed = ((result["seed"] ^ 0x9E3779B9) + st.session_state.sim_sample_index) % (2 ** 32)
        sample = sample_account(result["pulls"], result["pity"], result["guaranteed"], sample_seed)
        st.write(f'本组：{sample["gold"]}个金、{sample["up"]}个UP。结束时垫抽{sample["end_pity"]}，{"大" if sample["end_guarantee"] else "小"}保底。')
        sample_frame = pd.DataFrame(sample["events"])
        st.dataframe(sample_frame, hide_index=True, width="stretch")
        st.download_button("导出这组模拟记录 CSV", sample_frame.to_csv(index=False).encode("utf-8-sig"),
                           "模拟出金记录.csv", "text/csv", key="sample_export")
        st.caption("模拟记录仅作示例，不会写入你的真实抽卡档案。")
    with st.expander("概率曲线与统计口径"):
        frame = pd.DataFrame({"第几抽": np.arange(1, 80), "本抽出金率": PROBABILITIES})
        chart = alt.Chart(frame).mark_line(color="#70e2e7").encode(
            x=alt.X("第几抽:Q", title="距上次出金的第n抽"), y=alt.Y("本抽出金率:Q", axis=alt.Axis(format=".0%")),
            tooltip=["第几抽:Q", alt.Tooltip("本抽出金率:Q", format=".1%")]).properties(height=200)
        st.altair_chart(themed(chart), width="stretch")
        st.markdown("1–65抽：0.8%；66–70抽：每抽增加4个百分点；71–75抽：每抽增加8个百分点；76–78抽：每抽增加10个百分点；第79抽必出金。原公式在79抽超过100%，按100%处理。")
        st.markdown("小保底出金50%为UP，歪后下金必UP，UP后回到小保底；任何出金都清零垫抽。这里的概率是此前未出金条件下的本抽概率，不是首金位置的概率分布。")
        st.markdown("**精确期望**通过158个保底状态逐抽递推；**模拟分布**来自独立账号抽样。起始垫抽及此前歪掉的抽数不计入本次预算。")
        st.markdown("**完整UP周期成本**只累计已经获得的UP，包含此前的歪；**总投入÷UP数**还计入末尾未出UP的投入。把所有账号合并后相除，与每个账号先相除再求平均，也不是同一口径。")
        st.write(f'本组模拟：合并账号后 {number(result["pooled_cost"])}抽/UP；各账号先相除再平均 {number(result["account_cost"])}抽/UP（仅计出过UP的{result["positive_accounts"]:,}个账号）。')
        st.caption("模型不计珊瑚返还、兑换共鸣链、额外胜率补偿或不同卡池的特殊机制。")
    summary = pd.DataFrame({"指标": ["总抽数", "模拟账号数", "起始垫抽", "起始大保底", "随机种子", "精确平均UP数", "精确平均出金数", "预算除以期望UP", "长期UP周期", "模拟平均UP数", "模拟平均出金数", "逐账号平均抽数每UP"],
                            "数值": [result["pulls"], result["trials"], result["pity"], result["guaranteed"], result["seed"], theory["up"], theory["gold"], theory["cost_up"], MEAN_UP, result["up_mean"], result["gold_mean"], result["account_cost"]]})
    up_hist, gold_hist = np.bincount(result["up_counts"]), np.bincount(result["gold_counts"])
    length = max(len(up_hist), len(gold_hist))
    hist_frame = pd.DataFrame({"数量": range(length), "UP账号数": np.pad(up_hist, (0, length - len(up_hist))), "出金账号数": np.pad(gold_hist, (0, length - len(gold_hist)))})
    st.download_button("导出本次模拟统计 CSV", (summary.to_csv(index=False) + "\n" + hist_frame.to_csv(index=False)).encode("utf-8-sig"),
                       "鸣潮模拟统计.csv", "text/csv", key="sim_export")
