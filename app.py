import streamlit as st
import pandas as pd
import io
import requests
import time

st.set_page_config(page_title="鸣潮抽卡分析站", layout="wide")

def fetch_kuro_data(url):
    """通过 URL 自动抓取鸣潮官方数据并解析"""
    headers = {"Content-Type": "application/json"}
    
    # 鸣潮 API 参数：cardPoolType 1 是角色活动唤取（限定池）
    payload = {
        "cardPoolId": "",
        "cardPoolType": 1, 
        "languageCode": "zh-Hans",
        "recordId": ""
    }
    
    all_pulls = []
    
    # 循环分页请求数据
    try:
        while True:
            res = requests.post(url, json=payload, headers=headers).json()
            if res.get("code") != 0 or not res.get("data"):
                break
            
            data_list = res["data"]
            all_pulls.extend(data_list)
            
            # 更新游标，准备抓取下一页
            payload["recordId"] = data_list[-1]["id"]
            time.sleep(0.3) # 稍微停顿，防止被官方服务器拦截
            
    except Exception as e:
        return None, f"抓取失败，请检查链接是否完整或已过期: {str(e)}"
        
    if not all_pulls:
        return None, "未获取到数据，请确保游戏内有抽卡记录，或重新获取最新链接。"
        
    # 官方数据是最新到最老，我们需要反转成最老到最新来计算垫刀
    all_pulls.reverse()
    
    # 常驻五星名单（用于自动判断是否歪了）
    standard_5_stars = ["凌阳", "鉴心", "卡卡罗", "维里奈", "安可"]
    
    parsed_data = []
    pull_counter = 0
    
    for pull in all_pulls:
        pull_counter += 1
        # 如果出金了
        if pull.get("qualityLevel") == 5:
            name = pull.get("name")
            # 自动判断：如果是常驻五星就是歪了(否)，否则就是UP(是)
            is_up = "否" if name in standard_5_stars else "是"
            parsed_data.append({
                "角色名": name,
                "是UP?": is_up,
                "抽数": pull_counter
            })
            pull_counter = 0 # 清空计数器
            
    return pd.DataFrame(parsed_data), "success"

def calculate_stats(df):
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
            
        analysis_data.append({"角色名": char_name, "是UP?": "是" if is_up else "否", "抽数": pulls, "保底类型": pity_type, "实际花费": current_cost if is_up else None})
    
    stats = {
        "总出金": len(df_valid), "UP数": total_up_count, 
        "不歪率": f"{(win_count/win_opportunity*100):.1f}%" if win_opportunity > 0 else "0%",
        "平均出金": round(df_valid['抽数'].mean(), 1) if not df_valid.empty else 0,
        "UP平均花费": round(total_up_cost/total_up_count, 1) if total_up_count > 0 else 0
    }
    return pd.DataFrame(analysis_data), stats

if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame(columns=['角色名', '是UP?', '抽数'])

# --- 侧边栏 ---
with st.sidebar:
    st.header("🔗 一键自动抓取 (推荐)")
    st.caption("1. 运行 PowerShell 脚本提取 URL\n2. 将 URL 粘贴在下方\n3. 系统会自动计算垫刀和保底并填入表格。")
    api_url = st.text_input("粘贴你的 Convene URL:")
    
    if st.button("🚀 开始抓取限定角色池"):
        if api_url:
            with st.spinner("正在从官方服务器同步数据，请稍候..."):
                fetched_df, msg = fetch_kuro_data(api_url.strip())
                if msg == "success":
                    st.session_state.raw_data = fetched_df
                    st.success(f"成功抓取！共发现 {len(fetched_df)} 个五星记录。")
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.warning("请先粘贴 URL。")

    st.markdown("---")
    st.header("📁 文件导入")
    uploaded_file = st.file_uploader("上传历史 CSV 记录", type="csv")
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8-sig")
        imported_df = pd.read_csv(io.StringIO(content))
        if '是否UP?' in imported_df.columns:
            imported_df = imported_df.rename(columns={'是否UP?': '是UP?'})
        cols_to_keep = [c for c in ['角色名', '是UP?', '抽数'] if c in imported_df.columns]
        st.session_state.raw_data = imported_df[cols_to_keep]
        st.success("导入成功！")
        
    st.markdown("---")
    if st.button("🗑️ 清空所有数据"):
        st.session_state.raw_data = pd.DataFrame(columns=['角色名', '是UP?', '抽数'])
        st.rerun()

# --- 主界面 ---
st.title("🌊 鸣潮抽卡数据分析站")
st.info("💡 **全能模式**：你可以用左侧的 **URL抓取**，可以传 **CSV**，也可以直接在下面表格**手动敲字输入**。所有结果实时更新！")

edited_df = st.data_editor(
    st.session_state.raw_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "角色名": st.column_config.TextColumn("角色名", required=True),
        "是UP?": st.column_config.SelectboxColumn("是否UP?", options=["是", "否"], required=True),
        "抽数": st.column_config.NumberColumn("使用抽数", min_value=1, max_value=80, required=True, format="%d")
    },
    key="data_editor"
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
        if cost < 60: delta_color = "off"
        elif cost > 100: delta_color = "inverse"
        c4.metric("获得UP平均花费 (含歪)", f"{cost} 抽", delta_color=delta_color)
        
        st.write("#### 📜 详细分析日志")
        st.dataframe(res_df, use_container_width=True)
else:
    st.warning("暂无有效数据。左侧贴入URL，或在此手动录入你的第一金！")
