<template>
  <div
    class="professional-detail-collection"
    data-professional-field-family="detail-collection"
    :data-relation-model="authority.relationModel"
    :data-row-count="authority.rowCount"
    :data-column-count="authority.columnCount"
    :data-can-create="authority.canCreate"
    :data-removed-row-count="authority.removedRowCount"
    :data-validation-visible="authority.validationVisible"
    :data-summary-present="Boolean(authority.summary)"
    :data-presentation-mode="field.presentationMode"
    :data-render-profile="field.renderProfile"
    :data-control-state="field.readonly ? 'readonly' : 'editable'"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';
import { detailCollectionAuthority } from './professionalDetailCollectionModel';

const props = defineProps<{ field: FormSectionFieldSchema; adapter: RelationFieldAdapter }>();
const authority = computed(() => detailCollectionAuthority(props.field, props.adapter));
</script>

<style scoped>
.professional-detail-collection { min-width: 0; width: 100%; }
</style>
