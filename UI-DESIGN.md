# UI 设计文档 · 印尼股市营销文案变体系统

> 用途：交给图像生成模型（gptimages 2.0）产出高保真 UI 设计图。
> 本文件同时是「设计语言规范」+「逐屏视觉描述」+「可直接粘贴的生成提示词」。
> 权威需求来源：`DESIGN.md` v3 / `HANDOFF.md`。技术栈锁定 **Ant Design 全家桶 + Ant Design X（对话）+ Ant Design Charts**。
> 产品定位：内部「出稿加速器」，桌面 Web 后台工具，非营销官网。风格要**专业、克制、信息密度高**，不要花哨营销风。
>
> ⚠️ **图像生成红线（踩了会被拒绝出图）**：**提示词里绝不出现任何真实第三方品牌/产品/公司/媒体/股票代码名**（如 Ant Design、Linear、Vercel、CNBC、Kontan、BBRI 等）。技术栈品牌名只用于本文件的设计说明，**不进 ▶ 生成提示词**——它只决定视觉气质，模型不需要知道品牌名。所有实体一律用**虚构名**（账号 `@akun_demo`、股票 `SAHM-X`、来源「财经源A/B/C」），并在每段提示词结尾加 `Fully original design, no real brand logos, no real company names`。

---

## 0. 怎么用这份文档

1. 先读 **§1 设计语言** —— 所有图共用同一套色板/字体/圆角/间距，保证风格统一。
2. 每个界面一节，含：**布局结构 → 组件清单 → 样例内容 → §末尾「▶ 生成提示词」**。
3. 出图时把 **§1 全局提示词前缀** + 对应屏的「▶ 生成提示词」拼接使用。
4. 统一规格：**桌面 Web，1440×900（16:10），@2x**，浅色主题为主（附一版深色可选）。

---

## 1. 设计语言（所有图共用，锁死）

### 1.1 基调
- **风格关键词**：现代 SaaS 后台、克制、专业、数据感、留白充足、圆角柔和。
- **参照气质**：主流企业级后台仪表盘的克制质感，不是消费级营销页（**此参照仅供本文件理解，不要写进提示词**）。
- **框架**：企业级后台三段式 —— 左侧固定侧边导航 + 顶部栏 + 右侧主内容区。

### 1.2 色板
| 角色 | 色值 | 用途 |
|---|---|---|
| 品牌主色 Primary | `#2F54EB`（靛蓝） | 主按钮、选中态、关键链接、图表主色 |
| 主色浅底 | `#F0F5FF` | 选中项背景、标签底 |
| 成功 / 合规通过 | `#52C41A` | 「合规✓」徽章、达标状态 |
| 警告 / 软提示 | `#FAAD14` | 「软提示·待人工判断」标记 |
| 危险 / 硬拦截 | `#F5222D` | 「禁词命中·已拦截」标记 |
| 中性文字主 | `#1F1F1F` | 标题正文 |
| 中性文字次 | `#8C8C8C` | 辅助说明、时间戳 |
| 分割线 / 边框 | `#F0F0F0` | 卡片边、分隔线 |
| 页面背景 | `#F5F7FA` | 主内容区底色 |
| 卡片背景 | `#FFFFFF` | 卡片、面板 |

深色可选版：背景 `#141414`，卡片 `#1F1F1F`，文字 `#E6E6E6`，主色不变。

### 1.3 字体与排版
- 字体：**Inter / -apple-system** 拉丁字符，中文用 **PingFang SC / 思源黑体**。等宽用 **JetBrains Mono**（token 数、成本数字）。
- 字号：页面大标题 24/32；卡片标题 16/24；正文 14/22；辅助 12/20。
- 字重：标题 600，正文 400，数字看板 500。

### 1.4 元素规范
- 圆角：卡片 12px、按钮 8px、标签 4px、头像圆形。
- 阴影：卡片 `0 1px 4px rgba(0,0,0,0.06)`，悬浮态略加深。
- 间距：8 的倍数（8/16/24/32）。主内容区左右留白 32。
- 图标：线性风格（Ant Design Icons / Lucide 气质），1.5px 描边。

