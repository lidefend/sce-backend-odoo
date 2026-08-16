<script setup lang="ts">
import { computed } from 'vue';
import type { SceneField, SceneObjectPageContract } from '../contracts/sceneObjectPage';
import SceneActivityTabs from './primitives/SceneActivityTabs.vue';
import SceneButton from './primitives/SceneButton.vue';
import SceneFieldControl from './primitives/SceneFieldControl.vue';
import SceneNotice from './primitives/SceneNotice.vue';
import ScenePageFrame from './primitives/ScenePageFrame.vue';
import SceneRelationTable from './primitives/SceneRelationTable.vue';
import SceneReviewPanel from './primitives/SceneReviewPanel.vue';

const props = defineProps<{
  contract: SceneObjectPageContract;
  prototypeMode?: boolean;
  fieldValues?: Record<string, string>;
  reviewPanelOpen?: boolean;
}>();
const emit = defineEmits<{
  fieldChange: [fieldId: string, value: string];
  'update:reviewPanelOpen': [value: boolean];
}>();

const primaryAction = computed(() => props.contract.actions.find((action) => action.tier === 'primary'));
const otherActions = computed(() => props.contract.actions.filter((action) => action.tier !== 'primary'));

function fieldClass(field: SceneField): Record<string, boolean> {
  return {
    'scene-field--full': field.span === 'full',
    'scene-field--readonly': Boolean(field.readonly),
  };
}

function fieldValue(field: SceneField): string {
  return props.fieldValues?.[field.id] ?? field.value;
}
</script>

