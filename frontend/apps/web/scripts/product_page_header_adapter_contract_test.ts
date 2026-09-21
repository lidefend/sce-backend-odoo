import { strict as assert } from 'node:assert';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import {
  PRODUCT_PAGE_HEADER_AXES,
  PRODUCT_PAGE_HEADER_ENTRIES,
  PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS,
  resolveProductPageHeaderEntry,
  resolveProductPageHeaderFixedAxis,
  resolveProductPageHeaderForwardedAxes,
  type ProductPageHeaderAxis,
  type ProductPageHeaderEntryRegistry,
} from '../src/app/presentation/productPageHeaderAdapters';

const SRC = path.join(process.cwd(), 'frontend/apps/web/src');
const AUTHORITY = 'components/product-page-header/ProductPageHeader.vue';
const read = (relative: string) => readFileSync(path.join(SRC, relative), 'utf8');
const kebab = (value: string) => value.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
const camel = (value: string) => value.replace(/-([a-z])/g, (_, char: string) => char.toUpperCase());
const declaredPropsOf = (relative: string): string[] =>
  [...(read(relative).match(/defineProps<\{([\s\S]*?)\}>/) ?? ['', ''])[1].matchAll(/([A-Za-z_]\w*)\??:/g)].map(
    (match) => match[1],
  );

/**
 * 去掉 HTML 注释、块注释与整行 `//` 注释。注释里的「委托渲染」「登记表解析」不是实现：
 * 不剥离注释会让契约测试被诱饵满足（例如把解析调用注释掉、只留绑定的标识符）。
 */
function stripComments(source: string): string {
  return source
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .filter((line) => !line.trimStart().startsWith('//'))
    .join('\n');
}

/**
 * 引号感知地取出开标签内的属性块。**不能**用非贪婪正则直接扫到第一个 `>`：
 * 属性值里的 `>`／`>=`／`=>`（如 `:title="a > b"`）会提前截断标签，使该标签内后续的未声明属性静默漏检。
 */
function tagAttributeBlocks(source: string, names: readonly string[]): string[] {
  const blocks: string[] = [];
  const pattern = new RegExp(`<(?:${names.join('|')})(?=[\\s/>])`, 'g');
  for (const match of source.matchAll(pattern)) {
    const start = match.index + match[0].length;
    let index = start;
    let quote: string | null = null;
    while (index < source.length) {
      const char = source[index];
      if (quote) {
        if (char === quote) quote = null;
      } else if (char === '"' || char === "'") {
        quote = char;
      } else if (char === '>') {
        break;
      }
      index += 1;
    }
    blocks.push(source.slice(start, index));
  }
  return blocks;
}

const SLOT_AXES: ProductPageHeaderAxis[] = ['metaSlot', 'statusSlot', 'actionsSlot'];
const axisToProp = (axis: ProductPageHeaderAxis) => (axis.endsWith('Slot') ? null : axis);
const axisToSlot = (axis: ProductPageHeaderAxis) => (axis.endsWith('Slot') ? axis.slice(0, -'Slot'.length) : null);

function walkVue(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return walkVue(full);
    return name.endsWith('.vue') ? [path.relative(SRC, full)] : [];
  });
}

/**
 * 解析 `import` 子句。契约测试必须同时覆盖三种既有导入形态：
 * 默认导入（`import PageHeader from './PageHeader.vue'`）、
 * 具名导入（`import { ScPageHeader } from '../components/design-system'`）与
 * barrel 再导出——只认默认导入会让 `ApiKeyManagementView` 这类具名导入的调用点静默从覆盖中消失。
 */
type ImportedSymbol = { readonly local: string; readonly imported: string; readonly specifier: string };

