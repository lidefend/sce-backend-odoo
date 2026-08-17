<script setup lang="ts">
import { computed } from 'vue';
import type { SceneAction, SceneField, SceneObjectPageContract } from '../contracts/sceneObjectPage';

const props = defineProps<{
  contract: SceneObjectPageContract;
  prototypeMode?: boolean;
}>();

const primaryAction = computed(() => props.contract.actions.find((action) => action.tier === 'primary'));
const otherActions = computed(() => props.contract.actions.filter((action) => action.tier !== 'primary'));

function actionDesign(action: SceneAction): 'Emphasized' | 'Default' | 'Transparent' {
  if (action.tier === 'primary') return 'Emphasized';
  if (action.tier === 'transparent') return 'Transparent';
  return 'Default';
}

function fieldClass(field: SceneField): Record<string, boolean> {
  return {
    'scene-field--full': field.span === 'full',
    'scene-field--readonly': Boolean(field.readonly),
  };
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
      <ui5-dynamic-page class="scene-page" hide-pin-button>
        <ui5-dynamic-page-title slot="titleArea" class="scene-page-title">
          <div slot="heading" class="scene-title-heading">
            <div class="scene-title-heading__copy">
              <span class="scene-eyebrow">{{ contract.object.eyebrow }}</span>
              <div class="scene-title-line">
                <h1>{{ contract.object.title }}</h1>
                <span class="scene-status" :data-tone="contract.object.statusTone">{{ contract.object.status }}</span>
              </div>
              <p>{{ contract.object.subtitle }}</p>
            </div>
          </div>

          <ui5-toolbar slot="actionsBar" class="scene-title-actions" design="Transparent">
            <ui5-button
              v-for="action in otherActions"
              :key="action.id"
              :data-action-id="action.id"
              :design="actionDesign(action)"
              :disabled="action.disabled || prototypeMode"
            >
              {{ action.label }}
            </ui5-button>
            <ui5-button
              v-if="primaryAction"
              :data-action-id="primaryAction.id"
              :design="actionDesign(primaryAction)"
              :disabled="primaryAction.disabled || prototypeMode"
            >
              {{ primaryAction.label }}
            </ui5-button>
          </ui5-toolbar>

          <div class="scene-snapped-facts">
            <span v-for="fact in contract.headerFacts.slice(0, 4)" :key="fact.id">
              <small>{{ fact.label }}</small>{{ fact.value }}
            </span>
          </div>
        </ui5-dynamic-page-title>

        <ui5-dynamic-page-header slot="headerArea" class="scene-page-header">
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
        </ui5-dynamic-page-header>

        <div class="scene-content">
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
                  <ui5-label :for="field.id" :required="field.required">{{ field.label }}</ui5-label>

                  <div v-if="field.readonly" class="scene-readonly-value" :id="field.id" data-readonly-fact>
                    <span>{{ field.value || '无' }}</span>
                    <small v-if="field.source">来源：{{ field.source }}</small>
                  </div>

                  <ui5-date-picker
                    v-else-if="field.kind === 'date'"
                    :id="field.id"
                    :value="field.value"
                    format-pattern="yyyy-MM-dd"
                    :placeholder="field.placeholder"
                  />

                  <ui5-select v-else-if="field.kind === 'select'" :id="field.id">
                    <ui5-option
                      v-for="option in field.options || []"
                      :key="option.key"
                      :selected="option.key === field.value"
                    >
                      {{ option.label }}
                    </ui5-option>
                  </ui5-select>

                  <ui5-textarea
                    v-else-if="field.kind === 'textarea'"
                    :id="field.id"
                    :value="field.value"
                    :placeholder="field.placeholder"
                    growing
                    growing-max-rows="5"
                  />

                  <div v-else-if="field.kind === 'amount'" class="scene-amount-input">
                    <ui5-input
                      :id="field.id"
                      :value="field.value"
                      :placeholder="field.placeholder"
                      inputmode="decimal"
                    />
                    <span>CNY</span>
                  </div>

                  <ui5-input
                    v-else
                    :id="field.id"
                    :value="field.value"
                    :placeholder="field.placeholder"
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

          <section class="scene-activities" aria-labelledby="scene-activities-title" data-activity-tabs>
            <header class="scene-section-heading scene-section-heading--compact">
              <div>
                <span class="scene-section-kicker">ACTIVITY</span>
                <h2 id="scene-activities-title">{{ contract.activities.title }}</h2>
              </div>
            </header>

            <ui5-tabcontainer class="scene-activity-tabs" collapsed fixed>
              <ui5-tab
                v-for="(tab, tabIndex) in contract.activities.tabs"
                :key="tab.id"
                :text="tab.count === undefined ? tab.label : `${tab.label} ${tab.count}`"
                :selected="tabIndex === 0"
                :data-activity-tab="tab.id"
              >
                <div v-if="tab.items.length" class="scene-activity-list">
                  <article v-for="item in tab.items" :key="item.id" class="scene-activity-item">
                    <span class="scene-activity-dot" :data-tone="item.tone || 'Neutral'"></span>
                    <div>
                      <div class="scene-activity-item__title">
                        <strong>{{ item.title }}</strong><span>{{ item.meta }}</span>
                      </div>
                      <p>{{ item.detail }}</p>
                    </div>
                  </article>
                </div>
                <div v-else class="scene-empty-activity">{{ tab.emptyText || '暂无记录' }}</div>
              </ui5-tab>
            </ui5-tabcontainer>
          </section>
        </div>
      </ui5-dynamic-page>
    </main>

    <footer class="scene-mobile-actions" aria-label="移动端办理动作">
      <ui5-button v-if="primaryAction" design="Emphasized" :disabled="prototypeMode">
        {{ primaryAction.label }}
      </ui5-button>
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
  height: …6210 tokens truncated…款账户已解析',
            meta: '主数据',
            detail: '采用往来单位有效默认账户，账户校验通过。',
            tone: 'Positive',
          },
        ],
      },
    ],
  },
};
