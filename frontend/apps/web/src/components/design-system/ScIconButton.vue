<template><ScButton type="button" variant="ghost" class="sc-icon-button" :aria-label="label" :title="label" :disabled="disabled"><span aria-hidden="true"><slot /></span></ScButton></template>
<script setup lang="ts">
import ScButton from './ScButton.vue';
defineProps<{ label: string; disabled?: boolean }>();
</script>
<style scoped>.sc-icon-button{inline-size:var(--sc-product-control-height);padding:0;display:inline-grid;place-items:center}</style>
