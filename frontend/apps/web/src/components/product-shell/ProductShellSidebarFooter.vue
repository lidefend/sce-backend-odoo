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
    <ScButton
      v-if="productVersion && (!compact || mobile)"
      class="shell-sidebar-footer__version"
      type="button"
      variant="ghost"
      size="small"
      data-product-version
      data-product-build-identity
      :title="identityTitle"
      :aria-label="`${identityLabel}，点击复制构建身份`"
      @click="copyIdentity"
    >
      <span>{{ identityLabel }}</span>
      <span class="shell-sidebar-footer__copy" aria-live="polite">{{ copyStatus }}</span>
    </ScButton>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScIcon from '../design-system/ScIcon.vue';
import {
  buildIdentityCopyText,
  buildIdentityTitle,
  productIdentityLabel,
} from '../../app/runtime/buildIdentity';

const props = withDefaults(defineProps<{
  productVersion?: string;
  sourceRevision?: string;
  mobile?: boolean;
  compact?: boolean;
  showRefresh?: boolean;
}>(), {
  productVersion: '',
  sourceRevision: '',
  mobile: false,
  compact: false,
  showRefresh: false,
});

const emit = defineEmits<{
  (event: 'toggle-compact'): void;
  (event: 'refresh'): void;
  (event: 'logout'): void;
}>();

const identityLabel = computed(() => productIdentityLabel(props.productVersion, props.sourceRevision));
const identityTitle = computed(() => buildIdentityTitle(props.productVersion, props.sourceRevision));
const copyStatus = ref('');
let copyTimer: ReturnType<typeof setTimeout> | null = null;

async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the browser-local selection fallback.
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  textarea.remove();
  return copied;
}

async function copyIdentity() {
  const text = buildIdentityCopyText(props.productVersion, props.sourceRevision);
  copyStatus.value = await copyText(text) ? '已复制' : '复制失败';
  if (copyTimer) clearTimeout(copyTimer);
  copyTimer = setTimeout(() => {
    copyStatus.value = '';
    copyTimer = null;
  }, 1600);
}

onBeforeUnmount(() => {
  if (copyTimer) clearTimeout(copyTimer);
});
</script>

<style scoped>
.shell-sidebar-footer { flex-wrap: wrap; }
.shell-sidebar-footer__version {
  display: inline-flex;
  align-items: center;
  gap: var(--sc-space-1);
  flex-basis: 100%;
  min-width: 0;
  overflow-wrap: anywhere;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: copy;
  font: var(--sc-font-body-small);
  color: var(--sc-semantic-text-secondary);
}
.shell-sidebar-footer__version:focus-visible {
  outline: 2px solid var(--sc-semantic-border-focus, var(--sc-color-primary));
  outline-offset: 2px;
}
.shell-sidebar-footer__copy {
  color: var(--sc-semantic-text-tertiary, var(--sc-semantic-text-secondary));
  font: var(--sc-font-caption);
}
</style>
