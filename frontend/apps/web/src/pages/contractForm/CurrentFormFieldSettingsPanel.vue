<template>
  <section class="contract-form-settings">
    <header class="contract-form-settings-head">
      <div>
        <h4>当前页面字段配置</h4>
        <p>{{ scope.summary }}</p>
      </div>
      <span class="contract-form-settings-field-count">字段 {{ fieldCount }}</span>
    </header>
    <div class="contract-form-design-strip" aria-label="页面设计步骤">
      <div>
        <span>当前页面</span>
        <strong>{{ scope.scope }}</strong>
      </div>
      <div>
        <span>可配置项</span>
        <strong>字段名称、顺序、显示隐藏、新增字段</strong>
      </div>
      <div>
        <span>影响范围</span>
        <strong>{{ scope.saveTarget }}</strong>
      </div>
    </div>
    <section v-if="activeTab === 'fields'" class="contract-form-settings-fields">
      <header class="contract-form-settings-section-head">
        <div>
          <strong>字段配置</strong>
          <span>按旧表单分区点选字段，或按住字段拖拽调整顺序和分组。</span>
        </div>
        <div class="contract-form-settings-section-actions">
          <ScButton
            class="ghost small contract-field-central-create"
            type="button"
            :disabled="busy"
            @click="$emit('open-custom-field-create')"
          >
            新增字段
          </ScButton>
          <ScButton
            v-if="suggestedHiddenCount"
            class="ghost small"
            type="button"
            :disabled="busy"
            @click="$emit('hide-suggested-internal-fields')"
          >
            隐藏系统字段 {{ suggestedHiddenCount }}
          </ScButton>
        </div>
      </header>
      <div class="contract-form-designer-control-grid">
        <aside class="contract-form-designer-sidebar" aria-label="表单设计器导航">
          <header class="contract-form-designer-sidebar-head">
            <div>
              <span>字段目录</span>
              <strong>{{ fieldCount }} 个字段</strong>
            </div>
            <em>{{ groupNavigatorItems.length }} 个分组</em>
          </header>
          <section class="contract-form-field-search" aria-label="字段快速查找">
            <label>
              <span>查找字段</span>
              <ScInput
                :model-value="fieldSearchText"
                type="search"
                placeholder="搜索字段名称"
                :disabled="busy"
                @update:model-value="$emit('update:fieldSearchText', $event)"
              />
            </label>
            <div class="contract-form-field-search-summary">
              <span>匹配 {{ filteredFieldRows.length }} / {{ fieldCount }}</span>
              <ScButton
                v-if="fieldSearchText"
                class="link-button"
                type="button"
                :disabled="busy"
                @click="$emit('update:fieldSearchText', '')"
              >
                清空
              </ScButton>
            </div>
            <div v-if="filteredFieldRows.length" class="contract-form-field-search-results">
              <ScButton
                v-for="item in filteredFieldRows.slice(0, 8)"
                :key="`form-field-search-${item.fieldKey}`"
                type="button"
                class="contract-form-field-search-item"
                :class="{ 'contract-form-field-search-item--active': item.fieldKey === selectedFieldKey }"
                :disabled="busy"
                @click="$emit('select-field', item.fieldKey)"
              >
                <span>{{ item.label }}</span>
                <em>{{ item.groupTitle }}</em>
              </ScButton>
            </div>
            <p v-else class="contract-form-field-search-empty">没有匹配字段</p>
          </section>
          <section class="contract-form-field-navigator" aria-label="字段分组导航">
            <header>
              <strong>分组导航</strong>
              <span>点选分组定位画布</span>
            </header>
            <ScButton
              v-for="item in groupNavigatorItems"
              :key="item.title"
              type="button"
              class="contract-form-field-nav-item"
              :class="{ 'contract-form-field-nav-item--active': item.active }"
              @click="$emit('select-group', item.title)"
            >
              <span>{{ item.title }}</span>
              <em>{{ item.count }}</em>
            </ScButton>
          </section>
          <section class="contract-form-layout-tools" aria-label="表单布局配置">
            <header>
              <strong>页面布局</strong>
              <span>控制当前表单画布的整体列数。</span>
            </header>
            <label>
              <span>页面列数</span>
              <ScSelect :model-value="layoutColumns" :disabled="busy" :options="columnOptions" @update:model-value="$emit('layout-columns-change', $event)" />
            </label>
          </section>
        </aside>
        <aside class="record-form-inspector" aria-label="字段属性检查器">
          <section class="contract-field-selection-panel">
            <ScCard v-if="selectedFieldRow" appearance="record" class="contract-field-selection-card">
              <div class="contract-field-selection-main">
                <span>已选字段</span>
                <strong>{{ selectedFieldRow.label }}</strong>
                <small>{{ selectedFieldGroupTitle }}</small>
              </div>
              <div class="contract-field-selection-tools">
                <section class="contract-field-inspector-section">
                  <header>
                    <strong>基础属性</strong>
                  </header>
                  <label class="contract-field-label-edit">
                    <span>字段显示名称</span>
                    <ScInput
                      type="text"
                      :model-value="selectedFieldRow.label"
                      :disabled="busy"
                      @change="$emit('selected-field-label-change', $event)"
                    />
                  </label>
                  <div class="contract-field-governance-actions" role="radiogroup" :aria-label="`${selectedFieldRow.label}字段显示`">
                    <label
                      v-for="action in selectedFieldRow.actions"
                      :key="`${selectedFieldRow.fieldKey}-${action.key}`"
                      class="contract-field-governance-action"
                      :title="action.title"
                    >
                      <ScRadio
                        :name="`contract-field-governance-selected-${selectedFieldRow.fieldKey}`"
                        :value="action.value"
                        :checked="Boolean(action.checked)"
                        :disabled="Boolean(action.disabled)"
                        :label="action.label"
                        @change="$emit('selected-field-visibility-change', action.value)"
                      />
                      <span>{{ action.label }}</span>
                    </label>
                  </div>
                </section>
                <section class="contract-field-inspector-section">
                  <header>
                    <strong>布局与分组</strong>
                  </header>
                  <label class="contract-field-group-move">
                    <span>移动到分组</span>
                    <ScSelect
                      :model-value="selectedFieldGroupTitle"
                      :disabled="busy || groupOptions.length < 2"
                      :options="groupOptions.map((groupTitle) => ({ value: groupTitle, label: groupTitle }))"
                      @update:model-value="$emit('selected-field-group-move-change', $event)"
                    />
                  </label>
                  <label class="contract-field-group-rename">
                    <span>分组名称</span>
                    <ScInput
                      :model-value="selectedFieldGroupTitleEdit"
                      type="text"
                      :disabled="busy || !selectedFieldGroupTitle"
                      @update:model-value="$emit('update:selectedFieldGroupTitleEdit', $event)"
                      @change="$emit('selected-group-title-change', $event)"
                    />
                  </label>
                  <div class="contract-field-group-visibility" role="radiogroup" :aria-label="`${selectedFieldGroupTitle}分组显示`">
                    <span>分组显示</span>
                    <label>
                      <ScRadio
                        :name="`contract-field-group-visible-${selectedFieldGroupTitle}`"
                        value="show"
                        :checked="selectedGroupVisible"
                        :disabled="busy || !selectedFieldGroupTitle"
                        label="显示"
                        @change="$emit('selected-group-visibility-change', 'show')"
                      />
                      <span>显示</span>
                    </label>
                    <label>
                      <ScRadio
                        :name="`contract-field-group-visible-${selectedFieldGroupTitle}`"
                        value="hide"
                        :checked="!selectedGroupVisible"
                        :disabled="busy || !selectedFieldGroupTitle"
                        label="隐藏"
                        @change="$emit('selected-group-visibility-change', 'hide')"
                      />
                      <span>隐藏</span>
                    </label>
                  </div>
                  <label class="contract-field-group-columns">
                    <span>分组列数</span>
                    <ScSelect
                      :model-value="selectedGroupColumns"
                      :disabled="busy || !selectedFieldGroupTitle"
                      :options="columnOptions"
                      @update:model-value="$emit('selected-group-columns-change', $event)"
                    />
                  </label>
                  <label class="contract-field-size-control">
                    <span>字段尺寸</span>
                    <ScSelect
                      :model-value="selectedFieldSize"
                      :disabled="busy || !selectedFieldKey"
                      :options="fieldSizeOptions"
                      @update:model-value="$emit('selected-field-size-change', $event)"
                    />
                  </label>
                </section>
                <section class="contract-field-inspector-section">
                  <header>
                    <strong>位置调整</strong>
                  </header>
                  <div class="contract-field-position-move">
                    <label>
                      <span>移动位置</span>
                      <ScSelect
                        :model-value="orderTargetKey"
                        :disabled="busy || orderTargetOptions.length === 0"
                        :options="orderTargetOptions.map((option) => ({ value: option.fieldKey, label: option.label }))"
                        @update:model-value="$emit('update:orderTargetKey', $event)"
                      />
                    </label>
                    <label>
                      <span>放置方式</span>
                      <ScSelect
                        :model-value="orderPlacement"
                        :disabled="busy || orderTargetOptions.length === 0"
                        :options="placementOptions"
                        @update:model-value="$emit('update:orderPlacement', $event as 'before' | 'after')"
                      />
                    </label>
                    <ScButton
                      class="ghost small"
                      type="button"
                      :disabled="busy || !orderTargetKey"
                      @click="$emit('move-selected-field')"
                    >
                      移动
                    </ScButton>
                  </div>
                </section>
              </div>
            </ScCard>
            <div v-else class="contract-field-selection-empty">
              <strong>选择字段后开始配置</strong>
              <span>在下方表单点选字段后，可在这里调整显示、隐藏、顺序和分组。</span>
            </div>
          </section>
          <section class="contract-form-operation-log" aria-label="本次操作记录">
            <header>
              <div>
                <strong>本次操作记录</strong>
                <span>{{ operatorName }}</span>
              </div>
              <ScButton
                class="ghost small"
                type="button"
                :disabled="!operationLog.length"
                @click="$emit('clear-operation-log')"
              >
                清空记录
              </ScButton>
            </header>
            <ol v-if="operationLog.length" class="contract-form-operation-log-list">
              <li v-for="entry in operationLog.slice(0, 8)" :key="entry.id">
                <time>{{ formatOperationTime(entry.at) }}</time>
                <strong>{{ entry.action }}</strong>
                <span
                  class="contract-form-operation-log-status"
                  :class="`contract-form-operation-log-status--${entry.status}`"
                >
                  {{ operationStatusLabel(entry.status) }}
                </span>
                <span>{{ formatOperationSummary(entry.summary) }}</span>
              </li>
            </ol>
            <p v-else class="contract-form-operation-log-empty">暂无操作记录</p>
          </section>
        </aside>
      </div>
    </section>
    <div class="contract-field-governance-footer">
      <span v-if="hasDraftChanges" class="contract-field-governance-dirty">表单设置已调整，保存后生效</span>
      <span
        v-if="auditSummary"
        class="contract-field-governance-audit"
        :class="{ 'contract-field-governance-audit--warning': auditResult?.hasConflict }"
      >{{ auditSummary }}</span>
      <ScButton class="ghost" type="button" :disabled="busy || auditBusy" @click="$emit('audit')">
        {{ auditBusy ? '检查中...' : (auditResult ? '重新检查' : '检查效果') }}
      </ScButton>
      <ScButton class="chip-btn" type="button" :disabled="busy" @click="$emit('preview')">
        {{ hasDraftChanges ? '保存并预览' : '预览当前页面' }}
      </ScButton>
      <ScButton class="ghost" type="button" :disabled="busy || !hasDraftChanges" @click="$emit('save')">保存表单设置</ScButton>
      <ScButton class="ghost" type="button" :disabled="busy" @click="$emit('return-to-workbench')">返回工作台</ScButton>
      <ScButton class="ghost" type="button" :disabled="busy || !hasDraftChanges" @click="$emit('reset')">放弃调整</ScButton>
    </div>
  </section>
