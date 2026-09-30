# -*- coding: utf-8 -*-
"""
个人资产负债统一管理看板 — Streamlit 单页应用
- 基金净值法核算收益率（方式A：先算净值再处理出入金）
- 带息账户自动单利计息（消费贷/借出款）
- 多账户统一管理，每日批量更新
- 指数对比、时间维度筛选
- 现代UI设计
"""
import os
import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="资产管理看板", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp {background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); color: #e8e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;}
#MainMenu, footer, header {visibility: hidden;}
h1 {background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: 800; font-size: 2rem;}
div[data-testid="stMetric"] {background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 16px 20px; backdrop-filter: blur(10px); transition: transform 0.2s, box-shadow 0.2s;}
div[data-testid="stMetric"]:hover {transform: translateY(-2px); box-shadow: 0 8px 32px rgba(102,126,234,0.2);}
div[data-testid="stMetric"] label {color: #9ca3af !important; font-size: 0.85rem;}
div[data-testid="stMetricValue"] {font-size: 1.6rem; font-weight: 700; color: #fff;}
.stTabs [data-baseweb="tab-list"] {gap: 8px; background: rgba(255,255,255,0.04); padding: 6px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);}
.stTabs [data-baseweb="tab"] {background: transparent; border-radius: 10px; padding: 10px 20px; color: #9ca3af; font-weight: 600; font-size: 0.95rem; transition: all 0.2s;}
.stTabs [data-baseweb="tab"]:hover {color: #fff; background: rgba(255,255,255,0.06);}
.stTabs [aria-selected="true"] {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; color: #fff !important; box-shadow: 0 4px 15px rgba(102,126,234,0.4);}
.stButton > button {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; border-radius: 10px; color: #fff; font-weight: 600; padding: 0.5rem 1.5rem; transition: all 0.2s; box-shadow: 0 4px 15px rgba(102,126,234,0.3);}
.stButton > button:hover {transform: translateY(-1px); box-shadow: 0 6px 20px rgba(102,126,234,0.5); color: #fff;}
.stTextInput > div > div > input, .stNumberInput > div > div > input, .stDateInput > div > div > input {background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; color: #fff;}
.stSelectbox > div > div > div, .stMultiSelect > div > div > div {background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; color: #fff;}
.stDataFrame {border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1);}
h2, h3 {color: #e8e8f0; font-weight: 700; border-left: 4px solid #667eea; padding-left: 12px; margin-top: 1.5rem;}
.stInfo {background: rgba(102,126,234,0.15); border: 1px solid rgba(102,126,234,0.3); border-radius: 10px; color: #c7d2fe;}
.stSuccess {background: rgba(52,211,153,0.15); border: 1px solid rgba(52,211,153,0.3); border-radius: 10px; color: #6ee7b7;}
.stWarning {background: rgba(251,191,36,0.15); border: 1px solid rgba(251,191,36,0.3); border-radius: 10px; color: #fcd34d;}
</style>
""", unsafe_allow_html=True)

TABLE_ACCOUNTS = "accounts"
TABLE_NAV = "daily_nav"
TABLE_CASHFLOW = "cash_flow"
TABLE_ASSETS = "assets"

ACCOUNT_TYPES = {"stock": "股票账户", "option": "期权账户", "futures": "期货账户", "fund": "基金账户", "credit": "债权（借出款）", "liability": "负债（消费贷）", "other": "其他"}
CASHFLOW_CATEGORIES = ["工资转入", "新增投入", "消费贷提款", "贷款提款", "提现消费", "还贷本金", "还贷利息", "借出款项", "收回借款", "收到利息", "其他"]
INDEX_MAP = {"沪深300": "510300.SS", "中证500": "510500.SS", "科创50": "588000.SS", "创业板指": "159915.SZ", "纳斯达克100": "^NDX", "标普500": "^GSPC"}
TIME_RANGES = ["近一月", "近三月", "今年以来", "近一年", "近三年", "开户以来", "自定义"]
COLORS = {"primary": "#667eea", "chart_bg": "rgba(15,12,41,0.8)"}

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY", "")
    return create_client(url, key)

sb = get_supabase()

def calc_interest(principal, annual_rate, start_date, end_date):
    if principal <= 0 or annual_rate <= 0:
        return 0.0
    days = (end_date - start_date).days
    return round(principal * annual_rate / 100 * days / 365, 2) if days > 0 else 0.0

def update_account_interest(account_id):
    acc = sb.table(TABLE_ACCOUNTS).select("*").eq("id", account_id).execute().data
    if not acc:
        return
    acc = acc[0]
    if acc["interest_rate"] and acc["interest_rate"] > 0 and acc["last_interest_date"]:
        last_date = pd.to_datetime(acc["last_interest_date"]).date()
        today = datetime.date.today()
        if today > last_date:
            interest = calc_interest(acc["principal"], acc["interest_rate"], last_date, today)
            sb.table(TABLE_ACCOUNTS).update({
                "accrued_interest": round(acc["accrued_interest"] + interest, 2),
                "last_interest_date": today.isoformat(),
            }).eq("id", account_id).execute()

def get_all_accounts(active_only=True):
    q = sb.table(TABLE_ACCOUNTS).select("*").order("sort_order")
    if active_only:
        q = q.eq("is_active", True)
    accounts = q.execute().data
    today = datetime.date.today()
    for acc in accounts:
        if acc["interest_rate"] and acc["interest_rate"] > 0 and acc["last_interest_date"]:
            if today > pd.to_datetime(acc["last_interest_date"]).date():
                update_account_interest(acc["id"])
    return q.execute().data

def get_account_total(accounts):
    total = 0.0
    for acc in accounts:
        val = acc["principal"] + acc["accrued_interest"]
        if acc["direction"] == "liability":
            total -= val
        else:
            total += val
    return round(total, 2)

def get_nav_history():
    data = sb.table(TABLE_NAV).select("*").order("record_date").execute().data
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["record_date"] = pd.to_datetime(df["record_date"])
    return df

def get_cashflow_by_date(date_str):
    data = sb.table(TABLE_CASHFLOW).select("amount").eq("record_date", date_str).execute().data
    return sum(d["amount"] for d in data)

def calc_nav_for_date(record_date, total_asset, prev_nav, prev_shares):
    net_cf = get_cashflow_by_date(record_date)
    nav = (total_asset - net_cf) / prev_shares if prev_shares > 0 else 1.0
    shares = prev_shares + net_cf / nav if nav > 0 else prev_shares
    return round(nav, 6), round(shares, 4)

@st.cache_data(ttl=3600)
def get_index_data(index_name, start_date, end_date):
    try:
        import yfinance as yf
        ticker = INDEX_MAP.get(index_name)
        if not ticker:
            return pd.DataFrame()
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        close_col = "close" if "close" in df.columns else df.columns[-1]
        date_col = "date" if "date" in df.columns else df.columns[0]
        df = df[[date_col, close_col]].rename(columns={date_col: "date", close_col: "close"})
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()

def fmt_money(val):
    if val is None:
        return "¥0"
    return f"¥{val/10000:.2f}万" if abs(val) >= 10000 else f"¥{val:,.0f}"

def fmt_pct(val):
    return f"{val:+.2f}%" if val is not None else "0.00%"

def check_password():
    if "password_ok" not in st.session_state:
        st.session_state.password_ok = False
    if st.session_state.password_ok:
        return True
    st.markdown("## 🔐 请输入访问密码")
    pwd = st.text_input("密码", type="password", key="login_pwd")
    if st.button("登录", use_container_width=True):
        correct = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD", "asset2026")
        if pwd == correct:
            st.session_state.password_ok = True
            st.rerun()
        else:
            st.error("密码错误")
    return False

if not check_password():
    st.stop()

st.markdown("# 📊 资产管理看板")
st.caption(f"最后刷新：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

t1, t2, t3, t4, t5, t6 = st.tabs(["📊 总览", "💰 每日更新", "📈 投资分析", "💸 资金流水", "📋 持仓明细", "⚙️ 账户管理"])

# ===== Tab 1: 总览 =====
with t1:
    accounts = get_all_accounts()
    net_asset = get_account_total(accounts)
    nav_df = get_nav_history()
    if not nav_df.empty:
        latest = nav_df.iloc[-1]
        total_return = (latest["nav"] - 1.0) * 100
        total_profit = net_asset - latest["shares"] * latest["nav"] if latest["shares"] > 0 else 0
    else:
        total_return, total_profit = 0, 0
    today_change = nav_df.iloc[-1]["total_asset"] - nav_df.iloc[-2]["total_asset"] if len(nav_df) >= 2 else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("净资产", fmt_money(net_asset), f"{fmt_money(today_change)} 今日")
    c2.metric("累计收益率", fmt_pct(total_return))
    c3.metric("累计收益额", fmt_money(total_profit))
    c4.metric("账户数量", f"{len(accounts)} 个")
    st.markdown("### 资产分布")
    if accounts:
        dist_data = []
        for acc in accounts:
            val = acc["principal"] + acc["accrued_interest"]
            val = -val if acc["direction"] == "liability" else val
            dist_data.append({"账户": acc["account_name"], "类型": ACCOUNT_TYPES.get(acc["account_type"], acc["account_type"]), "金额": val, "方向": "负债" if acc["direction"] == "liability" else "资产"})
        dist_df = pd.DataFrame(dist_data)
        col_pie, col_tbl = st.columns([1, 1])
        with col_pie:
            asset_df = dist_df[dist_df["方向"] == "资产"]
            if not asset_df.empty:
                fig = px.pie(asset_df, values="金额", names="账户", color_discrete_sequence=px.colors.qualitative.Set3, hole=0.4)
                fig.update_layout(paper_bgcolor=COLORS["chart_bg"], plot_bgcolor=COLORS["chart_bg"], font=dict(color="#e8e8f0"), margin=dict(t=20, b=20, l=20, r=20))
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
        with col_tbl:
            d = dist_df.copy()
            d["金额"] = d["金额"].apply(lambda x: f"¥{x:,.2f}")
            st.dataframe(d, use_container_width=True, hide_index=True)
    else:
        st.info("暂无账户数据，请先在「账户管理」中添加账户")
    if not nav_df.empty:
        st.markdown("### 净资产走势")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=nav_df["record_date"], y=nav_df["total_asset"], fill='tozeroy', fillcolor='rgba(102,126,234,0.2)', line=dict(color=COLORS["primary"], width=2), mode='lines+markers', name='净资产', hovertemplate='%{x|%Y-%m-%d}<br>净资产: ¥%{y:,.0f}<extra></extra>'))
        fig.update_layout(paper_bgcolor=COLORS["chart_bg"], plot_bgcolor=COLORS["chart_bg"], font=dict(color="#e8e8f0"), xaxis=dict(gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickprefix='¥'), margin=dict(t=20, b=20, l=20, r=20), height=350)
        st.plotly_chart(fig, use_container_width=True)

# ===== Tab 2: 每日更新 =====
with t2:
    st.markdown("### 每日资产更新")
    accounts = get_all_accounts()
    record_date = st.date_input("记录日期", value=datetime.date.today())
    if not accounts:
        st.info("暂无账户，请先在「账户管理」中添加")
    else:
        st.caption("修改各账户余额，带息账户的利息系统自动计算。有出入金时在下方填写。")
        edit_data = [{"id": a["id"], "账户名称": a["account_name"], "类型": ACCOUNT_TYPES.get(a["account_type"], a["account_type"]), "本金余额": a["principal"], "累计利息": a["accrued_interest"], "利率(%)": a["interest_rate"]} for a in accounts]
        edited = st.data_editor(pd.DataFrame(edit_data), use_container_width=True, hide_index=True, column_config={
            "id": st.column_config.NumberColumn(disabled=True), "账户名称": st.column_config.TextColumn(disabled=True),
            "类型": st.column_config.TextColumn(disabled=True), "本金余额": st.column_config.NumberColumn(format="¥%.2f"),
            "累计利息": st.column_config.NumberColumn(format="¥%.2f", disabled=True), "利率(%)": st.column_config.NumberColumn(disabled=True),
        }, key="daily_edit")
        st.markdown("#### 当日出入金（有变动才填）")
        cf1, cf2, cf3, cf4 = st.columns([2, 1, 2, 1])
        with cf1: cf_cat = st.selectbox("类别", CASHFLOW_CATEGORIES, key="cf_cat")
        with cf2: cf_dir = st.selectbox("方向", ["入金", "出金"], key="cf_dir")
        with cf3: cf_amt = st.number_input("金额", min_value=0.0, value=0.0, step=100.0, key="cf_amt")
        with cf4: cf_note = st.text_input("备注", key="cf_note")
        if st.button("➕ 添加出入金记录"):
            if cf_amt > 0:
                amount = cf_amt if cf_dir == "入金" else -cf_amt
                sb.table(TABLE_CASHFLOW).insert({"record_date": record_date.isoformat(), "amount": amount, "category": cf_cat, "note": cf_note}).execute()
                st.success(f"已添加{cf_dir}：{cf_cat} ¥{cf_amt:,.0f}")
                st.rerun()
        today_cf = sb.table(TABLE_CASHFLOW).select("*").eq("record_date", record_date.isoformat()).execute().data
        if today_cf:
            st.markdown("**当日出入金明细**")
            cfd = pd.DataFrame(today_cf)
            cfd["方向"] = cfd["amount"].apply(lambda x: "入金" if x > 0 else "出金")
            cfd["金额"] = cfd["amount"].apply(lambda x: f"¥{abs(x):,.2f}")
            st.dataframe(cfd[["category", "方向", "金额", "note"]].rename(columns={"category": "类别", "note": "备注"}), use_container_width=True, hide_index=True)
        if st.button("💾 保存今日快照", type="primary", use_container_width=True):
            for _, row in edited.iterrows():
                sb.table(TABLE_ACCOUNTS).update({"principal": row["本金余额"], "accrued_interest": row["累计利息"]}).eq("id", int(row["id"])).execute()
            accounts_new = get_all_accounts()
            total = get_account_total(accounts_new)
            nav_df = get_nav_history()
            if not nav_df.empty:
                prev = nav_df.iloc[-1]
                prev_nav, prev_shares = prev["nav"], prev["shares"]
            else:
                prev_nav, prev_shares = 1.0, total
            nav, shares = calc_nav_for_date(record_date.isoformat(), total, prev_nav, prev_shares)
            breakdown = {str(a["id"]): a["principal"] + a["accrued_interest"] for a in accounts_new}
            existing = sb.table(TABLE_NAV).select("id").eq("record_date", record_date.isoformat()).execute().data
            if existing:
                sb.table(TABLE_NAV).update({"total_asset": total, "nav": nav, "shares": shares, "breakdown": breakdown}).eq("id", existing[0]["id"]).execute()
            else:
                sb.table(TABLE_NAV).insert({"record_date": record_date.isoformat(), "total_asset": total, "pnl_ratio": (nav - 1) * 100, "nav": nav, "shares": shares, "breakdown": breakdown}).execute()
            st.success(f"✅ 已保存！净资产：¥{total:,.2f}，净值：{nav:.4f}，份额：{shares:.2f}")
            st.rerun()

# ===== Tab 3: 投资分析 =====
with t3:
    st.markdown("### 净值走势与指数对比")
    nav_df = get_nav_history()
    if nav_df.empty:
        st.info("暂无净值数据，请先在「每日更新」中记录")
    else:
        cr, ci = st.columns([1, 2])
        with cr: time_range = st.selectbox("时间维度", TIME_RANGES, index=5)
        with ci: selected_indices = st.multiselect("对比指数（可多选）", list(INDEX_MAP.keys()), default=["沪深300"])
        start_date, end_date = None, None
        if time_range == "自定义":
            d1, d2 = st.columns(2)
            with d1: start_date = st.date_input("开始日期", value=nav_df["record_date"].min().date())
            with d2: end_date = st.date_input("结束日期", value=nav_df["record_date"].max().date())
        else:
            end_date = datetime.date.today()
            range_days = {"近一月": 30, "近三月": 90, "近一年": 365, "近三年": 1095}.get(time_range)
            if range_days:
                start_date = end_date - datetime.timedelta(days=range_days)
            elif time_range == "今年以来":
                start_date = datetime.date(end_date.year, 1, 1)
            else:
                start_date = nav_df["record_date"].min().date()
        mask = (nav_df["record_date"].dt.date >= start_date) & (nav_df["record_date"].dt.date <= end_date)
        filtered = nav_df[mask].copy()
        if filtered.empty:
            st.warning("所选时间段内无数据")
        else:
            first_nav, last_nav = filtered.iloc[0]["nav"], filtered.iloc[-1]["nav"]
            period_return = (last_nav / first_nav - 1) * 100
            days = (filtered.iloc[-1]["record_date"] - filtered.iloc[0]["record_date"]).days
            annual_return = ((last_nav / first_nav) ** (365 / max(days, 1)) - 1) * 100 if days > 0 else 0
            peak = np.maximum.accumulate(filtered["nav"].values)
            max_drawdown = ((filtered["nav"].values - peak) / peak * 100).min()
            annual_vol = filtered["nav"].pct_change().dropna().std() * np.sqrt(252) * 100 if len(filtered) > 1 else 0
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("区间收益率", fmt_pct(period_return))
            m2.metric("年化收益率", fmt_pct(annual_return))
            m3.metric("最大回撤", f"{max_drawdown:.2f}%")
            m4.metric("年化波动率", f"{annual_vol:.2f}%")
            m5.metric("期末净资产", fmt_money(filtered.iloc[-1]["total_asset"]))
            filtered["my_return"] = (filtered["nav"] / first_nav - 1) * 100
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=filtered["record_date"], y=filtered["my_return"], mode='lines+markers', name='我的组合', line=dict(color=COLORS["primary"], width=3), marker=dict(size=6), hovertemplate='%{x|%Y-%m-%d}<br>收益率: %{y:.2f}%<extra></extra>'))
            for idx_name in selected_indices:
                idx_df = get_index_data(idx_name, start_date, end_date + datetime.timedelta(days=1))
                if not idx_df.empty:
                    idx_df = idx_df[(idx_df["date"].dt.date >= start_date) & (idx_df["date"].dt.date <= end_date)]
                    if not idx_df.empty:
                        idx_df["idx_return"] = (idx_df["close"] / idx_df.iloc[0]["close"] - 1) * 100
                        fig.add_trace(go.Scatter(x=idx_df["date"], y=idx_df["idx_return"], mode='lines', name=idx_name, line=dict(width=1.5, dash='dash'), opacity=0.8))
            fig.update_layout(paper_bgcolor=COLORS["chart_bg"], plot_bgcolor=COLORS["chart_bg"], font=dict(color="#e8e8f0"), xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='日期'), yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='收益率 (%)', ticksuffix='%'), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=40, b=20, l=20, r=20), height=400, hovermode='x unified')
            fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.3)")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("#### 净资产走势")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=filtered["record_date"], y=filtered["total_asset"], fill='tozeroy', fillcolor='rgba(102,126,234,0.15)', line=dict(color=COLORS["primary"], width=2), mode='lines+markers', name='净资产'))
            fig2.update_layout(paper_bgcolor=COLORS["chart_bg"], plot_bgcolor=COLORS["chart_bg"], font=dict(color="#e8e8f0"), xaxis=dict(gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(gridcolor='rgba(255,255,255,0.05)', tickprefix='¥'), margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig2, use_container_width=True)

# ===== Tab 4: 资金流水 =====
with t4:
    st.markdown("### 出入金流水")
    cf_data = sb.table(TABLE_CASHFLOW).select("*").order("record_date", desc=True).execute().data
    if not cf_data:
        st.info("暂无出入金记录")
    else:
        cf_df = pd.DataFrame(cf_data)
        cf_df["record_date"] = pd.to_datetime(cf_df["record_date"])
        cf_df["方向"] = cf_df["amount"].apply(lambda x: "📈 入金" if x > 0 else "📉 出金")
        cf_df["金额显示"] = cf_df["amount"].apply(lambda x: f"¥{abs(x):,.2f}")
        total_in = cf_df[cf_df["amount"] > 0]["amount"].sum()
        total_out = abs(cf_df[cf_df["amount"] < 0]["amount"].sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("累计入金", fmt_money(total_in))
        c2.metric("累计出金", fmt_money(total_out))
        c3.metric("净入金", fmt_money(total_in - total_out))
        display_df = cf_df[["id", "record_date", "category", "方向", "金额显示", "note"]].rename(columns={"record_date": "日期", "category": "类别", "note": "备注"})
        display_df["日期"] = display_df["日期"].dt.strftime("%Y-%m-%d")
        edited_cf = st.data_editor(display_df, use_container_width=True, hide_index=True, column_config={
            "id": st.column_config.NumberColumn(disabled=True), "日期": st.column_config.TextColumn(),
            "类别": st.column_config.SelectboxColumn(options=CASHFLOW_CATEGORIES), "方向": st.column_config.TextColumn(disabled=True),
            "金额显示": st.column_config.TextColumn(disabled=True), "备注": st.column_config.TextColumn(),
        }, key="cf_editor")
        if st.button("💾 保存修改"):
            for _, row in edited_cf.iterrows():
                sb.table(TABLE_CASHFLOW).update({"record_date": row["日期"], "category": row["类别"], "note": row["备注"]}).eq("id", int(row["id"])).execute()
            st.success("已保存")
            st.rerun()
        del_id = st.number_input("删除记录ID", min_value=0, value=0, step=1)
        if st.button("🗑️ 删除该记录") and del_id > 0:
            sb.table(TABLE_CASHFLOW).delete().eq("id", del_id).execute()
            st.success(f"已删除ID={del_id}")
            st.rerun()

# ===== Tab 5: 持仓明细 =====
with t5:
    st.markdown("### 持仓明细（偶尔更新，不影响净值）")
    assets_data = sb.table(TABLE_ASSETS).select("*").order("id").execute().data
    if assets_data:
        assets_df = pd.DataFrame(assets_data)
        tp, tv, tpnl = assets_df["principal"].sum(), assets_df["market_value"].sum(), assets_df["cost_pnl"].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总本金", fmt_money(tp))
        c2.metric("总市值", fmt_money(tv))
        c3.metric("总盈亏", fmt_money(tpnl))
        c4.metric("总收益率", fmt_pct(tpnl / tp * 100 if tp > 0 else 0))
        edit_assets = st.data_editor(assets_df, use_container_width=True, hide_index=True, column_config={
            "id": st.column_config.NumberColumn(disabled=True),
            "asset_type": st.column_config.SelectboxColumn("资产类别", options=["股票", "ETF", "期权", "基金", "债券", "现金", "其他"]),
            "asset_name": st.column_config.TextColumn("标的名称"),
            "principal": st.column_config.NumberColumn("本金", format="¥%.2f"),
            "market_value": st.column_config.NumberColumn("当前市值", format="¥%.2f"),
            "cost_pnl": st.column_config.NumberColumn("持仓盈亏", format="¥%.2f"),
            "update_time": st.column_config.TextColumn(disabled=True),
        }, num_rows="dynamic", key="assets_editor")
        if st.button("💾 保存持仓修改"):
            for _, row in edit_assets.iterrows():
                data = {"asset_type": row["asset_type"], "asset_name": row["asset_name"], "principal": row["principal"], "market_value": row["market_value"], "cost_pnl": row["cost_pnl"]}
                if pd.notna(row.get("id")):
                    sb.table(TABLE_ASSETS).update(data).eq("id", int(row["id"])).execute()
                else:
                    sb.table(TABLE_ASSETS).insert(data).execute()
            st.success("已保存")
            st.rerun()
    else:
        st.info("暂无持仓数据")
        if st.button("➕ 添加第一条持仓"):
            sb.table(TABLE_ASSETS).insert({"asset_type": "股票", "asset_name": "示例", "principal": 0, "market_value": 0, "cost_pnl": 0}).execute()
            st.rerun()

# ===== Tab 6: 账户管理 =====
with t6:
    st.markdown("### 账户管理")
    accounts = get_all_accounts(active_only=False)
    if accounts:
        edit_acc = st.data_editor(pd.DataFrame(accounts), use_container_width=True, hide_index=True, column_config={
            "id": st.column_config.NumberColumn(disabled=True),
            "account_name": st.column_config.TextColumn("账户名称"),
            "account_type": st.column_config.SelectboxColumn("类型", options=list(ACCOUNT_TYPES.keys())),
            "direction": st.column_config.SelectboxColumn("方向", options=["asset", "liability"]),
            "interest_rate": st.column_config.NumberColumn("年利率(%)", format="%.2f"),
            "principal": st.column_config.NumberColumn("本金", format="¥%.2f"),
            "accrued_interest": st.column_config.NumberColumn("累计利息", format="¥%.2f"),
            "last_interest_date": st.column_config.TextColumn("计息基准日", disabled=True),
            "sort_order": st.column_config.NumberColumn("排序"),
            "is_active": st.column_config.CheckboxColumn("启用"),
            "update_time": st.column_config.TextColumn(disabled=True),
        }, num_rows="dynamic", key="acc_editor")
        if st.button("💾 保存账户修改"):
            for _, row in edit_acc.iterrows():
                data = {"account_name": row["account_name"], "account_type": row["account_type"], "direction": row["direction"], "interest_rate": row["interest_rate"], "principal": row["principal"], "accrued_interest": row["accrued_interest"], "sort_order": row["sort_order"], "is_active": row["is_active"]}
                if pd.notna(row.get("id")):
                    sb.table(TABLE_ACCOUNTS).update(data).eq("id", int(row["id"])).execute()
                else:
                    data["last_interest_date"] = datetime.date.today().isoformat()
                    sb.table(TABLE_ACCOUNTS).insert(data).execute()
            st.success("已保存账户设置")
            st.rerun()
    else:
        st.info("暂无账户")
    st.markdown("#### 快速添加账户")
    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1: new_name = st.text_input("账户名称", key="new_acc_name")
    with qc2: new_type = st.selectbox("类型", list(ACCOUNT_TYPES.keys()), key="new_acc_type")
    with qc3: new_dir = st.selectbox("方向", ["asset", "liability"], key="new_acc_dir")
    with qc4: new_rate = st.number_input("年利率(%)", value=0.0, key="new_acc_rate")
    if st.button("➕ 添加账户") and new_name:
        sb.table(TABLE_ACCOUNTS).insert({"account_name": new_name, "account_type": new_type, "direction": new_dir, "interest_rate": new_rate, "principal": 0, "accrued_interest": 0, "last_interest_date": datetime.date.today().isoformat(), "sort_order": len(accounts) + 1 if accounts else 1}).execute()
        st.success(f"已添加账户：{new_name}")
        st.rerun()
    st.markdown("### 📦 数据备份导出")
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button("导出账户数据"):
            st.download_button("下载账户CSV", pd.DataFrame(get_all_accounts(active_only=False)).to_csv(index=False).encode("utf-8-sig"), "accounts_backup.csv", "text/csv")
    with bc2:
        if st.button("导出净值数据"):
            st.download_button("下载净值CSV", get_nav_history().to_csv(index=False).encode("utf-8-sig"), "nav_backup.csv", "text/csv")
    with bc3:
        if st.button("导出入金数据"):
            st.download_button("下载流水CSV", pd.DataFrame(sb.table(TABLE_CASHFLOW).select("*").execute().data).to_csv(index=False).encode("utf-8-sig"), "cashflow_backup.csv", "text/csv")
    st.caption("提示：第一次保存快照时自动设定起始净值=1.0、起始份额=当日净资产")
