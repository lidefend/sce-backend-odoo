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
  [
    ...(codeOnly(read(relative)).match(/defineProps<\{([\s\S]*?)\}>/) ?? ['', ''])[1].matchAll(
      /([A-Za-z_]\w*)\??:/g,
    ),
  ].map((match) => match[1]);

const MASK = '\u0001';

/**
 * 生成「只剩真实代码」的视图，**长度与原文一致、下标与原文对齐**：
 * - `<!-- -->`／块注释／`//` 注释（含**行尾**内联形态）逐字符替换为空格：注释里的「委托渲染」「登记表解析」不是实现；
 * - `maskStrings` 为真时，字符串与模板字面量的**内容**逐字符替换为占位符：写在字面量里的
 *   `'<PageHeader />'` 或 `"const x = resolveProductPageHeaderFixedMode('page')"` 是文档诱饵，不是实现。
 * 扫描器**引号感知**，所以 `'https://…'` 里的 `//` 不会被误当成注释，`'/*'` 也不会开启块注释——
 * 用正则做这两件事都会留下「字符串里写一段注释符把真实代码夹掉」的静默通道。
 * 需要读取字面量**真实值**的断言（固定轴入口 id）按对齐下标在原文上取回。
 */
function codeView(source: string, maskStrings: boolean): string {
  const out = source.split('');
  const blank = (from: number, to: number) => {
    for (let at = from; at < to && at < out.length; at += 1) {
      if (out[at] !== '\n') out[at] = ' ';
    }
  };
  let index = 0;
  let quote: string | null = null;
  while (index < source.length) {
    const char = source[index];
    if (quote) {
      if (char === '\\' && index + 1 < source.length) {
        if (maskStrings) {
          out[index] = MASK;
          out[index + 1] = MASK;
        }
        index += 2;
        continue;
      }
      if (char === quote) {
        quote = null;
        index += 1;
        continue;
      }
      if (maskStrings) out[index] = MASK;
      index += 1;
      continue;
    }
    if (char === '"' || char === "'" || char === '`') {
      quote = char;
      index += 1;
      continue;
    }
    if (source.startsWith('<!--', index)) {
      const end = source.indexOf('-->', index + 4);
      const stop = end === -1 ? source.length : end + '-->'.length;
      blank(index, stop);
      index = stop;
      continue;
    }
    if (char === '/' && source[index + 1] === '*') {
      const end = source.indexOf('*/', index + 2);
      const stop = end === -1 ? source.length : end + '*/'.length;
      blank(index, stop);
      index = stop;
      continue;
    }
    if (char === '/' && source[index + 1] === '/' && source[index - 1] !== ':') {
      const end = source.indexOf('\n', index);
      const stop = end === -1 ? source.length : end;
      blank(index, stop);
      index = stop;
      continue;
    }
    index += 1;
  }
  return out.join('');
}

/** 注释清零、字面量原样：属性值里的 `$attrs` 这类「结构标记」只能在这个视图里读。 */
const stripComments = (source: string) => codeView(source, false);
/** 注释清零、字面量内容也掩码：只认这个视图判断「实现是否存在」，字面量诱饵不算实现。 */
const codeOnly = (source: string) => codeView(source, true);

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
const entryCode = (relative: string) => codeOnly(read(relative));
const authoritySource = stripComments(read(AUTHORITY));
const authorityCode = codeOnly(read(AUTHORITY));
const authorityProps = [
  ...(authorityCode.match(/defineProps<\{([\s\S]*?)\}>/) ?? ['', ''])[1].matchAll(/([A-Za-z_]\w*)\??:/g),
].map((match) => match[1]);

/**
 * 从掩码视图里读出「简单字面量」并按**对齐下标**还原原文真值。
 * 掩码视图与原文等长，因此字符串字面量内部的任何诱饵都被整段掩掉，无法伪装成实现；
 * 而掩码段的真实内容仍可在原文上按同一起止位置切回（固定轴入口 id 与绑定标识符都需要真值）。
 */
function maskedLiteral(raw: string, masked: string, pattern: RegExp): { value: string; start: number } | null {
  const match = pattern.exec(masked);
  if (!match || match[1] === undefined) return null;
  const start = match.index + match[0].indexOf(match[1]);
  return { value: raw.slice(start, start + match[1].length), start };
}
const authoritySlots = [...authoritySource.matchAll(/<slot\s+name="([A-Za-z_]\w*)"/g)].map((match) => match[1]);

/**
 * 槽位是输入面：只接受**静态具名槽**，且名字必须已在登记表里显式登记。
 * 默认槽与动态槽名（`:name`）无法静态校验被渲染的内容，一律硬失败而不是静默放行。
 */
