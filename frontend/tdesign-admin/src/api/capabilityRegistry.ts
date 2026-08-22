export interface ApiCapabilityRegistration {
  intent: string;
  client: string;
  pages: string[];
  permission: string;
  test: string;
}

function entries(intents: string[], client: string, pages: string[], permission = 'backend-contract') {
  return intents.map((intent): ApiCapabilityRegistration => ({
    intent,
    client,
    pages,
    permission,
    test: 'scripts/verify-api-capabilities.mjs',
  }));
}

export const apiCapabilityRegistry: ApiCapabilityRegistration[] = [
  ...entries(
    ['login', 'auth.logout', 'system.init', 'record.context.search', 'meta.intent_catalog', 'route.authority.validate'],
    'session',
    ['login', 'app-shell', 'operations-workbench', 'router'],
    'authenticated-session',
  ),
  ...entries(
    [
      'ui.contract.v2',
      'api.data',
      'api.data.create',
      'api.data.write',
      'api.data.unlink',
      'api.data.batch',
      'api.onchange',
      'execute_button',
      'search.favorite.set',
      'user.view.preference.get',
      'user.view.preference.set',
    ],
    'record-runtime',
    ['odoo-action', 'record-detail'],
    'model-rights-and-record-rules',
  ),
  ...entries(
    [
      'chatter.timeline',
      'chatter.post',
      'chatter.activity.schedule',
      'chatter.activity.update',
      'collaboration.users.search',
      'file.upload',
      'file.download',
    ],
    'collaboration',
    ['record-detail', 'messages'],
    'record-collaboration-rights',
  ),
  ...entries(
    ['global.message.conversations', 'global.message.inbox', 'global.message.send', 'global.message.read'],
    'global-messages',
    ['messages', 'notice'],
    'authenticated-user',
  ),
  ...entries(
    ['my.work.summary', 'my.work.complete', 'my.work.complete_batch'],
    'my-work',
    ['my-work', 'dashboard'],
    'work-item-authority',
  ),
  ...entries(
    ['usage.report', 'usage.export.csv', 'capability.visibility.report'],
    'usage',
    ['operations-usage'],
    'operations-admin',
  ),
  ...entries(
    ['auth.credential.list', 'auth.credential.create', 'auth.credential.revoke', 'auth.credential.rotate'],
    'credentials',
    ['governance-api-keys'],
    'credential-owner',
  ),
  ...entries(
    [
      'scene.health',
      'scene.package.list',
      'scene.package.export',
      'scene.package.dry_run_import',
      'scene.package.import',
      'scene.governance.set_channel',
      'scene.governance.rollback',
      'scene.governance.pin_stable',
      'scene.governance.export_contract',
    ],
    'scene-governance',
    ['scene-runtime', 'scene-health', 'scene-packages'],
    'scene-governance-admin',
  ),
  ...entries(
    [
      'ui.menu_config.panel.get',
      'ui.menu_config.panel.set',
      'ui.menu_config.menu.create',
      'ui.menu_config.menu.delete',
      'ui.menu_config.audit',
      'ui.menu_config.versions',
      'ui.menu_config.rollback',
    ],
    'menu-config',
    ['governance-menu-config'],
    'menu-config-admin',
  ),
  ...entries(
    [
      'ui.business_config.surface.get',
      'ui.business_config.change_set.open',
      'ui.business_config.change_set.get',
      'ui.business_config.change_set.stage',
      'ui.business_config.change_set.validate',
      'ui.business_config.change_set.preview',
      'ui.business_config.change_set.publish',
      'ui.business_config.change_set.rollback',
      'ui.business_config.change_set.discard',
      'ui.business_config.coverage.scan',
      'ui.business_config.coverage.bootstrap_missing',
      'ui.business_config.contract.list',
      'ui.business_config.contract.get',
      'ui.business_config.contract.versions',
      'ui.business_config.contract.rollback',
      'ui.business_config.snapshot.compare',
      'ui.business_config.snapshot.export',
      'ui.business_config.list_search.audit',
      'ui.business_config.list_search.set',
      'ui.business_config.list_search.bootstrap',
      'ui.business_config.analysis.audit',
      'ui.business_config.analysis.set',
      'ui.business_config.analysis.bootstrap',
      'ui.business_config.form.audit',
      'ui.business_config.form.bootstrap',
      'ui.business_config.lowcode.apply',
      'ui.business_config.contract.save',
      'ui.business_config.contract.publish',
      'ui.business_config.mutation_audit.snapshot',
    ],
    'business-config',
    ['governance-business-config'],
    'business-config-admin',
  ),
  ...entries(
    ['sc.approval_policy.config.get', 'sc.approval_policy.config.set', 'sc.approval_policy.steps.set'],
    'approval-config',
    ['governance-business-config'],
    'approval-policy-admin',
  ),
  ...entries(
    [
      'ui.form_field_policy.set',
      'ui.form_custom_field.create',
      'ui.form_field_order.set',
      'ui.form_field_config.batch_set',
    ],
    'form-designer',
    ['governance-form-field-config'],
    'form-config-admin',
  ),
  ...entries(
    [
      'release.operator.surface',
      'release.operator.promote',
      'release.operator.approve',
      'release.operator.freeze',
      'release.operator.sync_policy',
      'release.operator.update_policy',
      'release.operator.update_page_policy',
      'release.operator.rollback',
    ],
    'release-operator',
    ['operations-release-operator'],
    'release-admin',
  ),
];

export function capabilityRegistration(intent: string) {
  return apiCapabilityRegistry.find((entry) => entry.intent === intent);
}
