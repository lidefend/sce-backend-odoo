import type { ProductCapabilityCatalog } from '../api/productCapabilityCatalog';
import { intentRequest } from '../api/intents';
import { PRODUCT_CAPABILITY_INTENTS } from '../app/businessConfigBoundaries';
import { currentContextEpoch, isCurrentContextEpoch } from '../app/contextEpoch';

export interface NavigationProjectionState {
  workspaceScenarioProjection: {
    rows: Array<{
      scene_key: string;
      name: string;
      product_released: boolean;
      tenant_enabled: boolean;
      role_assigned: boolean;
      workspace_candidate: boolean;
    }>;
    workspace_candidate_count: number;
  } | null;
  workspaceScenarioRequestSequence: number;
  productCapabilityCatalog: ProductCapabilityCatalog | null;
  productCapabilityCatalogRequestSequence: number;
}

interface ProjectionStore extends NavigationProjectionState {
  token: string | null;
  persist(): void;
  invalidateWorkspaceScenarioProjection(): void;
}

/** Context-bound projection requests; backend contracts remain authoritative. */
export const navigationProjectionActions = {
    invalidateProductCapabilityCatalog(this: ProjectionStore) {
      this.productCapabilityCatalogRequestSequence += 1;
      this.productCapabilityCatalog = null;
    },
    invalidateWorkspaceScenarioProjection(this: ProjectionStore) {
      this.workspaceScenarioRequestSequence += 1;
      this.workspaceScenarioProjection = null;
    },
    async loadWorkspaceScenarioProjection(this: ProjectionStore) {
      this.invalidateWorkspaceScenarioProjection();
      const requestSequence = this.workspaceScenarioRequestSequence;
      const requestEpoch = currentContextEpoch();
      const result = await intentRequest<{
        contract_version?: string;
        rows?: Array<{
          scene_key: string;
          name: string;
          product_released: boolean;
          tenant_enabled: boolean;
          role_assigned: boolean;
          workspace_candidate: boolean;
        }>;
        workspace_candidate_count?: number;
      }>({
        intent: 'workspace.scenario.projection.get',
        params: {},
      });
      if (!isCurrentContextEpoch(requestEpoch)
        || requestSequence !== this.workspaceScenarioRequestSequence) return null;
      this.workspaceScenarioProjection = {
        rows: Array.isArray(result?.rows) ? result.rows : [],
        workspace_candidate_count: Number(result?.workspace_candidate_count || 0),
      };
      return this.workspaceScenarioProjection;
    },
    async loadProductCapabilityCatalog(this: ProjectionStore, force = false) {
      const requestEpoch = currentContextEpoch();
      if (!force && this.productCapabilityCatalog) return this.productCapabilityCatalog;
      if (!this.token) return null;
      const token = this.token;
      const requestSequence = ++this.productCapabilityCatalogRequestSequence;
      const result = await intentRequest<ProductCapabilityCatalog>({
        intent: PRODUCT_CAPABILITY_INTENTS.catalog,
      });
      if (!isCurrentContextEpoch(requestEpoch) || token !== this.token
        || requestSequence !== this.productCapabilityCatalogRequestSequence) return null;
      this.productCapabilityCatalog = result;
      this.persist();
      return this.productCapabilityCatalog;
    },
};

export function navigationProjectionState(): NavigationProjectionState {
  return {
    workspaceScenarioProjection: null,
    workspaceScenarioRequestSequence: 0,
    productCapabilityCatalog: null,
    productCapabilityCatalogRequestSequence: 0,
  };
}
