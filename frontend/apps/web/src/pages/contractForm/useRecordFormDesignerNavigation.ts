import type { Ref } from 'vue';

/**
 * The low-code designer entry and return path of a record form.
 *
 * A record opened from the business-config workbench carries the workbench's
 * action/view/return flags in its route query. Rebuilding that query is the
 * designer's own navigation concern, so it lives here instead of inside the
 * save owner: `useRecordFormActions` owns saving, this owns going back to the
 * designer with the configuration still addressable.
 */
export interface FormDesignerNavigationDependencies {
  actionId: Ref<number | string | null | undefined> & { value: unknown };
  contractActionRuleKey: (rule: unknown) => string;
  contractV2ActionRules: Ref<Array<Record<string, unknown>>>;
  parseMaybeJsonRecord: (raw: unknown) => Record<string, unknown>;
  buildLowCodeApplyBaseParams: (input: {
    actionId: unknown;
    viewId: unknown;
    targetParams: unknown;
    modelName: string;
  }) => unknown;
  buildLowCodePreviewQuery: (input: {
    routeQuery: Record<string, unknown>;
    returnToBusinessConfigFlag: string;
    openPagesFlag: string;
  }) => Record<string, unknown>;
  buildLowCodeReturnQuery: (input: {
    routeQuery: Record<string, unknown>;
    modelName: unknown;
    actionId: unknown;
    openPagesFlag: string;
  }) => Record<string, unknown>;
  BUSINESS_CONFIG_ACTION_KEYS: { currentFormFieldOrderSave: string };
  BUSINESS_CONFIG_ROUTE_FLAGS: { returnToBusinessConfig: string; openPages: string };
  hasCurrentFormFieldDraftChanges: Readonly<Ref<boolean>>;
  model: Ref<unknown>;
  route: { path: string; query: Record<string, unknown> };
  routeQueryText: (key: string) => string;
  router: { push: (target: { path: string; query: Record<string, unknown> }) => unknown };
  saveContractFieldOrder: () => Promise<boolean>;
}

export function useRecordFormDesignerNavigation(dependencies: FormDesignerNavigationDependencies) {
  const {
    actionId,
    contractActionRuleKey,
    contractV2ActionRules,
    parseMaybeJsonRecord,
    buildLowCodeApplyBaseParams,
    buildLowCodePreviewQuery,
    buildLowCodeReturnQuery,
    BUSINESS_CONFIG_ACTION_KEYS,
    BUSINESS_CONFIG_ROUTE_FLAGS,
    hasCurrentFormFieldDraftChanges,
    model,
    route,
    routeQueryText,
    router,
    saveContractFieldOrder,
  } = dependencies;

  function lowCodeApplyBaseParams() {
    const configAction = contractV2ActionRules.value.find(
      (rule) =>
        contractActionRuleKey(rule) === BUSINESS_CONFIG_ACTION_KEYS.currentFormFieldOrderSave,
    );
    const target = parseMaybeJsonRecord(configAction?.target);
    return buildLowCodeApplyBaseParams({
      actionId: actionId.value || route.query.action_id,
      viewId: routeQueryText('view_id') || routeQueryText('viewId'),
      targetParams: parseMaybeJsonRecord(target.params),
      modelName: String(model.value || ''),
    });
  }

  function lowCodeReturnQuery() {
    return buildLowCodeReturnQuery({
      routeQuery: route.query as Record<string, unknown>,
      modelName: model.value,
      actionId: actionId.value,
      openPagesFlag: BUSINESS_CONFIG_ROUTE_FLAGS.openPages,
    });
  }

  function previewLowCodeConfiguredPage() {
    const query = buildLowCodePreviewQuery({
      routeQuery: route.query as Record<string, unknown>,
      returnToBusinessConfigFlag: BUSINESS_CONFIG_ROUTE_FLAGS.returnToBusinessConfig,
      openPagesFlag: BUSINESS_CONFIG_ROUTE_FLAGS.openPages,
    });
    router.push({ path: route.path, query });
  }

  async function previewCurrentFormConfiguration() {
    if (hasCurrentFormFieldDraftChanges.value) {
      const saved = await saveContractFieldOrder();
      if (!saved) return;
    }
    previewLowCodeConfiguredPage();
  }

  function returnToBusinessConfigDesigner() {
    router.push({
      path: '/admin/business-config',
      query: lowCodeReturnQuery(),
    });
  }

  return {
    lowCodeApplyBaseParams,
    lowCodeReturnQuery,
    previewLowCodeConfiguredPage,
    previewCurrentFormConfiguration,
    returnToBusinessConfigDesigner,
  };
}
