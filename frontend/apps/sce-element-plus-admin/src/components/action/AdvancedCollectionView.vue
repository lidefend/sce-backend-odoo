<template>
  <div class="advanced-view">
    <template v-if="mode === 'pivot'"
      ><el-table :data="summaryRows" stripe
        ><el-table-column
          prop="label"
          :label="dimension?.label || '维度'" /><el-table-column
          prop="count"
          label="数量" /><el-table-column
          prop="total"
          :label="measure ? `${measure.label}汇总` : '汇总'" /></el-table
    ></template>
    <template v-else-if="mode === 'graph'"
      ><div class="graph-bars">
        <div v-for="item in summaryRows" :key="item.key" class="graph-row">
          <span>{{ item.label }}</span>
          <div class="graph-track">
            <b
              :style="{
                width: `${Math.max((Number(item.total || item.count) / graphMax) * 100, 2)}%`,
              }"
            />
          </div>
          <strong>{{ item.total || item.count }}</strong>
        </div>
      </div></template
    >
    <template v-else-if="mode === 'calendar'"
      ><div class="calendar-toolbar">
        <el-button @click="moveMonth(-1)">上月</el-button
        ><strong>{{ calendarCursor }}</strong
        ><el-button @click="moveMonth(1)">下月</el-button>
      </div>
      <div class="calendar-week">
        <span
          v-for="day in ['一', '二', '三', '四', '五', '六', '日']"
          :key="day"
          >{{ day }}</span
        >
      </div>
      <div class="calendar-grid">
        <div
          v-for="day in calendarDays"
          :key="day.key"
          class="calendar-day"
          :class="{ muted: !day.current }"
        >
          <time>{{ day.date }}</time
          ><button
            v-for="row in day.rows.slice(0, 3)"
            :key="row.id"
            @click="$emit('open', row)"
          >
            {{ title(row) }}</button
          ><small v-if="day.rows.length > 3">+{{ day.rows.length - 3 }}</small>
        </div>
      </div></template
    >
    <template v-else-if="mode === 'gantt'"
      ><div class="gantt-list">
        <div
          v-for="item in ganttRows"
          :key="item.row.id"
          class="gantt-row"
          @click="$emit('open', item.row)"
        >
          <div>
            <strong>{{ title(item.row) }}</strong
            ><small>{{ item.start }} - {{ item.end }}</small>
          </div>
          <div class="gantt-track">
            <b :style="{ left: `${item.left}%`, width: `${item.width}%` }" />
          </div>
        </div></div
    ></template>
    <template v-else
      ><el-table :data="rows" stripe
        ><el-table-column label="事项" min-width="220"
          ><template #default="{ row }"
            ><strong>{{ title(row) }}</strong
            ><small class="activity-note">{{
              row.summary || row.description || row.note || ""
            }}</small></template
          ></el-table-column
        ><el-table-column
          :prop="dateField?.code"
          label="截止日期"
          width="150"
        /><el-table-column :prop="statusField?.code" label="状态" width="130"
          ><template #default="{ row }"
            ><el-tag effect="plain" :type="statusType(row[statusField?.code || ''])">{{
              displayFieldValue(row[statusField?.code || ""], statusField?.code || "", statusField?.selection || [])
            }}</el-tag></template
          ></el-table-column
        ><el-table-column label="操作" width="90"
          ><template #default="{ row }"
            ><el-button link type="primary" @click="$emit('open', row)"
              >打开</el-button
            ></template
          ></el-table-column
        ></el-table
      ></template
    >
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { Dictionary, FieldSpec } from "@/types/contracts";
import { displayFieldValue, displayValue } from "@/utils/format";
import { statusTagType } from "@/utils/widget";
const props = defineProps<{
  mode: "pivot" | "graph" | "calendar" | "gantt" | "activity";
  rows: Dictionary[];
  fields: FieldSpec[];
  config?: Dictionary;
}>();
defineEmits<{ open: [row: Dictionary] }>();
const numeric = computed(() =>
  props.fields.filter((field) =>
    ["integer", "float", "monetary"].includes(field.type),
  ),
);
const dimensions = computed(() =>
  props.fields.filter((field) =>
    ["selection", "many2one", "char"].includes(field.type),
  ),
);
const dateFields = computed(() =>
  props.fields.filter((field) => ["date", "datetime"].includes(field.type)),
);
const dimension = computed(
  () =>
    dimensions.value.find(
      (field) => field.code === props.config?.dimension_field,
    ) || dimensions.value[0],
);
const measure = computed(
  () =>
    numeric.value.find((field) => field.code === props.config?.measure_field) ||
    numeric.value[0],
);
const dateField = computed(
  () =>
    dateFields.value.find((field) => field.code === props.config?.date_field) ||
    dateFields.value[0],
);
const statusField = computed(() =>
  props.fields.find((field) => /state|status|stage/.test(field.code)),
);
function statusType(value: unknown) {
  return statusTagType(displayFieldValue(
    value,
    statusField.value?.code || "",
    statusField.value?.selection || [],
    statusField.value?.type || "",
  ));
}
const summaryRows = computed(() => {
  const groups = new Map<
    string,
    { key: string; label: string; count: number; total: number }
  >();
  props.rows.forEach((row) => {
    const raw = row[dimension.value?.code || ""];
    const key = String(Array.isArray(raw) ? raw[0] : (raw ?? ""));
    const display = displayFieldValue(raw, dimension.value?.code || "", dimension.value?.selection || []);
    const label = display === "-" ? "未分类" : display;
    const current = groups.get(key) || { key, label, count: 0, total: 0 };
    current.count += 1;
    current.total += Number(row[measure.value?.code || ""] || 0);
    groups.set(key, current);
  });
  return [...groups.values()];
});
const graphMax = computed(() =>
  Math.max(
    ...summaryRows.value.map((row) => Number(row.total || row.count)),
    1,
  ),
);
const calendarCursor = ref(new Date().toISOString().slice(0, 7));
function moveMonth(offset: number) {
  const [year, month] = calendarCursor.value.split("-").map(Number);
  const next = new Date(year, month - 1 + offset, 1);
  calendarCursor.value = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}