</template>

<script setup lang="ts">
import ScCard from '../../components/design-system/ScCard.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScInput from '../../components/design-system/ScInput.vue';
import ScRadio from '../../components/design-system/ScRadio.vue';
import ScSelect from '../../components/design-system/ScSelect.vue';
import type {
  ContractFieldGovernanceRow,
  FormConfigAuditResult,
  FormConfigOperationLogEntry,
  LowCodeFieldSize,
} from './types';

type FormFieldConfigScope = {
  summary: string;
  scope: string;
  saveTarget: string;
};

const columnOptions = [1, 2, 3].map((value) => ({ value, label: `${value} 栏` }));
const fieldSizeOptions = [
  { value: 'normal', label: '标准' },
  { value: 'wide', label: '加宽' },
  { value: 'full', label: '整行' },
  { value: 'large', label: '大输入框' },
];
const placementOptions = [
  { value: 'before', label: '移到其前' },
  { value: 'after', label: '移到其后' },
];

type FormDesignerGroupNavigatorItem = {
  title: string;
  count: number;
  active: boolean;
};

type FormDesignerFieldSearchRow = {
  fieldKey: string;
  label: string;
  groupTitle: string;
};

type FormDesignerOrderTargetOption = {
  fieldKey: string;
  label: string;
};