<template>
  <div class="scene-shell" data-scene-object-page data-prototype-mode="true">
    <header class="scene-shellbar" aria-label="应用标题栏">
      <div class="scene-brandmark" aria-hidden="true">S</div>
      <div class="scene-brandcopy">
        <strong>{{ contract.identity.productName }}</strong>
        <span>{{ contract.identity.companyName }} · {{ contract.identity.roleName }}</span>
      </div>
      <div class="scene-shellbar__context">
        <span class="scene-shellbar__online" aria-hidden="true"></span>
        <span>企业工作台</span>
        <span class="scene-avatar" aria-hidden="true">财</span>
      </div>
    </header>

    <nav class="scene-worktabs" aria-label="活动页面">
      <button
        v-for="tab in contract.identity.workTabs"
        :key="tab.id"
        type="button"
        class="scene-worktab"
        :class="{ 'scene-worktab--active': tab.active }"
        :aria-current="tab.active ? 'page' : undefined"
      >
        <span>{{ tab.label }}</span>
        <span v-if="tab.active" class="scene-worktab__close" aria-hidden="true">×</span>
      </button>
    </nav>

    <div class="scene-breadcrumbs" aria-label="面包屑">
      <span v-for="(crumb, index) in contract.identity.breadcrumbs" :key="crumb">
        {{ crumb }}<i v-if="index < contract.identity.breadcrumbs.length - 1">/</i>
      </span>
    </div>

    <main class="scene-main">
      <ScenePageFrame class="scene-page">
        <template #heading>
          <div class="scene-title-heading">
            <div class="scene-title-heading__copy">
              <span class="scene-eyebrow">{{ contract.object.eyebrow }}</span>
              <div class="scene-title-line">
                <h1>{{ contract.object.title }}</h1>
                <span class="scene-status" :data-tone="contract.object.statusTone">{{ contract.object.status }}</span>
              </div>
              <p>{{ contract.object.subtitle }}</p>
            </div>
          </div>
        </template>

        <template #actions>
          <div class="scene-title-actions">
            <SceneButton
              v-for="action in otherActions"
              :key="action.id"
              :data-action-id="action.id"
              :tier="action.tier"
              :disabled="action.disabled || prototypeMode"
            >
              {{ action.label }}
            </SceneButton>
            <SceneButton
              v-if="primaryAction"
              :data-action-id="primaryAction.id"
              :tier="primaryAction.tier"
              :disabled="primaryAction.disabled || prototypeMode"
            >
              {{ primaryAction.label }}
            </SceneButton>
          </div>
        </template>

        <template #snapped>
          <div class="scene-snapped-facts">
            <span v-for="fact in contract.headerFacts.slice(0, 4)" :key="fact.id">
              <small>{{ fact.label }}</small>{{ fact.value }}
            </span>
          </div>
        </template>

        <template #header>
          <div class="scene-fact-strip" data-header-facts>
            <div
              v-for="fact in contract.headerFacts"
              :key="fact.id"
              class="scene-header-fact"
              :class="{ 'scene-header-fact--emphasis': fact.emphasis }"
              :data-tone="fact.tone || 'Neutral'"
            >
              <span>{{ fact.label }}</span>
              <strong>{{ fact.value }}</strong>
            </div>
          </div>
        </template>

        <div class="scene-content">
          <div v-if="contract.notices?.length" class="scene-notice-stack" data-scene-notices>
            <SceneNotice v-for="notice in contract.notices" :key="notice.id" :notice="notice" />
          </div>

          <section class="scene-task" aria-labelledby="scene-task-title" data-task-canvas>
            <header class="scene-section-heading">
              <div>
                <span class="scene-section-kicker">CURRENT TASK</span>
                <h2 id="scene-task-title">{{ contract.task.title }}</h2>
                <p>{{ contract.task.description }}</p>
              </div>
              <span class="scene-section-badge">办理字段</span>
            </header>

            <div v-for="group in contract.task.groups" :key="group.id" class="scene-field-group">
              <div class="scene-field-group__title">
                <h3>{{ group.title }}</h3>
                <p v-if="group.description">{{ group.description }}</p>
              </div>
              <div class="scene-field-grid">
                <div v-for="field in group.fields" :key="field.id" class="scene-field" :class="fieldClass(field)">
                  <label class="scene-field__label" :for="field.id">
                    {{ field.label }}<span v-if="field.required" aria-hidden="true">*</span>
                  </label>

                  <div v-if="field.readonly" class="scene-readonly-value" :id="field.id" data-readonly-fact>
                    <span>{{ field.value || '无' }}</span>
                    <small v-if="field.source">来源：{{ field.source }}</small>
                  </div>

                  <SceneFieldControl
                    v-else
                    :field="field"
                    :model-value="fieldValue(field)"
                    @update:model-value="emit('fieldChange', field.id, $event)"
                  />

                  <small v-if="field.hint" class="scene-field__hint">{{ field.hint }}</small>
                  <small v-if="field.source && !field.readonly" class="scene-field__source">已带入 · {{ field.source }}</small>
                </div>
              </div>
            </div>
          </section>

          <aside class="scene-context" aria-labelledby="scene-context-title" data-context-rail>
            <header class="scene-section-heading scene-section-heading--compact">
              <div>
                <span class="scene-section-kicker">BUSINESS CONTEXT</span>
                <h2 id="scene-context-title">{{ contract.context.title }}</h2>
                <p>{{ contract.context.description }}</p>
              </div>
              <span class="scene-section-badge scene-section-badge--neutral">只读事实</span>
            </header>

            <SceneReviewPanel
              v-if="contract.reviewPanel"
              :panel="contract.reviewPanel"
              :open="Boolean(reviewPanelOpen)"
              @update:open="emit('update:reviewPanelOpen', $event)"
            />

            <section v-for="group in contract.context.groups" :key="group.id" class="scene-context-group">
              <h3>{{ group.title }}</h3>
              <dl>
                <div v-for="fact in group.facts" :key="fact.id" :data-tone="fact.tone || 'Neutral'">
                  <dt>{{ fact.label }}</dt>
                  <dd>{{ fact.value }}</dd>
                </div>
              </dl>
            </section>
          </aside>

          <section v-if="contract.relations" class="scene-relations" aria-labelledby="scene-relations-title" data-relation-zone>
            <header class="scene-section-heading scene-section-heading--compact">
              <div>
                <span class="scene-section-kicker">RELATED FACTS</span>
                <h2 id="scene-relations-title">{{ contract.relations.title }}</h2>
                <p>{{ contract.relations.description }}</p>
              </div>
              <span class="scene-section-badge scene-section-badge--neutral">关系明细</span>
            </header>
            <div class="scene-relation-grid">
              <SceneRelationTable v-for="table in contract.relations.tables" :key="table.id" :table="table" />
            </div>
          </section>

          <section class="scene-activities" aria-labelledby="scene-activities-title" data-activity-tabs>
            <header class="scene-section-heading scene-section-heading--compact">
              <div>
                <span class="scene-section-kicker">ACTIVITY</span>
                <h2 id="scene-activities-title">{{ contract.activities.title }}</h2>
              </div>
            </header>

            <SceneActivityTabs :tabs="contract.activities.tabs" />
          </section>
        </div>
      </ScenePageFrame>
    </main>

    <footer class="scene-mobile-actions" aria-label="移动端办理动作">
      <SceneButton v-if="primaryAction" tier="primary" :disabled="prototypeMode">
        {{ primaryAction.label }}
      </SceneButton>
    </footer>
  </div>