### 1.5 侧边导航（所有内页共用）
顶部 Logo「变体工坊」+ 收起按钮。菜单项（图标+文字）：
- 💬 **文案生成**（默认高亮/工作台）
- 📰 **新闻库**
- 📊 **消耗看板**（仅管理员可见）
- ⚙️ **抓取与配额**（仅管理员可见）
底部：当前用户头像 + 角色标签（「素材员」/「管理员」）+ 退出。

### 1.6 顶部栏
左：面包屑/当前页标题。右：全局搜索框、通知铃铛、当日 token 消耗小徽标（`今日 12.4k tokens`）、头像。

### ▶ §1 全局提示词前缀（每张图都拼在最前面）
```
High-fidelity desktop web app UI design, 1440x900, @2x, clean modern enterprise SaaS admin dashboard,
light theme, background #F5F7FA, white cards with 12px rounded corners and soft subtle shadow,
primary brand color indigo #2F54EB, success green #52C41A, warning amber #FAAD14, danger red #F5222D,
Inter + PingFang SC typography, generous whitespace, 8px grid spacing, linear line icons,
left fixed sidebar navigation + top bar + main content area. Professional, restrained, data-dense, NOT a marketing page.
UI labels in Simplified Chinese. Crisp, pixel-perfect, realistic screenshot quality.
Fully original design, no real brand logos, no real company names.
```

---

## 2. 登录页

### 布局
- 左右分栏：**左 55% 品牌区**（靛蓝渐变背景 `#2F54EB → #1D39C4`，白色 Logo「变体工坊」+ 一句 slogan「让『想角度·写多版』从小时级压到分钟级」+ 抽象数据线条插画/几何装饰），**右 45% 表单区**（白底居中卡片）。
- 表单卡片：标题「登录」、用户名输入框、密码输入框、「记住我」勾选 + 「忘记密码」链接、靛蓝主按钮「登录」。
- 底部小字：「内部工具 · 仅授权账号访问」。

### 说明
- 双角色共用登录页，登录后按角色渲染不同菜单（管理员多两项）。
- 无注册入口（内部账号制）。

### ▶ 生成提示词
```
{全局前缀}
Login page, split layout: left 55% is an indigo gradient brand panel (#2F54EB to #1D39C4) with white logo "变体工坊",
a slogan line in white, and abstract flowing data-line geometric decoration; right 45% is a centered white login card
with title "登录", a username field, a password field, a "记住我" checkbox with "忘记密码" link, and a full-width
indigo primary button "登录". Small footer text "内部工具 · 仅授权账号访问". Minimal, elegant, enterprise SaaS login.
Fully original design, no real brand logos, no real company names.
```

---

## 3. 文案生成工作台（★核心屏，最重要）

这是素材员每天用的主界面。基于 **Ant Design X 对话范式**，但右侧挂「变体结果区」，是「对话驱动 + 卡片产出」的混合布局。

### 布局（三栏）
- **左：侧边导航**（§1.5，「文案生成」高亮）。
- **中：对话区**（约 40%）——
  - 顶部一条 **调性/账号选择器**（必选）：下拉「为哪个账号/调性写：@akun_demo 犀利散户体 ▾」，旁边小字提示「不同账号语感指纹独立，生成前必须选」。
  - 对话消息流：用户气泡（右，靛蓝底白字）「基于『某银行股财报超预期』这条，写 5 条短文案，钩子要强」；AI 气泡（左，白底）「已为 @akun_demo 生成 5 个变体，按综合分排序 👉」。
  - 底部输入框（Ant Design X Sender 组件）：多行输入 + 附件/引用新闻按钮 + 靛蓝「发送」；上方一排快捷 chips：「换个钩子」「更口语」「缩短到 IG 长度」「重新生成」。
