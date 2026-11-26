<template>
  <span v-if="attachmentLinks.length" class="field-value attachment-links">
    <a
      v-for="link in attachmentLinks"
      :key="`${link.name}-${link.url}`"
      href="#"
      target="_blank"
      rel="noopener"
      @click.prevent="previewAttachmentLink(link)"
    >
      {{ link.name }}
    </a>
  </span>
  <ScInlineState v-else-if="!display.trim()" state="empty" density="compact" :label="FIELD_VALUE_EMPTY_TEXT" />
  <span v-else class="field-value">{{ display }}</span>
  <AttachmentViewer ref="attachmentViewerRef" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { FieldDescriptor } from '@sc/schema';
import AttachmentViewer from './attachment/AttachmentViewer.vue';
import ScInlineState from './design-system/ScInlineState.vue';
import { parseAttachmentReferenceLinks } from '../utils/display';
import {
  presentDeclaredBusinessValue,
  resolveCurrencyDisplayLabel,
  type DeclaredBusinessField,
} from '../app/presentation/businessValuePresentation';
import { FIELD_VALUE_EMPTY_TEXT, hasDeclaredAttachmentIdentity } from '../utils/fieldSemantics';
import { attachmentLinkDownloadParams, openExternalAttachmentUrl } from '../utils/filePreview';

type FieldValueDescriptor = FieldDescriptor & Partial<DeclaredBusinessField> & {
  attachmentRole?: string;
};

const props = defineProps<{
  value: unknown;
  field?: FieldValueDescriptor;
  componentKey?: string;
  widget?: string;
  cellRole?: string;
  dataType?: string;
  currencyField?: string;
  currencyValue?: unknown;
  currencyLabel?: string;
  digits?: [number, number];
}>();
const attachmentViewerRef = ref<InstanceType<typeof AttachmentViewer> | null>(null);

const display = computed(() => {
  return presentDeclaredBusinessValue({
    field: {
      ...(props.field || {}),
      componentKey: props.componentKey || props.field?.componentKey,
      widget: props.widget || props.field?.widget,
      cellRole: props.cellRole || props.field?.cellRole,
      dataType: props.dataType || props.field?.dataType,
      currencyField: props.currencyField || props.field?.currencyField || props.field?.currency_field,
      digits: props.digits || props.field?.digits,
    },
    value: props.value,
    currencyLabel: props.currencyLabel || resolveCurrencyDisplayLabel(props.currencyValue),
    emptyText: FIELD_VALUE_EMPTY_TEXT,
  }).text;
});

const attachmentLinks = computed(() => hasDeclaredAttachmentIdentity(props.field)
  ? parseAttachmentReferenceLinks(props.value)
  : []);

async function previewAttachmentLink(link: { name: string; url: string }) {
  const params = attachmentLinkDownloadParams(link);
  if (params) {
    await attachmentViewerRef.value?.open(params, link.name);
    return;
  }
  openExternalAttachmentUrl(link.url);
}
</script>

<style scoped>
.field-value {
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.attachment-links {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}

.attachment-links a {
  color: var(--sc-primary, var(--sc-app-accent));
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
