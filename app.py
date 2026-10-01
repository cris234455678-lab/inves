# -*- coding: utf-8 -*-
import os, datetime, numpy as np, pandas as pd
import plotly.express as px, plotly.graph_objects as go
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="资产管理看板", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #eef1f6;
    --card: rgba(255,255,255,0.72);
    --card-solid: #ffffff;
    --fg: #1d1d1f;
    --fg-2: #4b5563;
    --fg-3: #8e8e93;
    --blue: #007AFF;
    --blue-2: #0051D5;
    --green: #34C759;
    --red: #FF3B30;
    --orange: #FF9500;
    --purple: #5856D6;
    --pink: #FF2D55;
    --teal: #5AC8FA;
}

* { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', 'PingFang SC', 'Helvetica Neue', 'Microsoft YaHei', sans-serif;
}

.stApp {
    background:
        radial-gradient(ellipse 900px 600px at 15% 0%, rgba(255,183,215,0.40), transparent 55%),
        radial-gradient(ellipse 800px 600px at 85% 100%, rgba(150,200,255,0.40), transparent 55%),
        radial-gradient(ellipse 700px 500px at 50% 50%, rgba(200,180,255,0.20), transparent 60%),
        linear-gradient(180deg, #eef1f6 0%, #e9ecf3 100%);
    background-attachment: fixed;
    color: var(--fg);
    min-height: 100vh;
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px;
}

/* ================= 侧边栏 (Finder 风格) ================= */
[data-testid="stSidebar"] {
    background: rgba(248,249,251,0.72) !important;
    backdrop-filter: blur(40px) saturate(180%);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
    border-right: 0.5px solid rgba(0,0,0,0.08);
    min-width: 240px !important;
    max-width: 240px !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

.side-brand {
    padding: 0 0.75rem 1rem 0.75rem;
    margin-bottom: 0.5rem;
}
.side-brand-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--fg);
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 8px;
}
.side-brand-title::before {
    content: '';
    width: 11px; height: 11px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FF3B30, #FF9500, #FFCC00, #34C759, #5AC8FA, #007AFF, #AF52DE);
    box-shadow: 0 0 8px rgba(0,122,255,0.3);
}
.side-brand-sub {
    font-size: 0.8rem;
    color: var(--fg-3);
    margin-top: 4px;
    padding-left: 19px;
}

[data-testid="stSidebar"] [role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 0 0.5rem;
}

[data-testid="stSidebar"] [role="radiogroup"] > label {
    display: flex !important;
    align-items: center;
    padding: 12px 16px !important;
    margin: 0 !important;
    border-radius: 10px !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    cursor: pointer;
    transition: background .15s ease, color .15s ease, border-color .15s ease;
    color: var(--fg-2) !important;
    font-size: 1.3rem !important;
    font-weight: 500;
    letter-spacing: -0.005em;
}