- **右：变体结果区**（约 45%）——**变体卡片纵向列表**（详见 §7 组件规范），顶部一行工具条：`共 5 个变体`、排序下拉「按综合分 ▾」、多样性提示徽标「两两风格距离 0.72 ✓ 多样性良好」。

### 变体卡片内容（右区每张卡，样例）
- 顶部：排名徽章 `#1`、综合分环形进度 `88`、一排维度小标签「钩子:悬念 · 结构:故事 · 情绪:FOMO · IG · CTA:强」。
- 正文（**印尼语样例文案，虚构标的**）：
  > "SAHM-X cetak laba di atas ekspektasi 📈 Gue udah masuk sejak 4.200. Sekarang? Angkanya bikin melek. Yang masih mikir-mikir, baca caption ini sampai habis 👇"
- 合规条：一排徽章 —— 绿色「合规✓」/ 或黄色「软提示 · 1 句待判断」/ 或红色「禁词命中·已改写」。若有软提示，正文里对应句底部黄色波浪下划线。
- AI 味条：小字「AI 味 12/100 · 风格距离 0.18（贴合 @akun_demo）」+ 一个绿色小盾。
- 底部操作按钮行：`采用`（靛蓝主）、`复制`、`编辑`、`重新生成`（幽灵按钮）；右下角未确认文案显示灰色标记「未确认」。

### 状态点缀
- 生成中：右区顶部一张骨架卡 + 流式文字逐条冒出（Top-K 流式先出，呼应 DESIGN §3 M5 性能）。
- 空态：右区居中插画 + 「选好账号/调性，在左侧描述你想要的文案，变体会出现在这里」。

### ▶ 生成提示词
```
{全局前缀}
Main workspace "文案生成" (copy variant generation), three-column layout.
Left: sidebar nav with "文案生成" highlighted (menu items 文案生成/新闻库/消耗看板/抓取与配额).
Center column (~40%): a chat conversation panel. At top a required tone selector dropdown
"为哪个账号/调性写：@akun_demo 犀利散户体 ▾" with small hint text. Below, chat bubbles: a right-aligned indigo user
bubble and a left-aligned white AI bubble. At the bottom a multiline chat composer input with attach button
and indigo "发送" button, and a row of quick-action chips "换个钩子" "更口语" "缩短长度" "重新生成".
Right column (~45%): a vertical list of "variant cards". Toolbar on top: "共 5 个变体", a sort dropdown "按综合分 ▾",
and a green diversity badge "风格距离 0.72 ✓". Each variant card shows: a rank badge "#1", a circular score ring "88",
a row of small dimension tags "钩子:悬念 · 结构:故事 · 情绪:FOMO · CTA:强", body copy in generic Indonesian marketing text about a fictional stock,
a compliance badge row (green "合规✓" or amber "软提示·1句待判断" or red "禁词命中·已改写"), a small line "AI味 12/100 · 风格距离 0.18",
and an action button row "采用"(indigo primary) "复制" "编辑" "重新生成", with a grey "未确认" tag. Data-dense, professional.
Fully original UI, no real company names, no real brand logos.
```

---

## 4. 新闻库（M2 只读 + 可选打标）

### 布局
- 顶部筛选栏：搜索框、来源多选（财经源A / 财经源B / 财经源C / 交易所公告 / 综合门户，**均为虚构占位名**）、时间范围、热度排序、「仅看未打标」开关。
- 主体：**新闻卡片列表 / 表格切换**。默认卡片流，每张卡：
  - 左侧竖条颜色 = 新鲜度（24h 内红色「突发」标、3 天内橙、更旧灰）。
  - 标题（印尼语 headline，虚构事件）、来源徽标 + 发布时间、关键事实 chips（`SAHM-X` `+laba 12%` `dividen`）、热度条（0–100）。
  - 右侧：**可选打标**两个幽灵按钮「相关 👍 / 不相关 👎」+ 一句灰字提示「打标可选，主要靠你是否基于它生成来自动学习」。
  - 一个次要按钮「用它生成 →」（跳回工作台并带入该新闻）。
