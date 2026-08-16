<script setup lang="ts">
import { computed } from 'vue';
import type { SceneCollectionContract } from '../contracts/sceneCollection';
import type { SceneTableRow } from '../contracts/sceneObjectPage';
import SceneButton from './primitives/SceneButton.vue';
import SceneRelationTable from './primitives/SceneRelationTable.vue';
import SceneWorkspaceHeader from './primitives/SceneWorkspaceHeader.vue';

const props = defineProps<{
  contract: SceneCollectionContract;
  selectedRowIds?: string[];
  prototypeMode?: boolean;
}>();
const emit = defineEmits<{
  toggleRow: [rowId: string];
  openRow: [row: SceneTableRow];
}>();

const primaryAction = computed(() => props.contract.actions.find((action) => action.tier === 'primary'));
const otherActions = computed(() => props.contract.actions.filter((action) => action.tier !== 'primary'));
const selected = computed(() => new Set(props.selectedRowIds || []));
const selectable = computed(() => props.contract.selectionMode === 'multiple' && !props.contract.readonly);

function toggleRow(rowId: string): void {
  if (selectable.value) emit('toggleRow', rowId);
}

function activateRow(row: SceneTableRow): void {
  if (selectable.value) {
    toggleRow(row.id);
    return;
  }
  emit('openRow', row);
}
</script>

<template>
  <div
    class="scene-collection-shell"
    data-scene-collection-surface
    :data-scene-collection-readonly="contract.readonly"
    :data-scene-contract-source="contract.sourceTrace?.kind || 'scene-contract'"
    :data-scene-contract-page-id="contract.sourceTrace?.pageId"
  >
    <SceneWorkspaceHeader :identity="contract.identity" />

    <main class="scene-collection-main">
      <section class="scene-collection-card">
        <header class="scene-collection-title">
          <div>
            <span class="scene-collection-eyebrow">{{ contract.eyebrow }}</span>
            <h1>{{ contract.title }}</h1>
            <p>{{ contract.description }}</p>
          </div>
          <div class="scene-collection-actions">
            <SceneButton
              v-for="action in otherActions"
              :key="action.id"
              :tier="action.tier"
              :disabled="action.disabled || prototypeMode"
            >
              {{ action.label }}
            </SceneButton>
            <SceneButton v-if="primaryAction" tier="primary" :disabled="primaryAction.disabled || prototypeMode">
              {{ primaryAction.label }}
            </SceneButton>
          </div>
        </header>

        <div class="scene-collection-summaries" data-collection-summaries>
          <article v-for="fact in contract.summaries" :key="fact.id" :data-tone="fact.tone || 'Neutral'">
            <span>{{ fact.label }}</span>
            <strong>{{ fact.value }}</strong>
          </article>
        </div>

        <div class="scene-collection-toolbar">
          <div class="scene-collection-filters" aria-label="当前筛选">
            <span
              v-for="filter in contract.readonly ? contract.filters : []"
              :key="filter.id"
              class="scene-collection-filter"
              :class="{ 'scene-collection-filter--active': filter.active }"
              :data-filter-id="filter.id"
            >
              <span>{{ filter.label }}</span>
              <strong>{{ filter.value }}</strong>
            </span>
            <button
              v-for="filter in contract.readonly ? [] : contract.filters"
              :key="filter.id"
              type="button"
              :class="{ 'scene-collection-filter--active': filter.active }"
              :data-filter-id="filter.id"
            >
              <span>{{ filter.label }}</span>
              <strong>{{ filter.value }}</strong>
            </button>
          </div>
          <span class="scene-collection-count">{{ contract.totalCount ?? contract.table.rows.length }} 条业务记录</span>
        </div>

        <div class="scene-collection-desktop-table" data-collection-table>
          <SceneRelationTable
            :table="contract.table"
            :interactive-rows="true"
            @activate-row="activateRow"
          />
        </div>

        <div
          class="scene-collection-mobile-cards"
          :role="selectable ? 'listbox' : 'list'"
          :aria-label="contract.rowPresentation.accessibilityLabel"
          data-collection-mobile-cards
        >
          <article
            v-for="row in contract.table.rows"
            :key="row.id"
            :class="{ 'scene-collection-mobile-card--selected': selected.has(row.id) }"
            :data-collection-row="row.id"
            :role="selectable ? 'option' : 'listitem'"
            :tabindex="selectable ? 0 : undefined"
            :aria-selected="selectable ? selected.has(row.id) : undefined"
            @click="activateRow(row)"
            @keydown.enter.prevent="activateRow(row)"
            @keydown.space.prevent="selectable ? toggleRow(row.id) : undefined"
          >
            <header>
              <strong>{{ row.values[contract.rowPresentation.titleField] }}</strong>
              <span v-if="contract.rowPresentation.statusField" :data-tone="row.tone || 'Neutral'">
                {{ row.values[contract.rowPresentation.statusField] }}
              </span>
            </header>
            <dl>
              <div v-for="columnKey in contract.rowPresentation.mobileFields" :key="columnKey">
                <template v-if="contract.table.columns.find((column) => column.key === columnKey)">
                  <dt>{{ contract.table.columns.find((column) => column.key === columnKey)?.label }}</dt>
                  <dd>{{ row.values[columnKey] || '无' }}</dd>
                </template>
              </div>
            </dl>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
