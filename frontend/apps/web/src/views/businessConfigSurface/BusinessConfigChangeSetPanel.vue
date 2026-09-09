<template>
  <ScPanel class="business-config-change-set" data-business-config-change-set="v1" :data-change-set-state="presentation.kind" :aria-busy="presentation.kind === 'loading' || undefined">
    <div class="change-set-heading">
      <div>
        <p class="eyebrow">待发布变更</p>
        <h2>{{ presentation.title }}</h2>
      </div>
      <ScStatusBadge :label="presentation.statusLabel" :semantic="presentation.statusSemantic" />
    </div>
    <p class="muted" :class="{ 'status error': presentation.kind === 'failed' }">{{ presentation.description }}</p>
    <ul v-if="presentation.showItems" class="change-set-items">
      <li v-for="item in changeSet.items" :key="item.id">
        <strong>{{ typeLabel(item.config_type) }}</strong>
        <span>{{ summary(item) }}</span>
        <ScStatusBadge
          :label="item.validation_result?.ok === false ? '检查失败' : item.risk_level === 'high' ? '高影响' : '可逆'"
          :semantic="item.validation_result?.ok === false ? 'danger' : item.risk_level === 'high' ? 'warning' : 'default'"
        />
      </li>
    </ul>
    <div v-if="hasActions" class="change-set-actions">
      <ScButton v-if="presentation.canRetryLoad" variant="secondary" :disabled="busy" @click="$emit('retry')">重试读取</ScButton>
      <ScButton v-if="presentation.canValidate" variant="ghost" :disabled="busy" @click="$emit('validate')">检查全部变化</ScButton>
      <ScButton v-if="presentation.canPreview" variant="secondary" :disabled="busy" @click="$emit('preview')">预览当前草稿</ScButton>
      <ScButton v-if="presentation.canPublish" :disabled="busy" @click="$emit('publish')">{{ publishing ? '发布中…' : '发布全部可逆配置' }}</ScButton>
      <ScButton v-if="presentation.canRollback" variant="danger" :disabled="busy" @click="$emit('rollback')">按批次回滚</ScButton>
      <ScButton v-if="presentation.canDiscard" variant="ghost" :disabled="busy" @click="$emit('discard')">放弃草稿</ScButton>
    </div>
    <details class="high-risk-boundary">
      <summary>独立高风险操作</summary>
      <p>自定义字段、新增原生菜单、审批规则、批量补齐和跨环境整改不属于当前批量发布，需要单独确认。</p>
    </details>
  </ScPanel>
  <BusinessConfigDraftPreview :preview="changeSet?.preview || null" @device="$emit('preview', $event)" />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScPanel from '../../components/design-system/ScPanel.vue';
import ScStatusBadge from '../../components/design-system/ScStatusBadge.vue';
import BusinessConfigDraftPreview from './BusinessConfigDraftPreview.vue';
import type { BusinessConfigChangeSet, BusinessConfigChangeSetItem } from '../../api/businessConfig';
import { resolveBusinessConfigChangeSetPresentation } from './changeSetPresentation';

const props = defineProps<{ changeSet: BusinessConfigChangeSet | null; loading?: boolean; busy?: boolean; publishing?: boolean; error?: string }>();
defineEmits<{ retry: []; validate: []; preview: [device?: 'desktop' | 'tablet' | 'mobile']; publish: []; rollback: []; discard: [] }>();

const presentation = computed(() => resolveBusinessConfigChangeSetPresentation(props.changeSet, {
  loading: props.loading,
  publishing: props.publishing,
  requestError: props.error,
}));
const hasActions = computed(() => presentation.value.canRetryLoad || presentation.value.canValidate || presentation.value.canPreview
  || presentation.value.canPublish || presentation.value.canRollback || presentation.value.canDiscard);
function typeLabel(value: string) { return ({ form: '表单', list: '列表', search: '搜索', analysis: '分析', menu: '菜单' } as Record<string, string>)[value] || '配置'; }
function summary(item: BusinessConfigChangeSetItem) {
  const value = item.diff_summary || {};
  return String(value.summary || value.label || item.target_key || '配置已修改');
}
</script>
