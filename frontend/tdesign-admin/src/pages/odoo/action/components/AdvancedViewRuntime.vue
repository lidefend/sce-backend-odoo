<template>
  <section class="advanced-view">
    <header class="advanced-toolbar">
      <div>
        <strong>{{ viewTitle }}</strong>
        <span>{{ summaryText }}</span>
      </div>
      <t-tag v-if="rendererNotice" theme="warning" variant="light">{{ rendererNotice }}</t-tag>
    </header>

    <div v-if="mode === 'graph'" ref="chartRef" class="chart" />
    <t-table v-else-if="mode === 'pivot'" :data="pivotRows" :columns="pivotColumns" row-key="key" bordered stripe>
      <template #total="{ row }">{{ formatNumber(row.total) }}</template>
      <template #measure_1="{ row }">{{ formatNumber(row.measure_1) }}</template>
      <template #measure_2="{ row }">{{ formatNumber(row.measure_2) }}</template>
    </t-table>

    <section v-else-if="mode === 'calendar'" class="calendar-view">
      <div class="calendar-controls">
        <t-button size="small" variant="outline" @click="shiftCalendar(-1)">上个月</t-button>
        <strong>{{ calendarMonth }}</strong>
        <t-button size="small" variant="outline" @click="shiftCalendar(1)">下个月</t-button>
      </div>
      <div class="calendar-weekdays">
        <span v-for="day in weekdays" :key="day">{{ day }}</span>
      </div>
      <div class="calendar-grid">
        <article
          v-for="day in calendarDays"
          :key="day.key"
          class="calendar-day"
          :class="{ 'calendar-day--outside': !day.inMonth, 'calendar-day--today': day.today }"
        >
          <time>{{ day.day }}</time>
          <button
            v-for="item in day.items"
            :key="String(item.row.id)"
            type="button"
            class="calendar-entry"
            @click="$emit('open', item.row)"
          >
            <strong>{{ title(item.row) }}</strong
            ><small>{{ item.summary }}</small>
          </button>
        </article>
      </div>
      <t-empty v-if="!calendarDays.some((day) => day.items.length)" description="当前记录没有可展示的日期字段" />
    </section>

    <section v-else-if="mode === 'gantt'" class="gantt-list">
      <article
        v-for="item in ganttRows"
        :key="String(item.row.id)"
        class="gantt-row"
        draggable="true"
        @dragstart="startGanttDrag(item.row)"
        @dragover.prevent
        @drop="dropGantt(item.row)"
        @click="$emit('open', item.row)"
      >
        <div class="gantt-row__identity">
          <strong>{{ title(item.row) }}</strong
          ><small>{{ item.start }} 至 {{ item.end }}</small>
        </div>
        <div class="gantt-track">
          <span :style="{ left: `${item.left}%`, width: `${item.width}%` }" /><b
            v-if="item.progress !== null"
            :style="{ left: `${Math.min(item.left + item.width, 96)}%` }"
            >{{ item.progress }}%</b
          >
        </div>
      </article>
      <t-empty v-if="!ganttRows.length" description="当前记录没有可展示的起止日期" />
    </section>

    <t-list v-else-if="mode === 'activity'" split>
      <t-list-item
        v-for="item in activityRows"
        :key="String(item.row.id)"
        class="activity-row"
        @click="$emit('open', item.row)"
      >
        <div class="activity-row__body">
          <strong>{{ title(item.row) }}</strong>
          <p>{{ item.summary }}</p>
          <small
            >{{ item.status }}<span v-if="item.priority"> · {{ item.priority }}</span></small
          >
        </div>
        <template #action>
          <t-space size="small">
            <t-tag :theme="item.overdue ? 'danger' : item.done ? 'success' : 'primary'" variant="light">{{
              item.date || '待安排'
            }}</t-tag>
            <t-button
              v-if="item.activityId && !item.done"
              size="small"
              theme="success"
              variant="text"
              @click.stop="$emit('activity-action', { row: item.row, activityId: item.activityId, action: 'done' })"
              >完成</t-button
            >
            <t-button
              v-if="item.activityId && !item.done"
              size="small"
              theme="danger"
              variant="text"
              @click.stop="$emit('activity-action', { row: item.row, activityId: item.activityId, action: 'cancel' })"
              >取消</t-button
            >
            <t-button
              v-if="item.activityId && !item.done"
              size="small"
              variant="text"
              @click.stop="
                $emit('activity-action', { row: item.row, activityId: item.activityId, action: 'reschedule' })
              "
              >改期</t-button
            >
          </t-space>
        </template>
      </t-list-item>
      <t-empty v-if="!activityRows.length" description="暂无活动记录" />
    </t-list>
  </section>
