<template>
  <nav v-if="pages.length" ref="tablistRef" class="activity-tabs" role="tablist" :aria-label="label">
    <div v-for="page in pages" :key="page.key" class="activity-tab" :class="{active:page.key===activeKey}" role="presentation">
      <button
        class="activity-tab-main"
        type="button"
        role="tab"
        :title="page.title"
        :aria-selected="page.key === activeKey"
        :aria-current="page.key === activeKey ? 'page' : undefined"
        aria-keyshortcuts="Delete"
        :tabindex="page.key === activeKey ? 0 : -1"
        @click="$emit('activate', page)"
        @keydown="activateFromKeyboard(page, $event)"
      >
        <span>{{ page.title }}</span>
        <span
          class="activity-tab-close"
          aria-hidden="true"
          :title="`${closeLabel} ${page.title}`"
          @click.stop="$emit('close', page)"
        ><ScIcon name="close" :size="14" /></span>
      </button>
    </div>
  </nav>
</template>
<script setup lang="ts">
import { nextTick, ref } from 'vue';
import ScIcon from '../design-system/ScIcon.vue';
import type { ActivityPage } from '../../stores/session';
import { resolveActivityTabKeyboardIndex } from './activityPageTabKeyboard';

const props = withDefaults(defineProps<{pages:ActivityPage[];activeKey:string;label?:string;closeLabel?:string}>(),{label:'活动页面',closeLabel:'关闭'});
const emit = defineEmits<{activate:[page:ActivityPage];close:[page:ActivityPage]}>();
const tablistRef = ref<HTMLElement | null>(null);

function activateFromKeyboard(page: ActivityPage, event: KeyboardEvent) {
  if (event.key === 'Delete') {
    event.preventDefault();
    emit('close', page);
    return;
  }
  const currentIndex = props.pages.findIndex((item) => item.key === page.key);
  const nextIndex = resolveActivityTabKeyboardIndex({ key: event.key, currentIndex, count: props.pages.length });
  if (nextIndex === null) return;
  event.preventDefault();
  emit('activate', props.pages[nextIndex]);
  void nextTick(() => {
    tablistRef.value?.querySelectorAll<HTMLButtonElement>('.activity-tab-main')[nextIndex]?.focus();
  });
}
</script>
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
  display: block;
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20px;
  align-items: center;
  width: 100%;
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  opacity: 0;
  transition: opacity var(--sc-motion-fast, 120ms) ease;
}

.activity-tab:hover .activity-tab-close,
.activity-tab.active .activity-tab-close,
.activity-tab-main:focus-visible .activity-tab-close {
  opacity: .65;
}

.activity-tab-close:hover {
  opacity: 1;
  color: var(--sc-app-danger-text);
  background: var(--sc-app-danger-bg);
}

@media (max-width: 760px) {
  .activity-tabs { gap: 8px; padding-inline: 8px; }
  .activity-tab { flex-basis: 150px; min-width: 120px; }
}
</style>