.scene-collection-shell,
.scene-hierarchy-shell {
  min-height: 100vh;
  background: var(--sc-scene-bg);
  color: var(--sc-scene-text);
  font-family: var(--sapFontFamily, "72", "Segoe UI", Arial, sans-serif);
}

.scene-collection-main,
.scene-hierarchy-main { max-width: 1540px; margin: 0 auto; padding: 0 24px 28px; }
.scene-collection-card,
.scene-hierarchy-card { overflow: hidden; border: 1px solid var(--sc-scene-border); border-radius: var(--sc-scene-surface-radius, 12px); background: var(--sc-scene-surface); box-shadow: 0 8px 24px rgba(30, 50, 70, 0.07); }

.scene-collection-title,
.scene-hierarchy-title { display: flex; align-items: flex-start; gap: 24px; padding: 20px 22px 17px; border-bottom: 1px solid var(--sc-scene-border); }
.scene-collection-title h1,
.scene-hierarchy-title h1 { margin: 3px 0 0; font-size: 24px; }
.scene-collection-title p,
.scene-hierarchy-title p { margin: 5px 0 0; color: var(--sc-scene-muted); font-size: 13px; }
.scene-collection-eyebrow,
.scene-hierarchy-eyebrow { color: var(--sc-scene-brand); font-size: 11px; font-weight: 700; letter-spacing: 0.08em; }
.scene-collection-actions,
.scene-hierarchy-actions { display: flex; gap: 8px; margin-left: auto; }

.scene-collection-summaries,
.scene-hierarchy-summaries { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: var(--sc-scene-border); border-bottom: 1px solid var(--sc-scene-border); }
.scene-collection-summaries article,
.scene-hierarchy-summaries article { display: grid; gap: 4px; min-height: 70px; padding: 13px 16px; background: var(--sc-scene-surface); }
.scene-collection-summaries span,
.scene-hierarchy-summaries span { color: var(--sc-scene-muted); font-size: 11px; }
.scene-collection-summaries strong,
.scene-hierarchy-summaries strong { font-size: 17px; }

.scene-collection-toolbar { display: flex; align-items: center; gap: 14px; padding: 14px 16px; }
.scene-collection-filters { display: flex; flex-wrap: wrap; gap: 7px; }
.scene-collection-filter,
.scene-collection-filters button { display: flex; gap: 7px; padding: 7px 10px; border: 1px solid var(--sc-scene-border); border-radius: 999px; background: var(--sc-scene-surface); color: var(--sc-scene-muted); font: inherit; font-size: 12px; }
.scene-collection-filter strong,
.scene-collection-filters button strong { color: var(--sc-scene-text); }
.scene-collection-filters .scene-collection-filter--active { border-color: var(--sc-scene-brand); background: var(--sc-scene-accent-soft); color: var(--sc-scene-brand); }
.scene-collection-count { margin-left: auto; color: var(--sc-scene-muted); font-size: 12px; white-space: nowrap; }
.scene-collection-desktop-table { padding: 0 16px 18px; }
.scene-collection-mobile-cards { display: none; }

@media (max-width: 640px) {
  .scene-collection-main,
  .scene-hierarchy-main { padding: 0 10px 18px; }
  .scene-collection-title,
  .scene-hierarchy-title { display: grid; padding: 15px 14px 13px; }
  .scene-collection-title h1,
  .scene-hierarchy-title h1 { font-size: 20px; }
  .scene-collection-actions,
  .scene-hierarchy-actions { width: 100%; margin-left: 0; overflow-x: auto; }
  .scene-collection-summaries,
  .scene-hierarchy-summaries { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .scene-collection-summaries article,
  .scene-hierarchy-summaries article { min-height: 62px; padding: 10px 12px; }
  .scene-collection-toolbar { display: grid; padding: 12px; }
  .scene-collection-count { margin-left: 0; }
  .scene-collection-desktop-table { display: none; }
  .scene-collection-mobile-cards { display: grid; gap: 9px; padding: 0 12px 14px; }
  .scene-collection-mobile-cards article { padding: 12px; border: 1px solid var(--sc-scene-border); border-radius: var(--sc-scene-control-radius, 9px); background: var(--sc-scene-surface); }
  .scene-collection-mobile-cards article header { display: flex; gap: 12px; justify-content: space-between; }
  .scene-collection-mobile-cards dl { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 12px; margin: 12px 0 0; }
  .scene-collection-mobile-cards dl div { min-width: 0; }
  .scene-collection-mobile-cards dt { color: var(--sc-scene-muted); font-size: 10px; }
  .scene-collection-mobile-cards dd { overflow: hidden; margin: 3px 0 0; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
  .scene-collection-mobile-card--selected { border-color: var(--sc-scene-brand) !important; background: var(--sc-scene-accent-soft) !important; }
}
</style>
