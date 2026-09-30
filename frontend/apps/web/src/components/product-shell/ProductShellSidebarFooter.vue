<template>
  <div class="footer shell-sidebar-footer" data-semantic-component="ProductShellSidebarFooter">
    <ScButton
      v-if="!mobile"
      class="sidebar-compact-toggle"
      appearance="outline-action"
      type="button"
      variant="ghost"
      size="small"
      :title="compact ? '展开侧边栏' : '收起侧边栏'"
      :aria-label="compact ? '展开侧边栏' : '收起侧边栏'"
      aria-controls="primary-sidebar"
      :aria-expanded="compact ? 'false' : 'true'"
      @click="emit('toggle-compact')"
    >
      <ScIcon name="panel-left" :size="16" />
      <span class="shell-sidebar-footer__label">{{ compact ? '展开' : '收起' }}</span>
    </ScButton>
    <ScButton
      v-if="showRefresh"
      class="sidebar-refresh"
      variant="ghost"
      size="small"
      type="button"
      aria-label="刷新"
      @click="emit('refresh')"
    >
      <ScIcon name="refresh" :size="16" />
      <span class="shell-sidebar-footer__label">刷新</span>
    </ScButton>
    <ScButton
      class="sidebar-logout"
      variant="ghost"
      size="small"
      type="button"
      aria-label="退出登录"
      @click="emit('logout')"
    >
      <ScIcon name="user" :size="16" />
      <span class="shell-sidebar-footer__label">退出登录</span>
    </ScButton>
    <span v-if="productVersion && (!compact || mobile)" class="shell-sidebar-footer__version" data-product-version :title="`产品版本 ${productVersion}`">版本 {{ productVersion }}</span>
  </div>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';

withDefaults(defineProps<{
  productVersion?: string;
  mobile?: boolean;
  compact?: boolean;
  showRefresh?: boolean;
}>(), {
  productVersion: '',
  mobile: false,
  compact: false,
  showRefresh: false,
});

const emit = defineEmits<{
  (event: 'toggle-compact'): void;
  (event: 'refresh'): void;
  (event: 'logout'): void;
}>();
</script>

<style scoped>
.shell-sidebar-footer { flex-wrap: wrap; }
.shell-sidebar-footer__version {
  flex-basis: 100%;
  min-width: 0;
  overflow-wrap: anywhere;
  font: var(--sc-font-body-small);
  color: var(--sc-semantic-text-muted);
}
</style>
