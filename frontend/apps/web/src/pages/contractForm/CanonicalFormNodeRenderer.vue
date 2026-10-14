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
    :data-contract-band="declaredNodeBand"
    :data-contract-style-token="node.styleToken || undefined"
    :style="{ '--canonical-node-grid-span': declaredNodeSpan }"
    :data-section-navigation-role="node.zoneRole"
    :data-group-title="node.title || undefined"
    :data-value-emphasis="valueEmphasis"
    :data-form-section-target="governedSection?.anchor || undefined"
    :data-section-content-kind="governedSection ? 'semantic-section' : undefined"
    :data-section-source-identity="governedSection ? node.nodeId : undefined"
    :data-section-title="governedSection?.label || undefined"
    :aria-label="governedSection?.label || undefined"
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
    <h3 v-if="groupHeadingVisible" class="canonical-form-node-title">{{ governedSection?.label }}</h3>
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
    <div v-if="children.length" class="canonical-form-node-children">
      <CanonicalFormNodeRenderer
        v-for="child in children"
        :key="child.nodeId"
        :node="child"
        :relation-adapter="relationAdapter"
        :prefer-readonly-facts="preferReadonlyFacts"
        :density="density"
        :hide-governed-section-heading="hideGovernedSectionHeading"
        @field-change="emit('field-change', $event)"
        @field-action="emit('field-action', $event)"
        @action-ref="emit('action-ref', $event)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CanonicalFormNode } from '../../app/presentation/canonicalFormRenderModel';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import FormSection from '../../components/template/FormSection.vue';
import { declaredLayoutBand, declaredLayoutSpan, requireDeclaredLayoutColumns, containedFieldLayout } from '../../components/template/layoutSpan';
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
import {
  governedFormStructureSectionIdentity,
  nativeBusinessSectionIdentity,
} from './nativeBusinessSection';

const props = defineProps<{
  node: CanonicalFormNode;
  relationAdapter?: RelationFieldAdapter;
  preferReadonlyFacts?: boolean;
  density?: 'default' | 'compact-task';
  hideGovernedSectionHeading?: boolean;
}>();
const emit = defineEmits<{
  'field-change': [payload: FormSectionFieldChange];
  'field-action': [payload: FormSectionFieldActionPayload];
  'action-ref': [action: ContractV2ActionRule];
}>();

const nodeKind = computed(() => String(props.node.kind || 'container').trim().toLowerCase());
const fields = computed(() => canonicalSectionFields(props.node)
  .filter((field) => canonicalFieldHasPresentableValue(field, props.relationAdapter))
  .map((field) => canonicalFieldToFormSection(
    field,
    props.relationAdapter,
    (fieldCode) => props.node.fields.find((candidate) => candidate.fieldCode === fieldCode),
  )).map(field => nodeKind.value === 'field' ? { ...field, span: containedFieldLayout().span } : field));
const readonlyFactLayout = computed(() => Boolean(
  props.preferReadonlyFacts
  && fields.value.length
  && fields.value.every((field) => field.readonly),
));
const valueEmphasis = computed(() => (
  readonlyFactLayout.value && fields.value.some((field) => field.type === 'monetary') ? 'monetary' : undefined
));
const children = computed(() => visibleCanonicalChildren(props.node));

/**
 * Ordinary native layout groups remain hidden. A released form-structure
 * group is different: its title is explicit contract authority and is shared
 * by the body heading and navigation target.
 */
const sectionTitle = computed(() => '');

/**
 * Feedback projections deliberately suppress the source group heading. Their
 * fields keep their labels inside the generic feedback surface instead of
 * becoming a second business section occurrence.
 */
const governedSection = computed(() => (
  props.hideGovernedSectionHeading
    ? null
    : governedFormStructureSectionIdentity(props.node) || nativeBusinessSectionIdentity(props.node)
));
const groupHeadingVisible = computed(() => Boolean(governedSection.value));

