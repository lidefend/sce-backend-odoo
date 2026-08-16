<script setup lang="ts">
import { computed } from 'vue';
import type { SceneHierarchyContract, SceneHierarchyNode } from '../contracts/sceneCollection';
import SceneButton from './primitives/SceneButton.vue';
import SceneWorkspaceHeader from './primitives/SceneWorkspaceHeader.vue';

const props = defineProps<{
  contract: SceneHierarchyContract;
  expandedNodeIds?: string[];
  prototypeMode?: boolean;
}>();
const emit = defineEmits<{ toggleNode: [nodeId: string] }>();

const expanded = computed(() => new Set(props.expandedNodeIds || []));
const primaryAction = computed(() => props.contract.actions.find((action) => action.tier === 'primary'));
const otherActions = computed(() => props.contract.actions.filter((action) => action.tier !== 'primary'));

interface VisibleNode { node: SceneHierarchyNode; depth: number }
const visibleNodes = computed<VisibleNode[]>(() => {
  const rows: VisibleNode[] = [];
  const visit = (nodes: SceneHierarchyNode[], depth: number): void => {
    nodes.forEach((node) => {
      rows.push({ node, depth });
      if (node.children?.length && expanded.value.has(node.id)) visit(node.children, depth + 1);
    });
  };
  visit(props.contract.nodes, 0);
  return rows;
});
</script>

<template>
  <div class="scene-hierarchy-shell" data-scene-hierarchy-surface>
    <SceneWorkspaceHeader :identity="contract.identity" />
    <main class="scene-hierarchy-main">
      <section class="scene-hierarchy-card">
        <header class="scene-hierarchy-title">
          <div>
            <span class="scene-hierarchy-eyebrow">{{ contract.eyebrow }}</span>
            <h1>{{ contract.title }}</h1>
            <p>{{ contract.description }}</p>
          </div>
          <div class="scene-hierarchy-actions">
            <SceneButton v-for="action in otherActions" :key="action.id" :tier="action.tier" :disabled="action.disabled || prototypeMode">
              {{ action.label }}
            </SceneButton>
            <SceneButton v-if="primaryAction" tier="primary" :disabled="primaryAction.disabled || prototypeMode">
              {{ primaryAction.label }}
            </SceneButton>
          </div>
        </header>

        <div class="scene-hierarchy-summaries" data-hierarchy-summaries>
          <article v-for="fact in contract.summaries" :key="fact.id" :data-tone="fact.tone || 'Neutral'">
            <span>{{ fact.label }}</span><strong>{{ fact.value }}</strong>
          </article>
        </div>

        <div class="scene-hierarchy-grid">
          <section class="scene-hierarchy-tree" role="tree" aria-label="业务层级" data-hierarchy-tree>
            <article
              v-for="item in visibleNodes"
              :key="item.node.id"
              role="treeitem"
              :aria-level="item.depth + 1"
              :aria-expanded="item.node.children?.length ? expanded.has(item.node.id) : undefined"
              :data-hierarchy-node="item.node.id"
              :style="{ paddingLeft: `${14 + item.depth * 24}px` }"
            >
              <button
                v-if="item.node.children?.length"
                type="button"
                class="scene-hierarchy-toggle"
                :aria-label="`${expanded.has(item.node.id) ? '折叠' : '展开'}${item.node.label}`"
                @click="emit('toggleNode', item.node.id)"
              >
                {{ expanded.has(item.node.id) ? '−' : '+' }}
              </button>
              <span v-else class="scene-hierarchy-leaf" aria-hidden="true">•</span>
              <div class="scene-hierarchy-node-copy">
                <strong>{{ item.node.label }}</strong>
                <small v-if="item.node.meta">{{ item.node.meta }}</small>
              </div>
              <span class="scene-hierarchy-value">{{ item.node.value }}</span>
              <span class="scene-hierarchy-status" :data-tone="item.node.tone || 'Neutral'">{{ item.node.status }}</span>
            </article>
          </section>

          <aside class="scene-hierarchy-guidance">
            <span>层级表达原则</span>
            <h2>先定位，再办理</h2>
            <p>树只承载归属、汇总与状态。业务编辑仍进入独立场景页，避免在层级浏览器内堆叠复杂表单。</p>
            <dl>
              <div><dt>当前展开</dt><dd>{{ expanded.size }} 个节点</dd></div>
              <div><dt>当前可见</dt><dd>{{ visibleNodes.length }} 行</dd></div>
              <div><dt>数据语义</dt><dd>契约提供</dd></div>
            </dl>
          </aside>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
.scene-hierarchy-grid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 16px; padding: 16px; }
.scene-hierarchy-tree { overflow: hidden; border: 1px solid var(--sc-scene-border); border-radius: 9px; }
.scene-hierarchy-tree article { display: grid; grid-template-columns: 28px minmax(0, 1fr) 150px 110px; gap: 8px; align-items: center; min-height: 50px; padding-top: 8px; padding-right: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--sc-scene-border); }
.scene-hierarchy-tree article:last-child { border-bottom: 0; }
.scene-hierarchy-toggle { width: 24px; height: 24px; border: 1px solid var(--sc-scene-border); border-radius: 5px; background: white; color: var(--sc-scene-brand); font-weight: 700; }
.scene-hierarchy-leaf { display: grid; width: 24px; place-items: center; color: #9aa8b6; }
.scene-hierarchy-node-copy { display: grid; min-width: 0; gap: 2px; }
.scene-hierarchy-node-copy strong,
.scene-hierarchy-node-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.scene-hierarchy-node-copy small { color: var(--sc-scene-muted); }
.scene-hierarchy-value { text-align: right; font-weight: 700; }
.scene-hierarchy-status { text-align: right; font-size: 12px; }
.scene-hierarchy-guidance { align-self: start; padding: 18px; border: 1px solid var(--sc-scene-border); border-radius: 9px; background: #f7fafc; }
.scene-hierarchy-guidance > span { color: var(--sc-scene-brand); font-size: 11px; font-weight: 700; }
.scene-hierarchy-guidance h2 { margin: 5px 0 8px; font-size: 18px; }
.scene-hierarchy-guidance p { color: var(--sc-scene-muted); font-size: 12px; line-height: 1.65; }
.scene-hierarchy-guidance dl { display: grid; gap: 9px; margin: 16px 0 0; }
.scene-hierarchy-guidance dl div { display: flex; justify-content: space-between; gap: 10px; }
.scene-hierarchy-guidance dt { color: var(--sc-scene-muted); font-size: 11px; }
.scene-hierarchy-guidance dd { margin: 0; font-size: 12px; font-weight: 700; }

@media (max-width: 760px) {
  .scene-hierarchy-grid { grid-template-columns: minmax(0, 1fr); padding: 12px; }
  .scene-hierarchy-tree article { grid-template-columns: 26px minmax(0, 1fr) auto; }
  .scene-hierarchy-value { grid-column: 2; text-align: left; color: var(--sc-scene-muted); font-size: 11px; }
  .scene-hierarchy-status { grid-column: 3; grid-row: 1 / span 2; }
  .scene-hierarchy-guidance { padding: 14px; }
}
</style>
