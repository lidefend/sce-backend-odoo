<template>
  <ScDialog v-if="contract && labels" :open="visible" :busy="busy" :title="labels.title" :close-label="labels.cancel_label"
    panel-class="native-import-wizard" data-dialog-purpose="native-import" @close="cancel">
    <template v-if="completed">
      <h3>{{ labels.result_label }}</h3>
      <p>{{ labels.imported_label }}：{{ completed.imported_count }}</p>
      <p>{{ labels.record_ids_label }}：{{ completed.ids.join(', ') }}</p>
    </template>
    <template v-else>
    <div v-if="templates.length"><p>{{ labels.templates_label }}</p>
      <a v-for="item in templates" :key="item.template" :href="item.template" download>{{ item.label }}</a>
    </div>
    <ScButton v-if="updateExport?.enabled" :disabled="busy" @click="exportUpdateFile">{{ updateExport.label }}</ScButton>
    <ScFileField :key="session" :accept="labels.file_accept" :choose-label="labels.choose_file_label"
      :empty-label="labels.empty_file_label" :disabled="busy" @change="selectFile" />
    <ScDisclosure :title="labels.options_label" :disabled="busy">
      <div v-for="field in optionFields" :key="field.name" class="native-import-wizard__column">
        <ScCheckbox v-if="field.type === 'boolean'" :checked="Boolean(options[field.name])"
          :disabled="busy" @update:checked="changeOption(field.name, $event)">{{ field.label }}</ScCheckbox>
        <template v-else><label :for="`import-option-${field.name}`">{{ field.label }}</label>
          <ScInput :id="`import-option-${field.name}`" :model-value="String(options[field.name] ?? '')"
            :disabled="busy" @update:model-value="changeOption(field.name, $event)" /></template>
      </div>
    </ScDisclosure>
    <ScButton :disabled="busy || !selectedFile" @click="inspect">{{ labels.preview_action_label }}</ScButton>
    <p>{{ labels.file_label }}：{{ contract.file_name }} · {{ labels.row_count_label }}：{{ contract.file_length }}</p>
    <div class="native-import-wizard__mapping">
      <div v-for="(header, index) in contract.headers" :key="index" class="native-import-wizard__column" :data-import-column="index">
        <label :for="`native-import-column-${index}`">{{ labels.column_label }}：{{ header }}</label>
        <ScSelect :id="`native-import-column-${index}`" :model-value="mapping[index] || ''" :options="fieldOptions"
          :disabled="busy" :aria-label="`${labels.field_label}：${header}`" @update:model-value="changeMapping(index, $event)" />
        <small>{{ labels.preview_label }}</small>
        <ul><li v-for="(value, row) in contract.preview[index] || []" :key="row">{{ value }}</li></ul>
      </div>
    </div>
    </template>
    <p v-if="message" role="status">{{ message }}</p>
    <ul v-if="messages.length" role="alert"><li v-for="(item, index) in messages" :key="index"><strong v-if="item.row_label">{{ item.row_label }}：</strong>{{ item.message }}</li></ul>
    <template #actions>
      <ScButton v-if="completed" variant="primary" @click="settle(completed)">{{ labels.done_label }}</ScButton>
      <template v-else>
      <ScButton variant="ghost" :disabled="busy" @click="cancel">{{ labels.cancel_label }}</ScButton>
      <ScButton variant="secondary" :disabled="busy || !inspected" @click="validate">{{ labels.validate_label }}</ScButton>
      <ScButton variant="primary" :disabled="busy || !validated" @click="execute">{{ labels.execute_label }}</ScButton>
      </template>
    </template>
  </ScDialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { exportRecordsCsv, importRecords, type ApiDataImportContract, type NativeImportField } from '../../api/data';