// Container/group nodes arrange their direct children on the declared grid.
//
// Column count: the projection declares it on every grid-owning container and
// has already applied the official default, so the renderer presents the
// declared value: it neither raises it to a minimum of its own nor clamps it to
// its own enum (a declared ``col="4"`` group must arrange four fields per row,
// not three).
//
// Placement: every child is placed by the declared layout span the contract
// projected for it, in the same 24-unit grid the field grid uses, and folds by
// the declared band. The renderer keeps no width rule of its own, so the node
// grid cannot place the same declaration differently from the field grid (it
// used to place every child at one column of the declared column count, kept a
// dead ``/6 -> 1..4`` span dialect and filled orphan rows with its own
// even-count rule).
const layoutColumns = computed(() => {
  if (nodeKind.value === 'field') return containedFieldLayout().columns;
  return requireDeclaredLayoutColumns(props.node.columns);
});
const declaredNodeSpan = computed(() => declaredLayoutSpan(props.node.span));
const declaredNodeBand = computed(() => declaredLayoutBand(declaredNodeSpan.value));
const hasContent = computed(() => canonicalNodeHasContent(props.node));
const nativeClass = computed(() => String(props.node.attributes.class || '').trim());
const presentableNodeText = computed(() => {
  const text = String(props.node.text || '');
  if (props.preferReadonlyFacts && /^[\s.·•:_-]+$/.test(text)) return '';
  return text;
});

</script>

<style scoped>
.canonical-form-node { min-width: 0; }
.canonical-form-node + .canonical-form-node { margin-top: 16px; }

/* Canonical container/group layout (form structure)
 * The contract declares this layout: a grid-owning container declares its
 * field-grid column count, and every node declares the 24-unit span it is
 * placed with. The renderer consumes those numbers only - field children and
 * structural children alike (a nested group declares the full grid width, so it
 * stacks) - and folds them by the one fold policy the field grid also
 * implements. The sheet spans the full task-section card so its interior
 * reaches the width that triggers the two-track form grid. */
.canonical-form-node--sheet { grid-column: 1 / -1; width: 100%; }
.canonical-form-node--notebook,
.canonical-form-node--page { grid-column: 1 / -1; }
/* The node grid repeats the field grid's structure, not only its numbers: the
 * node is the query container and the grid is a child of it. The difference is
 * load-bearing - a container query cannot style the query container itself, so
 * a grid that owned its own folds could never fold its own track count, and 24
 * tracks carry 23 column gaps that leave a narrow container no track at all. */
.canonical-form-node--container,
.canonical-form-node--group {
  min-width: 0;
  container-type: inline-size;
}
.canonical-form-node--container > .canonical-form-node-children,
.canonical-form-node--group > .canonical-form-node-children {
  display: grid;
  grid-template-columns: repeat(24, minmax(0, 1fr));
  gap: 16px 32px;
}
.canonical-form-node--container > .canonical-form-node-children > .canonical-form-node,
.canonical-form-node--group > .canonical-form-node-children > .canonical-form-node {
  grid-column: span var(--canonical-node-grid-span, 24);
  align-self: start;
  /* The generic sibling rule (.canonical-form-node + .canonical-form-node)
   * applies margin-top: 16px to every following node - inside the grid that
   * pushes the right/next field down by 16px and misaligns the row. Grid
   * children are spaced by the container gap, not this margin. */
  margin-top: 0;
}
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
.canonical-form-node--readonly-fact :deep(.field-control-main) {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  line-height: 22px;
}
.canonical-form-node--readonly-fact :deep(.readonly-value),
.canonical-form-node--readonly-fact :deep(.contract-readonly-value) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 0;
  line-height: 22px;
  font: inherit;
  color: var(--sc-app-text-primary);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
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
.canonical-form-node[data-density='compact-task'] + .canonical-form-node[data-density='compact-task'] { margin-top: 8px; }
.canonical-form-node[data-density='compact-task'].canonical-form-node--container,
.canonical-form-node[data-density='compact-task'].canonical-form-node--group { row-gap: 8px; }
.canonical-form-node[data-density='compact-task'].canonical-form-node--container > .canonical-form-node,
.canonical-form-node[data-density='compact-task'].canonical-form-node--group > .canonical-form-node { margin-top: 0; }
.canonical-form-node[data-density='compact-task'].canonical-form-node--readonly-fact { padding: 0; }

