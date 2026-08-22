<template>
  <record-drawer
    :visible="true"
    presentation="page"
    :model="model"
    :record-id="recordId"
    :action-id="actionId"
    :menu-id="menuId"
    :initial-mode="initialMode"
    @update:visible="goBack"
    @saved="onSaved"
    @deleted="goBack"
  />
</template>
<script setup lang="ts">
import { computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import RecordDrawer from '@/pages/odoo/action/components/RecordDrawer.vue';
import { restoreMissingRecordContext } from '@/utils/route/tabIdentity';

const route = useRoute();
const router = useRouter();
const initialQuery = { ...route.query };
const model = computed(() => String(route.params.model || ''));
const recordId = computed(() => {
  const id = Number(route.params.id || 0);
  return Number.isFinite(id) && id > 0 ? id : null;
});
const actionId = computed(() => Number(route.query.action_id || 0) || undefined);
const menuId = computed(() => Number(route.query.menu_id || 0) || undefined);
const initialMode = computed(() => (route.name === 'OdooRecordForm' ? (recordId.value ? 'edit' : 'create') : 'view'));

watch(
  () => route.query,
  (query) => {
    const restored = restoreMissingRecordContext(initialQuery, query);
    if (restored) void router.replace({ path: route.path, query: restored });
  },
  { deep: true },
);

function goBack() {
  if (window.history.length > 1) router.back();
  else router.push('/dashboard/base');
}

function onSaved(id: number) {
  if (route.name === 'OdooRecordForm') {
    void router.replace({
      name: 'OdooRecordDetail',
      params: { model: model.value, id: String(id) },
      query: route.query,
    });
  }
}
</script>
