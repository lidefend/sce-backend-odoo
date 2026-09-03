<template>
  <section
    v-if="node.visible && hasContent"
    :class="['canonical-form-node', `canonical-form-node--${nodeKind}`, nativeClass, { 'canonical-form-node--readonly-fact': readonlyFactLayout }]"
    :data-canonical-node-id="node.nodeId"
    data-semantic-component="CanonicalFormNodeRenderer"
    :data-state="readonlyFactLayout ? 'readonly-fact' : 'structured'"
    :data-canonical-node-kind="node.kind"
    :data-density="density"
    :data-native-class="nativeClass || undefined"
    :data-contract-span="node.span"
    :data-contract-style-token="node.styleToken || undefined"
    :style="{ '--canonical-node-grid-span': nodeGridSpan, '--canonical-layout-columns': layoutColumns }"
    :data-section-navigation-role="node.zoneRole"
    :data-group-title="node.title || undefined"
  >
    <span v-if="presentableNodeText" class="canonical-form-native-text">{{ presentableNodeText }}</span>
    <ScButton
      v-if="node.action"
      type="button"
      variant="ghost"
      size="small"
      class="canonical-form-native-action"
      appearance="context-action"
      :disabled="!node.action.enabled"
      :title="node.action.reasonCode || undefined"
      :data-action-ref="node.action.actionRef.actionId"
      :data-backend-identity="node.action.actionRef.backendIdentity"
      @click="node.action.enabled && emit('action-ref', node.action.actionRef)"
    >{{ node.title || node.action.label }}</ScButton>
    <div v-else-if="node.nativeWidget" class="canonical-form-native-widget" :data-native-widget="node.nativeWidget" role="status">
      {{ node.title || node.nativeWidget }}
    </div>
    <FormSection
      v-if="fields.length"
      :title="sectionTitle"
      :columns="layoutColumns"
      :fields="fields"
      :relation-adapter="relationAdapter"
      :prefer-readonly-facts="readonlyFactLayout"
      @field-change="emit('field-change', $event)"
      @field-action="emit('field-action', $event)"
      @action-ref="emit('action-ref', $event)"
    />
    <h3 v-else-if="node.title && children.length && groupHeadingVisible" class="canonical-form-node-title">{{ node.title }}</h3>
    <CanonicalFormNodeRenderer
      v-for="child in children"
      :key="child.nodeId"
      :node="child"
      :class="fieldChildOrphanClass(child)"
      :relation-adapter="relationAdapter"
      :prefer-readonly-facts="preferReadonlyFacts"
      :density="density"
      @field-change="emit('field-change', $event)"
      @field-action="emit('field-action', $event)"
      @action-ref="emit('action-ref', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CanonicalFormNode } from '../../app/presentation/canonicalFormRenderModel';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import FormSection from '../../components/template/FormSection.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import type { FormSectionFieldActionPayload, FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import {
  canonicalFieldToFormSection,
  canonicalNodeHasContent,
  canonicalSectionFields,
  canonicalFieldHasPresentableValue,
  visibleCanonicalChildren,
} from './canonicalFormRenderer';

const props = defineProps<{
  node: CanonicalFormNode;
  relationAdapter?: RelationFieldAdapter;
  preferReadonlyFacts?: boolean;
  density?: 'default' | 'compact-task';
}>();
const emit = defineEmits<{
  'field-change': [payload: FormSectionFieldChange];
  'field-action': [payload: FormSectionFieldActionPayload];
  'action-ref': [action: ContractV2ActionRule];
}>();

const nodeKind = computed(() => String(props.node.kind || 'container').trim().toLowerCase());
const fields = computed(() => canonicalSectionFields(props.node)
  .filter((field) => canonicalFieldHasPresentableValue(field, props.relationAdapter))
  .map((field) => canonicalFieldToFormSection(field, props.relationAdapter)));
const readonlyFactLayout = computed(() => Boolean(
  props.preferReadonlyFacts
  && fields.value.length
  && fields.value.every((field) => field.readonly),
));
const children = computed(() => visibleCanonicalChildren(props.node));

