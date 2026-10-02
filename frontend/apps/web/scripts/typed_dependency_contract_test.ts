import type { BusinessConfigScopeLifecycleDependencies } from '../src/views/businessConfigSurface/useBusinessConfigScopeLifecycle';
import type { BusinessConfigPublishLifecycleDependencies } from '../src/views/businessConfigSurface/useBusinessConfigPublishLifecycle';
import type { BusinessConfigRemediationLifecycleDependencies } from '../src/views/businessConfigSurface/useBusinessConfigRemediationLifecycle';
import type { BusinessConfigWorkbenchBootstrapDependencies } from '../src/views/businessConfigSurface/useBusinessConfigWorkbenchBootstrap';
import type { One2manyColumnOptionsDependencies } from '../src/pages/contractForm/one2manyColumnOptionsRuntime';
import type { useRecordCollaborationPresentation } from '../src/pages/contractForm/useRecordCollaborationPresentation';

declare const publish: BusinessConfigPublishLifecycleDependencies;
declare const remediation: BusinessConfigRemediationLifecycleDependencies;
declare const relations: One2manyColumnOptionsDependencies;
declare const collaboration: Parameters<typeof useRecordCollaborationPresentation>[0];
declare const entry: Parameters<typeof collaboration.updateNativeActivity>[0];

// @ts-expect-error Confirmation must remain an asynchronous boolean decision.
const wrongConfirmation: BusinessConfigScopeLifecycleDependencies['confirmScopeChange'] = () => 'yes';
// @ts-expect-error Invalid configuration kinds must not cross the publishing boundary.
publish.stageUnifiedDraftItem({ config_type: 'arbitrary', target_key: 'x' });
// @ts-expect-error API input retains its declared shape.
remediation.bootstrapBusinessFormConfig('payment.request');
// @ts-expect-error Scope identifiers are numeric, not display strings.
const wrongAction: BusinessConfigWorkbenchBootstrapDependencies['scopeAction'] = { value: '775' };
// @ts-expect-error Record listing requires its typed request object.
relations.listContractFormRecords('payment.request');
// @ts-expect-error Native activity events retain the finite action union.
collaboration.updateNativeActivity(entry, 'delete');

void wrongConfirmation;
void wrongAction;
