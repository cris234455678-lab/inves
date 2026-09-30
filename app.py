# -*- coding: utf-8 -*-
"""
投资资产看板 — Streamlit 单页应用
功能：密码登录 / 每日净值记录 / 走势分析与指数对比 / 持仓明细 / 数据备份
部署：Streamlit Community Cloud，环境变量在 Secrets 中配置
"""
import os
import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client, Client

# ============================================================
# 页面配置（必须放在最前面）
# ============================================================
st.set_page_config(
    page_title="投资资产看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# 常量
# ============================================================
TABLE_ASSETS = "assets"
TABLE_NAV = "daily_nav"

ASSET_TYPES = ["股票", "ETF", "期权", "基金", "债券", "现金", "其他"]

# 指数代码映射（用流动性最好的ETF跟踪对应指数，yfinance兼容性更好）
INDEX_MAP = {
    "沪深300":   "510300.SS",
    "中证500":   "510500.SS",
    "科创50":    "588000.SS",
    "创业板指":  "159915.SZ",
    "纳斯达克100": "^NDX",
    "标普500":   "^GSPC",
}

TIME_RANGES = ["近一月", "近三月", "今年以来", "近一年", "近三年", "开户以来", "自定义"]

# ============================================================
# Supabase 连接（单例缓存）
# ============================================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("未配置 SUPABASE_URL / SUPABASE_KEY，请在 Streamlit Secrets 中填写。")
        st.stop()
    return create_client(url, key)


# ============================================================
# 建表 SQL（供用户在 Supabase SQL Editor 执行）
# ============================================================
SETUP_SQL = """-- 持仓表
CREATE TABLE IF NOT EXISTS assets (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_type   TEXT    NOT NULL,
    asset_name   TEXT    NOT NULL,
    principal    NUMERIC(18,2) DEFAULT 0,
    market_value NUMERIC(18,2) DEFAULT 0,
    cost_pnl     NUMERIC(18,2) DEFAULT 0,
    update_time  TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon read"   ON assets;
CREATE POLICY "anon read"   ON assets FOR SELECT USING (true);
DROP POLICY IF EXISTS "anon write"  ON assets;
CREATE POLICY "anon write"  ON assets FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "anon update" ON assets;
CREATE POLICY "anon update" ON assets FOR UPDATE USING (true);
DROP POLICY IF EXISTS "anon delete" ON assets;
CREATE POLICY "anon delete" ON assets FOR DELETE USING (true);

-- 每日净值表
CREATE TABLE IF NOT EXISTS daily_nav (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_date DATE    NOT NULL UNIQUE,
    total_asset NUMERIC(18,2) NOT NULL DEFAULT 0,
    pnl_ratio   NUMERIC(10,4) NOT NULL DEFAULT 0,
    update_time TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE daily_nav ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "nav read"   ON daily_nav;
CREATE POLICY "nav read"   ON daily_nav FOR SELECT USING (true);
DROP POLICY IF EXISTS "nav write"  ON daily_nav;
CREATE POLICY "nav write"  ON daily_nav FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "nav update" ON daily_nav;
CREATE POLICY "nav update" ON daily_nav FOR UPDATE USING (true);
DROP POLICY IF EXISTS "nav delete" ON daily_nav;
CREATE POLICY "nav delete" ON daily_nav FOR DELETE USING (true);"""


# ============================================================
# 数据读写 —— 持仓
# ============================================================
def load_assets() -> pd.DataFrame:
    sb = get_supabase()
    try:
        resp = sb.table(TABLE_ASSETS).select("*").order("update_time", desc=True).execute()
    except Exception as e:
        if _is_table_missing(e):
            st.session_state["assets_missing"] = True
            return _empty_assets_df()
        raise
    st.session_state.pop("assets_missing", None)
    df = pd.DataFrame(resp.data)
    if df.empty:
        return _empty_assets_df()
    return df[["id", "asset_type", "asset_name", "principal", "market_value", "cost_pnl", "update_time"]]


def _empty_assets_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["id", "asset_type", "asset_name", "principal",
                                 "market_value", "cost_pnl", "update_time"])


