#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = process.cwd();
const OUTPUT = path.resolve(process.env.SC_FINAL_ACCEPTANCE_OUTPUT || '.runtime/final-acceptance');
const sha = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim();
const GEOMETRY_ROOT = path.resolve(process.env.SC_FINAL_GEOMETRY_ROOT || '.runtime/final-acceptance/geometry-current');
const FORM_ROOT = path.resolve(process.env.SC_FINAL_FORM_ROOT || `.runtime/final-acceptance/${sha.slice(0, 7)}/form`);
const FULL_ROOT = path.resolve(process.env.SC_FINAL_FULL_ROOT || '.runtime/final-acceptance/full-route-current-v2');
const COLOR_ROOT = path.resolve(process.env.SC_FINAL_COLOR_ROOT || '.runtime/final-acceptance/color-role-current');
const GEOMETRY_JSON = path.join(GEOMETRY_ROOT, 'geometry-scroll-audit.json');
const GEOMETRY_HTML = path.join(GEOMETRY_ROOT, 'geometry-scroll-audit.html');
const SPACING_JSON = path.join(GEOMETRY_ROOT, 'spacing-geometry-audit.json');
const SPACING_HTML = path.join(GEOMETRY_ROOT, 'spacing-geometry-audit.html');
const FORM_JSON = path.join(FORM_ROOT, 'form-audit.json');
const FULL_JSON = path.join(FULL_ROOT, 'full-product-audit.json');
const COLOR_JSON = path.join(COLOR_ROOT, 'report.json');
const BEFORE_FORM_JSON = path.resolve('.runtime/before-form-audit.json');
const BEFORE_FULL_ROOT = path.resolve('.runtime/frontend-system-audit/baseline/full-product');
const BEFORE_OUTPUT = path.join(OUTPUT, 'before-baseline');

const readJson = async (file) => JSON.parse(await fs.readFile(file, 'utf8'));
const escapeHtml = (value) => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;');

await fs.mkdir(OUTPUT, { recursive: true });
await fs.mkdir(BEFORE_OUTPUT, { recursive: true });
await fs.cp(BEFORE_FULL_ROOT, path.join(BEFORE_OUTPUT, 'full-product'), { recursive: true });
await Promise.all([
  fs.cp(GEOMETRY_ROOT, path.join(OUTPUT, 'geometry-evidence'), { recursive: true, force: true }),
  fs.cp(FORM_ROOT, path.join(OUTPUT, 'form-evidence'), { recursive: true, force: true }),
  fs.cp(FULL_ROOT, path.join(OUTPUT, 'full-product-evidence'), { recursive: true, force: true }),
  fs.cp(COLOR_ROOT, path.join(OUTPUT, 'color-evidence'), { recursive: true, force: true }),
]);
await Promise.all([
  [GEOMETRY_JSON, 'geometry-scroll-audit.json'], [GEOMETRY_HTML, 'geometry-scroll-audit.html'],
  [SPACING_JSON, 'spacing-geometry-audit.json'], [SPACING_HTML, 'spacing-geometry-audit.html'],
  [FORM_JSON, 'form-audit.json'], [path.join(FORM_ROOT, 'form-audit.html'), 'form-audit.html'],
  [FULL_JSON, 'full-product-audit.json'], [path.join(FULL_ROOT, 'full-product-audit.html'), 'full-product-audit.html'],
  [COLOR_JSON, 'color-role-audit.json'],
].map(([source, target]) => fs.copyFile(source, path.join(OUTPUT, target))));
for (const sourceRoot of [FORM_ROOT, FULL_ROOT]) {
  for (const name of await fs.readdir(sourceRoot)) {
    if (/\.png$/i.test(name)) await fs.copyFile(path.join(sourceRoot, name), path.join(OUTPUT, name));
  }
}

