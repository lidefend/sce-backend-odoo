import { ApiError } from '../api/client';
import type {
  CapabilityExplorerRow,
  CapabilityExplorerFilters,
} from '../api/platformCapabilityExplorer';

export type CapabilityStatusPresentation = {
  label: string;
  semantic: 'default' | 'info' | 'success' | 'warning' | 'danger';
};

export function capabilityEntryKey(row: Pick<CapabilityExplorerRow, 'entry_ref'>): string {
  return `${row.entry_ref.menu_xmlid}::${row.entry_ref.action_xmlid}`;
}

export function businessDomainPresentation(row: CapabilityExplorerRow): CapabilityStatusPresentation {
  if (row.business_domain.confidence === 'authoritative_scene_binding') {
    return {
      label: row.business_domain.label || row.business_domain.key || '',
      semantic: 'success',
    };
  }
  if (row.business_domain.confidence === 'center_only') {
    return { label: '业务领域未确认', semantic: 'warning' };
  }
  return { label: '业务领域未分类', semantic: 'default' };
}

export function sceneUsagePresentation(row: CapabilityExplorerRow): CapabilityStatusPresentation {
  return row.scene_usage.bound
    ? { label: `已场景化 · ${row.scene_usage.count}`, semantic: 'info' }
    : { label: '尚未场景化', semantic: 'default' };
}

export function technicalEligibilityPresentation(row: CapabilityExplorerRow): CapabilityStatusPresentation {
  return row.draft_eligibility.selectable
    ? { label: '技术可选', semantic: 'success' }
    : { label: '存在技术阻断', semantic: 'danger' };
}

export function releaseStatePresentation(state: string): CapabilityStatusPresentation {
  if (state === 'released') return { label: '已发布', semantic: 'success' };
  if (state === 'preview') return { label: '预览', semantic: 'info' };
  if (state === 'unknown') return { label: '发布状态未知', semantic: 'warning' };
  return { label: state, semantic: 'default' };
}

export function blockerLabel(blockers: string[]): string {
  return blockers.length ? blockers.join(' · ') : '无阻断';
}

export function buildListFilters(input: {
  centerKey?: string;
  confidence?: string;
  sceneStatus?: string;
  releaseState?: string;
  draftSelectable?: string;
}): CapabilityExplorerFilters {
  const filters: CapabilityExplorerFilters = {};
  if (input.centerKey) filters.center_keys = [input.centerKey];
  if (input.confidence) {
    filters.classification_confidence = [
      input.confidence as NonNullable<CapabilityExplorerFilters['classification_confidence']>[number],
    ];
  }
  if (input.sceneStatus) {
    filters.scene_status = [
      input.sceneStatus as NonNullable<CapabilityExplorerFilters['scene_status']>[number],
    ];
  }
  if (input.releaseState) filters.release_states = [input.releaseState];
  if (input.draftSelectable === 'true' || input.draftSelectable === 'false') {
    filters.draft_selectable = input.draftSelectable === 'true';
  }
  return filters;
}

export function isCatalogStaleError(error: unknown): boolean {
  return error instanceof ApiError && error.reasonCode === 'CATALOG_STALE';
}