const calendarDays = computed(() => {
  const [year, month] = calendarCursor.value.split("-").map(Number);
  const start = new Date(year, month - 1, 1);
  const gridStart = new Date(start);
  gridStart.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);
    const key = date.toISOString().slice(0, 10);
    return {
      key,
      date: date.getDate(),
      current: date.getMonth() === month - 1,
      rows: props.rows.filter(
        (row) =>
          String(row[dateField.value?.code || ""] || "").slice(0, 10) === key,
      ),
    };
  });
});
const ganttRows = computed(() => {
  const startField =
    dateFields.value.find((field) => /start|begin/.test(field.code)) ||
    dateFields.value[0];
  const endField =
    dateFields.value.find(
      (field) =>
        /end|deadline|date$/.test(field.code) &&
        field.code !== startField?.code,
    ) ||
    dateFields.value[1] ||
    startField;
  const dated = props.rows
    .map((row) => ({
      row,
      start: String(row[startField?.code || ""] || "").slice(0, 10),
      end: String(
        row[endField?.code || ""] || row[startField?.code || ""] || "",
      ).slice(0, 10),
    }))
    .filter((item) => item.start);
  const times = dated
    .flatMap((item) => [Date.parse(item.start), Date.parse(item.end)])
    .filter(Number.isFinite);
  const min = Math.min(...times);
  const max = Math.max(...times, min + 86400000);
  return dated.map((item) => ({
    ...item,
    left: ((Date.parse(item.start) - min) / (max - min)) * 100,
    width: Math.max(
      ((Date.parse(item.end) - Date.parse(item.start)) / (max - min)) * 100,
      2,
    ),
  }));
});
function title(row: Dictionary) {
  return String(
    row.display_name ||
      row.name ||
      row.title ||
      row.subject ||
      `记录 #${row.id || ""}`,
  );
}
</script>

<style scoped>
.advanced-view {
  min-height: 260px;
}
.graph-bars {
  display: grid;
  gap: 14px;
  padding: 20px;
}
.graph-row {
  display: grid;
  grid-template-columns: 160px minmax(120px, 1fr) 100px;
  align-items: center;
  gap: 12px;
}
.graph-track {
  height: 18px;
  background: var(--el-fill-color-light);
  border-radius: 3px;
  overflow: hidden;
}
.graph-track b {
  display: block;
  height: 100%;
  background: var(--el-color-primary);
}
.calendar-toolbar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-bottom: 12px;
}
.calendar-week,
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}
.calendar-week span {
  text-align: center;
  padding: 8px;
  color: var(--el-text-color-secondary);
}
.calendar-day {
  min-height: 110px;
  padding: 7px;
  border-right: 1px solid var(--el-border-color-lighter);
  border-top: 1px solid var(--el-border-color-lighter);
}
.calendar-day.muted {
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-placeholder);
}
.calendar-day time {
  display: block;
  margin-bottom: 5px;
}
.calendar-day button {
  display: block;
  width: 100%;
  margin: 3px 0;
  padding: 3px;
  border: 0;
  border-radius: 3px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  text-align: left;
  cursor: pointer;
}
.gantt-list {
  display: grid;
  gap: 8px;
}
.gantt-row {
  display: grid;
  grid-template-columns: 220px 1fr;
  align-items: center;
  gap: 15px;
  padding: 10px;
  cursor: pointer;
}
.gantt-row > div:first-child {
  display: grid;
}
.gantt-row small,
.activity-note {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.gantt-track {
  position: relative;
  height: 24px;
  background: var(--el-fill-color-light);
}
.gantt-track b {
  position: absolute;
  top: 4px;
  height: 16px;
  border-radius: 3px;
  background: var(--el-color-primary);
}
</style>