</template>
<script setup lang="ts">
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

import type { ActionSurfaceViewMode } from '../runtime/actionSurfaceRegistry';

type Dict = Record<string, any>;
interface Field {
  code: string;
  label: string;
  type: string;
  config?: Dict;
}
interface DatedRow {
  row: Dict;
  date: string;
  summary: string;
}

const props = defineProps<{
  mode: ActionSurfaceViewMode;
  rows: Dict[];
  fields: Field[];
  config?: Dict;
  aggregates?: Dict;
  groupedRows?: Dict[];
}>();
const emit = defineEmits<{
  open: [row: Dict];
  'activity-action': [payload: { row: Dict; activityId: number; action: 'done' | 'cancel' | 'reschedule' }];
  'timeline-change': [payload: { row: Dict; start?: string; end?: string }];
}>();
echarts.use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);
const chartRef = ref<HTMLElement>();
let chart: echarts.ECharts | undefined;
const config = computed(() => (props.config || {}) as Dict);
const rawConfig = computed(() => (config.value.view || config.value.config || config.value) as Dict);
const viewTitle = computed(
  () =>
    (
      ({
        pivot: '透视分析',
        graph: '图表分析',
        calendar: '日历视图',
        gantt: '甘特计划',
        activity: '活动视图',
      }) as Record<string, string>
    )[props.mode] || '高级视图',
);
const rendererNotice = computed(() => String(rawConfig.value.reason_code || rawConfig.value.reasonCode || ''));
const summaryText = computed(() => {
  const summary = measureFields.value
    .map((field) => {
      const aggregate = (props.aggregates?.[field.code] || {}) as Dict;
      const total = aggregate.sum ?? aggregate.total;
      return total === undefined ? '' : `${field.label}合计 ${formatNumber(total)}`;
    })
    .filter(Boolean)
    .join(' · ');
  return `${props.rows.length} 条记录 · ${dimensionFields.value.map((field) => field.label).join('、') || '无维度'}${summary ? ` · ${summary}` : ''}`;
});
const weekdays = ['一', '二', '三', '四', '五', '六', '日'];
const calendarCursor = ref('');
const ganttDragRow = ref<Dict | null>(null);
const dateFields = computed(() => props.fields.filter((field) => ['date', 'datetime'].includes(field.type)));
const summaryField = computed(() =>
  props.fields.find((field) => /summary|subject|title|activity|note|description/.test(field.code)),
);
const dimensionFields = computed(() => {
  const configured = rawConfig.value.dimensions || rawConfig.value.dimension_fields || rawConfig.value.group_by;
  const codes = Array.isArray(configured) ? configured.map((item) => String(item?.field || item?.code || item)) : [];
  const selected = codes.map((code) => props.fields.find((field) => field.code === code)).filter(Boolean) as Field[];
  return selected.length
    ? selected
    : ([props.fields.find((field) => ['selection', 'many2one', 'char'].includes(field.type)) || props.fields[0]].filter(
        Boolean,
      ) as Field[]);
});
const measureFields = computed(() => {
  const configured = rawConfig.value.measures || rawConfig.value.measure_fields;
  const codes = Array.isArray(configured) ? configured.map((item) => String(item?.field || item?.code || item)) : [];
  const selected = codes.map((code) => props.fields.find((field) => field.code === code)).filter(Boolean) as Field[];
  return selected.length
    ? selected
    : props.fields.filter((field) => ['integer', 'float', 'monetary'].includes(field.type)).slice(0, 3);
});
const pivotColumnField = computed(() => {
  const configured =
    rawConfig.value.column_dimensions || rawConfig.value.columnDimensions || rawConfig.value.col_group_by;
  const code = Array.isArray(configured)
    ? String(configured[0]?.field || configured[0]?.code || configured[0] || '')
    : '';
  return props.fields.find((field) => field.code === code) || dimensionFields.value[1];
});
const pivotRowField = computed(
  () => dimensionFields.value.find((field) => field.code !== pivotColumnField.value?.code) || dimensionFields.value[0],
);
const dateField = computed(
  () =>
    props.fields.find(
      (field) => field.code === String(rawConfig.value.date_field || rawConfig.value.dateField || ''),
    ) || dateFields.value[0],
);
const startField = computed(
  () =>
    props.fields.find(
      (field) => field.code === String(rawConfig.value.start_field || rawConfig.value.startField || ''),
    ) || dateFields.value[0],
);
const endField = computed(
  () =>
    props.fields.find((field) => field.code === String(rawConfig.value.end_field || rawConfig.value.endField || '')) ||
    dateFields.value[1] ||
    dateFields.value[0],
);
const progressField = computed(
  () =>
    props.fields.find(
      (field) => field.code === String(rawConfig.value.progress_field || rawConfig.value.progressField || ''),
    ) || props.fields.find((field) => /progress|percent|rate/.test(field.code)),
);