def upsert_assets(records: list[dict]):
    sb = get_supabase()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = []
    for r in records:
        item = dict(r)
        if item.get("id") in (None, "", pd.NA):
            item.pop("id", None)
        item["update_time"] = now
        for col in ("principal", "market_value", "cost_pnl"):
            v = item.get(col)
            item[col] = 0.0 if v is None or v == "" else float(v)
        payload.append(item)
    if payload:
        sb.table(TABLE_ASSETS).upsert(payload).execute()


def delete_asset(asset_id: int):
    get_supabase().table(TABLE_ASSETS).delete().eq("id", asset_id).execute()


# ============================================================
# 数据读写 —— 每日净值
# ============================================================
def load_nav() -> pd.DataFrame:
    sb = get_supabase()
    try:
        resp = sb.table(TABLE_NAV).select("*").order("record_date", desc=True).execute()
    except Exception as e:
        if _is_table_missing(e):
            st.session_state["nav_missing"] = True
            return _empty_nav_df()
        raise
    st.session_state.pop("nav_missing", None)
    df = pd.DataFrame(resp.data)
    if df.empty:
        return _empty_nav_df()
    df["record_date"] = pd.to_datetime(df["record_date"]).dt.date
    df["total_asset"] = pd.to_numeric(df["total_asset"], errors="coerce").fillna(0)
    df["pnl_ratio"] = pd.to_numeric(df["pnl_ratio"], errors="coerce").fillna(0)
    return df.sort_values("record_date").reset_index(drop=True)


def _empty_nav_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["id", "record_date", "total_asset", "pnl_ratio", "update_time"])


def upsert_nav(records: list[dict]):
    sb = get_supabase()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = []
    for r in records:
        item = dict(r)
        if item.get("id") in (None, "", pd.NA):
            item.pop("id", None)
        # record_date 转字符串
        d = item.get("record_date")
        if isinstance(d, (datetime.date, datetime.datetime)):
            item["record_date"] = d.isoformat() if hasattr(d, "isoformat") else str(d)
        elif d is not None:
            item["record_date"] = str(d)[:10]
        item["update_time"] = now
        item["total_asset"] = float(item.get("total_asset", 0) or 0)
        item["pnl_ratio"] = float(item.get("pnl_ratio", 0) or 0)
        payload.append(item)
    if payload:
        sb.table(TABLE_NAV).upsert(payload).execute()


def delete_nav(nav_id: int):
    get_supabase().table(TABLE_NAV).delete().eq("id", nav_id).execute()


def _is_table_missing(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in ("could not find", "does not exist", "pgrst205", "relation"))


# ============================================================
# 指数数据（yfinance，缓存1小时）
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_index(ticker: str, start: str, end: str) -> pd.DataFrame | None:
    """获取指数收盘价序列，返回 DataFrame[Date, Close]。失败返回 None。"""
    try:
        import yfinance as yf
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        # yfinance 新版可能返回 MultiIndex 列
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if "Close" not in df.columns:
            return None
        out = df[["Close"]].reset_index()
        out.columns = ["Date", "Close"]
        out["Date"] = pd.to_datetime(out["Date"]).dt.date
        return out
    except Exception:
        return None


# ============================================================
# 密码登录
# ============================================================
def login():
    if st.session_state.get("authenticated"):
        return
    st.markdown("### 🔒 请输入访问密码")
    pwd = st.text_input("密码", type="password", key="login_pwd")
    if st.button("登录", type="primary", use_container_width=True):
        correct = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD", "")
        if pwd == correct and pwd:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()


# ============================================================
# 工具函数
# ============================================================
def resolve_range(choice: str, nav_df: pd.DataFrame, custom_start=None, custom_end=None):
    """根据时间维度选择返回 (start_date, end_date)。"""
    today = datetime.date.today()
    if nav_df.empty:
        earliest = today
    else:
        earliest = nav_df["record_date"].min()

    if choice == "近一月":
        start = today - datetime.timedelta(days=30)
    elif choice == "近三月":
        start = today - datetime.timedelta(days=90)
    elif choice == "今年以来":
        start = datetime.date(today.year, 1, 1)
    elif choice == "近一年":
        start = today - datetime.timedelta(days=365)
    elif choice == "近三年":
        start = today - datetime.timedelta(days=365 * 3)
    elif choice == "自定义":
        start = custom_start or earliest
        end = custom_end or today
        return start, end
    else:  # 开户以来
        start = earliest
    return max(start, earliest), today


