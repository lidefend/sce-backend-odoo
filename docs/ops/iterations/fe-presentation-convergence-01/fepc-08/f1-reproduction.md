# FEPC-08 / F1 复现记录与暂停裁定

状态：**待核实、暂不修复；根因未知；不标记已解决**。用户于本轮明确要求停止额外复现成本，获得匹配 Windows 浏览器、缩放比例和具体帮助入口后再复查。

## 身份与范围

GitHub main / 本地基线 `27de8c2769d4c02a6e1076ad3f60fb9aa9f77e17`（PR758 后），审计分支 `audit/fepc-08-help-popover-diagnosis`。运行时声明 `3f46dd7eba9f351386fee446151ee9eb545d56a4`，版本 `1.0.0-rc.20`，构建 SHA256 `5690cde92298c32cb9e5e2c578380fe17e07bd7af21944bf72a42dbe577b027a`。两种身份分别记录，不推断部署错误。

目标 `/t/demo/r/project.project/15`，sc_demo，既有账号用户41 / business_full / 公司1。Linux headless Chromium147.0.7727.15，1440×1000，DPR1，visualViewport.scale1。没有 Windows 仿真；Windows 浏览器版本、缩放、显示缩放和具体字段尚未确认。

人工反馈（本轮原话）：“点击问号弹出提示文档，然后滚动内容区，弹窗提示飘在面上直接错位了”。这是人工观察，不是本机复现结果，也不是单纯要求滚动时关闭。

## 复现路径与结果

复用 FEPC-01 的“经营方式”问号；当前 DOM 无 aria-label 为“项目状态”的帮助按钮，不能证明与人工观察入口完全一致。

1. 打开项目15，点击经营方式问号：trigger y453，popup root y483，内容 y491。静止600ms保持。
2. 内容区 `MAIN#main-content.router-host` 滚动140px：即时采样 trigger313 / popup483，稳定后313 /343。捕获过短暂定位滞后，未证明与 Windows 现象同因。
3. 真实鼠标滚轮160px：50ms与500ms采样均保持 root差30px / 内容差38px。
4. 连续10次45px滚轮、间隔50ms：72次 rAF 采样 root差均30px。未复现持续错位；主线程rAF不保证捕获所有合成器绘制帧。
5. 触发控件滚出视口：trigger−437 / popup−407；expanded仍true，但两者均不可见。
6. 真实鼠标点击空白(30,900)，命中 nav-shell：浮层关闭。与历史“空白未关闭”记录不同；历史事件序列不明，不能倒推其原因。
7. 点击实际“经营概况”页签，再点击“预算差异(台账)”与“最新进度(%)”帮助：每次只存在一个浮层。打开“描述”帮助后点击“设置”：浮层消失。页签点击同时触发外部mousedown，不能分离证明纯隐藏生命周期。
8. 完整文档导航到已有台账action588：浮层无残留。SPA路由未验证。

自然document高度与视口均1000，window.scrollBy未产生位移，因此页面外层滚动不能记为通过。没有注入可滚动页面样式。

## 证据和执行限制

入口 [f1-measurements.json](f1-measurements.json) 索引5次探针原始脱敏输出与哈希；[source-identity.json](source-identity.json) 绑定运行时SHA源码。每个attempt配套实际探针和认证状态摘要。密码通过隐藏输入、token通过进程管道使用，不保存凭据、会话、完整HTML或业务响应。

attempt1在其他帮助选择器超时；attempt2其他帮助/页签未实际执行；attempt3“计划与责任”不存在而超时；attempt4改用DOM真实页签完成剩余交互；attempt5按人工补充追加连续滚轮，之后停止。失败原样保留，不算产品失败，不伪装通过。

浏览器只允许经既有API链核查的只读intent；每次启动阻止global.message.conversations，产生一条ERR_BLOCKED_BY_CLIENT控制台错误，属于探针限制。未记录新的首页指标；system.init仅用于页面必要初始化并投影身份。没有付款点击、业务写入、产品修改、合并或部署。

历史引用：上级 [findings.json](../findings.json) F1、[evidence-index.md](../evidence-index.md)；API01/02R归档位于仓库.git/codex-recovery/FEPC-07R/merge-closeout/files，原文件不改动。当前记录不改写历史测量。
