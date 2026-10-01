# 设计 Spec · 开源体检 PPT（浅色版）

> 本文件是三个设计方向 subagent 的**唯一共同输入**。三个方向独立工作、互不参考，只看本 spec。
> 内容与数据**一个标点都不许改**，只换视觉与排版。

---

## 1. 这是什么

一份 **18 页的技术复盘演示文稿**，主题是「以开源项目体检为例，讲清 AI 编码协作的三个阶段
Prompt → Context → Harness」。

原始版本是一份深色科技风的 Marp deck（背景 `#0A0E1A`，紫/绿/橙三阶段色，底部发光时间线）。
**本次任务是把同一批内容重做成浅色、明亮、简洁、留白充足的版本，并最终导出 .pptx。**

内容底本：`docs/开源项目改进评估报告.md`（对 `hechao_2024/accounting-management-system`
逐项核对 README / .gitignore / git 历史与远程 / 依赖文件 / 目录结构 / docs / 代码注释 得出）。

## 2. 受众与使用场景

- **主场景**：答辩 / 技术分享会现场投屏，观众距离 5-10 米，投影仪亮度一般、对比度差
- **次场景**：会后发 PDF / PPTX 给评审老师单独翻看，可能在笔记本上近距离阅读
- **推论**：浅色背景在投影仪上比深色更稳；字号必须够大；信息密度要低，不能靠细节堆信息
- **情感基调**：冷静、专业、可信、克制。**不要兴奋感、不要科技炫技、不要营销腔**
- **关键词**：编辑部式的秩序感 / 大量的呼吸感 / 层级清晰 / 一眼看懂论点

## 3. 硬约束（用户原话，必须遵守）

1. **浅色主题**：浅灰或纯白背景 + 高对比深色文字
2. **留白充足**
3. **去除渐变、阴影等厚重装饰**
4. **配色控制在 3 种以内**
5. **整体清爽现代**
6. **页面尺寸 16:9，1920×1080**，每屏内容完整不溢出
7. **每页信息密度适中**，标题层级清晰，重点内容加粗或用强调色突出，避免大段文字堆砌
8. **中文字体用无衬线**
9. **保留全部文字内容与数据不变**

## 4. 输出格式（三方向统一，否则无法横向对比）

- 每个方向产出 **2 个独立 HTML 文件**，每个文件 = 1 页，画布 **1920×1080 固定**
- 单文件、纯 HTML+CSS（CSS 内联在 `<style>` 里），不引外部图片、不用 React
- **必须实现 auto-fit 缩放**：页面按视口等比缩放并居中于深灰信纸底（letterbox），
  保证用户在任意窗口尺寸下都能看到完整一页。参考实现见本文件末尾「技术骨架」
- **每页不要自己写页码 / 进度条 / 时间线**（页码由 deck 外壳统一承载，写了会打架）
- 允许引 Google Fonts 的 Noto Sans SC（有系统字体兜底），但**不允许**把关键设计
  建立在某个必须联网才能拿到的字体上

## 5. 两个展示页的逐字文案（一个字都不能改）

### 页面 1 · 封面

```
眉标    开源项目体检 · 工程化演进
主标题  从 Prompt 到 Harness
副标题  一次开源项目体检的三阶段工程化演进
项目    hechao_2024 / accounting-management-system —— 智能个人记账管理系统
底本    docs/开源项目改进评估报告.md
        逐项核对 README / .gitignore / git 历史与远程 / 依赖文件 / 目录结构 / docs / 代码注释
三阶段   Prompt 紫 #7C3AED   Context 绿 #10B981   Harness 橙 #F59E0B
```

### 页面 2 · 证据 ①

```
标题    证据 ① · requirements.txt 依赖缺陷
标签    体检快照 · 改造前
```

代码块 A（语言 `ini`，逐字）：

```
# fast_backend/requirements.txt
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
sqlalchemy[asyncio]>=2.0.0
aiomysql>=0.2.0
python-dotenv>=1.0.0
pydantic>=2.0.0
bcrypt>=4.0.0
PyJWT>=2.8.0
python-multipart>=0.0.6
# langchain-openai>=0.1.0   # ← 被注释，标注「可选依赖」
```

代码块 B（语言 `bash`，逐字）：

```
# 严格照 README 操作
$ pip install -r requirements.txt
$ uvicorn main:app
ImportError: No module named 'langchain_core'
```

结论（4 条，逐字）：

