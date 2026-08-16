import {
  NormalizedCollectionPilotError,
  adaptReadonlyNormalizedCollection,
  type ReadonlyNormalizedCollectionSnapshot,
} from '../../../packages/ui/src/contracts/normalizedCollectionAdapter';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function snapshot(): ReadonlyNormalizedCollectionSnapshot {
  return {
    identity: {
      productName: 'Test product',
      companyName: 'Test company',
      roleName: 'Reader',
      breadcrumbs: ['Directory'],
      workTabs: [{ id: 'directory', label: 'Directory', active: true }],
    },
    contract: {
      pageInfo: {
        pageId: 'directory',
        sceneKey: 'directory.readonly',
        pageName: 'Directory',
        viewType: 'tree',
        contractVersion: '2.0',
      },
      layoutContract: {
        containerTree: [{
          widgetList: [
            { widgetId: 'field.name', fieldCode: 'name', label: 'Name' },
            { widgetId: 'field.state', fieldCode: 'state', label: 'State' },
          ],
        }],
        listProfile: {
          columns: ['name', 'state'],
          column_labels: { name: 'Name', state: 'State' },
          row_primary: 'name',
          status_field: 'state',
          cross_device_critical_columns: ['name', 'state'],
          selection_policy: { enabled: false },
          sourceAuthority: {
            formal_projection: true,
            no_business_fact_authority: true,
            source_key: 'test.normalized',
          },
        },
      },
      statusContract: {
        globalStatus: { pageVisible: true, pageAuth: 'readonly' },
        widgetStatus: [
          { widgetId: 'field.name', visible: true },
          { widgetId: 'field.state', visible: true },
        ],
        buttonStatus: [],
      },
      actionContract: { actionRuleList: [] },
    },
    records: [{ id: '1', values: { name: 'Alpha', state: 'Active' } }],
    runtime: {
      description: 'Read-only fixture',
      summaries: [],
      filters: [],
      totalCount: 1,
    },
  };
}

function expectRejected(mutator: (candidate: ReadonlyNormalizedCollectionSnapshot) => void, expected: string): void {
  const candidate = snapshot();
  mutator(candidate);
  try {
    adaptReadonlyNormalizedCollection(candidate);
  } catch (error) {
    assert(error instanceof NormalizedCollectionPilotError, 'expected normalized pilot error');
    assert(error.message.includes(expected), `unexpected rejection: ${error.message}`);
    return;
  }
  throw new Error(`expected rejection containing: ${expected}`);
}

const adapted = adaptReadonlyNormalizedCollection(snapshot());
assert(adapted.readonly && adapted.selectionMode === 'none', 'valid normalized snapshot must stay read-only');
assert(adapted.table.columns.map((column) => column.key).join(',') === 'name,state', 'column order must remain authoritative');
assert(adapted.sourceTrace?.kind === 'normalized-collection', 'source trace must remain observable');

expectRejected((candidate) => { candidate.contract.layoutContract.listProfile.selection_policy.enabled = true; }, 'forbids row selection');
expectRejected((candidate) => { candidate.contract.actionContract.actionRuleList.push({ actionId: 'write' }); }, 'forbids normalized actions');
expectRejected((candidate) => { candidate.contract.layoutContract.listProfile.sourceAuthority.formal_projection = false; }, 'lacks formal normalized source authority');
expectRejected((candidate) => { candidate.contract.layoutContract.containerTree[0].widgetList = []; }, 'missing from containerTree');

console.log('[normalizedCollectionAdapter.test] PASS cases=5 assertions=7');
