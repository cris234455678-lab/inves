# -*- coding: utf-8 -*-
"""
投资资产看板 — Streamlit 单页应用
功能：密码登录 / 汇总卡片 / 可编辑明细 / 饼图+柱状图 / 导出备份 / Supabase 持久化
部署：Streamlit Community Cloud，环境变量在 Secrets 中配置
"""
import os
import datetime
import pandas as pd
import plotly.express as px
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
TABLE_NAME = "assets"
# 资产类别下拉选项（可自行增删）
ASSET_TYPES = ["股票", "ETF", "期权", "基金", "债券", "现金", "其他"]


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
# 数据读写
# ============================================================
def load_assets() -> pd.DataFrame:
    """从 Supabase 读取全部持仓，按更新时间倒序。表不存在时返回空表并标记。"""
    sb = get_supabase()
    try:
        resp = sb.table(TABLE_NAME).select("*").order("update_time", desc=True).execute()
    except Exception as e:
        msg = str(e).lower()
        if "could not find" in msg or "does not exist" in msg or "pgrst205" in msg:
            st.session_state["table_missing"] = True
            return pd.DataFrame(
                columns=["id", "asset_type", "asset_name", "principal",
                         "market_value", "cost_pnl", "update_time"]
            )
        raise
    st.session_state.pop("table_missing", None)
    df = pd.DataFrame(resp.data)
    if df.empty:
        return pd.DataFrame(
            columns=["id", "asset_type", "asset_name", "principal",
                     "market_value", "cost_pnl", "update_time"]
        )
    df = df[["id", "asset_type", "asset_name", "principal",
             "market_value", "cost_pnl", "update_time"]]
    return df


def upsert_assets(records: list[dict]):
    """批量写入（有 id 则更新，无 id 则插入）。"""
    sb = get_supabase()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = []
    for r in records:
        item = dict(r)
        # 去掉空 id（新增行）
        if item.get("id") in (None, "", pd.NA):
            item.pop("id", None)
        item["update_time"] = now
        # 数值清洗
        for col in ("principal", "market_value", "cost_pnl"):
            v = item.get(col)
            if v is None or v == "":
                item[col] = 0.0
            else:
                item[col] = float(v)
        payload.append(item)
    if payload:
        sb.table(TABLE_NAME).upsert(payload).execute()


def delete_asset(asset_id: int):
    sb = get_supabase()
    sb.table(TABLE_NAME).delete().eq("id", asset_id).execute()