function parseImports(source: string): ImportedSymbol[] {
  const found: ImportedSymbol[] = [];
  for (const match of source.matchAll(/import\s+([^;]+?)\s+from\s+'([^']+)'/g)) {
    const clause = match[1];
    const specifier = match[2];
    const defaultMatch = clause.match(/^\s*([A-Za-z_$][\w$]*)\s*(?:,\s*\{|$)/);
    if (defaultMatch) found.push({ local: defaultMatch[1], imported: 'default', specifier });
    const namedMatch = clause.match(/\{([\s\S]*?)\}/);
    if (!namedMatch) continue;
    for (const item of namedMatch[1].split(',')) {
      const trimmed = item.trim().replace(/^type\s+/, '');
      if (!trimmed) continue;
      const [imported, local] = trimmed.split(/\s+as\s+/).map((part) => part.trim());
      if (!imported || !/^[A-Za-z_$][\w$]*$/.test(imported)) continue;
      found.push({ local: local ?? imported, imported, specifier });
    }
  }
  return found;
}

const entrySource = (relative: string) => stripComments(read(relative));
const authoritySource = stripComments(read(AUTHORITY));
const authorityProps = [...(authoritySource.match(/defineProps<\{([\s\S]*?)\}>/) ?? ['', ''])[1].matchAll(/([A-Za-z_]\w*)\??:/g)].map(
  (match) => match[1],
);
const authoritySlots = [...authoritySource.matchAll(/<slot\s+name="([A-Za-z_]\w*)"/g)].map((match) => match[1]);

const ENTRY_BY_PATH = new Map<string, ProductPageHeaderEntryRegistry>(
  PRODUCT_PAGE_HEADER_ENTRIES.map((entry) => [entry.path, entry]),
);
const ADAPTER_ENTRY_BY_PATH = new Map<string, ProductPageHeaderEntryRegistry>(
  PRODUCT_PAGE_HEADER_ENTRIES.filter((entry) => entry.kind === 'adapter').map((entry) => [entry.path, entry]),
);

/**
 * 解析模块说明符到 `src` 相对路径。相对路径与 `@/` 别名（vite `resolve.alias['@'] = src`）都必须覆盖：
 * 只认相对路径会让别名导入的调用点从覆盖中消失。
 */
function specifierBase(fromFile: string, specifier: string): string | null {
  if (specifier.startsWith('@/')) return path.posix.normalize(specifier.slice(2));
  if (specifier.startsWith('.')) return path.posix.normalize(path.posix.join(path.posix.dirname(fromFile), specifier));
  return null;
}

/** 把某个导入符号解析到权威或已登记入口；无法解析时返回 null。 */
function delegationTarget(fromFile: string, symbol: ImportedSymbol): 'authority' | ProductPageHeaderEntryRegistry | null {
  const base = specifierBase(fromFile, symbol.specifier);
  if (base === null) return null;
  for (const candidate of [base, `${base}.vue`, `${base}.ts`]) {
    if (candidate === AUTHORITY) return 'authority';
    const entry = ENTRY_BY_PATH.get(candidate);
    if (entry) return entry;
  }
  const indexFile = `${base}/index.ts`;
  if (!existsSync(path.join(SRC, indexFile))) return null;
  for (const line of read(indexFile).split('\n')) {
    const reExport = line.match(/export\s*\{([^}]*)\}\s*from\s*'\.\/([^']+)\.vue'/);
    if (!reExport) continue;
    const boundNames = reExport[1]
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const [imported, local] = part.split(/\s+as\s+/).map((item) => item.trim());
        return local ?? imported;
      });
    if (!boundNames.includes(symbol.local) && !boundNames.includes(symbol.imported)) continue;
    const resolved = path.posix.join(base, `${reExport[2]}.vue`);
    if (resolved === AUTHORITY) return 'authority';
    const entry = ENTRY_BY_PATH.get(resolved);
    if (entry) return entry;
  }
  return null;
}

const delegatedTargets = (relative: string) =>
  parseImports(read(relative))
    .map((symbol) => ({ symbol, target: delegationTarget(relative, symbol) }))
    .filter((item): item is { symbol: ImportedSymbol; target: 'authority' | ProductPageHeaderEntryRegistry } => item.target !== null);