/**
 * Section heading for the field form.
 * 后台逻辑分组（核心申请信息 / 申请识别与状态 / 本次付款事实 / 业务上下文 /
 * 结算与来源匹配 …）是开发侧的分组命名，对填单/查看用户都没有帮助。一律隐藏，
 * 字段直接平铺成连续表单（分组逻辑保留在 canonical 契约中，不动）。
 * 办理引导区（当前任务等）由 ObjectTaskPage 的卡片结构承载，不经由此处渲染。
 */
const sectionTitle = computed(() => '');

/**
 * Group/container headings for structural nodes (no direct fields).
 * 同样隐藏后台逻辑分组标题（含 notebook/page 包装容器的来源匹配等）。
 * 当前 notebook 仅作包装容器（无 tab 切换 UI），隐藏标题安全；若未来 notebook
 * 升级为真实 tab 结构，需在此恢复 page 标题以承载切换标签。
 */
const groupHeadingVisible = computed(() => false);

const columns = computed<1 | 2 | 3>(() => Math.max(1, Math.min(3, Number(props.node.columns || 1))) as 1 | 2 | 3);
const layoutColumns = computed<1 | 2 | 3>(() => {
  // Container/group nodes arrange their direct field children on a grid whose
  // column count follows the canonical contract (node.columns). A container
  // holding field children gets at least two columns so a single wide row (e.g.
  // project / counterparty many2one at 1103px full width) is avoided and fields
  // render at the ~half-width used elsewhere on the form. A node that only
  // carries structural children (nested groups / pages) stays a single column
  // so those children stack full-width.
  const children = visibleCanonicalChildren(props.node);
  if (!children.length) return 1;
  if (children.some((child) => child.kind === 'field')) return Math.max(2, columns.value) as 1 | 2 | 3;
  return 1;
});
const nodeGridSpan = computed(() => Math.max(1, Math.min(4, Math.ceil(Number(props.node.span || 24) / 6))));
const hasContent = computed(() => canonicalNodeHasContent(props.node));
const nativeClass = computed(() => String(props.node.attributes.class || '').trim());
const presentableNodeText = computed(() => {
  const text = String(props.node.text || '');
  if (props.preferReadonlyFacts && /^[\s.·•:_-]+$/.test(text)) return '';
  return text;
});

/**
 * Orphan-column fill for direct field children of a group/container.
 * A group whose field children count is odd would otherwise leave its last
 * field alone in the left half of the second grid row with a large blank
 * right half (e.g. 申请识别与状态 holding a single 业务分类 field). Widen that
 * last field to span the full row - a lone field never sits half-width in a
 * professional form.
 */
const fieldChildren = computed(() => visibleCanonicalChildren(props.node)
  .filter((child) => String(child.kind || '').trim().toLowerCase() === 'field'));
function fieldChildOrphanClass(child: CanonicalFormNode): string {
  if (layoutColumns.value < 2) return '';
  if (fieldChildren.value.length % 2 !== 1) return '';
  if (fieldChildren.value[fieldChildren.value.length - 1].nodeId !== child.nodeId) return '';
  return 'canonical-form-node--orphan-full';
}
</script>

<style scoped>
.canonical-form-node { min-width: 0; }
.canonical-form-node + .canonical-form-node { margin-top: 16px; }

/* Canonical container/group layout (form structure)
 * The canonical tree contracts a multi-column layout (node.columns, typically 2
 * on group nodes), but the renderer previously stacked every field node at full
 * width in a single column, wasting the task-section card's second column
 * (536px of a 1103px card). Arrange a node's direct children on a grid whose
 * column count follows --canonical-layout-columns: field children share the
 * columns; structural children (nested group/page) span all columns and stack.
 * The sheet spans the full task-section card so its interior reaches the
 * width that triggers the two-column form grid. */