/* The declared-grid fold. The field grid owns this fold and this stylesheet
 * implements the same one, not a second policy of its own: below the declared
 * single-column width the grid keeps one track with no column gap and every
 * node owns the row, on the declared two-track face a node past half the grid
 * owns the row and anything narrower takes one track, and above that the
 * declared 24-unit span is the placement. The fold redefines the track count
 * because 24 tracks carry 23 column gaps - keeping them would leave the
 * narrowest container no track at all and push every node past its card.
 * A compact readonly fact grid never takes the one-track fold: 24 declared
 * tracks carry 23 declared column gaps, which no folded container can fit, so
 * on a folded width it keeps the two-track face the declared medium width also
 * carries and its facts stay side by side. Half-width writable controls keep a
 * usable inline size on phones. */
@container (max-width: 479px) {
  .canonical-form-node--container:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children,
  .canonical-form-node--group:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children {
    grid-template-columns: minmax(0, 1fr);
    column-gap: 0;
  }
  .canonical-form-node--container:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children > .canonical-form-node,
  .canonical-form-node--group:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children > .canonical-form-node {
    grid-column: 1 / -1;
  }
  /* The compact readonly fact face: the declared two tracks, never the single
   * column. The declared 24 tracks cannot be held on a folded width either -
   * their 23 column gaps do not fit - so the grid keeps the two-track face and
   * places its facts by the same declared band. */
  .canonical-form-node--container.canonical-form-node--readonly-fact > .canonical-form-node-children,
  .canonical-form-node--group.canonical-form-node--readonly-fact > .canonical-form-node-children {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .canonical-form-node--container.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='half'],
  .canonical-form-node--group.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='half'] {
    grid-column: span 1;
  }
  .canonical-form-node--container.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='full'],
  .canonical-form-node--group.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='full'] {
    grid-column: 1 / -1;
  }
}
@container (min-width: 480px) and (max-width: 959px) {
  .canonical-form-node--container:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children,
  .canonical-form-node--group:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .canonical-form-node--container:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children > .canonical-form-node[data-contract-band='half'],
  .canonical-form-node--group:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children > .canonical-form-node[data-contract-band='half'] {
    grid-column: span 1;
  }
  .canonical-form-node--container:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children > .canonical-form-node[data-contract-band='full'],
  .canonical-form-node--group:not(.canonical-form-node--readonly-fact) > .canonical-form-node-children > .canonical-form-node[data-contract-band='full'] {
    grid-column: 1 / -1;
  }
  /* The same compact readonly fact face: the declared 24 tracks carry 23 column
   * gaps that do not fit this width range either, so a readonly grid holds the
   * two declared tracks here as well. */
  .canonical-form-node--container.canonical-form-node--readonly-fact > .canonical-form-node-children,
  .canonical-form-node--group.canonical-form-node--readonly-fact > .canonical-form-node-children {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .canonical-form-node--container.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='half'],
  .canonical-form-node--group.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='half'] {
    grid-column: span 1;
  }
  .canonical-form-node--container.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='full'],
  .canonical-form-node--group.canonical-form-node--readonly-fact > .canonical-form-node-children > .canonical-form-node[data-contract-band='full'] {
    grid-column: 1 / -1;
  }
}
.canonical-form-native-action:disabled { cursor: not-allowed; opacity: 0.55; }
.canonical-form-native-widget { color: var(--sc-app-text-secondary); }
.canonical-form-native-text { white-space: pre-wrap; }
</style>
