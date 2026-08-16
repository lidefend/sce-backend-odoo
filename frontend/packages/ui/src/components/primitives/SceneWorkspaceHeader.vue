<script setup lang="ts">
import type { SceneWorkspaceIdentity } from '../../contracts/sceneCollection';

defineProps<{ identity: SceneWorkspaceIdentity }>();
</script>

<template>
  <header class="scene-surface-shellbar" aria-label="应用标题栏">
    <div class="scene-surface-brandmark" aria-hidden="true">S</div>
    <div class="scene-surface-brandcopy">
      <strong>{{ identity.productName }}</strong>
      <span>{{ identity.companyName }} · {{ identity.roleName }}</span>
    </div>
    <div class="scene-surface-shellbar__context">
      <span class="scene-surface-shellbar__online" aria-hidden="true"></span>
      <span>企业工作台</span>
      <span class="scene-surface-avatar" aria-hidden="true">财</span>
    </div>
  </header>

  <nav class="scene-surface-worktabs" aria-label="活动页面">
    <button
      v-for="tab in identity.workTabs"
      :key="tab.id"
      type="button"
      class="scene-surface-worktab"
      :class="{ 'scene-surface-worktab--active': tab.active }"
      :aria-current="tab.active ? 'page' : undefined"
    >
      <span>{{ tab.label }}</span>
      <span v-if="tab.active" class="scene-surface-worktab__close" aria-hidden="true">×</span>
    </button>
  </nav>

  <div class="scene-surface-breadcrumbs" aria-label="面包屑">
    <span v-for="(crumb, index) in identity.breadcrumbs" :key="crumb">
      {{ crumb }}<i v-if="index < identity.breadcrumbs.length - 1">/</i>
    </span>
  </div>
</template>

<style>
.scene-surface-shellbar {
  display: flex;
  align-items: center;
  min-height: 60px;
  padding: 0 28px;
  border-bottom: 1px solid var(--sc-scene-border);
  background: var(--sc-scene-surface);
  box-shadow: 0 1px 4px rgba(26, 47, 72, 0.06);
}

.scene-surface-brandmark,
.scene-surface-avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: var(--sc-scene-brand);
  color: white;
  font-weight: 700;
}

.scene-surface-brandcopy {
  display: grid;
  gap: 2px;
  margin-left: 12px;
}

.scene-surface-brandcopy strong { font-size: 17px; }
.scene-surface-brandcopy span,
.scene-surface-shellbar__context { color: var(--sc-scene-muted); font-size: 12px; }

.scene-surface-shellbar__context {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.scene-surface-shellbar__online {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--sc-scene-success);
}

.scene-surface-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #edf2f7;
  color: #405269;
}

.scene-surface-worktabs {
  display: flex;
  min-height: 42px;
  padding: 0 24px;
  overflow-x: auto;
  border-bottom: 1px solid var(--sc-scene-border);
  background: #eef3f8;
}

.scene-surface-worktab {
  display: flex;
  flex: none;
  align-items: center;
  gap: 28px;
  min-width: 180px;
  padding: 0 16px;
  border: 0;
  border-right: 1px solid #d9e1ea;
  background: transparent;
  color: #4d5d6c;
  font: inherit;
  text-align: left;
}

.scene-surface-worktab--active {
  border-bottom: 3px solid var(--sc-scene-brand);
  background: white;
  color: var(--sc-scene-text);
  font-weight: 700;
}

.scene-surface-worktab__close { margin-left: auto; font-size: 17px; }
.scene-surface-breadcrumbs { padding: 14px 28px 8px; color: var(--sc-scene-muted); font-size: 13px; }
.scene-surface-breadcrumbs i { margin: 0 8px; color: #a2acb8; font-style: normal; }

@media (max-width: 640px) {
  .scene-surface-shellbar { min-height: 54px; padding: 0 14px; }
  .scene-surface-shellbar__context > span:not(.scene-surface-avatar) { display: none; }
  .scene-surface-worktabs { padding: 0 8px; }
  .scene-surface-worktab { min-width: 150px; }
  .scene-surface-breadcrumbs { padding: 10px 14px 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
}
</style>