def normalize_to_start(series: pd.Series) -> pd.Series:
    """将序列归一化为从0%开始的累计收益率。"""
    base = series.iloc[0]
    if base == 0 or pd.isna(base):
        return pd.Series([0.0] * len(series), index=series.index)
    return (series / base - 1) * 100


def calc_max_drawdown(values: pd.Series) -> float:
    """计算最大回撤（百分比，正数表示回撤幅度）。"""
    if len(values) < 2:
        return 0.0
    peak = values.cummax()
    dd = (values - peak) / peak * 100
    return float(abs(dd.min()))


def calc_annualized_return(total_return_pct: float, days: int) -> float:
    if days <= 0 or total_return_pct <= -100:
        return 0.0
    return ((1 + total_return_pct / 100) ** (365 / days) - 1) * 100


def calc_volatility(daily_returns: pd.Series) -> float:
    if len(daily_returns) < 2:
        return 0.0
    return float(daily_returns.std() * np.sqrt(252) * 100)


# ============================================================
# 渲染：建表引导
# ============================================================
def render_setup():
    st.error("数据库中还没有表，请先在 Supabase 建表。")
    st.markdown("**操作步骤**：Supabase 控制台 → 左侧 SQL Editor → New query → 粘贴以下语句 → Run")
    st.code(SETUP_SQL, language="sql")
    if st.button("建表完成，重新加载", type="primary"):
        for k in ("df_assets", "df_nav", "assets_missing", "nav_missing"):
            st.session_state.pop(k, None)
        st.rerun()
    st.stop()