</template>

<style>
:root {
  --sc-scene-bg: #f4f6f8;
  --sc-scene-surface: #ffffff;
  --sc-scene-border: #dfe5ec;
  --sc-scene-muted: #5f6b7a;
  --sc-scene-text: #1d2d3e;
  --sc-scene-brand: var(--sapBrandColor, #0a6ed1);
  --sc-scene-accent-soft: #eaf3fc;
  --sc-scene-warning: #a15c00;
  --sc-scene-success: #107e3e;
}

* {
  box-sizing: border-box;
}

.scene-shell {
  min-height: 100vh;
  background: var(--sc-scene-bg);
  color: var(--sc-scene-text);
  font-family: var(--sapFontFamily, "72", "Segoe UI", Arial, sans-serif);
}

.scene-shellbar {
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  min-height: 64px;
  padding: 0 28px;
  border-bottom: 1px solid var(--sc-scene-border);
  background: var(--sc-scene-surface);
  box-shadow: 0 1px 4px rgba(26, 47, 72, 0.06);
}

.scene-brandmark,
.scene-avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: var(--sc-scene-brand);
  color: white;
  font-weight: 700;
}

.scene-brandcopy {
  display: grid;
  gap: 2px;
  margin-left: 12px;
}

.scene-brandcopy strong {
  font-size: 17px;
}

.scene-brandcopy span,
.scene-shellbar__context {
  color: var(--sc-scene-muted);
  font-size: 12px;
}

.scene-shellbar__context {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.scene-shellbar__online {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--sc-scene-success);
}

.scene-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #edf2f7;
  color: #405269;
}

.scene-worktabs {
  display: flex;
  min-height: 44px;
  padding: 0 24px;
  border-bottom: 1px solid var(--sc-scene-border);
  background: #eef3f8;
}

.scene-worktab {
  display: flex;
  align-items: center;
  gap: 28px;
  min-width: 190px;
  padding: 0 16px;
  border: 0;
  border-right: 1px solid #d9e1ea;
  background: transparent;
  color: #4d5d6c;
  cursor: default;
  font: inherit;
  text-align: left;
}

.scene-worktab--active {
  border-bottom: 3px solid var(--sc-scene-brand);
  background: white;
  color: var(--sc-scene-text);
  font-weight: 700;
}

.scene-worktab__close {
  margin-left: auto;
  color: #627285;
  font-size: 17px…2 tokens truncated…+.scene-breadcrumbs {
  max-width: 1600px;
  margin: 0 auto;
  padding: 16px 32px 8px;
  color: var(--sc-scene-muted);
  font-size: 13px;
}

.scene-breadcrumbs i {
  margin: 0 8px;
  color: #a2acb8;
  font-style: normal;
}

.scene-main {
  max-width: 1600px;
  height: calc(100vh - 132px);
  min-height: 680px;
  margin: 0 auto;
  padding: 0 24px 24px;
}

.scene-page {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--sc-scene-border);
  border-radius: 12px;
  background: white;
  box-shadow: 0 8px 24px rgba(30, 50, 70, 0.08);
}

.scene-title-heading {
  display: flex;
  align-items: flex-start;
  min-width: 0;
}

.scene-title-heading__copy {
  min-width: 0;
}

