import type { Component } from 'vue';
import PaymentSettlementDetailCollectionControl from '../components/professional-fields/PaymentSettlementDetailCollectionControl.vue';
import { INDUSTRY_RENDERER_ROWS } from '../app/presentation/industry_renderer_manifest.generated';
import {
  registerIndustryRendererExtensions,
  unregisterIndustryRendererExtensions,
} from '../app/presentation/professionalComponentRegistry';

/**
 * Industry renderer implementations are resolved by the generated manifest's
 * renderer identity. The platform FormSection never imports this module or any
 * component below; it only consumes the unified registry resolver.
 */
const INDUSTRY_RENDERER_COMPONENTS: Readonly<Record<string, Component>> = Object.freeze({
  PaymentSettlementDetailCollectionControl,
});

export function registerIndustryRenderers(): void {
  registerIndustryRendererExtensions(INDUSTRY_RENDERER_ROWS.map((row) => {
    const component = INDUSTRY_RENDERER_COMPONENTS[row.renderer];
    if (!component) {
      throw new Error(`INDUSTRY_RENDERER_COMPONENT_MISSING:${row.renderer}:${row.componentKey}`);
    }
    return { row, component };
  }));
}

/** Remove the complete manifest set only after every key has been validated. */
export function unregisterIndustryRenderers(): void {
  unregisterIndustryRendererExtensions(INDUSTRY_RENDERER_ROWS.map((row) => row.componentKey));
}
