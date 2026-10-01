---
marp: true
theme: default
size: 16:9
lang: zh
paginate: true
title: 从 Prompt 到 Harness —— 一次开源项目体检的三阶段工程化演进
description: 以「智能个人记账管理系统」开源体检为例，走完 Prompt → Context → Harness 三阶段
---

<style>
/* ============ 全局：深色科技感 ============ */
section {
  background-color: #0A0E1A;
  background-image:
    radial-gradient(900px 430px at 10% -10%, rgba(124, 58, 237, .20), transparent 62%),
    radial-gradient(780px 380px at 92% 110%, rgba(16, 185, 129, .10), transparent 60%);
  color: #E7EBF3;
  font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "Noto Sans SC", "Source Han Sans SC", -apple-system, "Segoe UI", sans-serif;
  font-size: 21px;
  line-height: 1.62;
  padding: 50px 58px 96px;
  justify-content: flex-start;
  letter-spacing: .01em;
}
section.phase-p {
  background-image:
    radial-gradient(900px 430px at 10% -10%, rgba(124, 58, 237, .30), transparent 62%),
    radial-gradient(700px 340px at 92% 110%, rgba(124, 58, 237, .08), transparent 60%);
  --phase: #7C3AED;
}
section.phase-c {
  background-image:
    radial-gradient(900px 430px at 10% -10%, rgba(16, 185, 129, .26), transparent 62%),
    radial-gradient(700px 340px at 92% 110%, rgba(124, 58, 237, .10), transparent 60%);
  --phase: #10B981;
}
section.phase-h {
  background-image:
    radial-gradient(900px 430px at 10% -10%, rgba(245, 158, 11, .24), transparent 62%),
    radial-gradient(700px 340px at 92% 110%, rgba(16, 185, 129, .10), transparent 60%);
  --phase: #F59E0B;
}
section.phase-n { --phase: #64748B; }

h1 { font-size: 46px; color: #FFFFFF; margin: 0 0 8px; letter-spacing: .02em; line-height: 1.2; }
h2 {
  font-size: 31px; color: #FFFFFF; margin: 0 0 14px; line-height: 1.25;
  padding-left: 14px; border-left: 5px solid var(--phase, #64748B);
}
h3 { font-size: 21px; color: var(--phase, #94A3B8); margin: 0 0 8px; }
p, li { color: #CBD5E1; }
strong { color: #FFFFFF; }
em { color: var(--phase, #94A3B8); font-style: normal; }
a { color: var(--phase, #94A3B8); }
hr { border: 0; border-top: 1px dashed rgba(255, 255, 255, .12); }

/* 页码移出时间线区域 */
section::after {
  content: attr(data-marpit-pagination);
  position: absolute; right: 26px; top: 16px;
  font-size: 12px; color: #3B4257; letter-spacing: .12em;
}

/* ============ 通用组件 ============ */
code { font-family: "JetBrains Mono", "Fira Code", Consolas, "Courier New", monospace; }
pre {
  font-size: 15px; line-height: 1.5; border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, .10);
  background: #0D1322 !important; padding: 12px 14px !important;
}
.g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.g3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.kp { --k: #7C3AED; } .kc { --k: #10B981; } .kh { --k: #F59E0B; } .kn { --k: #64748B; }
.card {
  background: rgba(255, 255, 255, .045);
  border: 1px solid rgba(255, 255, 255, .09);
  border-left: 4px solid var(--k, #64748B);
  border-radius: 12px; padding: 13px 16px;
}
.card b { display: block; color: var(--k, #94A3B8); font-size: 19px; margin-bottom: 6px; }
.card ul { margin: 0; padding-left: 20px; font-size: 17px; }
.card li { margin: 3px 0; }
.ev {
  display: inline-block; font-size: 13px; padding: 2px 11px; border-radius: 999px;
  border: 1px solid var(--k, #64748B); color: var(--k, #64748B); letter-spacing: .06em;
}
.quote {
  border-left: 4px solid var(--phase, #64748B); padding: 6px 0 6px 14px;
  font-size: 23px; color: #FFFFFF; background: rgba(255, 255, 255, .04); border-radius: 0 8px 8px 0;
}
.muted { color: #7C879B; font-size: 16px; }

/* ============ 底部发光横向时间线 ============ */
nav.tl {
  position: absolute; left: 58px; right: 58px; bottom: 24px; height: 44px;
  display: flex; align-items: flex-start; justify-content: space-between;
}
nav.tl::before {
  content: ""; position: absolute; left: 0; right: 0; top: 11px; height: 2px; border-radius: 2px;
  background: linear-gradient(90deg, #1F2942, #1B2337 55%, #1F2942);
  box-shadow: 0 0 10px rgba(124, 58, 237, .28);
}
nav.tl i {
  position: relative; flex: 1; text-align: center; font-style: normal;
  font-size: 12px; letter-spacing: .16em; color: #39415A;
}
nav.tl i::before {
  content: ""; display: block; width: 12px; height: 12px; border-radius: 50%;
  margin: 6px auto 7px; background: #141B2D; border: 2px solid #26304A;
}
nav.tl i.p { --c: #7C3AED; }
nav.tl i.c { --c: #10B981; }
nav.tl i.h { --c: #F59E0B; }
nav.tl i.done { color: var(--c); }
nav.tl i.done::before {
  background: var(--c); border-color: var(--c);
  box-shadow: 0 0 10px var(--c), 0 0 22px rgba(0, 0, 0, 0);
}
nav.tl i.now { color: #FFFFFF; font-weight: 700; }
nav.tl i.now::before {
  background: var(--c); border-color: #FFFFFF;
  box-shadow: 0 0 14px var(--c), 0 0 30px var(--c); transform: scale(1.3);
}
nav.tl i.fade { color: var(--c); animation: tlFadeTxt 1.8s ease-in-out infinite; }
nav.tl i.fade::before { animation: tlFlick 1.8s ease-in-out infinite; }
@keyframes tlFlick {
  0%, 100% { opacity: 1; box-shadow: 0 0 12px var(--c); }
  45% { opacity: .26; box-shadow: 0 0 0 transparent; }
  70% { opacity: .85; }
}
@keyframes tlFadeTxt { 0%, 100% { opacity: .95; } 45% { opacity: .34; } 70% { opacity: .72; } }
nav.tl.converge::before {
  background: linear-gradient(90deg, #7C3AED, #10B981 50%, #F59E0B);
  box-shadow: 0 0 18px rgba(124, 58, 237, .75), 0 0 18px rgba(245, 158, 11, .55);
}
nav.tl.converge i { color: #FFFFFF; font-weight: 700; }
nav.tl.converge i::before {
  background: var(--c); border-color: #FFFFFF; box-shadow: 0 0 16px var(--c);
}

/* ============ 封面 ============ */
section.cover { justify-content: center; }
section.cover h1 {
  font-size: 60px; margin-bottom: 10px;
  background: linear-gradient(90deg, #7C3AED, #10B981 55%, #F59E0B);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.legend { display: flex; gap: 22px; font-size: 16px; margin-top: 22px; }
.legend span { display: flex; align-items: center; gap: 8px; color: #94A3B8; }
.legend i { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }

/* ============ 目录 ============ */
ol.toc { list-style: none; padding: 0; margin: 0; font-size: 19px; }
ol.toc li {
  display: flex; gap: 14px; align-items: baseline;
  padding: 7px 0; border-bottom: 1px dashed rgba(255, 255, 255, .09);
}
ol.toc b { color: var(--k, #64748B); min-width: 132px; font-size: 18px; }
ol.toc span { color: #94A3B8; }

/* ============ 四象限 ============ */
.quad {
  display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;
  gap: 10px; height: 396px; margin-top: 4px;
}
.q {
  border: 1px dashed rgba(255, 255, 255, .17); border-radius: 12px;
  padding: 14px 17px; background: rgba(255, 255, 255, .03); position: relative;
}
.q b { display: block; font-size: 19px; color: #CBD5E1; margin-bottom: 6px; }
.q p { margin: 0; font-size: 16px; color: #94A3B8; line-height: 1.5; }
.q .pin { position: absolute; right: 14px; top: 12px; font-size: 13px; color: #7C879B; }
.q.self { border: 2px solid #7C3AED; background: rgba(124, 58, 237, .15); box-shadow: 0 0 28px rgba(124, 58, 237, .30); }
.q.self b { color: #C4B5FD; }
.q.goal { border: 2px solid #10B981; background: rgba(16, 185, 129, .10); }
.q.goal b { color: #6EE7B7; }
.axisX { display: flex; justify-content: center; gap: 0; margin-top: 10px; font-size: 14px; color: #64748B; }

/* ============ 三列演进表 ============ */
table.evo { width: 100%; border-collapse: collapse; font-size: 16px; }
table.evo th { padding: 9px 10px; text-align: left; font-size: 19px; border-bottom: 2px solid; }
table.evo th.a { color: #7C3AED; border-color: #7C3AED; }
table.evo th.b { color: #10B981; border-color: #10B981; }
table.evo th.d { color: #F59E0B; border-color: #F59E0B; }
table.evo td {
  padding: 9px 10px; border-bottom: 1px solid rgba(255, 255, 255, .07);
  vertical-align: top; color: #CBD5E1;
}
table.evo td:first-child { color: #94A3B8; white-space: nowrap; font-size: 15px; }

/* ============ 路线图 ============ */
.rm { display: flex; flex-direction: column; gap: 11px; }
.rm .row { display: grid; grid-template-columns: 66px 1fr 300px; gap: 14px; align-items: start; }
.rm .lv {
  font-size: 17px; font-weight: 700; text-align: center; border-radius: 8px;
  padding: 3px 0; border: 1px solid var(--k); color: var(--k); background: rgba(255, 255, 255, .04);
}
.rm .act { font-size: 17px; color: #E2E8F0; }
.rm .why { font-size: 15px; color: #8B95AB; }
</style>

<!-- _class: cover -->
<!-- _paginate: false -->

<span class="ev kn">开源项目体检 · 工程化演进</span>

# 从 Prompt 到 Harness

## 一次开源项目体检的三阶段工程化演进

**项目**：`hechao_2024 / accounting-management-system` —— 智能个人记账管理系统
**底本**：`docs/开源项目改进评估报告.md`（逐项核对 README / .gitignore / git 历史与远程 / 依赖文件 / 目录结构 / docs / 代码注释）

<div class="legend">
  <span><i style="background:#7C3AED;box-shadow:0 0 10px #7C3AED"></i>Prompt 紫 · #7C3AED</span>
  <span><i style="background:#10B981;box-shadow:0 0 10px #10B981"></i>Context 绿 · #10B981</span>
  <span><i style="background:#F59E0B;box-shadow:0 0 10px #F59E0B"></i>Harness 橙 · #F59E0B</span>
</div>

<nav class="tl"><i class="p">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：开场不要急着讲技术。先抛结论——这个项目"功能不差，但工程化几乎为零"，而修好它的过程，恰好就是 AI 编码从 Prompt 走到 Harness 的完整路径。三色记住：紫=提示词，绿=上下文，橙=工具链。
-->

---

<!-- _class: toc phase-n -->

## 目录 · 18 页导航

<ol class="toc">
  <li class="kn"><b>序章 · P1–P5</b><span>总览定位、四象限判定、三阶段地图</span></li>
  <li class="kp"><b>Prompt · P6–P9</b><span>让 AI 直接写功能｜证据 ① 依赖缺陷 · ② import 链｜阶段边界</span></li>
  <li class="kc"><b>Context · P10–P15</b><span>把仓库塞进上下文｜证据 ③ docs 8 篇 · ④ 契约注释 · ⑤ 三个 ad-hoc 脚本</span></li>
  <li class="kh"><b>Harness · P16–P18</b><span>把约定锁进工具链｜清理清单 · P0/P1/P2 路线图 · 时间线收束</span></li>
</ol>

<div class="g3" style="margin-top:18px">
  <div class="card kp"><b>Prompt</b><ul><li>AI 看见：你给的那一句</li><li>产出：代码 + 文档</li></ul></div>
  <div class="card kc"><b>Context</b><ul><li>AI 看见：整个仓库状态</li><li>产出：诊断 + 优先级</li></ul></div>
  <div class="card kh"><b>Harness</b><ul><li>工具看见：每次提交</li><li>产出：可复现的工程状态</li></ul></div>
</div>

<nav class="tl"><i class="p">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：一句话讲清导航——前 5 页是"我们站在哪"，6–9 是"我们怎么让 AI 写代码"，10–15 是"我们怎么让 AI 看仓库"，16–18 是"我们怎么让工具替我们守规矩"。
-->

---

<!-- _class: phase-n -->

## 体检总览：一句话定位

<div class="quote" style="margin-bottom:16px">更像「毕业设计答辩材料」，而不是「开源项目」。</div>

<div class="g2">
  <div class="card kc"><b>强项</b><ul>
    <li><strong>三端完整</strong>：FastAPI 后端 + React Web + uni-app 移动端，AI 记账 / 对话功能跑通</li>
    <li><strong>README 11KB</strong>：功能、技术栈、环境要求、安装步骤、目录树、注意事项齐全，含 .env 模板与真机调试指南</li>
    <li><strong>后端分层清晰</strong>：models / schemas / crud / routers / ai / utils，中文注释质量较好</li>
    <li><strong>docs/</strong> 下成体系的 8 篇后端设计文档</li>
  </ul></div>
  <div class="card kh"><b>短板</b><ul>
    <li><strong>无 License</strong>、<strong>无测试</strong>、<strong>无 CI/CD</strong>、<strong>无社区机制</strong></li>
    <li>存在一处会让新手<strong>按 README 装完跑不起来</strong>的依赖缺陷</li>
    <li>根目录散落大量<strong>个人 / 内部文档</strong>与垃圾文件</li>
    <li>无截图、无 badges、无 FAQ、无 CHANGELOG、无 ROADMAP</li>
  </ul></div>
</div>

<p class="muted" style="margin-top:14px">评估维度：项目内容 · 技术选型 · 工程规范 · 可维护性 · 项目定位（共 5 维，逐项核对可复核文件）</p>

<nav class="tl"><i class="p">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：这页只讲一件事——把"功能"和"工程化"分开看。功能这块他是优等生，工程化这块是零。后面所有证据都是围绕这个落差展开的，别在这里就陷进细节。
-->

---

<!-- _class: quad phase-n -->

## 位置判定：功能完整度 × 工程化完备度

<div class="quad">
  <div class="q"><span class="pin">功能弱 · 工程化强</span><b>模板仓库</b><p>CI / LICENSE / 模板齐全<br>但没有真实业务</p></div>
  <div class="q goal"><span class="pin">功能强 · 工程化强</span><b>目标态</b><p>三端 + AI 可用<br>且能被他人接手、复现、贡献</p></div>
  <div class="q"><span class="pin">功能弱 · 工程化弱</span><b>玩具 Demo</b><p>功能与工程化<br>两头都不成立</p></div>
  <div class="q self"><span class="pin">功能强 · 工程化弱 ← 本项目</span><b>本项目所在</b><p>三端 + AI 功能完整<br>但无协议、无测试、无流水线、无社区机制</p></div>
</div>
<div class="axisX">横轴：功能完整度 →　｜　纵轴：工程化完备度 ↑</div>

<nav class="tl"><i class="p">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：这张图是全场唯一要记住的图。右上角是目标态，本项目卡在右下角——只差纵轴，不差横轴。所以后面三阶段做的事情，本质上都是"把纵轴拉上去"，而不是重写功能。
-->

---

<!-- _class: evo3 phase-n -->

## 三阶段地图：Prompt → Context → Harness

<table class="evo">
<thead>
<tr><th></th><th class="a">① Prompt 紫</th><th class="b">② Context 绿</th><th class="d">③ Harness 橙</th></tr>
</thead>
<tbody>
<tr><td>我在做什么</td><td>把需求一句话交给 AI，让它直接产出</td><td>把整个仓库状态塞进上下文，让它做诊断</td><td>把约定固化成工具与流水线，让它自动生效</td></tr>
<tr><td>AI 拿到什么</td><td>我描述的那一段话</td><td>README / .gitignore / git log / 依赖 / 目录树 / docs / 注释</td><td>每次提交、每次 CI 运行的真实信号</td></tr>
<tr><td>典型产物</td><td>业务代码、接口、设计文档、契约注释</td><td>五维评估报告 + P0/P1/P2 优先级清单</td><td>LICENSE / pytest / CI / 锁依赖 / docker-compose</td></tr>
<tr><td>本项目落点</td><td>docs/ 8 篇文档、routers/ai.py 契约注释</td><td>《开源项目改进评估报告》</td><td>清理清单 + P0/P1/P2 路线图</td></tr>
<tr><td>失效边界</td><td>看不见仓库，装完能不能跑没人知道</td><td>能诊断，但诊断不会自己落地</td><td>约束变硬，前期投入最高</td></tr>
</tbody>
</table>

<p class="muted" style="margin-top:12px">三阶段不是替代关系，是叠加关系：Harness 不会让 Prompt 失效，它只是让 Prompt 的产出<strong>一直成立</strong>。</p>

<nav class="tl"><i class="p done">Prompt</i><i class="c done">Context</i><i class="h done">Harness</i></nav>

<!--
演讲备注：这是地图页。讲的时候把三个颜色点一遍——紫是我说，绿是仓库说，橙是工具说。强调"叠加"这个词，免得听众以为上了 CI 就不用写提示词了。
-->

---

<!-- _class: phase-p -->

## 阶段一 · Prompt：让 AI 直接写功能

<div class="g2">
  <div class="card kp"><b>做法</b><ul>
    <li>需求一句话进，代码 / 文档 / 注释直接出</li>
    <li>人在 loop 里逐轮追问、逐轮改</li>
    <li>产出速度是这一阶段最大的价值</li>
  </ul></div>
  <div class="card kp"><b>Prompt 阶段的产物（本项目）</b><ul>
    <li><code>docs/fastapi-backend/</code> 下 8 篇成体系后端设计文档</li>
    <li><code>fast_backend/routers/ai.py</code> 顶部一大段「三条铁律」契约注释</li>
    <li><code>main.py</code> / <code>ai/llm.py</code> / <code>sql/init_mysql.sql</code> 的头注释</li>
  </ul></div>
</div>

<div class="card kn" style="margin-top:16px"><b>盲区</b><ul>
  <li>AI 只看见「你给的那一句」，<strong>看不见仓库的真实状态</strong> —— 于是「文档写得对」和「装完能跑」是两件事</li>
</ul></div>

<nav class="tl"><i class="p now">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：Prompt 阶段的成果要肯定——8 篇文档和 ai.py 的契约注释质量是真的高，这不是凑数的东西。但要把钩子埋下去：写得漂亮不等于跑得起来，下两页就是证据。
-->

---

<!-- _class: code phase-p -->

## 证据 ① · `requirements.txt` 依赖缺陷 <span class="ev kp">体检快照 · 改造前</span>

<div class="g2">
<div>

```python
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

</div>
<div>

```bash
# 严格照 README 操作
$ pip install -r requirements.txt
$ uvicorn main:app
ImportError: No module named 'langchain_core'
```

<div class="card kh" style="margin-top:12px"><b>结论</b><ul>
  <li>与 README 宣称的<strong>「不配 API Key 仅 AI 不可用，其余功能正常」直接矛盾</strong></li>
  <li>依赖全部 <code>&gt;=</code> 宽松范围，无精确锁定、无 <code>requirements-dev.txt</code>、无 <code>pyproject.toml</code></li>
  <li>uni-app 依赖用了 <code>@dcloudio/...@3.0.0-alpha-…</code> <strong>alpha 版本</strong></li>
  <li>无 Docker / docker-compose 编排</li>
</ul></div>

</div>
</div>

<nav class="tl"><i class="p now">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：这是全场最硬的一页，一定要念命令。pip install 然后 uvicorn，直接 ImportError——新手照着 README 走第一步就死。这句话要说出来："文档是对的，环境是死的。"另外顺带提一嘴 alpha 依赖，那是第二颗雷。
-->

---

<!-- _class: code phase-p -->

## 证据 ② · 顶层 import 链把「可选」变成「必选」

```python
# fast_backend/routers/ai.py —— 顶层导入，非惰性
from langchain_core.messages import HumanMessage, SystemMessage
from ai import memory, chat_chain, analyze_chain, faq_retriever

# fast_backend/ai/llm.py
from langchain_openai import ChatOpenAI

# fast_backend/main.py —— 顶层挂载，导入即触发
app.include_router(ai.router)
```

<div class="card kh" style="margin-top:14px"><b>三个文件串成一条导入链</b><ul>
  <li><code>main.py</code> 挂 ai 路由 → <code>routers/ai.py</code> 顶层 import langchain_core → <code>ai/llm.py</code> import langchain_openai</li>
  <li>只要应用启动，langchain 就是<strong>硬依赖</strong>；<strong>「可选」只是 requirements.txt 里的一行注释，不是代码事实</strong></li>
  <li>修复二选一：<strong>①</strong> 把 langchain-openai / langchain-core / httpx 移入正式依赖；<strong>②</strong> 改成惰性导入，让未安装 AI 依赖时应用仍可启动</li>
</ul></div>

<nav class="tl"><i class="p now">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：点出"注释不是事实"这个判断标准。requirements.txt 写"可选"，代码写"必选"，两者冲突时代码赢。这条也引出后面 Harness 的核心主张：凡是靠注释维持的约定，迟早会被违反。
-->

---

<!-- _class: phase-p -->

## 阶段一边界：能写功能，不能保证可运行

<div class="g3">
  <div class="card kp"><b>能写</b><ul><li>业务代码与接口</li><li>设计文档</li><li>高质量契约注释</li></ul></div>
  <div class="card kn"><b>不能保证</b><ul><li>装完能不能跑</li><li>跨机能不能复现</li><li>契约有没有被遵守</li></ul></div>
  <div class="card kh"><b>典型症状</b><ul><li>依赖写「可选」，代码写成「必选」</li><li>「三条铁律」<strong>依赖人脑遵守，无测试锁死</strong></li></ul></div>
</div>

<div class="quote" style="margin-top:22px">Prompt 阶段的天花板 = 单点产出质量，不是工程状态。</div>

<p class="muted" style="margin-top:14px">要突破这个天花板，得先让 AI 看见仓库 —— 进入 Context 阶段。</p>

<nav class="tl"><i class="p now">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：阶段收尾页。一句话总结"能写≠能跑"，然后明确转场：接下来不是让 AI 写更多，而是让 AI 看更多。这里可以停一拍，让听众换换气。
-->

---

<!-- _class: phase-c -->

## 阶段二 · Context：把整个仓库塞进上下文

<div class="g2">
  <div class="card kc"><b>评估方式（逐项核对）</b><ul>
    <li><code>README.md</code></li>
    <li><code>.gitignore</code></li>
    <li><code>git log</code> / <code>git remote -v</code> / <code>git ls-files</code></li>
    <li>依赖文件（<code>requirements.txt</code>）</li>
    <li>目录结构</li>
    <li><code>docs/</code> 全部文档</li>
    <li>代码注释（<code>main.py</code> / <code>ai/llm.py</code> / <code>init_mysql.sql</code>）</li>
  </ul></div>
  <div class="card kn"><b>未验证项（诚实标注）</b><ul>
    <li>Gitee 页面的 <strong>star / fork / issue 活跃度</strong>、推荐位与访问量 —— 本地看不到，需补充仓库主页截图或数量</li>
    <li>不因为拿不到就猜，直接在报告里标注为「未验证」</li>
  </ul></div>
</div>

<div class="card kc" style="margin-top:16px"><b>这一阶段的关键动作</b><ul>
  <li>不是"多写几句提示词"，而是把<strong>仓库的真实状态</strong>变成上下文 —— 让 AI 从"听你说"变成"看证据说"</li>
</ul></div>

<nav class="tl"><i class="p fade">Prompt</i><i class="c now">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：转场页，紫色节点开始闪烁变暗。这一页要讲"未验证项"——这是专业性的体现：拿不到的数据宁可标未验证，也不要编。很多评估毁在这一条上。
-->

---

<!-- _class: code phase-c -->

## 证据 ③ · `docs/` 8 篇成体系后端设计文档

<div class="g2">
<div>

```text
docs/
└── fastapi-backend/
    ├── 00-README.md
    ├── 01-工程骨架与环境.md
    ├── 02-数据库设计.md
    ├── 03-通用组件.md
    ├── 04-业务接口规范.md
    ├── 05-AI接口规范.md
    ├── 06-AI模块设计.md
    ├── 07-任务与部署.md
    ├── 08-迁移手册.md
    └── 10-实现骨架.md
```

</div>
<div>

```text
主要依据文件（可复核）
  README.md                     无截图与 badges
  .gitignore                    缺 .claude/ 等条目
  git log --oneline             10 条提交 · 双根提交 · 无 tag
  git remote -v                 origin 指向 GitHub 另一仓库
  fast_backend/requirements.txt langchain-openai 被注释
  ai/llm.py · routers/ai.py     顶层 import langchain 依赖
  git ls-files                  196 个文件，无测试/CI/LICENSE
  docs/ · .impeccable/          目录清单
```

</div>
</div>

<nav class="tl"><i class="p done">Prompt</i><i class="c now">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：8 篇文档是真资产，要夸。但注意右边那份"依据文件清单"——这才是 Context 阶段的精髓：每一条结论后面都挂着一个可复核的文件路径。没有这份清单，评估就只是观点。
-->

---

<!-- _class: code phase-c -->

## 证据 ④ · `routers/ai.py` 契约注释 <span class="ev kc">人工维护的上下文</span>

```python
"""AI 助手路由 — /api/ai（17 个端点骨架，契约见 10-实现骨架.md §六）

⚠️ 本模块返回裸 JSON，不套 {code,message,data} 信封（05 §0 铁律）。

三条铁律（违反即前端崩）：
1. 一律裸返回；业务失败统一 return ai_error("中文")（HTTP 200），
   勿抛 HTTPException（会被全局异常处理器包成 Result 信封，破坏裸契约）；
2. 会话/消息时间戳是 int 毫秒，不是 ISO 字符串（前端 Date.now() 直接比对）；
3. SSE 事件行 data: {"type":"content"|"done"|"error",...}\n\n（6.8）。

⚠️ 路由注册顺序：/sessions/batch-delete 必须在 /sessions/{session_id} 之前，
   Starlette 按注册顺序匹配，否则 "batch-delete" 会被当成 session_id 吃掉。
"""
```

<div class="card kh" style="margin-top:12px"><b>结构性风险</b><ul>
  <li>注释质量很高，但它是<strong>「依赖人脑遵守」的约定</strong> —— 没有一行测试锁死它</li>
  <li>契约写在注释里 = 契约的 enforcement 在人，不在机器</li>
</ul></div>

<nav class="tl"><i class="p done">Prompt</i><i class="c now">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：这段注释念一遍三条铁律，听众会笑——写得这么细，为什么还会出问题？答案就是下一条：因为它只是注释。这张是 Context 阶段最有说服力的一页，也是引出 Harness 最好的伏笔。
-->

---

<!-- _class: phase-c -->

## Context 的产出：五维评估报告

<div class="g3">
  <div class="card kc"><b>① 项目内容</b><ul><li>README 11KB 是强项</li><li>无截图 / 无 badges</li><li>根目录散落个人文档与重复 md</li></ul></div>
  <div class="card kc"><b>② 技术选型</b><ul><li>FastAPI + SQLAlchemy 2.0 + MySQL 8 + React 18 + uni-app</li><li>依赖缺陷、无锁、alpha 依赖、无编排</li></ul></div>
  <div class="card kc"><b>③ 工程规范</b><ul><li>提交遵循 Conventional Commits</li><li>无 LICENSE、无 tag、双根提交、origin 误指</li></ul></div>
</div>
<div class="g2" style="margin-top:14px">
  <div class="card kc"><b>④ 可维护性</b><ul><li>分层清晰、命名一致</li><li>测试完全缺失、CI/CD 完全缺失、契约靠人脑</li></ul></div>
  <div class="card kc"><b>⑤ 项目定位</b><ul><li>AI 自然语言记账差异化明确</li><li>无目标用户、无 ROADMAP、无 demo、无社区机制</li></ul></div>
</div>

<p class="muted" style="margin-top:12px">五个维度全部给出「现状判断 + 差距点 + 具体改进动作」，并汇总为下方 P0/P1/P2 优先级清单。</p>

<nav class="tl"><i class="p done">Prompt</i><i class="c now">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：五维不用逐条念，挑两个讲透——③ 工程规范的"无 LICENSE"和 ④ 可维护性的"测试为零"。其余让听众自己看，节奏会舒服很多。
-->

---

<!-- _class: phase-c -->

## 阶段二边界：AI 能诊断，诊断不会自己落地

<div class="g2">
  <div class="card kn"><b>Context 做到了什么</b><ul>
    <li>从"我觉得哪里不对"变成"哪一行不对"</li>
    <li>给出可复核的依据文件路径</li>
    <li>给出 P0 / P1 / P2 优先级</li>
  </ul></div>
  <div class="card kh"><b>Context 做不到什么</b><ul>
    <li><strong>报告写出来 ≠ 仓库变好</strong></li>
    <li>诊断与落地之间，缺一层「会被自动检查的机制」</li>
    <li>已有的 3 个 ad-hoc 脚本就是证据：验证过一次，没变成资产</li>
  </ul></div>
</div>

<div class="quote" style="margin-top:22px">Context 让 AI 说对话，Harness 让工具做对事。</div>

<nav class="tl"><i class="p done">Prompt</i><i class="c now">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：这张是转折枢纽。前半句肯定 Context（诊断质量高），后半句捅破它（诊断不会自己落地）。"会被自动检查的机制"这个短语要咬清楚，它就是 Harness 的定义。
-->

---

<!-- _class: code phase-c -->

## 证据 ⑤ · 3 个 `_*_check / verify` 脚本 <span class="ev kc">测过一次，没成资产</span>

<div class="g2">
<div>

```bash
$ ls fast_backend/_*.py
_check_finance_ctx.py    # 验证 AI 财务上下文
_test_monthly_api.py     # /api/statistics/monthly 一次性接口测试
_verify_stats.py         # Decimal 序列化 + 统计 SQL 编译验证
```

```python
# _verify_stats.py —— 典型 ad-hoc：打印出来靠人眼看
print("pydantic json-mode Decimal:",
      M(x=Decimal("8000.00")).model_dump(mode="json"))
```

</div>
<div>

<div class="card kn"><b>为什么它们不是测试</b><ul>
  <li>文件名以 <code>_</code> 开头，<strong>不会被 pytest 收集</strong></li>
  <li>靠 <code>print</code> + 人眼比对，<strong>无断言、无退出码约定</strong></li>
  <li>需要真实 MySQL / 真实 JWT，<strong>跑不进 CI</strong></li>
  <li>用完留在仓库里，<strong>反而成为结构噪音</strong></li>
</ul></div>
<div class="card kh" style="margin-top:12px"><b>改造动作</b><ul>
  <li>把它们改造为正式测试（覆盖 auth / record CRUD / category / statistics 的 happy path + 鉴权失败路径），或<strong>用完即删</strong></li>
  <li>配 <code>pytest.ini</code> + coverage</li>
</ul></div>

</div>
</div>

<nav class="tl"><i class="p done">Prompt</i><i class="c now">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：三个脚本是"伪测试"的绝佳样本——看起来有测试，实际零保障。重点讲 `_test_monthly_api.py` 这名字最像测试、最容易被误当成测试。判断标准很简单：CI 会跑它吗？不会就不是测试。
-->

---

<!-- _class: phase-h -->

## 阶段三 · Harness：把约定锁进工具链

<div class="g2">
  <div class="card kh"><b>先清结构噪音（体检清单）</b><ul>
    <li><strong><code>fast_backend_接口完整版/</code></strong> —— 磁盘 167 个文件、<strong>未入 git 的僵尸目录</strong>，易被误判为权威后端版本</li>
    <li>根目录与 <code>fast_backend/</code> 下<strong>各一个 <code>nul</code></strong>（Windows 重定向产物）</li>
    <li><code>question_text.txt</code> 空文件；<code>notes.md</code>、<code>task_plan.md</code> 开发记录入库</li>
    <li><code>personal-ledger-uniapp/.impeccable/</code> agent 产物入库</li>
    <li><code>10-实现骨架.md</code> 与 docs 下同名文件 <strong>MD5 完全一致</strong></li>
    <li><code>origin</code> 远程指向 GitHub 另一仓库 → <strong>误推风险</strong></li>
    <li><code>.gitignore</code> 漏 <code>.claude/</code>、<code>面试准备_*.md</code>、<code>开题报告/_build*</code></li>
  </ul></div>
  <div class="card kh"><b>再补工程化束具</b><ul>
    <li><strong>LICENSE</strong>（推荐 MIT）+ README 顶部声明</li>
    <li><strong>pytest 最小测试集</strong> + <code>pytest.ini</code> + coverage</li>
    <li><strong>CI 流水线</strong>：lint → 后端 pytest → 前端 build</li>
    <li><strong>锁依赖</strong>：<code>requirements-dev.txt</code> / <code>pyproject.toml</code> + lock</li>
    <li><strong>docker-compose</strong> 一键体验（MySQL + 后端 + 前端）</li>
    <li>CONTRIBUTING / ISSUE+PR 模板 / ROADMAP / CHANGELOG / 打 tag</li>
    <li>README 增补「生产部署」：Nginx 反代 + systemd + 备份 + HTTPS</li>
  </ul></div>
</div>

<nav class="tl"><i class="p done">Prompt</i><i class="c fade">Context</i><i class="h now">Harness</i></nav>

<!--
演讲备注：先清后补，顺序不能反。僵尸目录这条最有画面感——167 个文件躺在磁盘上不进 git，任何人 clone 下来都会以为 fast_backend 是真后端。清理完再谈 CI，不然流水线会去 lint 一堆垃圾。
-->

---

<!-- _class: roadmap phase-h -->

## 落地路线图：P0 / P1 / P2

<div class="rm">
  <div class="row kh"><div class="lv">P0</div><div class="act">修复 <code>requirements.txt</code> 缺失 langchain 依赖（或改惰性导入）</div><div class="why">新手按 README 装完起不来，第一印象杀手</div></div>
  <div class="row kh"><div class="lv">P0</div><div class="act">添加 LICENSE（MIT）</div><div class="why">无协议 = 不可开源，他人无法合法使用 / 修改 / 分发</div></div>
  <div class="row kh"><div class="lv">P0</div><div class="act">清理仓库：删 <code>fast_backend_接口完整版/</code>、<code>nul</code>、重复 md、个人资料；删 <code>origin</code> 远程；补 <code>.gitignore</code></div><div class="why">消除结构噪音与误推风险</div></div>
  <div class="row kp"><div class="lv">P1</div><div class="act">建 pytest 最小测试集 + Gitee / GitHub CI 流水线（lint → test → build）</div><div class="why">可维护性与可信度的最低门槛</div></div>
  <div class="row kp"><div class="lv">P1</div><div class="act">README 加截图 / badges / demo 路径 + docker-compose</div><div class="why">转化与体验，视觉型项目没有截图是致命短板</div></div>
  <div class="row kc"><div class="lv">P2</div><div class="act">Issue / PR 模板 + CONTRIBUTING + ROADMAP + tag / CHANGELOG</div><div class="why">社区化长期建设，给潜在贡献者一个接手的支点</div></div>
</div>

<p class="muted" style="margin-top:14px">P0 全是可在一小时内完成的动作，但每一条都卡在「别人愿不愿意用你的项目」上。</p>

<nav class="tl"><i class="p done">Prompt</i><i class="c done">Context</i><i class="h now">Harness</i></nav>

<!--
演讲备注：路线图别平铺念。三条 P0 是"能不能被用"，两条 P1 是"好不好用"，一条 P2 是"能不能长大"。最后补一句：P0 三条加起来不到一小时，但一直没人做——因为没有人、也没有工具在提醒你做。
-->

---

<!-- _class: timeline phase-h -->

## 18 页收束：三阶段时间线

<div class="g3">
  <div class="card kp"><b>Prompt 紫 · 把需求说清楚</b><ul><li>产出：代码 + 文档 + 契约注释</li><li>代价：看不见仓库 → 装完能不能跑没人知道</li></ul></div>
  <div class="card kc"><b>Context 绿 · 把仓库塞进上下文</b><ul><li>产出：五维诊断 + P0/P1/P2 清单</li><li>代价：能诊断，不会自己落地</li></ul></div>
  <div class="card kh"><b>Harness 橙 · 把约定锁进工具链</b><ul><li>产出：LICENSE / 测试 / CI / 锁依赖 / 编排</li><li>代价：前期投入最高，但一次投入长期生效</li></ul></div>
</div>

<div class="quote" style="margin-top:26px">AI 编码的瓶颈，从来不在「写」，而在「让写出来的东西一直成立」。</div>

<p class="muted" style="margin-top:14px">本项目体检的最后一公里：不是再写一版提示词，而是让 LICENSE、测试、CI、锁依赖替你把约定守住。</p>

<nav class="tl converge"><i class="p">Prompt</i><i class="c">Context</i><i class="h">Harness</i></nav>

<!--
演讲备注：收尾页。三色节点全部点亮并收束成一条线。最后那句要慢一点念——"一直成立"是整场的题眼。念完停两秒再收，不要急着说谢谢。
-->
