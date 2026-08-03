<template>
  <nav v-if="pages.length" class="activity-tabs" :aria-label="label">
    <div v-for="page in pages" :key="page.key" class="activity-tab" :class="{active:page.key===activeKey}">
      <button class="activity-tab-main" type="button" :title="page.title" @click="$emit('activate',page)"><span>{{ page.title }}</span></button>
      <button class="activity-tab-close" type="button" :aria-label="`${closeLabel} ${page.title}`" :title="`${closeLabel} ${page.title}`" @click.stop="$emit('close',page)"><ScIcon name="close" :size="14" /></button>
    </div>
  </nav>
</template>
<script setup lang="ts">import ScIcon from '../design-system/ScIcon.vue'; import type { ActivityPage } from '../../stores/session'; withDefaults(defineProps<{pages:ActivityPage[];activeKey:string;label?:string;closeLabel?:string}>(),{label:'活动页面',closeLabel:'关闭'}); defineEmits<{activate:[page:ActivityPage];close:[page:ActivityPage]}>();</script>
<style scoped>
.activity-tabs {
  display: flex;
  align-items: end;
  gap: 18px;
  min-width: 0;
  min-height: 36px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 12px;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  scrollbar-width: thin;
}

.activity-tab {
  position: relative;
  flex: 0 1 180px;
  min-width: 96px;
  max-width: 220px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20px;
  align-items: center;
  color: var(--sc-app-text-secondary);
}

.activity-tab::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 2px;
  background: transparent;
  content: '';
}

.activity-tab.active {
  color: var(--sc-app-info-text);
}

.activity-tab.active::after {
  background: var(--sc-semantic-surface-interactive);
}

.activity-tab-main,
.activity-tab-close {
  min-width: 0;
  height: 35px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.activity-tab-main {
  padding: 0 4px;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
}

.activity-tab.active .activity-tab-main {
  font-weight: 600;
}

.activity-tab-main span {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-tab-close {
  width: 20px;
  padding: 0;
  opacity: 0;
  transition: opacity var(--sc-motion-fast, 120ms) ease;
}

.activity-tab:hover .activity-tab-close,
.activity-tab.active .activity-tab-close,
.activity-tab-close:focus-visible {
  opacity: .65;
}

.activity-tab-close:hover {
  opacity: 1;
  color: var(--sc-app-danger-text);
  background: var(--sc-app-danger-bg);
}

@media (max-width: 760px) {
  .activity-tabs { display: none; }
}
</style>