function assertRegisteredSlots(owner: string, source: string, allowed: ReadonlySet<string>): void {
  for (const tag of [...source.matchAll(/<slot\b[^>]*>/g)].map((match) => match[0])) {
    const named = tag.match(/^<slot\s+name="([A-Za-z_]\w*)"/);
    assert.ok(
      named,
      `${owner} 的 ${tag} 不是静态具名槽：默认槽与动态槽名无法静态校验，必须显式登记（权威只有 3 个具名槽、无默认槽）`,
    );
    assert.ok(allowed.has(named[1]), `${owner} 暴露了未登记的槽 ${named[1]}：槽位必须与登记表一致`);
  }
}

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
  parseImports(stripComments(read(relative)))
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

// A2. 权威的槽位必须是静态具名槽，且与三个正式槽轴等价。
assertRegisteredSlots(
  'ProductPageHeader',
  authoritySource,
  new Set(SLOT_AXES.map((axis) => axisToSlot(axis) as string)),
);

// A3. 权威不得用 `$attrs` 兜底转发未登记轴：这会绕过「未登记轴必须显式决策」并让调用方静默注入。
assert.ok(
  !/\$attrs/.test(authoritySource),
  'ProductPageHeader 不得用 $attrs 兜底转发未登记轴：未登记轴必须在登记表中显式决策',
);

// B. 每个入口都必须存在、必须在模板中真实渲染上游（权威或已登记入口），且不得自建 header DOM。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  assert.ok(existsSync(path.join(SRC, entry.path)), `登记入口不存在: ${entry.path}`);
  const source = entryCode(entry.path);
  const upstream = delegatedTargets(entry.path);
  assert.ok(upstream.length > 0, `${entry.id} 未导入 ProductPageHeader 或任何已登记入口`);
  assert.ok(
    upstream.some(({ symbol }) => new RegExp(`<${symbol.local}\\b|<${kebab(symbol.local)}\\b`).test(source)),
    `${entry.id} 必须在其模板中真实渲染上游页头组件；只保留 import 不算委托`,
  );
  assert.ok(!/<header[\s>]/.test(source), `${entry.id} 不得自建 header DOM`);
  assert.ok(!/<h1[\s>]/.test(source), `${entry.id} 不得自建 h1，页面标题唯一权威是 ProductPageHeader`);
}