[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {
    display: none !important;
}

[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(0,122,255,0.06) !important;
    color: var(--fg) !important;
}

[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: rgba(0,122,255,0.10) !important;
    color: var(--blue) !important;
    font-weight: 600;
    border-color: rgba(0,122,255,0.20) !important;
    box-shadow: 0 1px 3px rgba(0,122,255,0.08);
}

[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {
    color: var(--blue) !important;
}

[data-testid="stSidebar"] [role="radiogroup"] > label p {
    color: inherit !important;
    font-size: 1.3rem !important;
    font-weight: inherit !important;
    margin: 0;
}

.side-footer {
    margin: 1.5rem 0.75rem 0 0.75rem;
    padding-top: 1rem;
    border-top: 0.5px solid rgba(0,0,0,0.08);
    font-size: 0.78rem;
    color: var(--fg-3);
    letter-spacing: 0.02em;
}
.side-footer span { color: var(--green); font-weight: 600; }

/* ================= 页面顶栏 ================= */
.page-hero {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    padding-bottom: 0.75rem;
}
.page-hero h1 {
    font-size: 1.9rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--fg);
    margin: 0;
    line-height: 1.1;
}
.page-hero .hero-meta {
    font-size: 0.78rem;
    color: var(--fg-3);
    display: flex;
    align-items: center;
    gap: 6px;
    padding-bottom: 4px;
}
.page-hero .hero-meta::before {
    content: '';
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px rgba(52,199,89,0.6);
    animation: blink 2s ease-in-out infinite;
}
@keyframes blink {
    0%,100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ================= 小节标题 ================= */
h2, h3 {
    color: var(--fg);
    font-weight: 600;
    font-size: 1.05rem;
    letter-spacing: -0.015em;
    margin: 1.8rem 0 1rem 0;
    padding: 0;
    border: none;
}

/* ================= 指标卡 (macOS Widget) ================= */
div[data-testid="stMetric"] {
    position: relative;
    background: var(--card);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border: 0.5px solid rgba(255,255,255,0.9);
    border-radius: 18px;
    padding: 18px 20px 16px 20px;
    box-shadow:
        0 0 0 0.5px rgba(0,0,0,0.04),
        0 1px 2px rgba(0,0,0,0.02),
        0 4px 12px rgba(0,0,0,0.04),
        0 16px 32px rgba(0,0,0,0.05);
    transition: transform .25s cubic-bezier(.4,0,.2,1), box-shadow .25s ease;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow:
        0 0 0 0.5px rgba(0,0,0,0.05),
        0 2px 4px rgba(0,0,0,0.02),
        0 8px 20px rgba(0,0,0,0.06),
        0 24px 48px rgba(0,0,0,0.08);
}

div[data-testid="stMetricLabel"] {
    color: var(--fg-3) !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.005em;
    text-transform: none;
}
div[data-testid="stMetricLabel"] p {
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    color: var(--fg-3) !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--fg);
    letter-spacing: -0.025em;
    margin-top: 6px;
    font-variant-numeric: tabular-nums;
}

div[data-testid="stMetricDelta"] {
    font-size: 0.78rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    margin-top: 2px;
}

[data-testid="column"]:first-of-type div[data-testid="stMetric"] {
    padding: 22px 22px 20px 22px;
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(240,246,255,0.85) 100%);
    backdrop-filter: blur(30px) saturate(180%);
}
[data-testid="column"]:first-of-type div[data-testid="stMetricValue"] {
    font-size: 2.2rem;
    color: var(--blue);
}

/* ================= 按钮 ================= */
.stButton > button,
.stDownloadButton > button {
    background: var(--card-solid);
    border: 0.5px solid rgba(0,0,0,0.1);
    border-radius: 9px;
    color: var(--fg);
    font-weight: 500;
    font-size: 0.85rem;
    letter-spacing: -0.005em;
    padding: 0.5rem 1.1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 6px rgba(0,0,0,0.03);
    transition: all .18s ease;
    font-family: inherit;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    background: #ffffff;
    border-color: rgba(0,0,0,0.14);
    color: var(--fg);
    transform: translateY(-0.5px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.05), 0 6px 16px rgba(0,0,0,0.06);
}

.stButton > button:active,
.stDownloadButton > button:active {
    transform: translateY(0);
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: var(--blue);
    border: 0.5px solid var(--blue-2);
    color: #ffffff;
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08), 0 4px 14px rgba(0,122,255,0.35);
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background: #0a84ff;
    color: #ffffff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08), 0 8px 22px rgba(0,122,255,0.45);
}

/* ================= 输入控件 ================= */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: rgba(255,255,255,0.9);
    border: 0.5px solid rgba(0,0,0,0.12);
    border-radius: 9px;
    color: var(--fg);
    font-size: 0.88rem;
    padding: 9px 12px;
    transition: all .18s ease;
    font-family: inherit;
    box-shadow: inset 0 1px 1px rgba(0,0,0,0.02);
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stDateInput > div > div > input:focus {
    border-color: var(--blue);
    box-shadow: 0 0 0 3.5px rgba(0,122,255,0.18), inset 0 1px 1px rgba(0,0,0,0.02);
    background: #ffffff;
    outline: none;
}

.stTextInput label,
.stNumberInput label,
.stDateInput label,
.stSelectbox label,
.stMultiSelect label {
    color: var(--fg-2) !important;
    font-weight: 500;
    font-size: 0.8rem;
    letter-spacing: -0.005em;
    text-transform: none;
}

