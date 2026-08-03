<template>
  <svg
    class="sc-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path :d="pathData" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  name: 'apps' | 'arrow-left' | 'arrow-right' | 'bell' | 'briefcase' | 'building' | 'chevron-right' | 'clipboard' | 'close' | 'columns' | 'construction' | 'contract' | 'file-text' | 'folder' | 'home' | 'menu' | 'panel-left' | 'plus' | 'project' | 'search' | 'settings' | 'star' | 'star-outline' | 'sun' | 'user';
  size?: 14 | 16 | 18 | 20 | 24;
}>(), { size: 20 });

const paths = {
  apps: 'M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z',
  'arrow-left': 'M19 12H5m6 6-6-6 6-6',
  'arrow-right': 'M5 12h14m-6-6 6 6-6 6',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Zm-8 12h4',
  briefcase: 'M9 6V4h6v2m-11 0h16v13H4V6Zm0 5h16M9 11v2h6v-2',
  building: 'M4 21V5l8-3 8 3v16M8 7h1m3 0h1m3 0h1M8 11h1m3 0h1m3 0h1M8 15h1m3 0h1m3 0h1M10 21v-3h4v3',
  'chevron-right': 'm9 18 6-6-6-6',
  clipboard: 'M9 5V3h6v2m-8 0H5v16h14V5h-2M9 10h6m-6 4h6m-6 4h4',
  close: 'M6 6l12 12M18 6 6 18',
  columns: 'M4 5h16v14H4V5Zm5 0v14m6-14v14',
  construction: 'm4 20 6-6m4-4 6-6m-3-1 4 4M5 4l5 5-2 2-5-5 2-2Zm7 8 8 8',
  contract: 'M6 3h9l3 3v15H6V3Zm9 0v4h4M9 11h4m-4 4 2 2 4-5',
  'file-text': 'M6 3h9l3 3v15H6V3Zm9 0v4h4M9 11h6m-6 4h6m-6 4h4',
  folder: 'M3 6h7l2 2h9v11H3V6Z',
  home: 'm3 11 9-8 9 8v10h-6v-6H9v6H3V11Z',
  menu: 'M4 7h16M4 12h16M4 17h16',
  'panel-left': 'M4 4h16v16H4V4Zm5 0v16',
  plus: 'M12 5v14M5 12h14',
  project: 'M3 6h7l2 2h9v13H3V6Zm4 9h2v2H7v-2Zm4-3h2v5h-2v-5Zm4-2h2v7h-2v-7Z',
  search: 'm21 21-4.35-4.35m2.35-5.65a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  settings: 'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1 1.56V20h-3v-.08a1.7 1.7 0 0 0-1-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 14.7a1.7 1.7 0 0 0-1.56-1H5v-3h.08a1.7 1.7 0 0 0 1.56-1A1.7 1.7 0 0 0 6.3 7.82l-.06-.06 2.12-2.12.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1-1.56V4h3v.08a1.7 1.7 0 0 0 1 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.56 1H20v3h-.08a1.7 1.7 0 0 0-1.56 1Z',
  star: 'm12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z',
  'star-outline': 'm12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z',
  sun: 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.36-6.36-1.42 1.42M7.06 16.94l-1.42 1.42m12.72 0-1.42-1.42M7.06 7.06 5.64 5.64M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7 8a7 7 0 0 0-14 0',
} as const;

const pathData = computed(() => paths[props.name]);
</script>

<style scoped>
.sc-icon { display: inline-block; flex: 0 0 auto; }
</style>