// C. 声明为 forwarded 的轴必须在入口里真实转发（同样只认掩码视图）。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  const source = entryCode(entry.path);
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
  const raw = read(entry.path);
  const masked = entryCode(entry.path);
  for (const disposition of entry.axes) {
    if (disposition.handling !== 'fixed') continue;
    const resolver = FIXED_RESOLVER[disposition.axis] ?? 'resolveProductPageHeaderFixedAxis';
    const name = kebab(disposition.axis);
    assert.ok(
      !new RegExp(`(?<![:\\w-])${name}="`).test(masked),
      `${entry.id} 的固定轴 ${disposition.axis} 仍有静态字面量，必须经 ${resolver} 读取登记表`,
    );
    assert.ok(
      !new RegExp(`:${name}="\\s*['\`]`).test(masked),
      `${entry.id} 的固定轴 ${disposition.axis} 不得绑定字符串字面量，必须绑定 ${resolver} 的返回值`,
    );
    // 绑定值必须是**简单标识符**：掩码视图里该属性值是一整段占位符，说明它是真实模板属性而不是
    // 写在某处字符串里的一句「`:presentation-mode="collectionMode"`」文本。
    const binding = maskedLiteral(raw, masked, new RegExp(`:${name}="(${MASK}+)"`));
    assert.ok(binding, `${entry.id} 的固定轴 ${disposition.axis} 必须以标识符引用形式绑定，而不是字面量`);
    assert.ok(
      /^[A-Za-z_$][\w$]*$/.test(binding.value),
      `${entry.id} 的固定轴 ${disposition.axis} 的绑定值 ${binding.value} 不是标识符`,
    );
    const constName = binding.value;
    const declaration = maskedLiteral(
      raw,
      masked,
      new RegExp(`const\\s+${constName}\\s*=\\s*${resolver}\\(\\s*'(${MASK}+)'\\s*\\)`),
    );
    assert.ok(
      declaration && declaration.value === entry.id,
      `${entry.id} 的固定轴 ${disposition.axis} 绑定值 ${constName} 必须来自 ${resolver}('${entry.id}')，` +
        `不得由装饰性调用或字面量诱饵遮蔽（实际解析到 ${declaration ? `'${declaration.value}'` : '未找到真实声明'}）`,
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
  assertRegisteredSlots(entry.id, source, forwardedSlots);
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

const ENTRY_BASENAMES = new Set([
  ...PRODUCT_PAGE_HEADER_ENTRIES.map((entry) => path.posix.basename(entry.path, '.vue')),
  path.posix.basename(AUTHORITY, '.vue'),
]);
const specifierBasename = (specifier: string) => path.posix.basename(specifier).replace(/\.vue$/, '');
const sourceFiles = walkVue(SRC);
const importsOf = (file: string) => parseImports(stripComments(read(file)));

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
for (const file of sourceFiles) {
  const source = read(file);
  const tagToEntry = new Map<string, ProductPageHeaderEntryRegistry>();
  for (const symbol of importsOf(file)) {
    const target = delegationTarget(file, symbol);
    if (target && target !== 'authority') tagToEntry.set(symbol.local, target);
  }
  if (tagToEntry.size === 0) continue;

  // F1. 动态组件绑定无法静态枚举调用面：绑定到已登记入口即失败，必须显式登记该形态。
  for (const block of tagAttributeBlocks(source, ['component', 'Component'])) {
    for (const dynamic of block.matchAll(/:is=(?:'([^']+)'|"([^"]+)")|v-bind=(?:'([^']+)'|"([^"]+)")/g)) {
      const expression = dynamic[1] ?? dynamic[2] ?? dynamic[3] ?? dynamic[4] ?? '';
      for (const identifier of expression.matchAll(/[A-Za-z_$][\w$]*/g)) {
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
// 否则该调用点会同时躲过 F 与 G。命中判据必须同时看**导入符号名**与**说明符末段**：
// 只看符号名时，`import Foo from '@design-system/ScPageHeader.vue'` 这种「改名 ＋ 不可解析包路径」会整体隐身。
for (const file of sourceFiles) {
  for (const symbol of importsOf(file)) {
    if (
      !ENTRY_BASENAMES.has(symbol.imported) &&
      !ENTRY_BASENAMES.has(symbol.local) &&
      !ENTRY_BASENAMES.has(specifierBasename(symbol.specifier))
    ) {
      continue;
    }
    assert.ok(
      delegationTarget(file, symbol) !== null,
      `${file} 以入口组件同名符号 ${symbol.local} 从 '${symbol.specifier}' 导入，却解析不到登记入口；该导入形态必须显式登记`,
    );
  }
}

// F2b. 改名的入口导入必须显式登记：`import Foo from '…/ScPageHeader.vue'` 配 `<Foo record-count="5" />`
// 会让标签扫描与调用点集合同时失明（标签名不再命中入口 basename）。
const KNOWN_ENTRY_IMPORT_ALIASES: ReadonlySet<string> = new Set([
  // `ContractFormProductHeader` 用 `PageHeaderTemplate` 指明它消费的是「模板页头」入口。
  'pages/contractForm/ContractFormProductHeader.vue#PageHeaderTemplate',
]);
for (const file of sourceFiles) {
  for (const symbol of importsOf(file)) {
    const target = delegationTarget(file, symbol);
    if (target === null) continue;
    const expected = target === 'authority' ? path.posix.basename(AUTHORITY, '.vue') : path.posix.basename(target.path, '.vue');
    if (symbol.local === expected) continue;
    assert.ok(
      KNOWN_ENTRY_IMPORT_ALIASES.has(`${file}#${symbol.local}`),
      `${file} 以 ${symbol.local} 改名导入入口 ${expected}：改名导入会让标签扫描与调用点集合同时失明，必须先显式登记`,
    );
  }
}

// F3. 动态 `import()` 无法静态枚举，说明符命中入口即硬失败（要求先显式登记该形态）。
// 注意 `import('…')` 也可能出现在**类型位置**（`import('./x').T`）：那属于同一类「静态不可枚举」，
// 一并硬失败，避免用类型导入给运行期动态渲染打掩护。
for (const file of sourceFiles) {
  const source = stripComments(read(file));
  for (const dynamic of source.matchAll(/import\s*\(\s*'([^']+)'\s*\)/g)) {
    assert.ok(
      !ENTRY_BASENAMES.has(specifierBasename(dynamic[1])),
      `${file} 动态导入入口 '${dynamic[1]}'：调用面无法静态枚举，必须先显式登记该形态`,
    );
  }
}

// G. 入口集合必须与登记表完全一致：新入口不得静默出现，登记入口不得失去委托。
const authorityConsumers = sourceFiles.filter((file) =>
  importsOf(file).some((symbol) => delegationTarget(file, symbol) === 'authority'),
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