```
结论
· 与 README 宣称的「不配 API Key 仅 AI 不可用，其余功能正常」直接矛盾
· 依赖全部 >= 宽松范围，无精确锁定、无 requirements-dev.txt、无 pyproject.toml
· uni-app 依赖用了 @dcloudio/...@3.0.0-alpha-… alpha 版本
· 无 Docker / docker-compose 编排
```

> 说明：">=" 里的 `>` 必须正确转义显示，不能被当成 HTML 标签吃掉。

## 6. 18 页全貌（仅为让三个方向理解整体节奏，本次只需做上面 2 页）

1 封面 · 2 目录 · 3 体检总览（强项/短板）· 4 四象限定位 · 5 三阶段地图（3 列表格）
6 阶段一 Prompt · 7 证据① 依赖缺陷（代码页）· 8 证据② 顶层 import 链（代码页）· 9 阶段一边界
10 阶段二 Context · 11 证据③ docs 8 篇（代码页）· 12 证据④ 契约注释（代码页）· 13 五维评估 · 14 阶段二边界 · 15 证据⑤ 三个 ad-hoc 脚本（代码页）
16 阶段三 Harness · 17 P0/P1/P2 路线图 · 18 时间线收束

节奏特征：**每 4 页一个循环**——阶段主张 → 代码证据 → 代码证据 → 边界收束。
所以这套版式必须同时容纳「大标题主张页」「双栏代码证据页」「三列对比表」「卡片矩阵」四种形态。

## 7. 视觉母题（决定 form 的种子，不许答不出）

这份内容的母题不是「科技」，是 **「证据链」**——通篇在拿文件路径、命令行输出、代码注释
作为论据。所以视觉上应该有一个**系统性的「标注 / 索引」语言**：栏目名、文件路径、
证据编号、状态标签。它替代掉原来那套发光时间线的装饰性表达。

## 8. 反 slop 禁区（本任务特别容易犯的）

- ❌ 紫蓝渐变、玻璃拟态、彩色投影阴影
- ❌ 每个标题配 emoji 或装饰 icon
- ❌ 圆角卡片 + 左侧彩色 border accent 一路铺满（除非是本方向刻意的语言，且要做得像有意图的）
- ❌ Inter / Roboto / Arial 当 display 字体（正文可用，标题不用）
- ❌ 用色块假装图片；本任务不需要任何图片，也不许留空图片位
- ✅ 中文排印用「」引号
- ✅ `text-wrap: pretty`、CSS Grid、`oklch()` 之类细节，是「像真设计师」的信号
- ✅ 一个细节做到 120%，其他 80%（例如把代码块的呈现做到极致，其他克制）

## 9. 可读性硬底线（任何风格温度都不豁免）

- 正文 ≥ 18px（1920 画布下，实际渲染要更接近 20-22px）
- 标签 / 注释 ≥ 14px
- 正文对比度 ≥ 4.5:1
- 留白必须是**构图**（每页有明确视觉锚点、视线有落点），不是内容缺席
  —— 反面教材：「大片死白 + 微缩字号」，第一眼像页面没渲染完
- **每页只有 1 个视觉焦点**，其他元素都退后

## 10. 技术骨架（两个 HTML 都用这个外壳）

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>…</title>
<style>
  html,body{margin:0;height:100%;background:#2A2D33;overflow:hidden}
  /* 固定画布 1920×1080，按视口等比缩放居中 */
  #stage{width:1920px;height:1080px;position:absolute;left:50%;top:50%;
         transform-origin:center center;
         transform:translate(-50%,-50%) scale(var(--s,1));overflow:hidden}
  /* …本方向的样式… */
</style>
</head>
<body>
<div id="stage">
  <!-- 页面内容，全部在 1920×1080 内，绝不允许溢出 -->
</div>
<script>
  (function(){
    var fit=function(){
      var s=Math.min(window.innerWidth/1920, window.innerHeight/1080);
      document.getElementById('stage').style.setProperty('--s', s);
    };
    fit(); window.addEventListener('resize', fit);
  })();
</script>
</body>
</html>
```

## 11. 交付要求

- 文件路径：
  - `开源体检PPT/design-demos/<方向代号>-01-cover.html`
  - `开源体检PPT/design-demos/<方向代号>-02-evidence-01.html`
- 写完后**不要自己截图**（由主流程统一截，保证三方向截图口径一致）
- 不要写 README、不要写额外文件
