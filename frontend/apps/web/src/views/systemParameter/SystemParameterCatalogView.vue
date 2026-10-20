<template>
  <ScPage class="system-parameter-catalog sc-product-main-surface" content-layout="data-grid" data-semantic-component="SystemParameterCatalogView">
    <div class="system-parameter-head">
      <div>
        <h1>系统参数</h1>
        <p>只展示产品批准的参数目录；部署密钥、数据库地址与认证信息不进入本页面。</p>
      </div>
      <ScButton type="button" variant="ghost" :disabled="loading" @click="load">重新读取</ScButton>
    </div>

    <ScInlineState v-if="loading" state="loading" label="正在加载参数目录。" />
    <ScInlineState v-else-if="error" state="error" :label="error">
      <template #actions><ScButton type="button" variant="secondary" @click="load">重试</ScButton></template>
    </ScInlineState>
    <ScInlineState v-else-if="gap" state="error" :label="gap" />

    <template v-else>
      <section v-for="category in categories" :key="category.key" class="parameter-category" :data-parameter-category="category.key">
        <h2>{{ category.label }}</h2>
        <div class="parameter-grid">
          <article
            v-for="parameter in byCategory.get(category.key) || []"
            :key="parameter.key"
            class="parameter-card"
            :data-parameter-key="parameter.key"
            :data-parameter-status="parameter.status"
            :data-parameter-available="parameter.available ? 'true' : 'false'"
          >
            <div class="parameter-card-head">
              <strong>{{ parameter.label }}</strong>
              <span class="parameter-status-badge" :data-parameter-status="parameter.status">{{ parameterStatusLabel(parameter.status) }}</span>
            </div>
            <p class="parameter-description">{{ parameter.description }}</p>
            <p class="parameter-meta">作用范围：{{ parameter.scope || '—' }} · 维护角色：{{ parameter.maintainer_role || '—' }}</p>
            <p class="parameter-impact">影响：{{ parameter.impact?.summary || '—' }}</p>

            <div v-if="parameter.available" class="parameter-edit">
              <select
                :value="currentValueFor(parameter)"
                :aria-label="parameter.label"
                @change="onSelect(parameter, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="option in parameter.allowed_values" :key="String(option)" :value="String(option)">{{ valueLabel(option) }}</option>
              </select>
              <ScButton type="button" variant="secondary" :disabled="previewLoading" @click="previewFor(parameter.key, currentValueFor(parameter))">预览影响</ScButton>
              <ScButton
                type="button"
                variant="primary"
                :disabled="publishing || !preview || preview.parameter !== parameter.key || !preview.ok"
                @click="publish(parameter.key, currentValueFor(parameter), '工作台发布')"
              >
                {{ publishing ? '发布中...' : '发布' }}
              </ScButton>
            </div>
            <p v-else class="parameter-reason">该参数尚未发布，暂不可修改。</p>
          </article>
        </div>
      </section>

      <section v-if="preview && preview.ok" class="impact-preview" data-semantic-component="SystemParameterImpactPreview">
        <h2>影响预览</h2>
        <p><strong>参数：</strong>{{ preview.parameter }}</p>
        <p><strong>影响面：</strong>{{ (preview.impact?.surfaces || []).join('、') || '—' }}</p>
        <p><strong>说明：</strong>{{ preview.impact?.summary || '—' }}</p>
        <p><strong>风险等级：</strong>{{ preview.impact?.risk_level || '—' }}</p>
        <p class="impact-note">发布将写入变更集并保留审计与回滚快照。</p>
      </section>
      <ScInlineState v-else-if="preview && !preview.ok" state="error" :label="preview.reason === 'not_implemented' ? '该参数尚未发布，暂不可修改。' : (preview.reason || '影响预览未通过')" />
      <ScInlineState v-if="previewError" state="error" :label="previewError" />

      <section v-if="changes.length" class="change-history" data-semantic-component="SystemParameterChangeHistory">
        <h2>最近变更</h2>
        <div v-for="change in changes" :key="change.id" class="change-row" :data-change-state="change.state">
          <span><strong>{{ change.parameter_key }}</strong> → {{ String(change.proposed_value) }}</span>
          <span class="change-state">{{ change.state }}</span>
          <ScButton v-if="change.state === 'published'" type="button" variant="ghost" :disabled="publishing" @click="rollback(change.id)">回滚</ScButton>
        </div>
      </section>
      <ScInlineState v-if="mutationError" state="error" :label="mutationError" />
    </template>
  </ScPage>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import ScPage from '../../components/design-system/ScPage.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScInlineState from '../../components/design-system/ScInlineState.vue';
import { parameterStatusLabel } from '../../app/productSystemParameterProjection';
import type { ProductSystemParameter } from '../../api/productSystemParameter';
import { useSystemParameterCatalog } from '../../composables/systemParameter/useSystemParameterCatalog';

const {
  loading,
  error,
  gap,
  categories,
  byCategory,
  previewLoading,
  preview,
  previewError,
  publishing,
  mutationError,
  changes,
  load,
  previewFor,
  publish,
  rollback,
} = useSystemParameterCatalog();

const pendingValues = new Map<string, unknown>();

function currentValueFor(parameter: ProductSystemParameter): unknown {
  if (pendingValues.has(parameter.key)) return pendingValues.get(parameter.key);
  return parameter.current_value ?? parameter.default;
}

function onSelect(parameter: ProductSystemParameter, value: string) {
  pendingValues.set(parameter.key, value);
}

function valueLabel(value: unknown): string {
  return String(value ?? '');
}

onMounted(() => {
  void load();
});
</script>

<style scoped>
.system-parameter-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.system-parameter-head h1 { margin: 0; }
.system-parameter-head p { margin: 4px 0 0; color: var(--sc-app-text-secondary); }
.parameter-category { margin-top: 24px; }
.parameter-category h2 { margin: 0 0 8px; font-size: 16px; }
.parameter-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.parameter-card { display: grid; gap: 8px; padding: 14px; border: 1px solid var(--sc-app-border); border-radius: var(--sc-radius-md); background: var(--sc-app-panel); min-width: 0; }
.parameter-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.parameter-card-head strong { overflow-wrap: anywhere; }
.parameter-status-badge { flex: none; font-size: 12px; padding: 2px 8px; border-radius: 999px; color: var(--sc-app-text-secondary); background: var(--sc-app-border); }
.parameter-description { margin: 0; color: var(--sc-app-text-primary); }
.parameter-meta, .parameter-impact { margin: 0; color: var(--sc-app-text-secondary); font-size: 12px; overflow-wrap: anywhere; }
.parameter-reason { margin: 0; color: var(--sc-app-text-muted); font-size: 12px; }
.parameter-edit { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.parameter-edit select { min-width: 140px; }
.impact-preview { margin-top: 24px; padding: 16px; border: 1px solid var(--sc-app-border); border-radius: var(--sc-radius-md); background: var(--sc-app-panel); }
.impact-preview h2 { margin: 0 0 8px; }
.impact-preview p { margin: 4px 0; }
.impact-note { color: var(--sc-app-text-secondary); font-size: 12px; }
.change-history { margin-top: 24px; }
.change-history h2 { margin: 0 0 8px; font-size: 16px; }
.change-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--sc-app-border); }
.change-state { color: var(--sc-app-text-secondary); font-size: 12px; }
</style>