.stSelectbox > div > div > div,
.stMultiSelect > div > div > div {
    background: rgba(255,255,255,0.9);
    border: 0.5px solid rgba(0,0,0,0.12);
    border-radius: 9px;
    color: var(--fg);
    font-size: 0.88rem;
    transition: all .18s ease;
    box-shadow: inset 0 1px 1px rgba(0,0,0,0.02);
}

.stSelectbox > div > div > div:hover,
.stMultiSelect > div > div > div:hover {
    border-color: rgba(0,0,0,0.2);
}

.stMultiSelect [data-baseweb="tag"] {
    background: var(--blue) !important;
    border-radius: 6px !important;
    color: #fff !important;
    font-weight: 500;
    border: none !important;
}

/* ================= 表格 ================= */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    border-radius: 14px;
    overflow: hidden;
    border: 0.5px solid rgba(0,0,0,0.08);
    background: var(--card-solid);
    box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 6px 20px rgba(0,0,0,0.05);
}

[data-testid="stDataFrame"] *,
[data-testid="stDataEditor"] * {
    font-family: inherit;
    font-variant-numeric: tabular-nums;
}

.stDataFrame {
    border-radius: 14px;
    overflow: hidden;
    border: 0.5px solid rgba(0,0,0,0.08);
    box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 6px 20px rgba(0,0,0,0.05);
}

.stDataFrame table { background: #ffffff; }

.stDataFrame th {
    background: rgba(248,249,251,0.95);
    color: var(--fg-2);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: none;
    letter-spacing: 0;
    border-bottom: 0.5px solid rgba(0,0,0,0.08);
    padding: 11px 14px;
}

.stDataFrame td {
    color: var(--fg);
    border-bottom: 0.5px solid rgba(0,0,0,0.05);
    padding: 9px 14px;
    font-size: 0.85rem;
}

.stDataFrame tr:hover td {
    background: rgba(0,122,255,0.04);
}

/* ================= 提示条 ================= */
[data-baseweb="notification"] {
    border-radius: 12px !important;
    border-left-width: 0 !important;
    font-size: 0.85rem;
}

.stInfo, .stAlert.stInfo {
    background: rgba(0,122,255,0.08);
    border: 0.5px solid rgba(0,122,255,0.2);
    border-radius: 12px;
    color: #1a4d8f;
    padding: 13px 17px;
    backdrop-filter: blur(10px);
}
.stSuccess {
    background: rgba(52,199,89,0.1);
    border: 0.5px solid rgba(52,199,89,0.25);
    border-radius: 12px;
    color: #1e6b2e;
    padding: 13px 17px;
    backdrop-filter: blur(10px);
}
.stWarning {
    background: rgba(255,149,0,0.1);
    border: 0.5px solid rgba(255,149,0,0.25);
    border-radius: 12px;
    color: #8a5000;
    padding: 13px 17px;
    backdrop-filter: blur(10px);
}
.stError {
    background: rgba(255,59,48,0.1);
    border: 0.5px solid rgba(255,59,48,0.25);
    border-radius: 12px;
    color: #8b1f1a;
    padding: 13px 17px;
    backdrop-filter: blur(10px);
}

/* ================= 其他 ================= */
.stCaption,
[data-testid="stCaptionContainer"] {
    color: var(--fg-3);
    font-size: 0.78rem;
}

hr, .stDivider {
    border-color: rgba(0,0,0,0.08) !important;
    margin: 1.6rem 0 !important;
}

.js-plotly-plot .plotly .modebar { opacity: 0.25; transition: opacity .2s; }
.js-plotly-plot:hover .plotly .modebar { opacity: 0.9; }

[data-testid="stPlotlyChart"] {
    border-radius: 16px;
    overflow: hidden;
    background: rgba(255,255,255,0.65);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 0.5px solid rgba(255,255,255,0.9);
    box-shadow:
        0 0 0 0.5px rgba(0,0,0,0.04),
        0 4px 12px rgba(0,0,0,0.04),
        0 16px 32px rgba(0,0,0,0.05);
    padding: 12px 8px;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(0,0,0,0.15);
    border-radius: 10px;
    border: 2px solid transparent;
    background-clip: content-box;
}
::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.3); background-clip: content-box; }