- 右侧可选抽屉：点标题展开原文摘要 + 结构化「热点卡」字段（headline / key_facts / tickers / angle_hints / freshness / heat）。

### 说明
- 用户与管理员都是只读；管理员额外能看抓取源信息。
- 抗注入是后端行为，UI 不体现，但热点卡字段按结构化展示（呼应 DESIGN §3 M3）。

### ▶ 生成提示词
```
{全局前缀}
"新闻库" (collected news) page, read-only. Top filter bar: search box, multi-select source filter
with fictional source names (财经源A / 财经源B / 财经源C), date range picker, heat sort dropdown, and a "仅看未打标" toggle.
Main area: a vertical list of news cards. Each card has a left color stripe for freshness (red "突发" tag for <24h,
amber for recent, grey for old), a generic Indonesian headline, a source badge + timestamp, a row of fact chips like
"SAHM-X" "+laba 12%" "dividen", a heat progress bar (0-100), on the right two ghost buttons "相关👍" "不相关👎"
with grey hint text "打标可选", and a secondary button "用它生成 →". Clean list, data-dense, professional admin style.
Fully original design, no real company names, no real brand logos.
```

---

## 5. 消耗看板（管理员，数据可视化图表）

### 布局
- 顶部一排 **KPI 统计卡**（4 个）：今日总 token、今日总成本(¥)、活跃用户数、本月配额使用率（环形进度）。数字用等宽字体，配同比涨跌小箭头。
- 中部图表区：
  - **左：折线/面积图** —— 近 30 天每日 token 消耗（按模型分色：Haiku / Sonnet / Opus 三条）。
  - **右：柱状图** —— 按用户 Top 10 消耗排行。
- 下部：**明细表格** —— 列：用户、时间、模型、输入 token、输出 token、成本、场景（生成/评审/清洗）。带分页、按列筛选、导出 CSV 按钮。
- 右上角：时间范围切换（今日 / 7 天 / 30 天 / 自定义）。

### 说明
- 呼应 DESIGN §6 成本护栏：按用户/时间聚合。图表主色用品牌靛蓝，模型区分用靛蓝/青/紫三色梯度。

### ▶ 生成提示词
```
{全局前缀}
Admin "消耗看板" (token usage & cost dashboard) with data-visualization charts. Top row: 4 KPI stat cards
(今日总token, 今日总成本¥, 活跃用户数, 本月配额使用率 as a ring progress), big monospaced numbers with up/down trend arrows.
Middle: left a 30-day area/line chart of daily token usage split by model (Haiku/Sonnet/Opus in indigo/teal/purple),
right a horizontal bar chart of top-10 users by consumption. Bottom: a detailed data table with columns
用户/时间/模型/输入token/输出token/成本/场景, pagination and an export CSV button. Top-right date range switch
(今日/7天/30天). Charts use indigo brand palette. Clean analytics dashboard, professional.
Fully original design, no real company names, no real brand logos.
```

---

## 6. 抓取与配额（管理员）

单页两个分区（Tab 或上下分块）：

### 6.1 抓取源配置
- 表格/卡片：每个源一行 —— 源名称、类型徽标（RSS / 搜索API / Playwright）、URL、抓取频率、上次抓取时间、健康状态（绿点「正常」/ 红点「改版异常」，呼应 DESIGN §7 抓取健康检查）、启用开关、「立即抓取」按钮。
- 顶部「+ 新增抓取源」主按钮 → 弹窗表单（源名、类型、URL、频率、源权重）。
- 一行灰字合规提示：「新增前确认该源 robots/ToS 与版权边界（DESIGN §7）」。

### 6.2 配额与限流
- 表单卡：单用户日 token 限额（数字输入）、超额提醒阈值（%）、异常调用熔断开关 + 触发条件、全局日预算。
- 右侧：当前各用户配额使用进度条列表（用户名 + 进度条 + `8.2k / 20k`）。