function raw(value: unknown) {
  return Array.isArray(value) ? (value[1] ?? value[0]) : value;
}
function title(row: Dict) {
  return String(row.name || row.display_name || row.code || row.title || row.id || '记录');
}
function displayDate(value: unknown) {
  return String(raw(value) || '').slice(0, 10);
}
function localDateKey(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
}
function numberValue(value: unknown) {
  const number = Number(raw(value) || 0);
  return Number.isFinite(number) ? number : 0;
}
function formatNumber(value: unknown) {
  return numberValue(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}

const pivotRows = computed(() => {
  if (pivotColumnField.value && pivotRowField.value) {
    const matrix = new Map<string, Dict>();
    props.rows.forEach((row) => {
      const rowKey = String(raw(row[pivotRowField.value!.code]) || '未分类');
      const columnKey = String(raw(row[pivotColumnField.value!.code]) || '未分类');
      const item = matrix.get(rowKey) || { key: rowKey, dimension: rowKey, count: 0, total: 0 };
      const value = measureFields.value[0] ? numberValue(row[measureFields.value[0].code]) : 1;
      item.count += 1;
      item.total += value;
      item[`column:${columnKey}`] = Number(item[`column:${columnKey}`] || 0) + value;
      matrix.set(rowKey, item);
    });
    return [...matrix.values()];
  }
  const grouped = (props.groupedRows || []).map((group) => {
    const aggregates = (group.aggregates || {}) as Dict;
    const firstMeasure = measureFields.value[0]?.code || '';
    const aggregate = (aggregates[firstMeasure] || {}) as Dict;
    return {
      key: String(group.group_key || group.key || group.label || '未分类'),
      dimension: String(group.label || group.value || group.group_key || '未分类'),
      count: Number(group.total_count || group.count || 0),
      total: Number(aggregate.sum ?? aggregate.total ?? 0),
    };
  });
  if (grouped.length) return grouped;
  const groups = new Map<string, Dict>();
  props.rows.forEach((row) => {
    const values = dimensionFields.value.map((field) => String(raw(row[field.code]) || '未分类'));
    const key = values.join(' / ');
    const group = groups.get(key) || { key, dimension: key, count: 0, total: 0 };
    group.count += 1;
    measureFields.value.forEach((field, index) => {
      const measureKey = index === 0 ? 'total' : `measure_${index}`;
      group[measureKey] = Number(group[measureKey] || 0) + numberValue(row[field.code]);
    });
    groups.set(key, group);
  });
  return [...groups.values()];
});
const pivotColumnValues = computed(() =>
  pivotColumnField.value
    ? [...new Set(props.rows.map((row) => String(raw(row[pivotColumnField.value!.code]) || '未分类')))]
    : [],
);
const pivotColumns = computed(() => [
  {
    colKey: 'dimension',
    title: dimensionFields.value.map((field) => field.label).join(' / ') || '维度',
    minWidth: 220,
  },
  { colKey: 'count', title: '记录数', width: 100 },
  ...pivotColumnValues.value.map((value) => ({ colKey: `column:${value}`, title: value, minWidth: 120 })),
  ...measureFields.value.map((field, index) => ({
    colKey: index === 0 ? 'total' : `measure_${index}`,
    title: `${field.label}合计`,
    minWidth: 140,
  })),
]);
const datedRows = computed<DatedRow[]>(() =>
  props.rows
    .map((row) => ({
      row,
      date: displayDate(row[dateField.value?.code || '']),
      summary: String(raw(row[summaryField.value?.code || '']) || ''),
    }))
    .filter((item) => item.date),
);
const calendarMonth = computed(
  () =>
    calendarCursor.value ||
    String(
      rawConfig.value.month ||
        rawConfig.value.calendar_month ||
        datedRows.value[0]?.date ||
        new Date().toISOString().slice(0, 7),
    ).slice(0, 7),
);
function shiftCalendar(delta: number) {
  const [year, month] = calendarMonth.value.split('-').map(Number);
  const next = new Date(year, month - 1 + delta, 1);
  calendarCursor.value = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}`;
}
function startGanttDrag(row: Dict) {
  ganttDragRow.value = row;
}
function dropGantt(row: Dict) {
  const source = ganttDragRow.value;
  if (!source || source === row) return;
  const sourceStart = Date.parse(displayDate(source[startField.value?.code || '']));
  const sourceEnd = Date.parse(displayDate(source[endField.value?.code || '']));
  const targetStart = Date.parse(displayDate(row[startField.value?.code || '']));
  if (![sourceStart, sourceEnd, targetStart].every(Number.isFinite)) return;
  const duration = Math.max(sourceEnd - sourceStart, 0);
  emit('timeline-change', {
    row: source,
    start: localDateKey(new Date(targetStart)),
    end: localDateKey(new Date(targetStart + duration)),
  });
  ganttDragRow.value = null;
}
const calendarDays = computed(() => {
  const [year, month] = calendarMonth.value.split('-').map(Number);
  const first = new Date(year, month - 1, 1);
  const start = new Date(year, month - 1, 1 - ((first.getDay() + 6) % 7));
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    const key = localDateKey(date);
    return {
      key,
      day: date.getDate(),
      inMonth: date.getMonth() === month - 1,
      today: key === localDateKey(new Date()),
      items: datedRows.value.filter((item) => item.date === key),
    };
  });
});
const ganttRows = computed(() => {
  const source = props.rows
    .map((row) => ({
      row,
      start: displayDate(row[startField.value?.code || '']),
      end: displayDate(row[endField.value?.code || '']),
      progress: progressField.value ? Math.max(0, Math.min(100, numberValue(row[progressField.value.code]))) : null,
    }))
    .filter((item) => item.start && item.end);
  const times = source.flatMap((item) => [Date.parse(item.start), Date.parse(item.end)]);
  if (!times.length) return [];
  const min = Math.min(...times);
  const max = Math.max(...times);
  const span = Math.max(max - min, 86_400_000);
  return source.map((item) => ({
    ...item,
    left: ((Date.parse(item.start) - min) / span) * 100,
    width: Math.max(((Date.parse(item.end) - Date.parse(item.start)) / span) * 100, 2),
  }));
});
const activityRows = computed(() => {
  const statusField = props.fields.find((field) => /activity_state|state|status|stage/.test(field.code));
  const priorityField = props.fields.find((field) => /priority|urgency/.test(field.code));
  return props.rows.map((row) => {
    const date = displayDate(row[dateField.value?.code || '']);
    const status = String(raw(row[statusField?.code || '']) || '待处理');
    return {
      row,
      activityId: Number(row.activity_id || row.activityId || row.activity?.id || 0) || undefined,
      date,
      summary: String(raw(row[summaryField.value?.code || '']) || '业务活动'),
      status,
      priority: String(raw(row[priorityField?.code || '']) || ''),
      overdue: Boolean(date && Date.parse(date) < Date.now()),
      done: /done|complete|完成|已完成/i.test(status),
    };
  });
});

async function renderChart() {
  if (props.mode !== 'graph') return;
  await nextTick();
  if (!chartRef.value) return;
  chart ||= echarts.init(chartRef.value);
  const chartType = String(rawConfig.value.chart_type || rawConfig.value.chartType || 'bar').toLowerCase();
  const values = pivotRows.value.map((item) => Number(item.total || item.count || 0));
  const labels = pivotRows.value.map((item) => String(item.dimension || item.key));
  const isPie = chartType === 'pie';
  chart.setOption({
    tooltip: { trigger: isPie ? 'item' : 'axis' },
    legend: isPie ? { bottom: 0 } : undefined,
    grid: isPie ? undefined : { left: 48, right: 24, top: 24, bottom: 64 },
    xAxis: isPie ? undefined : { type: 'category', data: labels, axisLabel: { rotate: labels.length > 8 ? 30 : 0 } },
    yAxis: isPie ? undefined : { type: 'value' },
    series: [
      {
        type: isPie ? 'pie' : chartType === 'line' ? 'line' : 'bar',
        data: isPie ? labels.map((name, index) => ({ name, value: values[index] })) : values,
        smooth: chartType === 'line',
        itemStyle: { color: '#0052d9' },
      },
    ],
  });
  chart.resize();
}
watch(() => [props.mode, props.rows, props.config], renderChart, { deep: true, immediate: true });
onBeforeUnmount(() => chart?.dispose());
</script>
<style scoped>
.advanced-view {
  min-height: 420px;
}
.advanced-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--td-text-color-secondary);
}
.advanced-toolbar strong {
  color: var(--td-text-color-primary);
}
.advanced-toolbar span {
  margin-left: 10px;
  font-size: 12px;
}
.chart {
  width: 100%;
  height: 460px;
}
.calendar-view {
  display: grid;
  gap: 6px;
}
.calendar-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.calendar-weekdays,
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(120px, 1fr));
  gap: 6px;
  overflow-x: auto;
}
.calendar-weekdays span {
  padding: 6px 10px;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.calendar-day {
  min-height: 100px;
  padding: 8px;
  border: 1px solid var(--td-border-level-1-color);
  background: var(--td-bg-color-container);
}
.calendar-day--outside {
  opacity: 0.55;
  background: var(--td-bg-color-secondarycontainer);
}
.calendar-day--today {
  border-color: var(--td-brand-color);
}
.calendar-day time {
  display: block;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.calendar-entry {
  display: grid;
  width: 100%;
  gap: 3px;
  padding: 6px;
  margin-top: 6px;
  border: 0;
  border-left: 3px solid var(--td-brand-color);
  background: var(--td-brand-color-light);
  text-align: left;
  cursor: pointer;
}
.calendar-entry strong,
.calendar-entry small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.calendar-entry small,
.gantt-row small,
.activity-row small {
  color: var(--td-text-color-secondary);
}
.gantt-list {
  display: grid;
  gap: 12px;
}
.gantt-row {
  display: grid;
  grid-template-columns: minmax(180px, 280px) 1fr;
  gap: 18px;
  align-items: center;
  cursor: pointer;
}
.gantt-row__identity {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.gantt-row__identity strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gantt-track {
  position: relative;
  height: 26px;
  background: var(--td-bg-color-secondarycontainer);
  border-radius: 4px;
  overflow: visible;
}
.gantt-track span {
  position: absolute;
  top: 4px;
  height: 18px;
  background: var(--td-brand-color);
  border-radius: 3px;
}
.gantt-track b {
  position: absolute;
  top: 4px;
  transform: translateX(8px);
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.activity-row {
  cursor: pointer;
}
.activity-row__body {
  display: grid;
  gap: 4px;
}
.activity-row__body p {
  margin: 0;
  color: var(--td-text-color-secondary);
}
@media (max-width: 720px) {
  .advanced-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .gantt-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }
}
</style>