.canonical-form-node--sheet { grid-column: 1 / -1; width: 100%; }
.canonical-form-node--container,
.canonical-form-node--group {
  display: grid;
  grid-template-columns: repeat(var(--canonical-layout-columns, 1), minmax(0, 1fr));
  gap: 16px 32px;
}
.canonical-form-node--container > .canonical-form-node,
.canonical-form-node--group > .canonical-form-node {
  grid-column: span 1;
  align-self: start;
  /* The generic sibling rule (.canonical-form-node + .canonical-form-node)
   * applies margin-top: 16px to every following node - inside a 2-column
   * grid that pushes the right/next field down by 16px and misaligns the
   * row. Grid children are spaced by the container gap, not this margin. */
  margin-top: 0;
}
/* Orphan-column fill: the last direct field child of a group with an odd
 * field count spans the full row instead of leaving a blank half-card. */
.canonical-form-node--container > .canonical-form-node--orphan-full,
.canonical-form-node--group > .canonical-form-node--orphan-full { grid-column: 1 / -1; }
.canonical-form-node--container > .canonical-form-node--group,
.canonical-form-node--group > .canonical-form-node--group,
.canonical-form-node--container > .canonical-form-node--container,
.canonical-form-node--group > .canonical-form-node--container,
.canonical-form-node--container > .canonical-form-node--notebook,
.canonical-form-node--group > .canonical-form-node--notebook,
.canonical-form-node--container > .canonical-form-node--sheet,
.canonical-form-node--group > .canonical-form-node--sheet { grid-column: 1 / -1; }
.canonical-form-node--notebook,
.canonical-form-node--page { grid-column: 1 / -1; }
/* A group/container heading is a block heading, not a grid item - let it span
 * the full width so the first field starts in the first column. */
.canonical-form-node--container > .canonical-form-node-title,
.canonical-form-node--group > .canonical-form-node-title { grid-column: 1 / -1; }
.canonical-form-node--field.canonical-form-node--readonly-fact {
  display: block;
  max-width: 100%;
}
.canonical-form-node--field:not(.canonical-form-node--readonly-fact) {
  display: block;
  width: 100%;
}
.canonical-form-node--readonly-fact + .canonical-form-node--readonly-fact,
.canonical-form-native-text + .canonical-form-node--readonly-fact,
.canonical-form-node--readonly-fact + .canonical-form-native-text { margin-top: 0; }
.canonical-form-node--readonly-fact :deep(.template-form-section) {
  display: block;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
/* Readonly facts keep their compact grid layout. Forcing every fact node
 * inline made each field's height follow the surrounding line-height (~90px
 * for a label + value that only need ~47px), so the fact strip and the
 * handling-info items below it read sparse. Restore grid on the fact's
 * form-section grid and field so heights collapse to content (49-69px) while
 * the fact grid (4-across on the summary strip, 2-wide on handling items)
 * keeps placing them in the same columns. */
.canonical-form-node--readonly-fact :deep(.template-form-section-grid),
.canonical-form-node--readonly-fact :deep(.field) { display: grid; }
.canonical-form-node--readonly-fact :deep(.field-control-row),
.canonical-form-node--readonly-fact :deep(.field-control-main) { display: inline; }
.canonical-form-node--readonly-fact :deep(.readonly-value),
.canonical-form-node--readonly-fact :deep(.contract-readonly-value) {
  min-height: 0;
  line-height: 22px;
  font: inherit;
  color: var(--sc-app-text-primary);
}
/* Section heading parity with TDesign card titles (t-card__title 16px/600).
 * canonical sections (e.g. 申请识别与状态) previously rendered at 15px with
 * inherited h3 weight (700), reading as a different hierarchy level than
 * template/t-card sections (当前任务, 业务上下文) at 16px/600 inside the same
 * form. Align both paths to the same section-heading scale. */
.canonical-form-node-title {
  margin: 0 0 12px;
  color: var(--sc-app-text-primary);
  font-size: 16px;
  font-weight: 600;
}
.canonical-form-node[data-density='compact-task'] > .canonical-form-node-title {
  margin: 0 0 2px;
  font-size: 13px;
  line-height: 18px;
}
.canonical-form-node[data-density='compact-task'].canonical-form-node--readonly-fact { padding: 4px 0; }
.canonical-form-native-action:disabled { cursor: not-allowed; opacity: 0.55; }
.canonical-form-native-widget { color: var(--sc-app-text-secondary); }
.canonical-form-native-text { white-space: pre-wrap; }
</style>
