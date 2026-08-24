<template>
  <div
    class="professional-relation-field"
    data-professional-field-family="relation"
    :data-relation-kind="field.type"
    :data-relation-model="field.descriptor?.relation || ''"
    :data-relation-create-mode="field.relationCreateMode || 'none'"
    :data-presentation-mode="field.presentationMode"
    :data-render-profile="field.renderProfile"
    :data-control-state="field.readonly ? 'readonly' : 'editable'"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import type { FormSectionFieldSchema } from '../template/formSection.types';

defineProps<{ field: FormSectionFieldSchema }>();
</script>

<style scoped>
.professional-relation-field { min-width: 0; width: 100%; }
</style>
