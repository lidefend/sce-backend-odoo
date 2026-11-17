<template>
  <div
    v-if="presentation.kind === 'feedback'"
    class="native-explicit-feedback"
    :data-purpose="presentation.purpose"
    :data-contract-container-id="containerId"
    tabindex="-1"
  >
    <TDesignAlert
      v-if="presentation.purpose !== 'explanation'"
      :theme="presentation.purpose === 'error' ? 'error' : presentation.purpose === 'warning' ? 'warning' : 'info'"
      :role="presentation.role"
      :aria-live="presentation.purpose === 'error' ? 'assertive' : 'polite'"
    >{{ presentation.content }}</TDesignAlert>
    <p v-else>{{ presentation.content }}</p>
  </div>
  <ScButton
    v-else-if="presentation.kind === 'anchor'"
    type="button"
    variant="ghost"
    :data-contract-container-id="containerId"
    @click="$emit('navigate', $event)"
  >{{ presentation.content }}</ScButton>
  <div
    v-else-if="presentation.kind === 'ribbon'"
    class="native-ribbon"
    :class="presentation.styleClass"
    :data-contract-container-id="containerId"
    data-native-widget="web_ribbon"
  >{{ presentation.content }}</div>
  <TDesignAlert
    v-else-if="presentation.kind === 'insight_summary' && presentation.insight"
    class="native-node-insight"
    :theme="presentation.insight.tone"
    role="status"
    :data-contract-container-id="containerId"
    :data-native-node-payload="presentation.insight.title"
  >
    <strong>{{ presentation.insight.title }}</strong>
    <p v-if="presentation.insight.message">{{ presentation.insight.message }}</p>
    <p v-if="presentation.insight.detail" class="native-node-muted">{{ presentation.insight.detail }}</p>
  </TDesignAlert>
  <ScCard
    v-else-if="presentation.kind === 'action_list' && presentation.actionList"
    class="native-node-action-list"
    :title="presentation.actionList.title"
    :bordered="false"
    :data-contract-container-id="containerId"
    :data-native-node-payload="presentation.actionList.title"
  >
    <ScEmptyState
      v-if="!presentation.actionList.items.length"
      density="compact"
      :heading-level="5"
      :title="presentation.actionList.emptyText"
    />
    <div v-else class="native-node-action-items">
      <article
        v-for="item in presentation.actionList.items"
        :key="item.id"
        class="native-node-action-item"
        :class="`tone-${item.tone}`"
        :data-native-action-state="item.state"
      >
        <div class="native-node-action-copy">
          <strong>{{ item.title }}</strong>
          <p v-if="item.description">{{ item.description }}</p>
        </div>
        <ScButton
          v-if="item.enabled && item.actionLabel"
          type="button"
          size="small"
          variant="primary"
          :data-action-ref="item.actionRef"
          @click="$emit('action', actionPayload(item))"
        >{{ item.actionLabel }}</ScButton>
        <span v-else-if="item.state === 'done'" class="native-node-action-done">已完成</span>
      </article>
    </div>
  </ScCard>
</template>

<script setup lang="ts">
import type { NodeComponentPresentation } from '../../app/presentation/nodeComponentPresentation';
import ScButton from '../design-system/ScButton.vue';
import ScCard from '../design-system/ScCard.vue';
import ScEmptyState from '../design-system/ScEmptyState.vue';
import { TDesignAlert } from '../design-system/tdesignPrimitiveBridge';

defineProps<{
  presentation: NodeComponentPresentation;
  containerId: string;
}>();

defineEmits<{
  navigate: [event: Event];
  action: [payload: Record<string, unknown>];
}>();

function actionPayload(item: NonNullable<NodeComponentPresentation['actionList']>['items'][number]) {
  const buttonType = item.actionType === 'object_method' ? 'object' : 'action';
  return {
    name: item.actionRef,
    label: item.actionLabel,
    kind: buttonType,
    buttonType,
    payload: {
      ...item.actionPayload,
      method: buttonType === 'object' ? item.actionRef : '',
      ref: buttonType === 'action' ? item.actionRef : '',
      type: buttonType,
    },
  };
}
</script>

<style scoped>
.native-ribbon {
  font: var(--sc-font-mark-small);
  justify-self: end;
  max-width: 100%;
  border-radius: 4px;
  background: var(--sc-app-danger-text);
  color: var(--sc-semantic-text-on-interactive);
  padding: 4px 10px;
  overflow-wrap: anywhere;
}

.native-ribbon.text-bg-danger {
  background: var(--sc-app-danger-text);
}

.native-node-insight {
  width: 100%;
}

.native-node-insight p {
  margin: 6px 0 0;
}

.native-node-muted {
  color: var(--sc-app-text-secondary);
}

.native-node-action-list {
  width: 100%;
}

.native-node-action-items {
  display: grid;
  gap: var(--sc-space-sm);
}

.native-node-action-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-space-sm);
  padding: var(--sc-space-sm);
  border: 1px solid var(--sc-app-border);
  border-left-width: 4px;
  border-radius: var(--sc-product-panel-radius);
  min-width: 0;
}

.native-node-action-item.tone-success { border-left-color: var(--sc-app-success-text); }
.native-node-action-item.tone-warning { border-left-color: var(--sc-app-warning-text); }
.native-node-action-item.tone-info { border-left-color: var(--sc-app-info-text); }

.native-node-action-copy {
  min-width: 0;
}

.native-node-action-copy p {
  margin: 4px 0 0;
  color: var(--sc-app-text-secondary);
}

.native-node-action-done {
  color: var(--sc-app-success-text);
  font-weight: 600;
}

@container (max-width: 480px) {
  .native-node-action-item {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
