<template>
  <section
    class="boq-import-preview"
    data-boq-import-preview
    :data-view-state="model.viewState"
    data-readonly="true"
    :aria-busy="false"
  >
    <!-- 错误态：结构化错误透传，不白屏 -->
    <div v-if="model.viewState === 'error'" class="boq-import-preview__error" data-preview-error>
      <p class="boq-import-preview__error-code" data-error-code>{{ model.errorCode }}</p>
      <p class="boq-import-preview__error-message" data-error-message>{{ model.errorMessage }}</p>
      <p v-if="model.suggestedAction" class="boq-import-preview__error-hint" data-suggested-action>
        {{ model.suggestedAction }}
      </p>
    </div>

    <!-- 空态：missing_payload 契约语义 -->
    <div
      v-else-if="model.viewState === 'missing_payload' || model.viewState === 'degraded_shape'"
      class="boq-import-preview__empty"
      data-preview-empty
    >
      <p class="boq-import-preview__empty-title">{{ model.batch?.name || '清单导入批次' }}</p>
      <p class="boq-import-preview__empty-message" data-empty-message>{{ model.stateMessage }}</p>
    </div>

    <!-- 就绪态：只读统计卡 + 解析诊断 -->
    <template v-else>
      <header class="boq-import-preview__header" data-preview-header>
        <h3 class="boq-import-preview__title">{{ model.batch?.name || '清单导入批次' }}</h3>
        <dl class="boq-import-preview__meta" data-preview-meta>
          <div class="boq-import-preview__meta-item">
            <dt>文件</dt>
            <dd data-batch-filename>{{ model.batch?.filename || '—' }}</dd>
          </div>
          <div class="boq-import-preview__meta-item">
            <dt>批次状态</dt>
            <dd data-batch-state>{{ model.batch?.state || '—' }}</dd>
          </div>
          <div class="boq-import-preview__meta-item">
            <dt>导入时间</dt>
            <dd data-batch-imported-at>{{ model.batch?.importedAtLabel || '—' }}</dd>
          </div>
          <div class="boq-import-preview__meta-item">
            <dt>快照协议</dt>
            <dd data-preview-schema>{{ model.previewSchema }}</dd>
          </div>
        </dl>
      </header>

      <ul class="boq-import-preview__stats" data-preview-stats>
        <li
          v-for="stat in model.stats"
          :key="stat.key"
          class="boq-import-preview__stat"
          :class="`boq-import-preview__stat--${stat.emphasis}`"
          :data-stat-key="stat.key"
        >
          <span class="boq-import-preview__stat-label">{{ stat.label }}</span>
          <span class="boq-import-preview__stat-value">{{ stat.value }}</span>
        </li>
      </ul>

      <div v-if="model.diagnostics.length" class="boq-import-preview__diagnostics" data-preview-diagnostics>
        <p class="boq-import-preview__diagnostics-title">解析诊断</p>
        <ul>
          <li v-for="(line, index) in model.diagnostics" :key="index">{{ line }}</li>
        </ul>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
/**
 * BOQ 导入批次只读预检快照面板（G3.2）。
 *
 * 数据契约：contracts/domain/boq.yaml v1（只读域）。
 * 只读投影组件：不含任何写操作（导入入口沿用既有向导，
 * digest 绑定 + [SC_GUARD:*] 错误透传），错误/空态均结构化渲染。
 */
import type { BoqImportPreviewViewModel } from '../../app/presentation/boqImportPreview';

defineProps<{
  model: BoqImportPreviewViewModel;
}>();
</script>

<style scoped>
.boq-import-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--sc-border-color, #d9d9d9);
  border-radius: 8px;
  font-size: 14px;
}

.boq-import-preview__header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.boq-import-preview__title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.boq-import-preview__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  margin: 0;
}

.boq-import-preview__meta-item {
  display: flex;
  gap: 6px;
}

.boq-import-preview__meta-item dt {
  color: var(--sc-text-secondary, #666);
}

.boq-import-preview__meta-item dd {
  margin: 0;
}

.boq-import-preview__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.boq-import-preview__stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  border-radius: 6px;
  background: var(--sc-surface-muted, #f5f5f5);
}

.boq-import-preview__stat--warning {
  background: var(--sc-surface-warning, #fff7e6);
}

.boq-import-preview__stat-label {
  color: var(--sc-text-secondary, #666);
  font-size: 12px;
}

.boq-import-preview__stat-value {
  font-weight: 600;
}

.boq-import-preview__diagnostics {
  border-top: 1px solid var(--sc-border-color, #e8e8e8);
  padding-top: 8px;
}

.boq-import-preview__diagnostics-title {
  margin: 0 0 4px;
  font-weight: 600;
}

.boq-import-preview__diagnostics ul {
  margin: 0;
  padding-left: 18px;
  color: var(--sc-text-secondary, #666);
  font-size: 12px;
}

.boq-import-preview__error,
.boq-import-preview__empty {
  padding: 12px;
  border-radius: 6px;
}

.boq-import-preview__error {
  background: var(--sc-surface-danger-muted, #fff1f0);
}

.boq-import-preview__error-code {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--sc-danger, #cf1322);
}

.boq-import-preview__error-message,
.boq-import-preview__empty-message {
  margin: 4px 0 0;
}

.boq-import-preview__error-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--sc-text-secondary, #666);
}

.boq-import-preview__empty {
  background: var(--sc-surface-muted, #f5f5f5);
}

.boq-import-preview__empty-title {
  margin: 0;
  font-weight: 600;
}
</style>
