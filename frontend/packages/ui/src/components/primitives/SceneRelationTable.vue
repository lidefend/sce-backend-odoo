<script setup lang="ts">
import { computed, watchEffect } from 'vue';
import type { SceneRelationTable } from '../../contracts/sceneObjectPage';
import { useSceneUiKit } from '../../kits/context';

const props = defineProps<{ table: SceneRelationTable }>();
const { kit, runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
const driverTable = computed(() => runtime.value?.components.table);
const tdesignColumns = computed(() => props.table.columns.map((column) => ({
  colKey: column.key,
  title: column.label,
  width: column.width,
  align: column.align || 'left',
  ellipsis: true,
})));
const tdesignRows = computed(() => props.table.rows.map((row) => ({
  id: row.id,
  ...row.values,
})));

watchEffect(() => {
  if (componentModel.value === 'web-components') void runtime.value?.ensurePrimitive?.('table');
});
</script>

<template>
  <section class="scene-relation-table" :data-relation-table="table.id" :data-table-driver="kit">
    <header>
      <div>
        <h3>{{ table.title }}</h3>
        <p v-if="table.description">{{ table.description }}</p>
      </div>
      <span>{{ table.rows.length }} 项</span>
    </header>

    <div v-if="table.rows.length" class="scene-relation-table__viewport">
      <ui5-table v-if="componentModel === 'web-components'" overflow-mode="Popin" class="scene-ui5-table">
        <ui5-table-header-row slot="headerRow">
          <ui5-table-header-cell
            v-for="column in table.columns"
            :key="column.key"
            :width="column.width"
          >
            {{ column.label }}
          </ui5-table-header-cell>
        </ui5-table-header-row>
        <ui5-table-row v-for="row in table.rows" :key="row.id" :data-row-id="row.id">
          <ui5-table-cell v-for="column in table.columns" :key="column.key">
            <span :data-tone="column.key === 'status' ? row.tone || 'Neutral' : undefined">
              {{ row.values[column.key] || '无' }}
            </span>
          </ui5-table-cell>
        </ui5-table-row>
      </ui5-table>

      <component
        :is="driverTable"
        v-else-if="componentModel === 'vue' && driverTable"
        :data="tdesignRows"
        :columns="tdesignColumns"
        row-key="id"
        size="small"
        bordered
        hover
        table-layout="fixed"
      />

      <table v-else class="scene-native-table">
        <thead>
          <tr>
            <th v-for="column in table.columns" :key="column.key" :style="{ width: column.width, textAlign: column.align || 'left' }">
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in table.rows" :key="row.id" :data-row-id="row.id">
            <td v-for="column in table.columns" :key="column.key" :style="{ textAlign: column.align || 'left' }">
              <span :data-tone="column.key === 'status' ? row.tone || 'Neutral' : undefined">
                {{ row.values[column.key] || '无' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="scene-relation-table__empty">{{ table.emptyText || '暂无关联明细' }}</div>
  </section>
</template>

<style scoped>
.scene-relation-table {
  min-width: 0;
  border: 1px solid var(--sc-scene-border);
  border-radius: 9px;
  background: var(--sc-scene-surface);
}

.scene-relation-table > header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  padding: 13px 14px 11px;
  border-bottom: 1px solid var(--sc-scene-border);
}

.scene-relation-table h3,
.scene-relation-table p {
  margin: 0;
}

.scene-relation-table h3 {
  font-size: 14px;
}

.scene-relation-table p,
.scene-relation-table > header > span,
.scene-relation-table__empty {
  color: var(--sc-scene-muted);
  font-size: 12px;
}

.scene-relation-table p {
  margin-top: 3px;
}

.scene-relation-table__viewport {
  max-width: 100%;
  overflow-x: auto;
}

.scene-native-table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  font-size: 12px;
}

.scene-native-table th,
.scene-native-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e6ebf0;
  color: #314559;
}

.scene-native-table th {
  background: #f6f8fa;
  color: #536476;
  font-weight: 600;
}

[data-tone='Critical'] {
  color: var(--sc-scene-warning);
  font-weight: 700;
}

[data-tone='Positive'] {
  color: var(--sc-scene-success);
  font-weight: 700;
}

.scene-ui5-table,
.scene-relation-table :deep(.t-table) {
  width: 100%;
}

.scene-relation-table__empty {
  padding: 28px;
  text-align: center;
}
</style>
