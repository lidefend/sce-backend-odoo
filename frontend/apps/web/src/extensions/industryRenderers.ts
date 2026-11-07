// 行业 Renderer 扩展注册入口：平台 FormSection 不 import 行业组件，行业模块在这里
// 消费生成的 industry_renderer_manifest，并在 App mount 前把专业组件注册进统一 Resolver。
import type { Component } from 'vue';
import PaymentSettlementDetailCollectionControl from '../components/professional-fields/PaymentSettlementDetailCollectionControl.vue';
import { INDUSTRY_RENDERER_ROWS } from '../app/presentation/industry_renderer_manifest.generated';
import {
  registerIndustryRegistration,
  registerIndustryRenderer,
} from '../app/presentation/professionalComponentRegistry';

const RENDERER_COMPONENTS: Readonly<Record<string, Component>> = {
  PaymentSettlementDetailCollectionControl,
};

export function registerIndustryRenderers(): void {
  for (const row of INDUSTRY_RENDERER_ROWS) {
    const component = RENDERER_COMPONENTS[row.renderer];
    if (!component) {
      throw new Error(`INDUSTRY_RENDERER_COMPONENT_MISSING:${row.renderer}:${row.componentKey}`);
    }
    registerIndustryRenderer(row.renderer, component);
    registerIndustryRegistration(row);
  }
}