### ▶ 生成提示词
```
{全局前缀}
Admin "抓取与配额" page with two sections.
Section 1 "抓取源配置": a table where each row is a crawl source with columns 源名称, a type badge (RSS/搜索API/Playwright),
URL, 抓取频率, 上次抓取时间, a health status dot (green "正常" / red "改版异常"), an enable toggle, and a "立即抓取" button.
A "+ 新增抓取源" indigo primary button on top and a grey compliance hint line.
Section 2 "配额与限流": a form card with 单用户日token限额 number input, 超额提醒阈值%, an 异常调用熔断 toggle, 全局日预算,
and on the right a list of per-user quota usage progress bars like "8.2k / 20k". Professional admin settings UI.
Fully original design, no real company names, no real brand logos.
```

---

## 7. 关键复用组件规范（供各屏一致）

### 7.1 变体卡片 VariantCard（最核心组件）
```
┌─────────────────────────────────────────────┐
│ #1  ⟨88⟩   钩子:悬念 · 结构:故事 · FOMO · IG   │  ← 排名+综合分环+维度标签
│                                               │
│ SAHM-X cetak laba di atas ekspektasi 📈 ...   │  ← 印尼语正文（虚构标的）
│ ...baca caption ini sampai habis 👇           │     (软提示句黄色波浪下划线)
│                                               │
│ 🟢 合规✓   AI味 12/100 · 风格距离 0.18        │  ← 合规+AI味条
│ ─────────────────────────────────────────    │
│ [采用]  [复制]  [编辑]  [重新生成]     未确认  │  ← 操作行
└─────────────────────────────────────────────┘
```
三种合规态徽章：🟢`合规✓`（绿）/ 🟡`软提示·N句待判断`（黄）/ 🔴`禁词命中·已改写`（红）。

### 7.2 调性选择器 ToneSelector
下拉，每项：账号头像 + `@账号名` + 调性描述小字（如「犀利散户体 · 短句 · 大量俚语」）。顶部固定说明条「不同账号语感指纹独立，绝不混用」。

### 7.3 合规徽章 ComplianceBadge / 未确认标记 / 新鲜度标签
统一用 §1.2 色板：成功绿、软提示黄、硬拦截红、未确认灰。

### ▶ 生成提示词（单独出一张组件规范图）
```
{全局前缀}
A UI component spec sheet on a light canvas showing the "VariantCard" component in its three compliance states
side by side: state A green "合规✓", state B amber "软提示·1句待判断" (one sentence in the body has an amber wavy underline),
state C red "禁词命中·已改写". Each card shows rank badge "#1", circular score ring, dimension tags row,
Indonesian body copy, an "AI味 12/100 · 风格距离 0.18" line, and action buttons 采用/复制/编辑/重新生成 with a grey "未确认" tag.
Also show a ToneSelector dropdown with account avatars and tone descriptions. Clean design-system spec layout with labels.
Fully original design, no real company names, no real brand logos.
```

---

## 8. 二期界面（占位，本轮可不出图）
- **突发快线面板**：新闻「突发」入口 → 极简生成 → 机器评审 → **一键人工确认** → 直出（DESIGN §5，快线保留一键确认）。
- **反馈/权重可视化**（内部）：bandit 组合权重、hook 级采用率趋势、软提示命中×采用率监控（R-3）。
- **人工盲评面板**：每周 20–30 条抽样盲评（P1-3 外部校准锚）。

---

## 9. 出图清单（交给 gptimages 2.0）

| # | 界面 | 优先级 | 提示词位置 |
|---|---|---|---|
| 1 | 登录页 | P1 | §2 ▶ |
| 2 | 文案生成工作台（核心） | **P0** | §3 ▶ |
| 3 | 新闻库 | P1 | §4 ▶ |
| 4 | 消耗看板 | P1 | §5 ▶ |
| 5 | 抓取与配额 | P2 | §6 ▶ |
| 6 | 变体卡片组件规范图 | P1 | §7 ▶ |

> 建议出图顺序：先出 **#2 工作台**（定全局风格基准），确认色板/组件后，用同一 §1 前缀批量出其余屏，保证风格统一。深色版可对 #2、#5 各补一张。