# ============================================================
# 密码登录
# ============================================================
def login():
    """简单密码验证，通过后 st.session_state['authenticated']=True。"""
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
# 主页面
# ============================================================
def main():
    login()

    st.title("📊 投资资产看板")
    st.caption(f"最后刷新：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # ---------- 加载数据 ----------
    if "df_orig" not in st.session_state:
        st.session_state.df_orig = load_assets()

    df = st.session_state.df_orig.copy()

    # 表不存在时显示建表引导
    if st.session_state.get("table_missing"):
        st.error("数据库中还没有 assets 表，请先在 Supabase 建表。")
        st.markdown("**操作步骤**：Supabase 控制台 → 左侧 SQL Editor → New query → 粘贴以下语句 → Run")
        st.code("""CREATE TABLE IF NOT EXISTS assets (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_type   TEXT    NOT NULL,
    asset_name   TEXT    NOT NULL,
    principal    NUMERIC(18,2) DEFAULT 0,
    market_value NUMERIC(18,2) DEFAULT 0,
    cost_pnl     NUMERIC(18,2) DEFAULT 0,
    update_time  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon read"   ON assets FOR SELECT USING (true);
CREATE POLICY "anon write"  ON assets FOR INSERT WITH CHECK (true);
CREATE POLICY "anon update" ON assets FOR UPDATE USING (true);
CREATE POLICY "anon delete" ON assets FOR DELETE USING (true);""", language="sql")
        if st.button("建表完成，重新加载", type="primary"):
            st.session_state.pop("df_orig", None)
            st.rerun()
        st.stop()

    # ---------- 顶部汇总卡片 ----------
    total_principal = float(df["principal"].sum()) if not df.empty else 0.0
    total_value = float(df["market_value"].sum()) if not df.empty else 0.0
    total_pnl = total_value - total_principal
    total_return = (total_pnl / total_principal * 100) if total_principal else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总本金", f"¥{total_principal:,.0f}")
    c2.metric("总资产", f"¥{total_value:,.0f}")
    delta_color = "normal" if total_pnl >= 0 else "inverse"
    c3.metric("总盈亏", f"¥{total_pnl:,.0f}", delta=f"{total_return:+.2f}%",
              delta_color=delta_color)
    c4.metric("总收益率", f"{total_return:+.2f}%")

    st.divider()

    # ---------- 资产明细（可编辑）----------
    st.subheader("📋 资产明细（直接编辑单元格，底部可新增行）")

    edit_df = df.copy()
    edited = st.data_editor(
        edit_df,
        num_rows="dynamic",          # 允许底部新增行
        use_container_width=True,
        hide_index=True,
        column_order=["asset_type", "asset_name", "principal", "market_value", "cost_pnl", "id"],
        column_config={
            "id": st.column_config.NumberColumn("id", disabled=True, width="small"),
            "asset_type": st.column_config.SelectboxColumn(
                "资产类别", options=ASSET_TYPES, required=True),
            "asset_name": st.column_config.TextColumn("标的名称", required=True),
            "principal": st.column_config.NumberColumn("本金", format="%.2f", min_value=0),
            "market_value": st.column_config.NumberColumn("当前市值", format="%.2f", min_value=0),
            "cost_pnl": st.column_config.NumberColumn("持仓盈亏", format="%.2f"),
            "update_time": st.column_config.Column("更新时间", disabled=True, width="small"),
        },
        key="asset_editor",
    )

    # 保存按钮
    col_save, col_del, col_refresh = st.columns([1, 1, 1])
    with col_save:
        if st.button("💾 保存修改", type="primary", use_container_width=True):
            records = edited.to_dict("records")
            # 过滤掉完全空的新增行
            records = [r for r in records
                       if r.get("asset_name") and str(r["asset_name"]).strip()]
            if records:
                upsert_assets(records)
                st.session_state.df_orig = load_assets()
                st.success("已保存到数据库")
                st.rerun()
            else:
                st.warning("没有可保存的数据")

    with col_del:
        # 删除指定 id
        del_id = st.number_input("删除行ID", min_value=1, step=1,
                                 key="del_id_input", label_visibility="collapsed")
        if st.button("🗑️ 删除该行", use_container_width=True):
            delete_asset(int(del_id))
            st.session_state.df_orig = load_assets()
            st.rerun()

    with col_refresh:
        if st.button("🔄 重新加载", use_container_width=True):
            st.session_state.df_orig = load_assets()
            st.rerun()

    st.caption("提示：编辑后点「保存修改」才会写入数据库；持仓盈亏可手动填，也可留空后自行计算。")

    st.divider()

    # ---------- 图表 ----------
    if not df.empty:
        chart_col1, chart_col2 = st.columns(2)

        # 饼图：按资产类别
        with chart_col1:
            st.subheader("🥧 资产类别分布")
            pie_df = df.groupby("asset_type")["market_value"].sum().reset_index()
            fig_pie = px.pie(
                pie_df, names="asset_type", values="market_value",
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10),
                                  showlegend=False, height=380)
            st.plotly_chart(fig_pie, use_container_width=True)

        # 柱状图：各标的市值
        with chart_col2:
            st.subheader("📊 各标的市值")
            bar_df = df.sort_values("market_value", ascending=True)
            fig_bar = px.bar(
                bar_df, x="market_value", y="asset_name", orientation="h",
                color="asset_type",
                color_discrete_sequence=px.colors.qualitative.Set2,
                labels={"market_value": "市值(元)", "asset_name": ""},
            )
            fig_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10),
                                  height=380, showlegend=True,
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("暂无数据，在上方表格中新增标的后即可看到图表。")

    st.divider()

    # ---------- 导出备份 ----------
    st.subheader("📦 数据备份")
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ 导出全部数据 (CSV)",
        data=csv,
        file_name=f"投资资产备份_{datetime.date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # ---------- 底部说明 ----------
    with st.expander("ℹ️ 使用说明 / 后续扩展"):
        st.markdown("""
        - **新增标的**：在表格底部空白行直接填写，资产类别下拉选择，填完点「保存修改」。
        - **修改数据**：直接点击单元格编辑，保存后生效。
        - **删除行**：先在表格中找到该行的 id（可临时取消隐藏 id 列查看），在删除框输入 id 后删除。
        - **手机端**：页面自适应，手机浏览器直接访问即可。
        - **后续可扩展**：净值时序曲线、最大回撤、期权希腊字母(Delta/IV)、资产筛选与时间维度切换——在本表基础上新增字段即可。
        """)


if __name__ == "__main__":
    main()