const [geometry, spacing, form, fullProduct, color, beforeForm] = await Promise.all([
  readJson(GEOMETRY_JSON),
  readJson(SPACING_JSON),
  readJson(FORM_JSON),
  readJson(FULL_JSON),
  readJson(COLOR_JSON),
  readJson(BEFORE_FORM_JSON),
]);
const sourceIdentities = {
  geometry: geometry.source_sha,
  spacing: spacing.source_sha,
  form: form.source_sha,
  full_product: fullProduct.source_sha,
  color: color.source?.provenance?.head,
};
for (const [source, sourceSha] of Object.entries(sourceIdentities)) {
  if (sourceSha !== sha) throw new Error(`${source} evidence SHA mismatch: ${sourceSha || '(missing)'} != ${sha}`);
}
const dirtyFiles = execFileSync('git', ['status', '--short'], { cwd: ROOT, encoding: 'utf8' }).trim().split('\n').filter(Boolean);
const visualSupervisorDecision = String(process.env.SC_VISUAL_SUPERVISOR_DECISION || 'pending').trim();
if (!['pending', 'accepted', 'rejected'].includes(visualSupervisorDecision)) {
  throw new Error(`invalid SC_VISUAL_SUPERVISOR_DECISION=${visualSupervisorDecision}`);
}

const failures = [
  ...(geometry.failures || []).map((item) => ({ source: 'geometry-scroll-audit', ...item })),
  ...(spacing.failures || []).map((item) => ({ source: 'spacing-geometry-audit', ...item })),
  ...(form.issues || []).map((item) => ({ source: 'form-audit', ...item })),
  ...(fullProduct.failures || []).map((item) => ({ source: 'full-product-audit', ...item })),
  ...(color.failures || []).map((item) => ({ source: 'color-role-audit', ...item })),
];
const failureList = {
  schema: 'frontend-professional-failure-list.v1',
  generated_at: new Date().toISOString(),
  source_sha: sha,
  current_failures: failures,
  current_p0: failures.filter((item) => item.severity === 'P0').length,
  current_p1: failures.filter((item) => item.severity === 'P1').length,
  baseline_negative_findings: beforeForm.issues || [],
  visual_supervisor_decision: visualSupervisorDecision,
};
await fs.writeFile(path.join(OUTPUT, 'failure-list.json'), `${JSON.stringify(failureList, null, 2)}\n`, 'utf8');
await fs.writeFile(path.join(OUTPUT, 'failures.json'), `${JSON.stringify(failureList, null, 2)}\n`, 'utf8');

const pairs = [
  { template: '首页/工作台', before: 'before-baseline/full-product/representative-home-project_manager---1440.png', after: 'representative-home-project_manager---1440.png' },
  { template: '通用列表', before: 'before-baseline/full-product/representative-general-contract-project_manager-354-1440.png', after: 'representative-general-contract-project_manager-354-1440.png' },
  { template: '只读表单', before: 'before-baseline/form-final-readonly-1440.png', after: 'form-final-readonly-1440.png' },
  { template: '新建/移动表单', before: 'before-baseline/form-final-create-390.png', after: 'form-final-create-390.png' },
  { template: '关系弹窗', before: 'before-baseline/form-final-relation-dialog-390.png', after: 'form-final-relation-dialog-390.png' },
  { template: 'one2many 明细', before: 'before-baseline/form-final-one2many-390.png', after: 'form-final-one2many-390.png' },
  { template: '表单设计器', before: 'before-baseline/form-final-designer-390.png', after: 'form-final-designer-390.png' },
  { template: '状态页', before: 'before-baseline/form-final-empty-record.png', after: 'form-final-empty-record.png' },
];
for (const pair of pairs) {
  await Promise.all([pair.before, pair.after].map(async (file) => {
    await fs.access(path.join(OUTPUT, file));
  }));
}
await fs.writeFile(path.join(OUTPUT, 'before-after-manifest.json'), `${JSON.stringify({ schema: 'frontend-before-after-manifest.v1', baseline_sha: '2ae5dd9ff99f54db66e80bf1e9855a3d59ee090e', candidate_source_sha: sha, pairs }, null, 2)}\n`, 'utf8');

