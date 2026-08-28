/**
 * Global scene UI kit (界面风格) runtime.
 *
 * 界面风格是跨页面的全局渲染设置：选择整套 Scene* 组件底层的驱动
 * （tdesign-modern / sc-native）。与 token 风格（data-sc-theme-profile）
 * 正交——token 通过 CSS 全局生效，kit 通过本模块全局生效，所有
 * SceneUiProvider 消费同一份全局 kit，从而"一个切换、全系统生效"。
 */
import { ref } from 'vue';
import type { SceneUiKitId } from '@sc/ui/form';

export type { SceneUiKitId };

export const SCENE_UI_KIT_STORAGE_KEY = 'sc_scene_ui_kit';

export const SCENE_UI_KIT_OPTIONS: ReadonlyArray<{ id: SceneUiKitId; label: string; description: string }> = [
  { id: 'tdesign-modern', label: '现代商务', description: 'TDesign 现代化组件体系，信息密度高、视觉一致。' },
  { id: 'sc-native', label: '原生降级', description: '轻量原生组件渲染，用于兼容与性能回退。' },
];

/** 全局界面风格，模块级响应式：所有消费方 watch 它即可实时跟随切换。 */
export const sceneUiKitRef = ref<SceneUiKitId>('tdesign-modern');

export function isSceneUiKitId(value: unknown): value is SceneUiKitId {
  return value === 'tdesign-modern' || value === 'sc-native';
}

export function sceneUiKitLabel(kit: SceneUiKitId): string {
  return SCENE_UI_KIT_OPTIONS.find((option) => option.id === kit)?.label ?? kit;
}

/** 启动时读取持久化值并应用到全局 ref。 */
export function bootSceneUiKit(): SceneUiKitId {
  let kit: SceneUiKitId = 'tdesign-modern';
  try {
    const stored = localStorage.getItem(SCENE_UI_KIT_STORAGE_KEY);
    if (isSceneUiKitId(stored)) kit = stored;
  } catch {
    kit = 'tdesign-modern';
  }
  sceneUiKitRef.value = kit;
  return kit;
}

/** 切换并持久化全局界面风格。 */
export function persistSceneUiKit(kit: SceneUiKitId): void {
  sceneUiKitRef.value = kit;
  try {
    localStorage.setItem(SCENE_UI_KIT_STORAGE_KEY, kit);
  } catch {
    /* ignore storage failures */
  }
}
