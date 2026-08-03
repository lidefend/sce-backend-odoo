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
  name: 'apps' | 'arrow-left' | 'arrow-right' | 'briefcase' | 'building' | 'chevron-right' | 'close' | 'columns' | 'folder' | 'home' | 'menu' | 'plus' | 'search' | 'settings' | 'star' | 'star-outline';
  size?: 14 | 16 | 18 | 20 | 24;
}>(), { size: 20 });

const paths = {
  apps: 'M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z',
  'arrow-left': 'M19 12H5m6 6-6-6 6-6',
  'arrow-right': 'M5 12h14m-6-6 6 6-6 6',
  briefcase: 'M9 6V4h6v2m-11 0h16v13H4V6Zm0 5h16M9 11v2h6v-2',
  building: 'M4 21V5l8-3 8 3v16M8 7h1m3 0h1m3 0h1M8 11h1m3 0h1m3 0h1M8 15h1m3 0h1m3 0h1M10 21v-3h4v3',
  'chevron-right': 'm9 18 6-6-6-6',
  close: 'M6 6l12 12M18 6 6 18',
  columns: 'M4 5h16v14H4V5Zm5 0v14m6-14v14',
  folder: 'M3 6h7l2 2h9v11H3V6Z',
  home: 'm3 11 9-8 9 8v10h-6v-6H9v6H3V11Z',
  menu: 'M4 7h16M4 12h16M4 17h16',
  plus: 'M12 5v14M5 12h14',
  search: 'm21 21-4.35-4.35m2.35-5.65a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  settings: 'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1 1.56V20h-3v-.08a1.7 1.7 0 0 0-1-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 14.7a1.7 1.7 0 0 0-1.56-1H5v-3h.08a1.7 1.7 0 0 0 1.56-1A1.7 1.7 0 0 0 6.3 7.82l-.06-.06 2.12-2.12.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1-1.56V4h3v.08a1.7 1.7 0 0 0 1 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.56 1H20v3h-.08a1.7 1.7 0 0 0-1.56 1Z',
  star: 'm12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z',
  'star-outline': 'm12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z',
} as const;

const pathData = computed(() => paths[props.name]);
</script>

<style scoped>
.sc-icon { display: inline-block; flex: 0 0 auto; }
</style>