// A. 权威的正式面与登记轴必须等价，且不得重复——新增 prop/slot 而不登记即失败。
assert.deepEqual(
  [...new Set(PRODUCT_PAGE_HEADER_AXES)].length,
  PRODUCT_PAGE_HEADER_AXES.length,
  'PRODUCT_PAGE_HEADER_AXES 存在重复轴',
);
assert.deepEqual(
  [...PRODUCT_PAGE_HEADER_AXES].sort(),
  [...authorityProps.map((prop) => prop as ProductPageHeaderAxis), ...authoritySlots.map((slot) => `${slot}Slot` as ProductPageHeaderAxis)].sort(),
  'ProductPageHeader 正式面与 PRODUCT_PAGE_HEADER_AXES 不一致：新增轴必须在入口登记表中显式决策',
);
assert.ok(
  SLOT_AXES.every((axis) => PRODUCT_PAGE_HEADER_AXES.includes(axis)),
  '三个正式槽轴必须包含在 PRODUCT_PAGE_HEADER_AXES 内',
);

// A2. 权威不得用 `$attrs` 兜底转发未登记轴：这会绕过「未登记轴必须显式决策」并让调用方静默注入。
assert.ok(
  !/\$attrs/.test(authoritySource),
  'ProductPageHeader 不得用 $attrs 兜底转发未登记轴：未登记轴必须在登记表中显式决策',
);

// B. 每个入口都必须存在、必须在模板中真实渲染上游（权威或已登记入口），且不得自建 header DOM。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  assert.ok(existsSync(path.join(SRC, entry.path)), `登记入口不存在: ${entry.path}`);
  const source = entrySource(entry.path);
  const upstream = delegatedTargets(entry.path);
  assert.ok(upstream.length > 0, `${entry.id} 未导入 ProductPageHeader 或任何已登记入口`);
  assert.ok(
    upstream.some(({ symbol }) => new RegExp(`<${symbol.local}\\b|<${kebab(symbol.local)}\\b`).test(source)),
    `${entry.id} 必须在其模板中真实渲染上游页头组件；只保留 import 不算委托`,
  );
  assert.ok(!/<header[\s>]/.test(source), `${entry.id} 不得自建 header DOM`);
  assert.ok(!/<h1[\s>]/.test(source), `${entry.id} 不得自建 h1，页面标题唯一权威是 ProductPageHeader`);
}

// C. 声明为 forwarded 的轴必须在入口里真实转发。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  const source = entrySource(entry.path);
  for (const axis of resolveProductPageHeaderForwardedAxes(entry.id)) {
    const prop = axisToProp(axis);
    if (prop) {
      assert.ok(source.includes(`:${kebab(prop)}=`), `${entry.id} 声明转发 ${axis}，但未在模板中转发 :${kebab(prop)}`);
      continue;
    }
    const slot = axisToSlot(axis);
    assert.ok(source.includes(`#${slot}`), `${entry.id} 声明转发 ${axis}，但未在模板中转发 #${slot}`);
  }
}