import { fileToBase64 } from '../../api/files';
import { contractGapError } from '../../app/contract/contractGap';
import ScDialog from '../design-system/ScDialog.vue';
import ScButton from '../design-system/ScButton.vue';
import ScSelect from '../design-system/ScSelect.vue';
import ScFileField from '../design-system/ScFileField.vue';
import ScInput from '../design-system/ScInput.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScDisclosure from '../design-system/ScDisclosure.vue';

type Input = { model: string; context: Record<string, unknown>; buildIdempotencyKey: (file: File) => string };
const visible = ref(false);
const session = ref(0);
const selectedFile = ref<File | null>(null);
const inspected = ref(false);
const completed = ref<ApiDataImportContract | null>(null);
const updateExport = ref<ApiDataImportContract['update_export']>();
const templates = ref<NonNullable<ApiDataImportContract['native_templates']>>([]);
const optionFields = ref<NonNullable<ApiDataImportContract['option_fields']>>([]);
const options = ref<Record<string, unknown>>({});
let inputContext: Input | null = null;
const busy = ref(false);
const validated = ref(false);
const contract = ref<ApiDataImportContract | null>(null);
const mapping = ref<Array<string | false>>([]);
const message = ref('');
const messages = ref<ApiDataImportContract['messages']>([]);
const labels = computed(() => contract.value?.wizard);
let request: Parameters<typeof importRecords>[0] | null = null;
let resolveResult: ((result: ApiDataImportContract | null) => void) | null = null;
const fieldOptions = computed(() => {
  const options = [{ value: '', label: labels.value?.ignore_label || '' }];
  function visit(fields: NativeImportField[], path: string[], names: string[]) {
    for (const field of fields) {
      const identity = [...path, field.id];
      const titles = [...names, field.string];
      options.push({ value: identity.join('/'), label: titles.join(' / ') });
      if (field.fields?.length) visit(field.fields, identity, titles);
    }
  }
  visit(contract.value?.native_fields || [], [], []);
  return options;
});
function requireNativeContract(value: ApiDataImportContract) {
  const keys = ['title', 'file_label', 'row_count_label', 'column_label', 'field_label', 'preview_label',
    'ignore_label', 'validate_label', 'execute_label', 'cancel_label', 'valid_label', 'mapping_changed_label',
    'choose_file_label', 'empty_file_label', 'preview_action_label', 'options_label', 'templates_label',
    'file_accept', 'done_label', 'result_label', 'imported_label', 'record_ids_label'];
  if (value.wizard?.schema !== 'native_import.v1' || value.wizard.authority !== 'base_import.import'
    || !Array.isArray(value.native_fields) || !value.native_fields.length
    || keys.some(key => !value.wizard?.[key])) {
    throw contractGapError({ kind: 'contract_defect', missing: 'native_import.v1',
      requiredDeclarationLayer: 'P0:smart_core:base_import' }, '原生导入向导契约不完整');
  }
}
async function open(input: Input): Promise<ApiDataImportContract | null> {
  if (busy.value || resolveResult) return null;
  busy.value = true;
  try {
    const described = await importRecords({ model: input.model, fileName: '', fileBase64: '',
      context: input.context, phase: 'describe', dryRun: true });
    requireNativeContract(described);
    if (!described.option_fields?.length || !described.native_options) {
      throw contractGapError({ kind: 'contract_defect', missing: 'native_import.option_fields',
        requiredDeclarationLayer: 'P0:smart_core:base_import' }, '原生导入解析选项契约缺失');
    }
    if (!described.update_export || typeof described.update_export.enabled !== 'boolean'
      || described.update_export.import_compatible !== true || !described.update_export.fields.length
      || !described.update_export.label || !described.update_export.empty_label) {
      throw contractGapError({ kind: 'contract_defect', missing: 'native_import.update_export',
        requiredDeclarationLayer: 'P0:smart_core:base_import' }, '原生导入更新标识契约缺失');
    }
    updateExport.value = described.update_export;
    inputContext = input; request = null; selectedFile.value = null; session.value += 1;
    inspected.value = false; completed.value = null;
    contract.value = described; mapping.value = [];
    templates.value = described.native_templates || [];
    optionFields.value = described.option_fields; options.value = { ...described.native_options };
    messages.value = []; message.value = ''; validated.value = false; visible.value = true;
    return new Promise(resolve => { resolveResult = resolve; });
  } finally { busy.value = false; }
}
async function exportUpdateFile() {
  if (busy.value || !inputContext || !updateExport.value?.enabled) return;
  busy.value = true; message.value = '';
  try {
    const result = await exportRecordsCsv({ model: inputContext.model, context: inputContext.context,
      fields: updateExport.value.fields, importCompatible: updateExport.value.import_compatible });
    if (!result.count) { message.value = updateExport.value.empty_label; return; }
    const link = document.createElement('a');
    link.href = `data:${result.mime_type};base64,${result.content_b64}`;
    link.download = result.file_name; link.click();
  } catch (error) { message.value = error instanceof Error ? error.message : String(error); }
  finally { busy.value = false; }
}
function invalidatePreview() {
  inspected.value = false; validated.value = false; mapping.value = [];
  messages.value = []; message.value = '';
  if (contract.value) contract.value = { ...contract.value, headers: [], preview: [], file_length: 0 };
}
function selectFile(files: File[]) {
  if (busy.value) return;
  selectedFile.value = files[0] || null; request = null; invalidatePreview();
}
function changeOption(name: string, value: unknown) {
  if (busy.value) return;
  options.value[name] = value; invalidatePreview();
}
async function inspect() {
  if (busy.value || !selectedFile.value || !inputContext) return;
  busy.value = true; invalidatePreview();
  try {
    const file = selectedFile.value;
    const { data, mimetype } = await fileToBase64(file);
    request = { model: inputContext.model, fileName: file.name, fileBase64: data, fileType: mimetype,
      context: inputContext.context, idempotencyKey: inputContext.buildIdempotencyKey(file) };
    const result = await importRecords({ ...request, phase: 'inspect', dryRun: true, options: options.value });
    requireNativeContract(result);
    contract.value = result; mapping.value = [...result.mapping];
    options.value = { ...result.native_options }; inspected.value = true;
  } catch (error) { message.value = error instanceof Error ? error.message : String(error); }
  finally { busy.value = false; }
}
function changeMapping(index: number, value: string | number) {
  if (busy.value) return;
  mapping.value[index] = String(value || '') || false;
  validated.value = false; messages.value = []; message.value = labels.value?.mapping_changed_label || '';
}
async function run(phase: 'validate' | 'execute') {
  if (!request || !contract.value || !inspected.value || busy.value || (phase === 'execute' && !validated.value)) return;
  busy.value = true; message.value = '';
  try {
    const result = await importRecords({ ...request, fields: [...mapping.value], columns: contract.value.headers,
      phase, dryRun: phase !== 'execute', options: options.value });
    messages.value = result.messages || [];
    validated.value = result.valid === true && result.error_count === 0;
    if (phase === 'execute' && validated.value) completed.value = result;
    else if (validated.value) message.value = labels.value?.valid_label || '';
  } catch (error) {
    validated.value = false;
    message.value = error instanceof Error ? error.message : String(error);
  } finally { busy.value = false; }
}
function validate() { return run('validate'); }
function execute() { return run('execute'); }
function settle(result: ApiDataImportContract | null) {
  visible.value = false; request = null; inputContext = null;
  const resolve = resolveResult; resolveResult = null; resolve?.(result);
}
function cancel() { if (!busy.value) settle(completed.value); }
defineExpose({ open });
</script>

<style scoped>
.native-import-wizard__mapping { display: grid; gap: 16px; }
.native-import-wizard__column { display: grid; gap: 8px; }
.native-import-wizard__column ul { margin: 0; padding-inline-start: 20px; }
</style>