.scene-eyebrow,
.scene-section-kicker {
  color: var(--sc-scene-brand);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.scene-title-line {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.scene-title-line h1 {
  overflow: hidden;
  margin: 2px 0 0;
  font-size: 25px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scene-title-heading p {
  margin: 5px 0 0;
  color: var(--sc-scene-muted);
  font-size: 13px;
}

.scene-status {
  flex: none;
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--sc-scene-accent-soft);
  color: var(--sc-scene-brand);
  font-size: 12px;
  font-weight: 700;
}

.scene-status[data-tone='Critical'] {
  background: #fff3df;
  color: var(--sc-scene-warning);
}

.scene-title-actions {
  min-width: max-content;
}

.scene-snapped-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 28px;
  padding: 4px 0;
}

.scene-snapped-facts span {
  display: grid;
  gap: 2px;
  font-size: 13px;
  font-weight: 700;
}

.scene-snapped-facts small {
  color: var(--sc-scene-muted);
  font-size: 11px;
  font-weight: 400;
}

.scene-fact-strip {
  display: grid;
  grid-template-columns: repeat(8, minmax(100px, 1fr));
  gap: 1px;
  overflow: hidden;
  border: 1px solid var(--sc-scene-border);
  border-radius: 8px;
  background: var(--sc-scene-border);
}

.scene-header-fact {
  display: grid;
  align-content: center;
  min-height: 66px;
  padding: 10px 13px;
  background: white;
}

.scene-header-fact span {
  color: var(--sc-scene-muted);
  font-size: 11px;
}

.scene-header-fact strong {
  overflow: hidden;
  margin-top: 5px;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scene-header-fact--emphasis {
  background: #f5faff;
}

.scene-header-fact[data-tone='Critical'] strong {
  color: var(--sc-scene-warning);
}

.scene-header-fact[data-tone='Positive'] strong {
  color: var(--sc-scene-success);
}

.scene-content {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(300px, 0.82fr);
  gap: 18px;
  padding: 18px;
  background: var(--sc-scene-bg);
}

.scene-notice-stack {
  display: grid;
  grid-column: 1 / -1;
  gap: 8px;
}

.scene-task,
.scene-context,
.scene-relations,
.scene-activities {
  min-width: 0;
  border: 1px solid var(--sc-scene-border);
  border-radius: 10px;
  background: white;
}

.scene-task {
  padding: 20px 22px;
}

.scene-context {
  align-self: start;
  padding: 20px;
  background: #fbfcfd;
}

.scene-relations {
  grid-column: 1 / -1;
  padding: 18px 20px 20px;
}

.scene-relation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.scene-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--sc-scene-border);
}

.scene-section-heading h2 {
  margin: 3px 0 0;
  font-size: 20px;
}

.scene-section-heading p {
  margin: 5px 0 0;
  color: var(--sc-scene-muted);
  font-size: 13px;
  line-height: 1.5;
}

.scene-section-heading--compact h2 {
  font-size: 18px;
}

.scene-section-badge {
  flex: none;
  padding: 4px 8px;
  border-radius: 5px;
  background: var(--sc-scene-accent-soft);
  color: var(--sc-scene-brand);
  font-size: 11px;
  font-weight: 700;
}

.scene-section-badge--neutral {
  background: #edf0f3;
  color: #556575;
}

.scene-field-group {
  padding: 18px 0 4px;
}

.scene-field-group + .scene-field-group {
  margin-top: 8px;
  border-top: 1px dashed var(--sc-scene-border);
}

.scene-field-group__title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}

.scene-field-group__title h3,
.scene-context-group h3 {
  margin: 0;
  color: #33465a;
  font-size: 14px;
}

.scene-field-group__title p {
  margin: 0;
  color: var(--sc-scene-muted);
  font-size: 12px;
}

.scene-field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 15px 18px;
}

.scene-field {
  display: grid;
  min-width: 0;
  gap: 5px;
}

.scene-field--full {
  grid-column: 1 / -1;
}

.scene-amount-input {
  position: relative;
}

.scene-amount-input span {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  color: var(--sc-scene-muted);
  font-size: 12px;
  pointer-events: none;
}

.scene-readonly-value {
  display: grid;
  min-height: 36px;
  align-content: center;
  padding: 5px 10px;
  border-left: 3px solid #b6c5d6;
  background: #f7f9fb;
  color: #2e4053;
}

.scene-readonly-value span {
  font-size: 14px;
  font-weight: 600;
}

.scene-readonly-value small,
.scene-field__source,
.scene-field__hint {
  color: var(--sc-scene-muted);
  font-size: 11px;
}

.scene-field__source {
  color: var(--sc-scene-brand);
}

.scene-context-group {
  padding: 16px 0;
  border-bottom: 1px solid var(--sc-scene-border);
}

.scene-context-group:last-child {
  border-bottom: 0;
}

