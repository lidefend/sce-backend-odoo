<template>
  <div v-if="presentation === 'page'" class="record-page-shell">
    <slot />
  </div>
  <t-drawer
    v-else
    :visible="visible"
    :header="false"
    size="min(1080px, 100%)"
    :footer="false"
    destroy-on-close
    @close="$emit('close')"
  >
    <slot />
  </t-drawer>
</template>
<script setup lang="ts">
withDefaults(
  defineProps<{
    visible: boolean;
    presentation?: 'drawer' | 'page';
  }>(),
  { presentation: 'drawer' },
);

defineEmits<{ close: [] }>();
</script>
<style scoped>
.record-page-shell {
  min-height: calc(100vh - 168px);
}
</style>