const principles = [
  ['单一主工作面', 'AppShell 只保留一个主业务画布；列表使用 data-grid 全宽；记录/表单/聚焦表单采用明确宽度合同。', 'geometry-scroll-audit.json；首页、列表、表单、设计器截图'],
  ['单一滚动责任', '普通页面由 #main-content 持有纵向滚动；表格、弹窗和设计器仅在明确边界内局部滚动。', `${geometry.rows?.length || 0} 行几何/滚动矩阵；负向溢出夹具`],
  ['稳定上下文', '命令栏与章节导航用实测高度发布统一 sticky offset；锚点 scroll-margin 同源。', 'form-audit：long_form 与 sticky_header 断言'],
  ['渐进披露', '列表工具区连续；低频动作进入更多操作；移动设计器主画布先于目录和检查器。', '五视口列表、表单与设计器截图'],
  ['低噪声层级', '复用设计令牌与 ScIcon；首页移除宣传型渐变和装饰，统一浅色业务层级。', '首页前后截图；设计系统守卫'],
  ['可预测反馈', '保存中、成功、失败、校验错误和空记录靠近作用对象且不触发布局跳动。', 'form-audit 保存/校验/empty 状态矩阵'],
  ['响应式重组', '侧栏进入抽屉、列表卡片化、设计器在 1300 以下堆叠且 768/390 主画布优先。', `五视口表单 ${form.assertions?.length || 0} 项断言；全产品 ${fullProduct.route_rows?.length || 0} 次路由检查`],
  ['无障碍', '通用模态焦点陷阱、Escape、焦点恢复；many2one combobox/listbox 键盘语义；focus-visible 与触控尺寸。', '关系弹窗、键盘、one2many 操作可达断言'],
  ['行业适配', '编号、日期、金额、状态保持语义对齐；审批顺序、附件和协作采用企业工作流结构。', 'BOSS/PUMA 差异矩阵；合同/项目/施工代表页'],
];
const principleRows = principles.map(([principle, mapping, evidence]) => `<tr><td>${escapeHtml(principle)}</td><td>${escapeHtml(mapping)}</td><td>${escapeHtml(evidence)}</td></tr>`).join('');
const mappingHtml = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChatGPT 产品纪律到 SCE 映射</title><style>body{font:14px system-ui;margin:32px;color:#172033;background:#f4f7fb}main{max-width:1280px;margin:auto;background:#fff;border:1px solid #d9e1eb;border-radius:12px;padding:24px}h1,p{margin-top:0}p{color:#596579;line-height:1.7}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #e5eaf0}th{background:#f7f9fc}@media(max-width:700px){body{margin:12px}main{padding:14px}table{font-size:12px}}</style></head><body><main><h1>ChatGPT 产品纪律到 SCE 工程系统的映射</h1><p><strong>来源边界：</strong>本页的九项 ChatGPT 产品纪律来自用户在本专题中冻结的验收要求（2026-08-05），不是对第三方产品页面的采样或仿制。实现不复制聊天气泡、品牌资产、窄聊天列或营销样式。</p><p><strong>参考边界：</strong>BOSS/PUMA 仅作为目标企业系统专业度参考，来源与脱敏截图哈希见 <a href="form-audit.html">表单专项</a>；泛微今承达被单独标记为辅助成熟产品，不冒充 ChatGPT 或 BOSS/PUMA。</p><table><thead><tr><th>原则</th><th>SCE 工程映射</th><th>证据</th></tr></thead><tbody>${principleRows}</tbody></table></main></body></html>`;
await fs.writeFile(path.join(OUTPUT, 'chatgpt-principles-to-sce.html'), mappingHtml, 'utf8');

const conceptDecisions = [
  ['adopted', '设计令牌 → 通用组件 → 页面模板 → 真实业务页面', '落实到正式 Sc 设计系统、ScIcon 和 Contract/Intent 运行时；空间与色彩报告验证生产页面消费。'],
  ['adopted', '4px 基础网格与 4/8/12/16/24/32 节奏', '使用共享语义 spacing token；浏览器 computed style 与 bounding box 审计，不以源码计数冒充。'],
  ['adopted', '工程行业信息表达', '编号、日期、金额、状态继续由正式字段合同与生产渲染器表达；状态色只承担业务语义。'],
  ['adopted', '指标 → 趋势 → 异常 → 明细的信息架构', '仅吸收低彩度、业务内容优先的层级思想，不复制概念稿卡片或图表视觉。'],
  ['rejected', '按 window.innerWidth 维护第二套移动字段/标签/状态逻辑', '与单一 Contract、跨端关键字段一致性冲突；现实现使用同一权威列合同做响应式降级。'],
  ['rejected', '概念目录源码、演示样式、API 假设和“已完成”结论', '概念目录不是可执行或已验收基线，且含硬编码色、Emoji、any、模拟刷新及缺少焦点管理等反例。'],
  ['rejected', 'Ant Design 旧色值、Tailwind 混用、重卡片与高饱和状态卡', '违反当前正式 token、低噪声企业表面和无硬编码颜色门禁。'],
  ['deferred', 'BOQ 树、ECharts、Excel/PDF、甘特、富文本、白标', '属于独立业务能力，须在当前体验闭环后按真实 API、权限、安全、性能与无障碍另行立项。'],
];
const conceptHtml = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>概念材料取舍记录</title><style>body{font:14px system-ui;margin:32px;color:#172033}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #d8dee8;padding:10px;text-align:left;vertical-align:top}.adopted{color:#087443}.deferred{color:#9a6700}.rejected{color:#b42318}</style></head><body><h1>concept-input-triage</h1><p>来源：用户概念材料 <code>/home/lidefend/workspace/2026-08-05-21-27-25</code>；仅作为思考输入，不复制源码、样式、数据、凭证或完成结论。</p><table><thead><tr><th>裁定</th><th>输入</th><th>生产落实/理由</th></tr></thead><tbody>${conceptDecisions.map(([status, input, reason]) => `<tr><td class="${status}">${status}</td><td>${escapeHtml(input)}</td><td>${escapeHtml(reason)}</td></tr>`).join('')}</tbody></table></body></html>`;
await fs.writeFile(path.join(OUTPUT, 'concept-input-triage.html'), conceptHtml, 'utf8');

const showcaseRows = (color.rows || []).map((row) => {
  const source = String(row.screenshot || '');
  const name = path.basename(source);
  const copied = `color-evidence/${name}`;
  return `<article><h2>${escapeHtml(row.target?.label || row.target?.kind || '生产组件状态')}</h2><p>${escapeHtml(row.viewport?.width || row.viewport?.key)} · ${escapeHtml(row.theme)}</p><a href="${encodeURI(copied)}"><img src="${encodeURI(copied)}" alt="生产组件状态截图"></a></article>`;
}).join('');
const showcaseHtml = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>生产组件状态矩阵</title><style>body{font:14px system-ui;margin:24px;color:#172033;background:#edf2f7}main{max-width:1440px;margin:auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}header{grid-column:1/-1}article{background:#fff;border:1px solid #d8dee8;padding:16px}img{width:100%;display:block}h2{font-size:16px}</style></head><body><main><header><h1>正式生产组件状态矩阵</h1><p>截图由真实生产组件、真实路由与浏览器状态审计产生；不是另写静态组件冒充。覆盖 default/hover/focus/selected/error/empty/dialog 与明暗主题，自动断言见 color-role-audit.json。</p></header>${showcaseRows}</main></body></html>`;
await fs.writeFile(path.join(OUTPUT, 'component-state-showcase.html'), showcaseHtml, 'utf8');

const pairCards = pairs.map((pair) => `<article><h3>${escapeHtml(pair.template)}</h3><div><figure><figcaption>改前 · 2ae5dd9</figcaption><a href="${encodeURI(pair.before)}"><img src="${encodeURI(pair.before)}" alt="${escapeHtml(pair.template)}改前"></a></figure><figure><figcaption>改后 · 当前候选</figcaption><a href="${encodeURI(pair.after)}"><img src="${encodeURI(pair.after)}" alt="${escapeHtml(pair.template)}改后"></a></figure></div></article>`).join('');
const machinePass = geometry.passed && spacing.passed && form.status === 'PASS' && fullProduct.status === 'PASS' && color.passed && failures.length === 0;
const visualAccepted = machinePass && visualSupervisorDecision === 'accepted';
const statusText = !machinePass
  ? '自动门禁存在失败，尚未形成候选'
  : visualAccepted ? '自动门禁与监督者逐截图视觉验收均已通过' : '自动门禁已通过，等待监督者最终验收';
const indexHtml = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SCE 自定义前端专业成品验收</title><style>body{font:14px system-ui;margin:0;padding:28px;color:#172033;background:#edf2f7}main{max-width:1500px;margin:auto}.hero,section{background:#fff;border:1px solid #d9e1eb;border-radius:12px;padding:22px;margin-bottom:18px}h1,h2,h3,p{margin-top:0}.pending{color:#9a6700}.pass{color:#087443}.links{display:flex;gap:10px;flex-wrap:wrap}.links a{padding:8px 11px;border:1px solid #cfd8e5;border-radius:6px;color:#155eef;text-decoration:none}article>div{display:grid;grid-template-columns:1fr 1fr;gap:12px}figure{margin:0;min-width:0}figcaption{margin-bottom:6px;color:#596579}img{display:block;width:100%;border:1px solid #d9e1eb;border-radius:6px}@media(max-width:760px){body{padding:12px}.hero,section{padding:14px}article>div{grid-template-columns:1fr}}</style></head><body><main><header class="hero"><h1>自定义前端专业成品 · 总验收入口</h1><p class="${visualAccepted ? 'pass' : machinePass ? 'pending' : ''}">${statusText}</p><p>源码 SHA：<code>${escapeHtml(sha)}</code> · 工作树：${dirtyFiles.length ? `有 ${dirtyFiles.length} 项未提交改动（提交后重绑 SHA）` : 'clean'} · 生成时间：${escapeHtml(new Date().toISOString())}</p><div class="links"><a href="geometry-scroll-audit.html">几何与滚动</a><a href="spacing-geometry-audit.html">空间几何</a><a href="color-role-audit.json">色彩角色</a><a href="form-audit.html">完整表单体系</a><a href="full-product-audit.html">全产品路由</a><a href="component-state-showcase.html">组件状态矩阵</a><a href="chatgpt-principles-to-sce.html">原则映射</a><a href="concept-input-triage.html">概念取舍</a><a href="failures.json">失败清单 JSON</a></div></header><section><h2>门禁摘要</h2><p class="${machinePass ? 'pass' : ''}">几何 ${geometry.passed ? 'PASS' : 'FAIL'}（${geometry.rows?.length || 0} 行） · 空间 ${spacing.passed ? 'PASS' : 'FAIL'} · 色彩 ${color.passed ? 'PASS' : 'FAIL'} · 表单 ${form.status}（${form.assertions?.length || 0} 项） · 全产品 ${fullProduct.status}（${fullProduct.route_rows?.length || 0} 行） · 当前 P0/P1 ${failures.length}</p><p>监督者视觉裁决：${escapeHtml(visualSupervisorDecision)}。自动化结果不替代逐截图视觉裁决。</p></section><section><h2>改前 / 改后证据</h2>${pairCards}</section></main></body></html>`;
await fs.writeFile(path.join(OUTPUT, 'index.html'), indexHtml, 'utf8');

console.log(JSON.stringify({ status: machinePass ? 'AUTOMATION_PASS_AWAITING_VISUAL_REVIEW' : 'FAIL', sha, dirty_files: dirtyFiles.length, failures: failures.length, output: OUTPUT }, null, 2));
if (!machinePass) process.exitCode = 1;