.scene-context-group dl {
  display: grid;
  gap: 10px;
  margin: 12px 0 0;
}

.scene-context-group dl div {
  display: grid;
  grid-template-columns: minmax(90px, 0.7fr) minmax(0, 1.3fr);
  gap: 12px;
  align-items: baseline;
}

.scene-context-group dt {
  color: var(--sc-scene-muted);
  font-size: 12px;
}

.scene-context-group dd {
  min-width: 0;
  margin: 0;
  color: #293c50;
  font-size: 13px;
  font-weight: 600;
  text-align: right;
  overflow-wrap: anywhere;
}

.scene-context-group [data-tone='Critical'] dd {
  color: var(--sc-scene-warning);
}

.scene-activities {
  grid-column: 1 / -1;
  padding: 18px 20px 8px;
}

.scene-activity-tabs {
  width: 100%;
  margin-top: 6px;
}

.scene-activity-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 14px 4px 8px;
}

.scene-activity-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--sc-scene-border);
  border-radius: 8px;
  background: #fbfcfd;
}

.scene-activity-dot {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: #8395a7;
}

.scene-activity-dot[data-tone='Positive'] {
  background: var(--sc-scene-success);
}

.scene-activity-dot[data-tone='Information'] {
  background: var(--sc-scene-brand);
}

.scene-activity-item__title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.scene-activity-item__title span,
.scene-activity-item p,
.scene-empty-activity {
  color: var(--sc-scene-muted);
  font-size: 12px;
}

.scene-activity-item p {
  margin: 5px 0 0;
  line-height: 1.45;
}

.scene-empty-activity {
  padding: 28px;
  text-align: center;
}

.scene-mobile-actions {
  display: none;
}

@media (max-width: 1100px) {
  .scene-fact-strip {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .scene-content {
    grid-template-columns: minmax(0, 1fr);
  }

  .scene-context,
  .scene-relations,
  .scene-activities {
    grid-column: 1;
  }
}

@media (max-width: 640px) {
  .scene-shellbar {
    min-height: 56px;
    padding: 0 14px;
  }

  .scene-brandcopy strong {
    font-size: 15px;
  }

  .scene-brandcopy span,
  .scene-shellbar__context > span:not(.scene-avatar) {
    display: none;
  }

  .scene-worktabs {
    min-height: 40px;
    padding: 0;
  }

  .scene-worktab {
    min-width: 0;
    flex: 1 1 50%;
    gap: 6px;
    padding: 0 10px;
    font-size: 12px;
  }

  .scene-worktab span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .scene-breadcrumbs {
    overflow: hidden;
    padding: 10px 14px 6px;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .scene-main {
    height: calc(100vh - 128px);
    min-height: 620px;
    padding: 0 8px 74px;
  }

  .scene-page {
    height: 100%;
    min-height: 0;
    border-radius: 9px;
  }

  .scene-title-line {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .scene-title-line h1 {
    max-width: 100%;
    font-size: 20px;
  }

  .scene-title-actions {
    display: none;
  }

  .scene-snapped-facts {
    display: none;
  }

  .scene-fact-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .scene-header-fact {
    min-height: 58px;
    padding: 8px 10px;
  }

  .scene-content {
    gap: 10px;
    padding: 8px;
  }

  .scene-task,
  .scene-context,
  .scene-relations,
  .scene-activities {
    padding: 15px 13px;
    border-radius: 8px;
  }

  .scene-section-heading {
    gap: 8px;
  }

  .scene-section-heading h2 {
    font-size: 17px;
  }

  .scene-field-group__title {
    display: block;
  }

  .scene-field-group__title p {
    margin-top: 4px;
  }

  .scene-field-grid,
  .scene-relation-grid,
  .scene-activity-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .scene-context-group dl div {
    grid-template-columns: minmax(0, 1fr);
    gap: 3px;
  }

  .scene-context-group dd {
    text-align: left;
  }

  .scene-mobile-actions {
    position: fixed;
    z-index: 20;
    right: 0;
    bottom: 0;
    left: 0;
    display: flex;
    justify-content: flex-end;
    padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
    border-top: 1px solid var(--sc-scene-border);
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 -6px 18px rgba(28, 49, 70, 0.08);
    backdrop-filter: blur(8px);
  }

  .scene-mobile-actions > :first-child {
    width: 100%;
  }
}
</style>