// D. 声明为 fixed 的轴必须由登记表解析，且绑定值必须引用该解析常量——不留「装饰性调用 ＋ 字面量绑定」的静默分叉。
const FIXED_RESOLVER: Record<string, string> = { presentationMode: 'resolveProductPageHeaderFixedMode' };
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  const source = entrySource(entry.path);
  for (const disposition of entry.axes) {
    if (disposition.handling !== 'fixed') continue;
    const resolver = FIXED_RESOLVER[disposition.axis] ?? 'resolveProductPageHeaderFixedAxis';
    const name = kebab(disposition.axis);
    assert.ok(
      !new RegExp(`(?<![:\\w-])${name}="`).test(source),
      `${entry.id} 的固定轴 ${disposition.axis} 仍有静态字面量，必须经 ${resolver} 读取登记表`,
    );
    assert.ok(
      !new RegExp(`:${name}="\\s*['\`]`).test(source),
      `${entry.id} 的固定轴 ${disposition.axis} 不得绑定字符串字面量，必须绑定 ${resolver} 的返回值`,
    );
    const binding = source.match(new RegExp(`:${name}="([A-Za-z_$][\\w$]*)"`));
    assert.ok(binding, `${entry.id} 的固定轴 ${disposition.axis} 必须以标识符引用形式绑定，而不是字面量`);
    const constName = binding[1];
    assert.ok(
      new RegExp(`const\\s+${constName}\\s*=\\s*${resolver}\\(\\s*['\"]${entry.id}['\"]\\s*\\)`).test(source),
      `${entry.id} 的固定轴 ${disposition.axis} 绑定值 ${constName} 必须来自 ${resolver}('${entry.id}')，不得由装饰性调用遮蔽`,
    );
    assert.equal(resolveProductPageHeaderFixedAxis(entry.id, disposition.axis), disposition.value);
  }
}

// E. 薄入口的声明面不得超出登记表，且不得用 `$attrs` 透传未登记轴。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  if (entry.kind !== 'adapter') continue;
  const source = entrySource(entry.path);
  assert.ok(!/\$attrs/.test(source), `${entry.id} 不得用 $attrs 透传未登记轴：未登记轴必须在登记表中显式决策`);
  const allowed = new Set(
    entry.axes
      .filter((disposition) => disposition.handling !== 'not_exposed')
      .map((disposition) => axisToProp(disposition.axis))
      .filter((prop): prop is ProductPageHeaderAxis => Boolean(prop)),
  );
  for (const prop of declaredPropsOf(entry.path)) {
    assert.ok(allowed.has(prop as ProductPageHeaderAxis), `${entry.id} 声明了未登记输入 ${prop}`);
  }
  // 槽位同样是「输入面」：薄入口不得暴露未登记／未转发的槽。
  const forwardedSlots = new Set(
    entry.axes
      .filter((disposition) => disposition.handling === 'forwarded' && disposition.axis.endsWith('Slot'))
      .map((disposition) => axisToSlot(disposition.axis)),
  );
  for (const slot of [...source.matchAll(/<slot\s+name="([A-Za-z_]\w*)"/g)].map((match) => match[1])) {
    assert.ok(forwardedSlots.has(slot), `${entry.id} 暴露了未登记的槽 ${slot}：槽位必须与登记表一致`);
  }
}

// F. 调用方的调用面必须逐点固定：标签形态（PascalCase／kebab）、导入形态（默认／具名／barrel）与集合本身都被钉死。
const PASS_THROUGH = new Set(['class', 'style', 'key', 'ref', 'is', 'slot', 'id']);

/**
 * 把属性名归一为「入口必须声明的输入名」。`:x` 与 `v-bind:x` 等价，`v-model`／`v-model:x` 落到 Vue 实际
 * 使用的 prop（`modelValue`／`x`），`.modifier` 不改 prop 名；`v-if`／`v-for` 等非输入面指令返回 null。
 * 只跳过 `v-` 前缀会让 `v-bind:x`／`v-model` 成为「静默丢参」的一 token 绕过。
 */
function normaliseBoundAttribute(rawName: string): string | null {
  let name: string;
  if (rawName === 'v-model') name = 'modelValue';
  else if (rawName.startsWith('v-model:')) name = rawName.slice('v-model:'.length);
  else if (rawName.startsWith('v-bind:')) name = rawName.slice('v-bind:'.length);
  else if (rawName.startsWith(':')) name = rawName.slice(1);
  else if (rawName.startsWith('v-')) return null;
  else name = rawName;
  return name.split('.')[0] || null;
}

/**
 * 逐字扫描开标签内的属性名。**必须感知引号**：正则式扫描会把属性值内部的标识符
 * （如 `v-if="... && status !== 'error'"` 里的 `status`）误判为属性名，从而产生假失败／假放行。
 */