# ============================================================
# 渲染：走势分析 Tab
# ============================================================
def render_analysis(nav_df: pd.DataFrame):
    st.subheader("📈 净值走势与指数对比")

    if nav_df.empty:
        st.info("暂无净值数据，请先到「📝 每日记录」Tab 录入第一条数据。")
        return

    # ---- 筛选栏 ----
    col_range, col_index, col_custom = st.columns([2, 3, 2])
    with col_range:
        range_choice = st.selectbox("时间维度", TIME_RANGES, index=5, key="range_choice")
    with col_index:
        selected_indices = st.multiselect(
            "对比指数（可多选）", list(INDEX_MAP.keys()),
            default=["沪深300"], key="selected_indices",
        )
    custom_start, custom_end = None, None
    if range_choice == "自定义":
        with col_custom:
            custom_start = st.date_input("起始日期", value=nav_df["record_date"].min())
            custom_end = st.date_input("结束日期", value=datetime.date.today())

    start_date, end_date = resolve_range(range_choice, nav_df, custom_start, custom_end)

    # 筛选净值数据
    mask = (nav_df["record_date"] >= start_date) & (nav_df["record_date"] <= end_date)
    plot_df = nav_df[mask].copy().reset_index(drop=True)

    if plot_df.empty:
        st.warning("所选时间范围内没有净值数据。")
        return

    # ---- 汇总指标 ----
    first_asset = plot_df["total_asset"].iloc[0]
    last_asset = plot_df["total_asset"].iloc[-1]
    total_return = (last_asset / first_asset - 1) * 100 if first_asset else 0
    days = (plot_df["record_date"].iloc[-1] - plot_df["record_date"].iloc[0]).days or 1
    ann_return = calc_annualized_return(total_return, days)
    max_dd = calc_max_drawdown(plot_df["total_asset"])
    daily_ret = plot_df["total_asset"].pct_change().dropna()
    vol = calc_volatility(daily_ret)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("区间收益率", f"{total_return:+.2f}%")
    m2.metric("年化收益率", f"{ann_return:+.2f}%")
    m3.metric("最大回撤", f"{max_dd:.2f}%")
    m4.metric("年化波动率", f"{vol:.2f}%")
    m5.metric("期末总资产", f"¥{last_asset:,.0f}")

    st.divider()

    # ---- 图1：总资产走势 ----
    st.markdown("**总资产走势**")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=plot_df["record_date"], y=plot_df["total_asset"],
        mode="lines+markers", name="总资产",
        line=dict(color="#FF4B4B", width=2.5),
        fill="tozeroy", fillcolor="rgba(255,75,75,0.08)",
        hovertemplate="%{x|%Y-%m-%d}<br>¥%{y:,.0f}<extra></extra>",
    ))
    fig1.update_layout(
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="", yaxis_title="总资产(元)",
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.divider()

    # ---- 图2：收益率对比（归一化） ----
    st.markdown("**收益率对比（从区间起点归一化为 0%）**")

    # 我的收益率
    my_return = normalize_to_start(plot_df["total_asset"])
    compare_df = pd.DataFrame({
        "日期": plot_df["record_date"],
        "我的组合": my_return.values,
    })

    # 获取指数数据
    index_data = {}
    fetch_start = (start_date - datetime.timedelta(days=5)).isoformat()
    fetch_end = (end_date + datetime.timedelta(days=1)).isoformat()
    for name in selected_indices:
        ticker = INDEX_MAP[name]
        idx_df = fetch_index(ticker, fetch_start, fetch_end)
        if idx_df is not None and not idx_df.empty:
            idx_mask = (idx_df["Date"] >= start_date) & (idx_df["Date"] <= end_date)
            idx_plot = idx_df[idx_mask].copy()
            if not idx_plot.empty:
                idx_plot["ret"] = normalize_to_start(idx_plot["Close"])
                index_data[name] = idx_plot[["Date", "ret"]]

    # 合并到 compare_df（按日期对齐）
    for name, idf in index_data.items():
        idf = idf.rename(columns={"Date": "日期", "ret": name})
        compare_df = compare_df.merge(idf, on="日期", how="left")
        compare_df[name] = compare_df[name].ffill()

    # 画图
    fig2 = go.Figure()
    colors = ["#FF4B4B", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#17becf"]
    fig2.add_trace(go.Scatter(
        x=compare_df["日期"], y=compare_df["我的组合"],
        mode="lines+markers", name="我的组合",
        line=dict(color=colors[0], width=3),
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>",
    ))
    for i, name in enumerate(selected_indices):
        if name in compare_df.columns:
            fig2.add_trace(go.Scatter(
                x=compare_df["日期"], y=compare_df[name],
                mode="lines", name=name,
                line=dict(color=colors[(i + 1) % len(colors)], width=1.5, dash="dash"),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>",
            ))
    fig2.add_hline(y=0, line_dash="solid", line_color="rgba(0,0,0,0.2)", line_width=1)
    fig2.update_layout(
        height=420, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="", yaxis_title="累计收益率(%)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", ticksuffix="%"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 指数数据获取状态提示
    failed = [n for n in selected_indices if n not in compare_df.columns]
    if failed:
        st.caption(f"⚠️ 以下指数数据获取失败（可能网络问题或该区间无数据）：{', '.join(failed)}")


# ============================================================
# 渲染：持仓明细 Tab
# ============================================================
def render_assets(assets_df: pd.DataFrame):
    # 汇总卡片
    total_principal = float(assets_df["principal"].sum()) if not assets_df.empty else 0.0
    total_value = float(assets_df["market_value"].sum()) if not assets_df.empty else 0.0
    total_pnl = total_value - total_principal
    total_return = (total_pnl / total_principal * 100) if total_principal else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总本金", f"¥{total_principal:,.0f}")
    c2.metric("总资产", f"¥{total_value:,.0f}")
    delta_color = "normal" if total_pnl >= 0 else "inverse"
    c3.metric("总盈亏", f"¥{total_pnl:,.0f}", delta=f"{total_return:+.2f}%", delta_color=delta_color)
    c4.metric("总收益率", f"{total_return:+.2f}%")

    st.divider()
    st.subheader("📋 资产明细（直接编辑单元格，底部可新增行）")

    edited = st.data_editor(
        assets_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=["asset_type", "asset_name", "principal", "market_value", "cost_pnl", "id"],
        column_config={
            "id": st.column_config.NumberColumn("id", disabled=True, width="small"),
            "asset_type": st.column_config.SelectboxColumn("资产类别", options=ASSET_TYPES, required=True),
            "asset_name": st.column_config.TextColumn("标的名称", required=True),
            "principal": st.column_config.NumberColumn("本金", format="%.2f", min_value=0),
            "market_value": st.column_config.NumberColumn("当前市值", format="%.2f", min_value=0),
            "cost_pnl": st.column_config.NumberColumn("持仓盈亏", format="%.2f"),
            "update_time": st.column_config.Column("更新时间", disabled=True, width="small"),
        },
        key="asset_editor",
    )

    col_save, col_del, col_refresh = st.columns([1, 1, 1])
    with col_save:
        if st.button("💾 保存修改", type="primary", use_container_width=True):
            records = [r for r in edited.to_dict("records")
                       if r.get("asset_name") and str(r["asset_name"]).strip()]
            if records:
                upsert_assets(records)
                st.session_state.df_assets = load_assets()
                st.success("已保存到数据库")
                st.rerun()
            else:
                st.warning("没有可保存的数据")
    with col_del:
        del_id = st.number_input("删除行ID", min_value=1, step=1, key="del_id_input", label_visibility="collapsed")
        if st.button("🗑️ 删除该行", use_container_width=True):
            delete_asset(int(del_id))
            st.session_state.df_assets = load_assets()
            st.rerun()
    with col_refresh:
        if st.button("🔄 重新加载", use_container_width=True):
            st.session_state.df_assets = load_assets()
            st.rerun()

    st.caption("提示：编辑后点「保存修改」才会写入数据库；持仓盈亏可手动填。")

    st.divider()

    # 图表
    if not assets_df.empty:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown("**🥧 资产类别分布**")
            pie_df = assets_df.groupby("asset_type")["market_value"].sum().reset_index()
            fig_pie = px.pie(pie_df, names="asset_type", values="market_value", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Set2)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False, height=360)
            st.plotly_chart(fig_pie, use_container_width=True)
        with chart_col2:
            st.markdown("**📊 各标的市值**")
            bar_df = assets_df.sort_values("market_value", ascending=True)
            fig_bar = px.bar(bar_df, x="market_value", y="asset_name", orientation="h",
                             color="asset_type", color_discrete_sequence=px.colors.qualitative.Set2,
                             labels={"market_value": "市值(元)", "asset_name": ""})
            fig_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360,
                                  showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("暂无数据，在上方表格中新增标的后即可看到图表。")


# ============================================================
# 渲染：每日记录 Tab
# ============================================================
def render_nav_entry(nav_df: pd.DataFrame):
    st.subheader("📝 每日净值记录")

    # 录入区
    with st.container(border=True):
        st.markdown("**新增 / 更新一条记录**")
        col_d, col_a, col_r, col_b = st.columns([2, 2, 2, 1])
        with col_d:
            new_date = st.date_input("日期", value=datetime.date.today(), key="new_date")
        with col_a:
            new_asset = st.number_input("总资产(元)", min_value=0.0, step=100.0,
                                        format="%.2f", key="new_asset")
        with col_r:
            new_ratio = st.number_input("盈亏比(%)，留空自动计算", value=None,
                                        step=0.01, format="%.2f", key="new_ratio")
        with col_b:
            st.write("")
            st.write("")
            if st.button("➕ 录入", type="primary", use_container_width=True):
                # 自动计算盈亏比（相对于最早记录的总资产）
                if new_ratio is None:
                    if not nav_df.empty:
                        base = nav_df["total_asset"].min()
                        # 用最早一条记录的资产作为基准
                        base = nav_df.sort_values("record_date")["total_asset"].iloc[0]
                        ratio = (new_asset / base - 1) * 100 if base else 0
                    else:
                        ratio = 0.0
                else:
                    ratio = float(new_ratio)
                upsert_nav([{"record_date": new_date, "total_asset": new_asset, "pnl_ratio": ratio}])
                st.session_state.df_nav = load_nav()
                st.success(f"已录入 {new_date}：总资产 ¥{new_asset:,.2f}，盈亏比 {ratio:.2f}%")
                st.rerun()

    st.caption("提示：同一日期再次录入会覆盖更新；盈亏比留空则自动按起始本金计算。")

    st.divider()

    # 历史记录
    st.markdown("**历史记录（可直接编辑，底部可新增行）**")
    nav_display = nav_df.copy()
    nav_display["record_date"] = nav_display["record_date"].astype(str)

    edited_nav = st.data_editor(
        nav_display,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=["record_date", "total_asset", "pnl_ratio", "id"],
        column_config={
            "id": st.column_config.NumberColumn("id", disabled=True, width="small"),
            "record_date": st.column_config.TextColumn("日期", required=True),
            "total_asset": st.column_config.NumberColumn("总资产", format="%.2f", min_value=0),
            "pnl_ratio": st.column_config.NumberColumn("盈亏比(%)", format="%.2f"),
            "update_time": st.column_config.Column("更新时间", disabled=True, width="small"),
        },
        key="nav_editor",
    )

    col_save2, col_del2, col_refresh2 = st.columns([1, 1, 1])
    with col_save2:
        if st.button("💾 保存修改", type="primary", use_container_width=True, key="nav_save"):
            records = [r for r in edited_nav.to_dict("records")
                       if r.get("record_date") and str(r["record_date"]).strip()]
            if records:
                upsert_nav(records)
                st.session_state.df_nav = load_nav()
                st.success("已保存")
                st.rerun()
    with col_del2:
        del_nav_id = st.number_input("删除记录ID", min_value=1, step=1, key="del_nav_id", label_visibility="collapsed")
        if st.button("🗑️ 删除该记录", use_container_width=True, key="nav_del"):
            delete_nav(int(del_nav_id))
            st.session_state.df_nav = load_nav()
            st.rerun()
    with col_refresh2:
        if st.button("🔄 重新加载", use_container_width=True, key="nav_refresh"):
            st.session_state.df_nav = load_nav()
            st.rerun()


# ============================================================
# 渲染：备份导出 Tab
# ============================================================
def render_backup(assets_df: pd.DataFrame, nav_df: pd.DataFrame):
    st.subheader("📦 数据备份")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**持仓明细**")
        if not assets_df.empty:
            st.dataframe(assets_df, use_container_width=True, hide_index=True)
            csv_a = assets_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⬇️ 导出持仓 CSV", data=csv_a,
                               file_name=f"持仓明细_{datetime.date.today()}.csv",
                               mime="text/csv", use_container_width=True)
        else:
            st.info("暂无持仓数据")

    with col2:
        st.markdown("**每日净值**")
        if not nav_df.empty:
            st.dataframe(nav_df, use_container_width=True, hide_index=True)
            csv_n = nav_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⬇️ 导出净值 CSV", data=csv_n,
                               file_name=f"每日净值_{datetime.date.today()}.csv",
                               mime="text/csv", use_container_width=True)
        else:
            st.info("暂无净值数据")

    st.divider()
    with st.expander("ℹ️ 使用说明"):
        st.markdown("""
        - **每日记录**：每个交易日收盘后到「📝 每日记录」录入总资产，盈亏比可留空自动计算。
        - **走势分析**：到「📈 走势分析」选择时间维度和对比指数，查看归一化收益率曲线。
        - **持仓明细**：到「💼 持仓明细」维护各标的的本金和市值，饼图柱状图自动生成。
        - **修改密码**：Streamlit 页面右下角 Manage app → Settings → Secrets → 修改 APP_PASSWORD。
        - **指数说明**：A股指数用对应ETF收盘价跟踪（沪深300=510300、中证500=510500、科创50=588000、创业板=159915），美股用指数本身（^NDX、^GSPC）。
        """)


# ============================================================
# 主页面
# ============================================================
def main():
    login()

    st.title("📊 投资资产看板")
    st.caption(f"最后刷新：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 加载数据（缓存到 session_state）
    if "df_assets" not in st.session_state:
        st.session_state.df_assets = load_assets()
    if "df_nav" not in st.session_state:
        st.session_state.df_nav = load_nav()

    assets_df = st.session_state.df_assets
    nav_df = st.session_state.df_nav

    # 表不存在时显示建表引导
    if st.session_state.get("assets_missing") or st.session_state.get("nav_missing"):
        render_setup()

    # Tab 布局
    tab1, tab2, tab3, tab4 = st.tabs(["📈 走势分析", "💼 持仓明细", "📝 每日记录", "📦 备份导出"])

    with tab1:
        render_analysis(nav_df)
    with tab2:
        render_assets(assets_df)
    with tab3:
        render_nav_entry(nav_df)
    with tab4:
        render_backup(assets_df, nav_df)


if __name__ == "__main__":
    main()
