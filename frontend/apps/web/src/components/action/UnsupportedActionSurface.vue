<template>
  <ScErrorState
    class="unsupported-action-surface"
    :title="title"
    :description="`${description}（${reasonCode}）`"
  />
</template>

<script setup lang="ts">
import ScErrorState from '../design-system/ScErrorState.vue';

withDefaults(defineProps<{ reasonCode?: string }>(), { reasonCode: 'ACTION_SURFACE_RENDERER_NOT_REGISTERED' });
const title = '当前视图暂不可用';
const description = '页面契约指定的渲染器尚未注册，请联系管理员完善页面配置。';
</script>

<style scoped>
.unsupported-action-surface { margin: var(--sc-space-6); }
</style>
