<template>
  <main class="acceptance-shell">
    <header>
      <p class="acceptance-eyebrow">SC Design System</p>
      <h1>企业 UI 引擎验收夹具</h1>
      <p>仅验证通用组件引擎、语义令牌、交互和响应式，不包含业务或客户语义。</p>
    </header>

    <section aria-labelledby="controls-title">
      <h2 id="controls-title">基础控件</h2>
      <div class="acceptance-controls">
        <ScButton variant="primary" @click="dialogOpen = true">打开对话框</ScButton>
        <ScButton @click="drawerOpen = true">打开抽屉</ScButton>
        <ScStatusBadge value="ready" label="可用" semantic="success" />
        <label>选项<ScSelect v-model="selectedOption"><option value="a">选项 A</option><option value="b">选项 B</option></ScSelect></label>
        <label>日期<ScDateField v-model="selectedDate" /></label>
        <label>文本<ScTextField v-model="textValue" label="文本" /></label>
        <label>说明<ScTextArea v-model="notesValue" label="说明" :rows="3" /></label>
        <ScCheckbox v-model="confirmed" label="确认统一控件">确认统一控件</ScCheckbox>
      </div>
      <p role="status">当前选项：{{ selectedOption }}；当前日期：{{ selectedDate }}；文本：{{ textValue }}；说明：{{ notesValue }}；确认：{{ confirmed ? '是' : '否' }}</p>
    </section>

    <section aria-labelledby="hierarchy-title">
      <h2 id="hierarchy-title">层级表格</h2>
      <ScHierarchyTable
        label="通用层级数据"
        :columns="columns"
        :rows="visibleRows"
        outline-column="name"
        code-column="code"
        :selected-key="selectedKey"
        @select="selectedKey = $event.key"
        @open="openedKey = $event.key"
        @toggle="toggleRow"
      />
      <p role="status">已选择：{{ selectedKey || '无' }}；已打开：{{ openedKey || '无' }}</p>
    </section>

    <ScDialog :open="dialogOpen" title="通用对话框" close-label="关闭对话框" @close="dialogOpen = false">
      <p>对话框内容使用产品语义组件承载。</p>
      <template #actions><ScButton variant="primary" @click="dialogOpen = false">确认</ScButton></template>
    </ScDialog>
    <ScDrawer :open="drawerOpen" title="通用抽屉" close-label="关闭抽屉" @close="drawerOpen = false">
      <p>抽屉内容使用统一主题和焦点管理。</p>
    </ScDrawer>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ScButton from '../src/components/design-system/ScButton.vue';
import ScCheckbox from '../src/components/design-system/ScCheckbox.vue';
import ScDateField from '../src/components/design-system/ScDateField.vue';
import ScDialog from '../src/components/design-system/ScDialog.vue';
import ScDrawer from '../src/components/design-system/ScDrawer.vue';
import ScHierarchyTable, {
  type ScHierarchyTableColumn,
  type ScHierarchyTableRow,
} from '../src/components/design-system/ScHierarchyTable.vue';
import ScSelect from '../src/components/design-system/ScSelect.vue';
import ScStatusBadge from '../src/components/design-system/ScStatusBadge.vue';
import ScTextArea from '../src/components/design-system/ScTextArea.vue';
import ScTextField from '../src/components/design-system/ScTextField.vue';

const dialogOpen = ref(false);
const drawerOpen = ref(false);
const selectedOption = ref('a');
const selectedDate = ref('2026-08-12');
const textValue = ref('初始值');
const notesValue = ref('初始说明');
const confirmed = ref(false);
const selectedKey = ref<string | number>();
const openedKey = ref<string | number>();
const expanded = ref(true);
const columns: ScHierarchyTableColumn[] = [
  { key: 'code', label: '编码', width: 180 },
  { key: 'name', label: '名称', width: 360 },
  { key: 'state', label: '状态', width: 160 },
  { key: 'amount', label: '数值', width: 180, align: 'right' },
];
const rows = computed<ScHierarchyTableRow[]>(() => [
  { key: 'root', depth: 0, expandable: true, expanded: expanded.value, values: { code: 'NODE-01', name: '父节点', state: '进行中', amount: '36,398.87' }, tone: 'group' },
  ...(expanded.value ? [
    { key: 'child-a', depth: 1, expandable: false, expanded: false, values: { code: 'NODE-01.01', name: '子节点 A', state: '可用', amount: '18,199.43' } },
    { key: 'child-b', depth: 1, expandable: false, expanded: false, values: { code: 'NODE-01.02', name: '子节点 B', state: '需关注', amount: '18,199.44' }, cellTones: { amount: 'warning' } },
  ] as ScHierarchyTableRow[] : []),
]);
const visibleRows = computed(() => rows.value);
function toggleRow(row: ScHierarchyTableRow): void {
  if (row.key === 'root') expanded.value = !expanded.value;
}
</script>

<style scoped>
.acceptance-shell {
  display: grid;
  width: min(1180px, calc(100% - 2 * var(--sc-product-page-gutter)));
  margin-inline: auto;
  padding-block: var(--sc-product-space-4);
  gap: var(--sc-product-space-3);
}

header,
section {
  min-width: 0;
  padding: var(--sc-product-space-3);
  border: 1px solid var(--sc-semantic-border-default);
  border-radius: var(--sc-product-radius-panel);
  background: var(--sc-semantic-surface-panel);
}

h1,
h2,
p {
  margin-top: 0;
}

.acceptance-eyebrow {
  color: var(--sc-semantic-text-brand);
  font-weight: 700;
}

.acceptance-controls {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: end;
  gap: var(--sc-product-space-2);
}

label {
  display: grid;
  gap: var(--sc-product-space-1);
  color: var(--sc-semantic-text-secondary);
}

@media (max-width: 1100px) {
  .acceptance-controls {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .acceptance-shell {
    width: 100%;
    padding: var(--sc-product-space-2);
  }

  .acceptance-controls {
    grid-template-columns: 1fr;
  }
}
</style>