function attributeNames(block: string): string[] {
  const names: string[] = [];
  const isSpace = (char: string | undefined) => char !== undefined && /\s/.test(char);
  let index = 0;
  const skipWhitespace = () => {
    while (index < block.length && isSpace(block[index])) index += 1;
  };
  skipWhitespace();
  while (index < block.length) {
    if (block[index] === '/' || block[index] === '>') break;
    const start = index;
    while (index < block.length && !/[\s=/>]/.test(block[index])) index += 1;
    const name = block.slice(start, index);
    skipWhitespace();
    if (block[index] === '=') {
      index += 1;
      skipWhitespace();
      const quote = block[index];
      if (quote === '"' || quote === "'") {
        index += 1;
        while (index < block.length && block[index] !== quote) index += 1;
        index += 1;
      } else {
        while (index < block.length && !isSpace(block[index])) index += 1;
      }
    }
    if (name) names.push(name);
    skipWhitespace();
  }
  return names;
}

/** 已登记的薄入口调用点全集；任何新增／改形（kebab 标签、barrel 具名导入、动态 `:is`）都必须在此显式登记。 */
const KNOWN_CALL_SITES = [
  'pages/ContractFormPage.vue#ContractFormProductHeader',
  'pages/KanbanPage.vue#PageHeader',
  'pages/contractForm/ContractFormProductHeader.vue#PageHeaderTemplate',
  'views/ApiKeyManagementView.vue#ScPageHeader',
  'views/NotFoundView.vue#ScPageHeader',
  'views/businessConfigSurface/BusinessConfigContextBar.vue#ScPageHeader',
];

const discoveredCallSites: string[] = [];
for (const file of walkVue(SRC)) {
  const source = read(file);
  const tagToEntry = new Map<string, ProductPageHeaderEntryRegistry>();
  for (const symbol of parseImports(source)) {
    const target = delegationTarget(file, symbol);
    if (target && target !== 'authority') tagToEntry.set(symbol.local, target);
  }
  if (tagToEntry.size === 0) continue;

  // F1. 动态组件绑定无法静态枚举调用面：绑定到已登记入口即失败，必须显式登记该形态。
  for (const block of tagAttributeBlocks(source, ['component', 'Component'])) {
    for (const dynamic of block.matchAll(/:is="([^"]+)"|v-bind="([^"]+)"/g)) {
      for (const identifier of (dynamic[1] ?? dynamic[2] ?? '').matchAll(/[A-Za-z_$][\w$]*/g)) {
        assert.ok(
          !tagToEntry.has(identifier[0]),
          `${file} 用动态绑定渲染已登记入口 ${identifier[0]}，调用面无法静态枚举；必须先显式登记该形态`,
        );
      }
    }
  }

  for (const [tag, entry] of tagToEntry) {
    // 受管例外入口（`contract-form`）自带领域属性面，其调用面不以登记轴为界，因此只登记调用点、
    // 不做「属性 ⊆ 登记轴」比对；薄入口才是「调用方属性 ⊆ 声明面」的强约束对象。
    const strictFace = ADAPTER_ENTRY_BY_PATH.has(entry.path);
    const declared = new Set(declaredPropsOf(entry.path));
    for (const block of tagAttributeBlocks(source, [tag, kebab(tag)])) {
      discoveredCallSites.push(`${file}#${tag}`);
      for (const rawName of attributeNames(block)) {
        assert.ok(rawName !== 'v-bind', `${file} 对 ${entry.id} 使用 v-bind 对象展开，调用面无法静态枚举；必须改为显式具名属性`);
        if (rawName.startsWith('#') || rawName.startsWith('@') || rawName.startsWith('v-on:')) continue;
        const name = normaliseBoundAttribute(rawName);
        if (name === null) continue;
        if (name.startsWith('data-') || name.startsWith('aria-')) continue;
        if (PASS_THROUGH.has(name)) continue;
        if (!strictFace) continue;
        assert.ok(
          declared.has(camel(name)),
          `${file} 向 ${entry.id} 传入 ${name}，但该入口未声明：静默丢参必须改为显式登记或显式转发`,
        );
      }
    }
  }
}
assert.deepEqual(
  [...discoveredCallSites].sort(),
  [...KNOWN_CALL_SITES].sort(),
  '薄入口调用点集合必须与 KNOWN_CALL_SITES 完全一致：新增调用点或改变标签／导入形态都必须显式登记',
);

