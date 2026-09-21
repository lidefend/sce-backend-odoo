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
const kebab = (value: string) => value.replace(/[A-Z]/g, (char) => `-${char.toLowerCase()}`);
const camel = (value: string) => value.replace(/-([a-z])/g, (_, char: string) => char.toUpperCase());

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

const authoritySource = read(AUTHORITY);
const authorityProps = [...(authoritySource.match(/defineProps<\{([\s\S]*?)\}>/) ?? ['', ''])[1].matchAll(/([A-Za-z_]\w*)\??:/g)].map(
  (match) => match[1],
);
const authoritySlots = [...authoritySource.matchAll(/<slot\s+name="([A-Za-z_]\w*)"/g)].map((match) => match[1]);

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

// B. 每个入口都必须存在、必须委托权威渲染，且不得自建 header DOM。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  assert.ok(existsSync(path.join(SRC, entry.path)), `登记入口不存在: ${entry.path}`);
  const source = read(entry.path);
  assert.ok(source.includes('ProductPageHeader'), `${entry.id} 未委托 ProductPageHeader 渲染`);
  assert.ok(!/<header[\s>]/.test(source), `${entry.id} 不得自建 header DOM`);
  assert.ok(!/<h1[\s>]/.test(source), `${entry.id} 不得自建 h1，页面标题唯一权威是 ProductPageHeader`);
}

// C. 声明为 forwarded 的轴必须在入口里真实转发。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  const source = read(entry.path);
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

// D. 声明为 fixed 的轴必须单一来源于登记表，入口不得留字面量。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  const source = read(entry.path);
  for (const disposition of entry.axes) {
    if (disposition.handling !== 'fixed') continue;
    const name = kebab(disposition.axis);
    assert.ok(
      !new RegExp(`(?<![:\\w-])${name}="`).test(source),
      `${entry.id} 的固定轴 ${disposition.axis} 仍有字面量，必须经 resolveProductPageHeaderFixedAxis 读取登记表`,
    );
    assert.ok(
      source.includes(`resolveProductPageHeaderFixed${disposition.axis === 'presentationMode' ? 'Mode' : 'Axis'}(`),
      `${entry.id} 的固定轴 ${disposition.axis} 必须由登记表解析`,
    );
    assert.equal(resolveProductPageHeaderFixedAxis(entry.id, disposition.axis), disposition.value);
  }
}

// E. 薄入口的声明面不得超出登记表（不得私自增加权威未登记的输入）。
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  if (entry.kind !== 'adapter') continue;
  const declared = [...(read(entry.path).match(/defineProps<\{([\s\S]*?)\}>/) ?? ['', ''])[1].matchAll(/([A-Za-z_]\w*)\??:/g)].map(
    (match) => match[1],
  );
  const allowed = new Set(
    entry.axes
      .filter((disposition) => disposition.handling !== 'not_exposed')
      .map((disposition) => axisToProp(disposition.axis))
      .filter((prop): prop is ProductPageHeaderAxis => Boolean(prop)),
  );
  for (const prop of declared) {
    assert.ok(allowed.has(prop as ProductPageHeaderAxis), `${entry.id} 声明了未登记输入 ${prop}`);
  }
}

