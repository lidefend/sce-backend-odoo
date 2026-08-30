<template>
  <el-sub-menu v-if="item.children.length" :index="`group:${item.key}`">
    <template #title>
      <el-tooltip :content="item.label" placement="right" :disabled="!collapsed"><el-icon><component :is="item.icon" /></el-icon></el-tooltip>
      <span v-if="item.executable" class="menu-title executable-group-label" @click.stop="openEntry">{{ item.label }}</span>
      <span v-else class="menu-title">{{ item.label }}</span>
    </template>
    <app-menu-node v-for="child in item.children" :key="child.key" :item="child" :collapsed="collapsed" />
  </el-sub-menu>
  <el-menu-item v-else-if="item.executable" :index="item.route">
    <el-tooltip :content="item.label" placement="right" :disabled="!collapsed"><el-icon><component :is="item.icon" /></el-icon></el-tooltip>
    <template #title><span class="menu-title">{{ item.label }}</span></template>
  </el-menu-item>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import type { MenuItem } from '@/utils/navigation'

defineOptions({ name: 'AppMenuNode' })
const props = defineProps<{ item: MenuItem; collapsed?: boolean }>()
const router = useRouter()

function openEntry() {
  if (props.item.route) void router.push(props.item.route)
}
</script>

<style scoped>
.executable-group-label {
  flex: 1;
}
</style>