// F2. 以入口组件同名符号导入、却解析不到登记入口的说明符（未登记的别名、包路径等）必须显式登记，
// 否则该调用点会同时躲过 F 与 G。
const ENTRY_BASENAMES = new Set([
  ...PRODUCT_PAGE_HEADER_ENTRIES.map((entry) => path.posix.basename(entry.path, '.vue')),
  path.posix.basename(AUTHORITY, '.vue'),
]);
for (const file of walkVue(SRC)) {
  for (const symbol of parseImports(read(file))) {
    if (!ENTRY_BASENAMES.has(symbol.imported) && !ENTRY_BASENAMES.has(symbol.local)) continue;
    assert.ok(
      delegationTarget(file, symbol) !== null,
      `${file} 以入口组件同名符号 ${symbol.local} 从 '${symbol.specifier}' 导入，却解析不到登记入口；该导入形态必须显式登记`,
    );
  }
}

// G. 入口集合必须与登记表完全一致：新入口不得静默出现，登记入口不得失去委托。
const authorityConsumers = walkVue(SRC).filter((file) =>
  parseImports(read(file)).some((symbol) => delegationTarget(file, symbol) === 'authority'),
);
const directExpected = [
  ...PRODUCT_PAGE_HEADER_ENTRIES.filter((entry) => entry.kind === 'adapter').map((entry) => entry.path),
  ...PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS,
];
assert.deepEqual(
  [...authorityConsumers].sort(),
  [...directExpected].sort(),
  '直接消费 ProductPageHeader 的入口集合必须与登记表（薄入口 ＋ 直接消费页面）完全一致',
);
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  assert.ok(
    delegatedTargets(entry.path).some(({ target }) => target === 'authority' || ADAPTER_ENTRY_BY_PATH.has(target.path)),
    `${entry.path} 未委托 ProductPageHeader 或任何已登记入口渲染`,
  );
}
for (const consumer of PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS) {
  assert.ok(existsSync(path.join(SRC, consumer)), `登记的权威直接消费页面不存在: ${consumer}`);
}

// H. 登记表自身可解析：入口 id 唯一，且 not_exposed／fixed 必须给出理由。
const ids = PRODUCT_PAGE_HEADER_ENTRIES.map((entry) => entry.id);
assert.deepEqual([...new Set(ids)].length, ids.length, '入口 id 重复');
for (const id of ids) {
  const entry = resolveProductPageHeaderEntry(id);
  for (const disposition of entry.axes) {
    if (disposition.handling === 'not_exposed') {
      assert.ok(disposition.reason.trim().length > 0, `${id}/${disposition.axis} 未给出不暴露理由`);
    }
    if (disposition.handling === 'fixed') {
      assert.ok(disposition.reason.trim().length > 0, `${id}/${disposition.axis} 未给出固定理由`);
    }
  }
  assert.deepEqual(
    entry.axes.map((disposition) => disposition.axis).sort(),
    [...PRODUCT_PAGE_HEADER_AXES].sort(),
    `${id} 未对全部正式轴作出决策`,
  );
}

console.log(
  `[product_page_header_adapter_contract] PASS entries=${PRODUCT_PAGE_HEADER_ENTRIES.length} axes=${PRODUCT_PAGE_HEADER_AXES.length} call_sites=${discoveredCallSites.length} direct_consumers=${PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS.length}`,
);
