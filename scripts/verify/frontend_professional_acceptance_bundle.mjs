#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = process.cwd();
const OUTPUT = path.resolve(process.env.SC_FINAL_ACCEPTANCE_OUTPUT || '.runtime/final-acceptance');
const GEOMETRY_JSON = path.resolve('.runtime/geometry-scroll-audit.json');
const GEOMETRY_HTML = path.resolve('.runtime/geometry-scroll-audit.html');
const FORM_JSON = path.resolve('.runtime/form-audit.json');
const FULL_JSON = path.resolve('.runtime/full-product-audit.json');
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
await fs.copyFile(GEOMETRY_JSON, path.join(OUTPUT, 'geometry-scroll-audit.json'));
await fs.copyFile(GEOMETRY_HTML, path.join(OUTPUT, 'geometry-scroll-audit.html'));

const [geometry, form, fullProduct, beforeForm] = await Promise.all([
  readJson(GEOMETRY_JSON),
  readJson(FORM_JSON),
  readJson(FULL_JSON),
  readJson(BEFORE_FORM_JSON),
]);
const sha = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim();
const dirtyFiles = execFileSync('git', ['status', '--short'], { cwd: ROOT, encoding: 'utf8' }).trim().split('\n').filter(Boolean);

const failures = [
  ...(geometry.failures || []).map((item) => ({ source: 'geometry-scroll-audit', ...item })),
  ...(form.issues || []).map((item) => ({ source: 'form-audit', ...item })),
  ...(fullProduct.failures || []).map((item) => ({ source: 'full-product-audit', ...item })),
];
const failureList = {
  schema: 'frontend-professional-failure-list.v1',
  generated_at: new Date().toISOString(),
  source_sha: sha,
  current_failures: failures,
  current_p0: failures.filter((item) => item.severity === 'P0').length,
  current_p1: failures.filter((item) => item.severity === 'P1').length,
  baseline_negative_findings: beforeForm.issues || [],
  visual_supervisor_decision: 'pending',
};
await fs.writeFile(path.join(OUTPUT, 'failure-list.json'), `${JSON.stringify(failureList, null, 2)}\n`, 'utf8');

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
  ['单一滚动责任', '普通页面由 #main-content 持有纵向滚动；表格、弹窗和设计器仅在明确边界内局部滚动。', '30 行几何/滚动矩阵；负向溢出夹具'],
  ['稳定上下文', '命令栏与章节导航用实测高度发布统一 sticky offset；锚点 scroll-margin 同源。', 'form-audit：long_form 与 sticky_header 断言'],
  ['渐进披露', '列表工具区连续；低频动作进入更多操作；移动设计器主画布先于目录和检查器。', '五视口列表、表单与设计器截图'],
  ['低噪声层级', '复用设计令牌与 ScIcon；首页移除宣传型渐变和装饰，统一浅色业务层级。', '首页前后截图；设计系统守卫'],
  ['可预测反馈', '保存中、成功、失败、校验错误和空记录靠近作用对象且不触发布局跳动。', 'form-audit 保存/校验/empty 状态矩阵'],
  ['响应式重组', '侧栏进入抽屉、列表卡片化、设计器在 1300 以下堆叠且 768/390 主画布优先。', '五视口表单 111 项断言；全产品 142 次路由检查'],
  ['无障碍', '通用模态焦点陷阱、Escape、焦点恢复；many2one combobox/listbox 键盘语义；focus-visible 与触控尺寸。', '关系弹窗、键盘、one2many 操作可达断言'],
  ['行业适配', '编号、日期、金额、状态保持语义对齐；审批顺序、附件和协作采用企业工作流结构。', 'BOSS/PUMA 差异矩阵；合同/项目/施工代表页'],
];
const principleRows = principles.map(([principle, mapping, evidence]) => `<tr><td>${escapeHtml(principle)}</td><td>${escapeHtml(mapping)}</td><td>${escapeHtml(evidence)}</td></tr>`).join('');
const mappingHtml = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChatGPT 产品纪律到 SCE 映射</title><style>body{font:14px system-ui;margin:32px;color:#172033;background:#f4f7fb}main{max-width:1280px;margin:auto;background:#fff;border:1px solid #d9e1eb;border-radius:12px;padding:24px}h1,p{margin-top:0}p{color:#596579;line-height:1.7}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #e5eaf0}th{background:#f7f9fc}@media(max-width:700px){body{margin:12px}main{padding:14px}table{font-size:12px}}</style></head><body><main><h1>ChatGPT 产品纪律到 SCE 工程系统的映射</h1><p><strong>来源边界：</strong>本页的九项 ChatGPT 产品纪律来自用户在本专题中冻结的验收要求（2026-08-05），不是对第三方产品页面的采样或仿制。实现不复制聊天气泡、品牌资产、窄聊天列或营销样式。</p><p><strong>参考边界：</strong>BOSS/PUMA 仅作为目标企业系统专业度参考，来源与脱敏截图哈希见 <a href="form-audit.html">表单专项</a>；泛微今承达被单独标记为辅助成熟产品，不冒充 ChatGPT 或 BOSS/PUMA。</p><table><thead><tr><th>原则</th><th>SCE 工程映射</th><th>证据</th></tr></thead><tbody>${principleRows}</tbody></table></main></body></html>`;
await fs.writeFile(path.join(OUTPUT, 'chatgpt-principles-to-sce.html'), mappingHtml, 'utf8');

const pairCards = pairs.map((pair) => `<article><h3>${escapeHtml(pair.template)}</h3><div><figure><figcaption>改前 · 2ae5dd9</figcaption><a href="${encodeURI(pair.before)}"><img src="${encodeURI(pair.before)}" alt="${escapeHtml(pair.template)}改前"></a></figure><figure><figcaption>改后 · 当前候选</figcaption><a href="${encodeURI(pair.after)}"><img src="${encodeURI(pair.after)}" alt="${escapeHtml(pair.template)}改后"></a></figure></div></article>`).join('');
const machinePass = geometry.passed && form.status === 'PASS' && fullProduct.status === 'PASS' && failures.length === 0;
const indexHtml = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SCE 自定义前端专业成品验收</title><style>body{font:14px system-ui;margin:0;padding:28px;color:#172033;background:#edf2f7}main{max-width:1500px;margin:auto}.hero,section{background:#fff;border:1px solid #d9e1eb;border-radius:12px;padding:22px;margin-bottom:18px}h1,h2,h3,p{margin-top:0}.pending{color:#9a6700}.pass{color:#087443}.links{display:flex;gap:10px;flex-wrap:wrap}.links a{padding:8px 11px;border:1px solid #cfd8e5;border-radius:6px;color:#155eef;text-decoration:none}article>div{display:grid;grid-template-columns:1fr 1fr;gap:12px}figure{margin:0;min-width:0}figcaption{margin-bottom:6px;color:#596579}img{display:block;width:100%;border:1px solid #d9e1eb;border-radius:6px}@media(max-width:760px){body{padding:12px}.hero,section{padding:14px}article>div{grid-template-columns:1fr}}</style></head><body><main><header class="hero"><h1>自定义前端专业成品 · 总验收入口</h1><p class="${machinePass ? 'pending' : ''}">${machinePass ? '自动门禁已通过，等待监督者最终验收' : '自动门禁存在失败，尚未形成候选'}</p><p>源码 SHA：<code>${escapeHtml(sha)}</code> · 工作树：${dirtyFiles.length ? `有 ${dirtyFiles.length} 项未提交改动（提交后重绑 SHA）` : 'clean'} · 生成时间：${escapeHtml(new Date().toISOString())}</p><div class="links"><a href="geometry-scroll-audit.html">几何与滚动</a><a href="form-audit.html">完整表单体系</a><a href="full-product-audit.html">全产品路由</a><a href="chatgpt-principles-to-sce.html">原则映射</a><a href="failure-list.json">失败清单 JSON</a></div></header><section><h2>门禁摘要</h2><p class="${machinePass ? 'pass' : ''}">几何 ${geometry.passed ? 'PASS' : 'FAIL'}（${geometry.rows?.length || 0} 行） · 表单 ${form.status}（${form.assertions?.length || 0} 项） · 全产品 ${fullProduct.status}（${fullProduct.route_rows?.length || 0} 行） · 当前 P0/P1 ${failures.length}</p><p>自动化结果不替代逐截图视觉裁决；本页不自行宣布专题完成。</p></section><section><h2>改前 / 改后证据</h2>${pairCards}</section></main></body></html>`;
await fs.writeFile(path.join(OUTPUT, 'index.html'), indexHtml, 'utf8');

console.log(JSON.stringify({ status: machinePass ? 'AUTOMATION_PASS_AWAITING_VISUAL_REVIEW' : 'FAIL', sha, dirty_files: dirtyFiles.length, failures: failures.length, output: OUTPUT }, null, 2));
if (!machinePass) process.exitCode = 1;