defineProps<{
  scope: FormFieldConfigScope;
  fieldCount: number;
  activeTab: string;
  busy: boolean;
  suggestedHiddenCount: number;
  fieldSearchText: string;
  filteredFieldRows: FormDesignerFieldSearchRow[];
  groupNavigatorItems: FormDesignerGroupNavigatorItem[];
  selectedFieldKey: string;
  layoutColumns: number;
  selectedFieldRow?: ContractFieldGovernanceRow;
  selectedFieldGroupTitle: string;
  groupOptions: string[];
  selectedFieldGroupTitleEdit: string;
  selectedGroupVisible: boolean;
  selectedGroupColumns: number;
  selectedFieldSize: LowCodeFieldSize;
  orderTargetKey: string;
  orderPlacement: 'before' | 'after';
  orderTargetOptions: FormDesignerOrderTargetOption[];
  operatorName: string;
  operationLog: FormConfigOperationLogEntry[];
  hasDraftChanges: boolean;
  auditSummary: string;
  auditResult?: FormConfigAuditResult | null;
  auditBusy: boolean;
  formatOperationTime: (at: string) => string;
  operationStatusLabel: (status: FormConfigOperationLogEntry['status']) => string;
  formatOperationSummary: (summary: string) => string;
}>();

defineEmits<{
  'open-custom-field-create': [];
  'hide-suggested-internal-fields': [];
  'update:fieldSearchText': [value: string];
  'select-field': [fieldKey: string];
  'select-group': [title: string];
  'layout-columns-change': [value: string];
  'selected-field-label-change': [value: string];
  'selected-field-visibility-change': [value: string];
  'selected-field-group-move-change': [value: string];
  'update:selectedFieldGroupTitleEdit': [value: string];
  'selected-group-title-change': [value: string];
  'selected-group-visibility-change': [value: 'show' | 'hide'];
  'selected-group-columns-change': [value: string];
  'selected-field-size-change': [value: string];
  'update:orderTargetKey': [value: string];
  'update:orderPlacement': [value: 'before' | 'after'];
  'move-selected-field': [];
  'clear-operation-log': [];
  audit: [];
  preview: [];
  save: [];
  'return-to-workbench': [];
  reset: [];
}>();

function inputValue(event: Event) {
  return String((event.target as HTMLInputElement | HTMLSelectElement).value || '');
}
</script>

<style src="./CurrentFormFieldSettingsPanel.css"></style>
