import { computed } from 'vue';
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router';
import { usePageContract } from '../../app/pageContract';
import { executePageContractAction } from '../../app/pageContractActionRuntime';

type UseBusinessConfigSurfacePageContractOptions = {
  router: Router;
  route: RouteLocationNormalizedLoaded;
  refresh: () => Promise<void> | void;
};

/**
 * The `business_config` page contract: which sections are enabled and how the
 * header renders them, plus the global action dispatcher. Section enablement
 * and styling stay contract-driven; the view only binds the result.
 */
export function useBusinessConfigSurfacePageContract(options: UseBusinessConfigSurfacePageContractOptions) {
  const pageContract = usePageContract('business_config');
  const pageSectionEnabled = pageContract.sectionEnabled;
  const pageSectionStyle = pageContract.sectionStyle;
  const pageSectionTagIs = pageContract.sectionTagIs;
  const pageActionIntent = pageContract.actionIntent;
  const pageActionTarget = pageContract.actionTarget;
  const pageGlobalActions = pageContract.globalActions;
  const pageSectionsReady = computed(() => (
    pageSectionEnabled('root', true)
    && pageSectionEnabled('header', true)
    && pageSectionEnabled('coverage', true)
    && pageSectionEnabled('designer', true)
  ));
  const pageSectionContractValid = computed(() => (
    pageSectionTagIs('root', 'section')
    && pageSectionTagIs('header', 'header')
    && pageSectionTagIs('coverage', 'section')
    && pageSectionTagIs('designer', 'section')
  ));
  const pageSectionsFingerprint = computed(() => JSON.stringify([
    pageSectionContractValid.value,
    pageSectionStyle('root'),
    pageSectionStyle('header'),
    pageSectionStyle('coverage'),
    pageSectionStyle('designer'),
  ]));
  async function executeGlobalPageAction(actionKey: string) {
    await executePageContractAction({
      actionKey,
      router: options.router,
      actionIntent: pageActionIntent,
      actionTarget: pageActionTarget,
      query: options.route.query,
      onRefresh: options.refresh,
    });
  }

  return {
    pageSectionStyle,
    pageGlobalActions,
    pageSectionsReady,
    pageSectionContractValid,
    pageSectionsFingerprint,
    executeGlobalPageAction,
  };
}
