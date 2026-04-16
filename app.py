import streamlit as st
import pandas as pd
import io
import requests
import time
import altair as alt # 新增：引入强大的高级图表库
import urllib.parse # 添加在文件最顶部的 import 区域

st.set_page_config(page_title="鸣潮抽卡分析站 | 可视化版", layout="wide")

def fetch_kuro_data(url):
    """自动解析前端 URL 并请求库洛后端 API"""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 1. 拦截错误输入
    if "?" not in url:
        return None, "抓取失败：这不是一个有效的带参数的抽卡链接。"
        
    # 2. 核心戏法：从你的网页 URL 中拆解出所有的身份令牌
    try:
        # 分离出问号后面的参数部分
        query_string = url.split("?")[1]
        # 将参数解析为字典
        params_dict = urllib.parse.parse_qs(query_string)
        # 将列表值转换为普通字典
        payload = {k: v[0] for k, v in params_dict.items()}
    except Exception as e:
        return None, f"URL 解析失败: {str(e)}"

    # 3. 锁定目标：强制查询 1 号池（角色限定唤取）
    payload["cardPoolType"] = 1
    
    # 4. 智能路由：判断是国服还是国际服
    # 国服 API 通常是 aki-game2.com，外服通常是 .net
    api_endpoint = "https://gmserver-api.aki-game2.com/gacha/record/query"
    if "global" in payload.get("serverId", "").lower() or ".net" in url:
        api_endpoint = "https://gmserver-api.aki-game2.net/gacha/record/query"

    all_pulls = []
    
    # 5. 开始向真正的后端接口请求数据
    try:
        while True:
            response = requests.post(api_endpoint, json=payload, headers=headers)
            
            if response.status_code != 200:
                return None, f"请求被官方服务器拒绝 (HTTP {response.status_code})。请确认链接未过期。"
                
            res = response.json()
            
            # 检查官方接口返回的错误码
            if res.get("code") != 0:
                return None, f"官方服务器提示: {res.get('message', '未知错误(大概率链接已过期)')}"
                
            if not res.get("data"):
                break # 这一页没数据了，说明抓取完毕
                
            data_list = res["data"]
            all_pulls.extend(data_list)
            
            # 把记录翻页指针更新为当前页最后一条的ID，准备抓下一页
            payload["recordId"] = data_list[-1]["id"]
            time.sleep(0.3) # 停顿防封
            
    except Exception as e:
        return None, f"网络请求异常: {str(e)}"
        
    if not all_pulls:
        return None, "未获取到数据，可能是这个池子你还没有抽过卡。"
        
    # 官方数据是从新到旧，为了算垫刀，反转成从旧到新
    all_pulls.reverse()
    standard_5_stars = ["凌阳", "鉴心", "卡卡罗", "维里奈", "安可"]
    
    parsed_data = []
    pull_counter = 0
    for pull in all_pulls:
        pull_counter += 1
        if pull.get("qualityLevel") == 5:
            name = pull.get("name")
            is_up = "否" if name in standard_5_stars else "是"
            parsed_data.append({
                "时间": pull.get("time", ""),
                "角色名": name,
                "是UP?": is_up,
                "抽数": pull_counter
            })
            pull_counter = 0 
            
    return pd.DataFrame(parsed_data), "success"
def merge_records(old_df, new_df):
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
    st.header("🔗 第一步：增量抓取")
    api_url = st.text_input("粘贴 URL 同步近6个月数据:")
    if st.button("🚀 抓取并合并"):
        if api_url:
            with st.spinner("正在同步..."):
                fetched_df, msg = fetch_kuro_data(api_url.strip())
                if msg == "success":
                    st.session_state.raw_data = merge_records(st.session_state.raw_data, fetched_df)
                    st.success("抓取成功！已剔除重复项。")
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.warning("请先粘贴 URL。")

    st.markdown("---")
    st.header("📁 第二步：历史导入")
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
    st.header("💾 第三步：导出备份")
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
st.title("🌊 鸣潮抽卡数据分析站")

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
    height=250 # 稍微固定高度，避免太长挡住图表
)
st.session_state.raw_data = edited_df

st.divider()

if not edited_df.empty and not edited_df['角色名'].isna().all():
    res_df, m = calculate_stats(edited_df)
    if m:
        # 指标卡片
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
        
        # ================= 新增：可视化图表区 =================
        st.subheader("📊 UP角色花费欧非图鉴")
        
        # 只筛选出UP角色用来画图
        up_df = res_df[res_df['是UP?'] == '是'].copy()
        
        if not up_df.empty:
            # 为了防止重名角色导致图表合并，我们给角色加个序号
            up_df['获取序号'] = range(1, len(up_df) + 1)
            up_df['展示名'] = up_df['获取序号'].astype(str) + ". " + up_df['角色名']
            
            # 【修复点】：用 Python 提前算好颜色，避开 Altair 库的嵌套计算 bug
            def get_color(cost):
                if pd.isna(cost): return '#808080'
                if cost <= 65: return '#28a745'   # 绿色：欧皇
                elif cost <= 73: return '#ffc107' # 黄色：亚洲人
                else: return '#dc3545'            # 红色：非酋
                
            up_df['柱子颜色'] = up_df['实际花费'].apply(get_color)
            
            # 使用 Altair 构建图表
            chart = alt.Chart(up_df).mark_bar(cornerRadiusEnd=4, height=20).encode(
                x=alt.X('实际花费:Q', title='花费抽数 (含垫刀)', scale=alt.Scale(domain=[0, 160])),
                y=alt.Y('展示名:N', title='', sort=alt.EncodingSortField(field="获取序号", order="ascending")),
                # 直接读取算好的颜色列 (scale=None 告诉它直接用色值，不要自己去映射)
                color=alt.Color('柱子颜色:N', scale=None),
                tooltip=[
                    alt.Tooltip('角色名', title='角色'),
                    alt.Tooltip('实际花费', title='实际花费抽数'),
                    alt.Tooltip('保底类型', title='抽取情况')
                ]
            ).properties(
                height=max(200, len(up_df) * 45) # 图表高度自适应
            ).configure_axis(
                labelFontSize=13,
                titleFontSize=14
            )
            
            # 渲染图表
            st.altair_chart(chart, use_container_width=True)
            
            # 图表图例说明
            st.caption("🟢 **欧皇**：≤ 65 抽 | 🟡 **平庸**：66 - 73 抽 | 🔴 **非酋**：≥ 74 抽 （*注：大保底花费可能超过80抽*）")
        else:
            st.info("尚未获取UP角色，无法生成可视化图鉴。")
        # ======================================================
