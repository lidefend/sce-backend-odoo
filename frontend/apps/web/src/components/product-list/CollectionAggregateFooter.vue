<template>
  <tfoot
    v-if="rows.length && layout === 'table'"
    class="collection-aggregate-footer"
    data-semantic-component="CollectionAggregateFooter"
    :data-aggregate-context="context"
  >
    <tr
      v-for="row in rows"
      :key="row.key"
      class="collection-aggregate-row"
      :data-aggregate-scope="row.scope"
    >
      <th :colspan="labelColspan" class="collection-aggregate-label" scope="row">
        {{ row.label }}
      </th>
      <td
        v-for="column in columns"
        :key="`${row.key}-${column.key}`"
        :style="column.style"
        :class="[column.densityClass, { 'collection-aggregate-number': column.numeric }]"
        :data-aggregate-field="column.key"
      >
        <span v-if="column.numeric" class="collection-aggregate-number-value">
          {{ row.values[column.key] || '' }}
        </span>
        <template v-else>{{ row.values[column.key] || '' }}</template>
      </td>
    </tr>
  </tfoot>
  <section
    v-else-if="rows.length"
    class="collection-aggregate-summary"
    data-semantic-component="CollectionAggregateFooter"
    :data-aggregate-context="context"
    data-aggregate-layout="summary"
    aria-label="列表汇总"
  >
    <dl
      v-for="row in rows"
      :key="row.key"
      class="collection-aggregate-summary-row"
      :data-aggregate-scope="row.scope"
    >
      <dt class="collection-aggregate-summary-label" data-aggregate-row-label>{{ row.label }}</dt>
      <template v-for="column in columns" :key="`${row.key}-${column.key}`">
        <div v-if="row.values[column.key]" class="collection-aggregate-summary-value">
          <dt>{{ column.label || column.key }}</dt>
          <dd
            :class="{ 'collection-aggregate-number': column.numeric }"
            :data-aggregate-field="column.key"
          >
            <span v-if="column.numeric" class="collection-aggregate-number-value">
              {{ row.values[column.key] }}
            </span>
            <template v-else>{{ row.values[column.key] }}</template>
          </dd>
        </div>
      </template>
    </dl>
  </section>
</template>

<script setup lang="ts">
export type CollectionAggregateScope = 'page' | 'total';

export type CollectionAggregateColumn = {
  key: string;
  label?: string;
  numeric: boolean;
  densityClass?: string;
  style?: Record<string, string>;
};

export type CollectionAggregateRow = {
  key: string;
  scope: CollectionAggregateScope;
  label: string;
  values: Record<string, string>;
};

defineProps<{
  context: 'flat' | 'group';
  layout?: 'table' | 'summary';
  labelColspan: number;
  columns: readonly CollectionAggregateColumn[];
  rows: readonly CollectionAggregateRow[];
}>();
</script>

<style scoped src="./CollectionAggregateFooter.css"></style>