// F. 调用方传给薄入口的属性必须在该入口声明面内：静默丢参必须失败，而不是被 Vue 落成 DOM 属性。
const ENTRY_BY_IMPORT = new Map<string, ProductPageHeaderEntryRegistry>();
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  if (entry.kind !== 'adapter') continue;
  ENTRY_BY_IMPORT.set(entry.path, entry);
}
const PASS_THROUGH = new Set(['class', 'style', 'key', 'ref', 'is', 'slot', 'id']);
function attributeNames(block: string): string[] {
  return [...block.matchAll(/(?:^|\s)(:?[@#]?[A-Za-z_][\w:.-]*)\s*(?:=|(?=\s|$|\/?>))/g)].map((match) => match[1]);
}
let checkedCallSites = 0;
for (const file of walkVue(SRC)) {
  const source = read(file);
  const imports = [...source.matchAll(/import\s+([A-Za-z_]\w*)\s+from\s+'([^']+)'/g)];
  const tagToEntry = new Map<string, ProductPageHeaderEntryRegistry>();
  for (const [, local, specifier] of imports) {
    if (!specifier.startsWith('.')) continue;
    const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(file), specifier));
    const entry = ENTRY_BY_IMPORT.get(resolved);
    if (entry) tagToEntry.set(local, entry);
  }
  for (const [tag, entry] of tagToEntry) {
    const declared = new Set(
      [...(read(entry.path).match(/defineProps<\{([\s\S]*?)\}>/) ?? ['', ''])[1].matchAll(/([A-Za-z_]\w*)\??:/g)].map(
        (match) => match[1],
      ),
    );
    for (const usage of source.matchAll(new RegExp(`<${tag}\\b([\\s\\S]*?)/?>`, 'g'))) {
      checkedCallSites += 1;
      for (const rawName of attributeNames(usage[1])) {
        const name = rawName.replace(/^(:|@|#|v-bind:|v-on:)/, '');
        if (rawName.startsWith('#') || rawName.startsWith('v-') || rawName.startsWith('@')) continue;
        if (name.startsWith('data-') || name.startsWith('aria-')) continue;
        if (PASS_THROUGH.has(name)) continue;
        const camelName = camel(name);
        assert.ok(
          declared.has(camelName),
          `${file} 向 ${entry.id} 传入 ${name}，但该入口未声明：静默丢参必须改为显式登记或显式转发`,
        );
      }
    }
  }
}
assert.ok(checkedCallSites > 0, '未扫描到任何薄入口调用点');

// G. 入口集合必须与登记表完全一致：新入口不得静默出现，登记入口不得失去委托。
const localImports = (file: string): string[] =>
  [...read(file).matchAll(/import\s+[A-Za-z_$][\w$]*\s+from\s+'([^']+)'/g)]
    .filter((match) => match[1].startsWith('.'))
    .map((match) => path.posix.normalize(path.posix.join(path.posix.dirname(file), match[1])));
const authorityConsumers = walkVue(SRC).filter((file) => localImports(file).includes(AUTHORITY));
const directExpected = [
  ...PRODUCT_PAGE_HEADER_ENTRIES.filter((entry) => entry.kind === 'adapter').map((entry) => entry.path),
  ...PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS,
];
assert.deepEqual(
  [...authorityConsumers].sort(),
  [...directExpected].sort(),
  '直接消费 ProductPageHeader 的入口集合必须与登记表（薄入口 ＋ 直接消费页面）完全一致',
);
const registeredPaths = new Set(PRODUCT_PAGE_HEADER_ENTRIES.map((entry) => entry.path));
for (const entry of PRODUCT_PAGE_HEADER_ENTRIES) {
  const imports = localImports(entry.path);
  assert.ok(
    imports.includes(AUTHORITY) || imports.some((specifier) => registeredPaths.has(specifier)),
    `${entry.path} 未委托 ProductPageHeader 或任何已登记入口渲染`,
  );
}
for (const consumer of PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS) {
  assert.ok(existsSync(path.join(SRC, consumer)), `登记的权威直接消费页面不存在: ${consumer}`);
}

// H. 登记表自身可解析：入口 id 唯一，且 not_exposed 必须给出理由。
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
assert.deepEqual(SLOT_AXES, ['metaSlot', 'statusSlot', 'actionsSlot']);

console.log(
  `[product_page_header_adapter_contract] PASS entries=${PRODUCT_PAGE_HEADER_ENTRIES.length} axes=${PRODUCT_PAGE_HEADER_AXES.length} call_sites=${checkedCallSites} direct_consumers=${PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS.length}`,
);
