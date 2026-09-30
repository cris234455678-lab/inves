# 投资资产看板 — 部署说明

基于 Streamlit + Supabase 的单页面轻量化投资资产看板，电脑/手机浏览器自适应。

## 文件清单

| 文件 | 说明 |
|------|------|
| `app.py` | 主程序（单脚本，全部功能在同一页面） |
| `requirements.txt` | Python 依赖清单 |
| `README.md` | 本部署说明 |

---

## 第一步：创建 Supabase 免费数据库

1. 打开 https://supabase.com ，用 GitHub 账号登录，点 **New project**。
2. 项目名随意（如 `investment-dashboard`），区域选离你近的（Singapore / Tokyo），设置数据库密码（记下来）。
3. 等待项目创建完成（约1分钟）。
4. 左侧菜单进入 **SQL Editor** → 点 **New query**，粘贴以下建表语句并执行（Run）：

```sql
CREATE TABLE IF NOT EXISTS assets (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_type  TEXT    NOT NULL,
    asset_name  TEXT    NOT NULL,
    principal   NUMERIC(18,2) DEFAULT 0,
    market_value NUMERIC(18,2) DEFAULT 0,
    cost_pnl    NUMERIC(18,2) DEFAULT 0,
    update_time TIMESTAMPTZ DEFAULT NOW()
);

-- 允许匿名角色读写（Streamlit 用 service key 更安全，这里用 anon key 即可）
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon read"  ON assets FOR SELECT USING (true);
CREATE POLICY "anon write" ON assets FOR INSERT WITH CHECK (true);
CREATE POLICY "anon update" ON assets FOR UPDATE USING (true);
CREATE POLICY "anon delete" ON assets FOR DELETE USING (true);
```

5. 左侧菜单进入 **Project Settings** → **API**，复制两个值：
   - **Project URL**（形如 `https://xxxx.supabase.co`）
   - **anon public** key（很长的一串）

---

## 第二步：上传到 GitHub

1. 在 GitHub 新建一个仓库（Public 或 Private 均可），如 `investment-dashboard`。
2. 把 `app.py`、`requirements.txt`、`README.md` 三个文件上传到仓库根目录。
   - 可以直接在 GitHub 网页点 **Add file → Upload files** 拖拽上传。
   - 仓库里必须有 `requirements.txt`，Streamlit 会自动安装依赖。

---

## 第三步：部署到 Streamlit Community Cloud（免费）

1. 打开 https://share.streamlit.io ，用 GitHub 账号登录并授权。
2. 点 **New app**：
   - **Repository**：选你刚建的仓库
   - **Branch**：`main`
   - **Main file path**：`app.py`
3. 点 **Advanced settings** → **Secrets**，填入三行（替换成你自己的值）：

```toml
SUPABASE_URL = "https://你的项目.supabase.co"
SUPABASE_KEY = "你的anon_public_key"
APP_PASSWORD = "你自己设的访问密码"
```

4. 点 **Deploy!**，等待约1-2分钟构建完成。
5. 部署成功后会得到一个网址（形如 `https://xxx.streamlit.app`），手机和电脑浏览器都能直接访问。

---

## 第四步：使用

1. 打开网址，输入你在 Secrets 里设的 `APP_PASSWORD` 登录。
2. 在「资产明细」表格底部空白行填写标的信息，点 **保存修改**。
3. 顶部汇总卡片和下方图表会自动更新。
4. 需要备份时点 **导出全部数据(CSV)**。

---

## 本地运行（可选，用于调试）

```bash
pip install -r requirements.txt

#  Windows PowerShell 设置临时环境变量
$env:SUPABASE_URL="https://xxx.supabase.co"
$env:SUPABASE_KEY="你的key"
$env:APP_PASSWORD="你的密码"

streamlit run app.py
```

---

## 数据表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT 自增主键 | 系统自动生成，删除行时需要 |
| asset_type | TEXT | 资产类别（股票/ETF/期权/基金/债券/现金/其他） |
| asset_name | TEXT | 标的名称 |
| principal | NUMERIC | 本金 |
| market_value | NUMERIC | 当前市值 |
| cost_pnl | NUMERIC | 持仓盈亏 |
| update_time | TIMESTAMPTZ | 最后更新时间（自动） |

## 后续扩展方向

- 新增 `daily_nav` 表记录每日净值 → 画净值时序曲线、最大回撤
- 新增 `option_greeks` 表 → 展示 Delta/Gamma/Theta/Vega/IV
- 接入行情 API 自动刷新市值
- 多用户支持（目前单密码登录）