.stTextInput > div > div > input[type="password"] {
    letter-spacing: 0.25em;
}
</style>
""", unsafe_allow_html=True)

TABLE_ACCOUNTS = "accounts"
TABLE_NAV = "daily_nav"
TABLE_CASHFLOW = "cash_flow"
TABLE_ASSETS = "assets"

ACCOUNT_TYPES = {"stock": "股票账户", "option": "期权账户", "futures": "期货账户", "fund": "基金账户", "credit": "债权（借出款）", "liability": "负债（消费贷）", "other": "其他"}
ACCOUNT_TYPE_REVERSE = {v: k for k, v in ACCOUNT_TYPES.items()}
DIRECTION_CN = {"asset": "资产", "liability": "负债"}
DIRECTION_REVERSE = {"资产": "asset", "负债": "liability"}
LIABILITY_OWNER = {"self": "自己使用", "proxy": "代他人使用"}
LIABILITY_OWNER_REVERSE = {v: k for k, v in LIABILITY_OWNER.items()}

CASHFLOW_CATEGORIES = ["工资转入", "新增投入", "消费贷提款", "贷款提款", "提现消费", "还贷本金", "还贷利息", "借出款项", "收回借款", "收到利息", "其他"]
INDEX_MAP = {"沪深300": "510300.SS", "中证500": "510500.SS", "科创50": "588000.SS", "创业板指": "159915.SZ", "纳斯达克100": "^NDX", "标普500": "^GSPC"}
TIME_RANGES = ["近一月", "近三月", "今年以来", "近一年", "近三年", "开户以来", "自定义"]

MAIN_BLUE = "#007AFF"
CHART_BG = "rgba(0,0,0,0)"
CHART_GRID = "rgba(0,0,0,0.06)"
CHART_TEXT = "#4b5563"

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
        # 关键修复：日期归零到"当天"，去掉时间部分
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        return df
    except Exception:
        return pd.DataFrame()

def fmt_money(val):
    if val is None:
        return "¥0"
    return f"¥{val/10000:.2f}万" if abs(val) >= 10000 else f"¥{val:,.0f}"

def fmt_pct(val):
    return f"{val:+.2f}%" if val is not None else "0.00%"

def fmt_short_time(val):
    """把时间戳格式化为短格式：MM-DD HH:MM"""
    if val is None or (isinstance(val, float) and pd.isna(val)) or val == "":
        return ""
    try:
        ts = pd.to_datetime(val)
        return ts.strftime("%m-%d %H:%M")
    except Exception:
        return str(val)[:16]

def chart_layout(fig, height=350):
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=CHART_TEXT, size=11, family="-apple-system, BlinkMacSystemFont, Inter, sans-serif"),
        # 关键修复：tickformat 只显示年月日
        xaxis=dict(
            gridcolor=CHART_GRID, zerolinecolor=CHART_GRID, linecolor=CHART_GRID,
            tickformat="%Y-%m-%d",
        ),
        yaxis=dict(gridcolor=CHART_GRID, zerolinecolor=CHART_GRID, linecolor=CHART_GRID),
        margin=dict(t=20, b=15, l=15, r=15),
        height=height,
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor=CHART_GRID, borderwidth=1),
    )
    return fig

def page_header(title: str, subtitle: str = ""):
    meta = subtitle if subtitle else datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    st.markdown(f"""
    <div class="page-hero">
        <h1>{title}</h1>
        <div class="hero-meta">{meta}</div>
    </div>
    """, unsafe_allow_html=True)

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

# ================= 侧边栏导航 =================
with st.sidebar:
    st.markdown("""
    <div class="side-brand">
        <div class="side-brand-title">资产管理</div>
        <div class="side-brand-sub">Portfolio · v1.0</div>
    </div>
    """, unsafe_allow_html=True)

    nav = st.radio(
        "导航",
        ["总览", "每日更新", "投资分析", "资金流水", "持仓明细", "账户管理"],
        label_visibility="collapsed",
        key="sidebar_nav"
    )

    st.markdown(f"""
    <div class="side-footer">
        状态：<span>在线</span><br>
        {datetime.datetime.now().strftime('%Y.%m.%d')}
    </div>
    """, unsafe_allow_html=True)

# ================= 路由 =================
if nav == "总览":
    page_header("总览")
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

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
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
                fig = px.pie(asset_df, values="金额", names="账户",
                             color_discrete_sequence=["#007AFF", "#34C759", "#FF9500", "#5856D6", "#FF2D55", "#5AC8FA"],
                             hole=0.55)
                chart_layout(fig)
                fig.update_traces(textposition='inside', textinfo='percent+label',
                                  marker=dict(line=dict(color="#ffffff", width=2)),
                                  textfont=dict(family="-apple-system, BlinkMacSystemFont, Inter, sans-serif", size=11, color="#ffffff"))
                st.plotly_chart(fig, use_container_width=True)
        with col_tbl:
            d = dist_df.copy()
            d["金额"] = d["金额"].apply(lambda x: f"¥{x:,.2f}")
            st.dataframe(d, use_container_width=True, hide_index=True)
    else:
        st.info("暂无账户数据，请先在「账户管理」中添加账户")

    # 负债分析
    if accounts:
        liab_accs = [a for a in accounts if a["direction"] == "liability"]
        if liab_accs:
            st.markdown("### 负债与利息")
            lc1, lc2, lc3, lc4 = st.columns(4)
            total_liab = sum(a["principal"] + a["accrued_interest"] for a in liab_accs)
            self_liab = sum(a["principal"] + a["accrued_interest"] for a in liab_accs if a.get("liability_owner", "self") == "self")
            proxy_liab = sum(a["principal"] + a["accrued_interest"] for a in liab_accs if a.get("liability_owner", "self") == "proxy")
            # 利息：债权利息=收益，所有负债利息=支出（代他人使用的负债也对应着等额债权，债权收益会自然抵消）
            credit_accs = [a for a in accounts if a["direction"] == "asset" and a.get("account_type") == "credit"]
            interest_income = sum(a["accrued_interest"] for a in credit_accs)
            interest_expense = sum(a["accrued_interest"] for a in liab_accs)
            net_interest = interest_income - interest_expense
            lc1.metric("总负债", fmt_money(total_liab))
            lc2.metric("自己使用", fmt_money(self_liab))
            lc3.metric("代他人使用", fmt_money(proxy_liab))
            lc4.metric("净利息收支", fmt_money(net_interest), f"收益{fmt_money(interest_income)} / 支出{fmt_money(interest_expense)}")
            
            # 负债构成饼图
            liab_data = []
            for a in liab_accs:
                owner = LIABILITY_OWNER.get(a.get("liability_owner", "self"), a.get("liability_owner", "self"))
                liab_data.append({"账户": a["account_name"], "归属": owner, "金额": a["principal"] + a["accrued_interest"]})
            liab_df = pd.DataFrame(liab_data)
            col_pie2, col_tbl2 = st.columns([1, 1])
            with col_pie2:
                fig_l = px.pie(liab_df, values="金额", names="账户",
                               color_discrete_sequence=["#FF3B30", "#FF9500", "#AF52DE", "#FF2D55", "#5856D6"],
                               hole=0.55)
                chart_layout(fig_l)
                fig_l.update_traces(textposition='inside', textinfo='percent+label',
                                    marker=dict(line=dict(color="#ffffff", width=2)),
                                    textfont=dict(family="-apple-system, BlinkMacSystemFont, Inter, sans-serif", size=11, color="#ffffff"))
                st.plotly_chart(fig_l, use_container_width=True)
            with col_tbl2:
                d2 = liab_df.copy()
                d2["金额"] = d2["金额"].apply(lambda x: f"¥{x:,.2f}")
                st.dataframe(d2, use_container_width=True, hide_index=True)

    if not nav_df.empty:
        st.markdown("### 净资产走势")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=nav_df["record_date"], y=nav_df["total_asset"],
                                 fill='tozeroy', fillcolor='rgba(0,122,255,0.10)',
                                 line=dict(color=MAIN_BLUE, width=2.5), mode='lines+markers',
                                 marker=dict(size=5, color=MAIN_BLUE, line=dict(color="#ffffff", width=1.5)),
                                 name='净资产',
                                 hovertemplate='%{x|%Y-%m-%d}<br>净资产: ¥%{y:,.0f}<extra></extra>'))
        chart_layout(fig, 320)
        fig.update_yaxes(tickprefix='¥')
        st.plotly_chart(fig, use_container_width=True)

elif nav == "每日更新":
    page_header("每日更新")
    accounts = get_all_accounts()
    record_date = st.date_input("记录日期", value=datetime.date.today())
    if not accounts:
        st.info("暂无账户，请先在「账户管理」中添加")
    else:
        st.caption("修改各账户余额，带息账户的利息系统自动计算。有出入金时在下方填写。")
        edit_data = [{"id": a["id"], "账户名称": a["account_name"], "类型": ACCOUNT_TYPES.get(a["account_type"], a["account_type"]), "本金余额": a["principal"], "累计利息": a["accrued_interest"], "利率(%)": a["interest_rate"]} for a in accounts]
        edited = st.data_editor(pd.DataFrame(edit_data), use_container_width=True, hide_index=True, column_config={
            "id": st.column_config.NumberColumn(disabled=True),
            "账户名称": st.column_config.TextColumn(disabled=True),
            "类型": st.column_config.TextColumn(disabled=True),
            "本金余额": st.column_config.NumberColumn(format="¥%.2f"),
            "累计利息": st.column_config.NumberColumn(format="¥%.2f", disabled=True),
            "利率(%)": st.column_config.NumberColumn(disabled=True),
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

elif nav == "投资分析":
    page_header("投资分析")
    nav_df = get_nav_history()
    if nav_df.empty:
        st.info("暂无净值数据，请先在「每日更新」中记录")
    else:
        # 关键修复：净值日期也归零
        nav_df["record_date"] = pd.to_datetime(nav_df["record_date"]).dt.normalize()

        cr, ci = st.columns([1, 2])
        with cr: time_range = st.selectbox("时间维度", TIME_RANGES, index=5)
        with ci: selected_indices = st.multiselect("对比指数（可多选）", list(INDEX_MAP.keys()), default=["沪深300"])

        min_d = pd.to_datetime(nav_df["record_date"].min()).date()
        max_d = pd.to_datetime(nav_df["record_date"].max()).date()

        if "custom_start_date" not in st.session_state:
            st.session_state.custom_start_date = min_d
        if "custom_end_date" not in st.session_state:
            st.session_state.custom_end_date = max_d

        if st.session_state.custom_start_date < min_d:
            st.session_state.custom_start_date = min_d
        if st.session_state.custom_start_date > max_d:
            st.session_state.custom_start_date = max_d
        if st.session_state.custom_end_date < min_d:
            st.session_state.custom_end_date = min_d
        if st.session_state.custom_end_date > max_d:
            st.session_state.custom_end_date = max_d

        start_date, end_date = None, None
        if time_range == "自定义":
            d1, d2 = st.columns(2)
            with d1:
                start_date = st.date_input(
                    "开始日期",
                    key="custom_start_date",
                    min_value=min_d,
                    max_value=max_d,
                )
            with d2:
                end_date = st.date_input(
                    "结束日期",
                    key="custom_end_date",
                    min_value=min_d,
                    max_value=max_d,
                )
            start_date = pd.to_datetime(start_date).date() if start_date else min_d
            end_date = pd.to_datetime(end_date).date() if end_date else max_d
            if start_date > end_date:
                st.warning("开始日期晚于结束日期，已自动交换")
                start_date, end_date = end_date, start_date
        else:
            end_date = datetime.date.today()
            range_days = {"近一月": 30, "近三月": 90, "近一年": 365, "近三年": 1095}.get(time_range)
            if range_days:
                start_date = end_date - datetime.timedelta(days=range_days)
            elif time_range == "今年以来":
                start_date = datetime.date(end_date.year, 1, 1)
            else:
                start_date = min_d

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
            fig.add_trace(go.Scatter(x=filtered["record_date"], y=filtered["my_return"], mode='lines+markers',
                                     name='我的组合', line=dict(color=MAIN_BLUE, width=3),
                                     marker=dict(size=6, color=MAIN_BLUE, line=dict(color="#ffffff", width=1.5)),
                                     hovertemplate='%{x|%Y-%m-%d}<br>收益率: %{y:.2f}%<extra></extra>'))
            idx_colors = ["#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#5856D6", "#AF52DE"]
            for i, idx_name in enumerate(selected_indices):
                idx_df = get_index_data(idx_name, start_date, end_date + datetime.timedelta(days=1))
                if not idx_df.empty:
                    idx_df = idx_df[(idx_df["date"].dt.date >= start_date) & (idx_df["date"].dt.date <= end_date)]
                    if not idx_df.empty:
                        idx_df["idx_return"] = (idx_df["close"] / idx_df.iloc[0]["close"] - 1) * 100
                        fig.add_trace(go.Scatter(x=idx_df["date"], y=idx_df["idx_return"], mode='lines',
                                                 name=idx_name,
                                                 line=dict(color=idx_colors[i % len(idx_colors)], width=1.5, dash='dot'),
                                                 opacity=0.85,
                                                 hovertemplate='%{x|%Y-%m-%d}<br>' + idx_name + ': %{y:.2f}%<extra></extra>'))
            chart_layout(fig, 380)
            fig.update_yaxes(ticksuffix='%', title='收益率 (%)')
            # 关键修复：X 轴只显示年月日
            fig.update_xaxes(
                title='日期',
                tickformat='%Y-%m-%d',
                hoverformat='%Y-%m-%d',
                type='date',
            )
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                          bgcolor="rgba(255,255,255,0.9)"), hovermode='x unified')
            fig.add_hline(y=0, line_dash="dot", line_color="rgba(0,0,0,0.15)", line_width=1)
            st.plotly_chart(fig, use_container_width=True)
            # 增加更多趋势指标：净值走势、回撤走势
            st.markdown("#### 净值与回撤走势")
            fig2 = go.Figure()
            # 净值走势（左轴）
            fig2.add_trace(go.Scatter(x=filtered["record_date"], y=filtered["nav"], mode='lines+markers',
                                     name='净值', line=dict(color=MAIN_BLUE, width=2.5),
                                     marker=dict(size=5, color=MAIN_BLUE, line=dict(color="#ffffff", width=1.5)),
                                     yaxis='y',
                                     hovertemplate='%{x|%Y-%m-%d}<br>净值: %{y:.4f}<extra></extra>'))
            # 回撤走势（右轴）
            peak_vals = np.maximum.accumulate(filtered["nav"].values)
            drawdown = ((filtered["nav"].values - peak_vals) / peak_vals * 100)
            fig2.add_trace(go.Scatter(x=filtered["record_date"], y=drawdown, mode='lines',
                                     name='回撤', line=dict(color="#FF3B30", width=1.5, dash='dot'),
                                     fill='tozeroy', fillcolor='rgba(255,59,48,0.08)',
                                     yaxis='y2',
                                     hovertemplate='%{x|%Y-%m-%d}<br>回撤: %{y:.2f}%<extra></extra>'))
            chart_layout(fig2, 320)
            fig2.update_layout(
                yaxis=dict(title='净值', side='left'),
                yaxis2=dict(title='回撤 (%)', side='right', overlaying='y', ticksuffix='%'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode='x unified'
            )
            fig2.update_xaxes(tickformat='%Y-%m-%d', hoverformat='%Y-%m-%d', type='date')
            fig2.update_yaxes(tickprefix='¥')
            fig2.update_xaxes(tickformat='%Y-%m-%d', hoverformat='%Y-%m-%d')
            st.plotly_chart(fig2, use_container_width=True)

elif nav == "资金流水":
    page_header("资金流水")
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
            "id": st.column_config.NumberColumn(disabled=True),
            "日期": st.column_config.TextColumn(),
            "类别": st.column_config.SelectboxColumn(options=CASHFLOW_CATEGORIES),
            "方向": st.column_config.TextColumn(disabled=True),
            "金额显示": st.column_config.TextColumn(disabled=True),
            "备注": st.column_config.TextColumn(),
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

elif nav == "持仓明细":
    page_header("持仓明细")
    assets_data = sb.table(TABLE_ASSETS).select("*").order("id").execute().data
    if assets_data:
        assets_df = pd.DataFrame(assets_data)

        # 关键修复：把 update_time 格式化为短格式 MM-DD HH:MM
        if "update_time" in assets_df.columns:
            assets_df["update_time"] = assets_df["update_time"].apply(fmt_short_time)

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
            "update_time": st.column_config.TextColumn("更新时间", disabled=True, width="small"),
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

elif nav == "账户管理":
    page_header("账户管理")
    accounts = get_all_accounts(active_only=False)
    if accounts:
        display_acc = pd.DataFrame(accounts).copy()
        display_acc["account_type"] = display_acc["account_type"].map(lambda x: ACCOUNT_TYPES.get(x, x))
        display_acc["direction"] = display_acc["direction"].map(lambda x: DIRECTION_CN.get(x, x))
        display_acc["liability_owner"] = display_acc["liability_owner"].fillna("self").map(lambda x: LIABILITY_OWNER.get(x, x))

        # 关键修复：账户管理的 update_time 也短格式化
        if "update_time" in display_acc.columns:
            display_acc["update_time"] = display_acc["update_time"].apply(fmt_short_time)

        edit_acc = st.data_editor(display_acc, use_container_width=True, hide_index=True, column_config={
            "id": st.column_config.NumberColumn(disabled=True),
            "account_name": st.column_config.TextColumn("账户名称"),
            "account_type": st.column_config.SelectboxColumn("类型", options=list(ACCOUNT_TYPES.values())),
            "direction": st.column_config.SelectboxColumn("方向", options=["资产", "负债"]),
            "liability_owner": st.column_config.SelectboxColumn("负债归属", options=list(LIABILITY_OWNER.values())),
            "interest_rate": st.column_config.NumberColumn("年利率(%)", format="%.2f"),
            "principal": st.column_config.NumberColumn("本金", format="¥%.2f"),
            "accrued_interest": st.column_config.NumberColumn("累计利息", format="¥%.2f"),
            "last_interest_date": st.column_config.TextColumn("计息基准日", disabled=True),
            "sort_order": st.column_config.NumberColumn("排序"),
            "is_active": st.column_config.CheckboxColumn("启用"),
            "update_time": st.column_config.TextColumn("更新时间", disabled=True, width="small"),
        }, num_rows="dynamic", key="acc_editor")

        if st.button("💾 保存账户修改"):
            for _, row in edit_acc.iterrows():
                type_cn = row["account_type"]
                type_en = ACCOUNT_TYPE_REVERSE.get(type_cn, type_cn)
                direction_cn = row["direction"]
                direction_en = DIRECTION_REVERSE.get(direction_cn, direction_cn)

                data = {
                    "account_name": row["account_name"],
                    "account_type": type_en,
                    "direction": direction_en,
                    "liability_owner": LIABILITY_OWNER_REVERSE.get(row["liability_owner"], "self"),
                    "interest_rate": row["interest_rate"],
                    "principal": row["principal"],
                    "accrued_interest": row["accrued_interest"],
                    "sort_order": row["sort_order"],
                    "is_active": row["is_active"],
                }
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
    with qc2: new_type = st.selectbox("类型", list(ACCOUNT_TYPES.keys()), format_func=lambda k: ACCOUNT_TYPES[k], key="new_acc_type")
    with qc3: new_dir = st.selectbox("方向", ["asset", "liability"], format_func=lambda k: DIRECTION_CN[k], key="new_acc_dir")
    with qc4: new_owner = st.selectbox("负债归属", list(LIABILITY_OWNER.keys()), format_func=lambda k: LIABILITY_OWNER[k], key="new_acc_owner")
    with qc4: new_rate = st.number_input("年利率(%)", value=0.0, key="new_acc_rate")
    if st.button("➕ 添加账户") and new_name:
        sb.table(TABLE_ACCOUNTS).insert({"account_name": new_name, "account_type": new_type, "direction": new_dir, "liability_owner": new_owner, "interest_rate": new_rate, "principal": 0, "accrued_interest": 0, "last_interest_date": datetime.date.today().isoformat(), "sort_order": len(accounts) + 1 if accounts else 1}).execute()
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