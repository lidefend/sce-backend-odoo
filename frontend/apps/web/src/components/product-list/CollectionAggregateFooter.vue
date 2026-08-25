<template>
  <tfoot
    v-if="rows.length"
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
</template>

<script setup lang="ts">
export type CollectionAggregateScope = 'page' | 'total';

export type CollectionAggregateColumn = {
  key: string;
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
  labelColspan: number;
  columns: readonly CollectionAggregateColumn[];
  rows: readonly CollectionAggregateRow[];
}>();
</script>

<style scoped src="./CollectionAggregateFooter.css"></style>
