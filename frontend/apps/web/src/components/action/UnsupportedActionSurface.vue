<template>
  <section class="unsupported-action-surface" role="alert">
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <code>{{ reasonCode }}</code>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ reasonCode?: string }>(), { reasonCode: 'ACTION_SURFACE_RENDERER_NOT_REGISTERED' });
const title = '当前视图暂不可用';
const description = '页面契约指定的渲染器尚未注册，请联系管理员完善页面配置。';
</script>

<style scoped>
.unsupported-action-surface {
  display: grid;
  gap: var(--sc-space-2);
  padding: var(--sc-space-6);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
}
.unsupported-action-surface h2,
.unsupported-action-surface p { margin: 0; }
.unsupported-action-surface code { color: var(--sc-app-text-secondary); }
</style>
