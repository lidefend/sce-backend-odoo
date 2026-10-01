import { strict as assert } from 'node:assert';
import {
  COMPONENT_CONTRACT_SEMANTIC_MISSING,
  SETTLEMENT_INTRODUCE_REQUIRED_PATHS,
  requireSettlementIntroduceContract,
  resolveSettlementIntroduceContract,
  settlementIntroduceContractGapLabel,
} from '../src/components/professional-fields/paymentSettlementIntroduceDialogModel';

// Mirrors the construction product layer's declaration so the test proves the
// resolver reads contract semantics instead of substituting its own defaults.
const declaredField = {
  componentConfig: {
    fieldType: 'one2many',
    introduceLabel: '从结算单引入',
    actionRefs: {
      search: 'search.ref',
      preview: 'preview.ref',
      introduce: 'introduce.ref',
    },
    introduceDialog: {
      purpose: 'introduce-purpose',
      title: 'title.term',
      description: 'description.term',
      searchPlaceholder: 'search.placeholder',
      searchActionLabel: 'search.action',
      searchLoadingLabel: 'search.loading',
      searchEmptyLabel: 'search.empty',
      resultContractLabel: 'result.contract',
      resultAmountLabel: 'result.amount',
      resultLineCountLabel: 'result.lineCount',
      resultLineCountSuffix: 'result.lineSuffix',
      switchSourceLabel: 'switch.source',
      selectAllLabel: 'select.all',
      summarySelectedPrefix: 'summary.selected',
      summaryLineCountSuffix: 'summary.lineSuffix',
      summarySettlementAmountLabel: 'summary.settlementAmount',
      summaryApplicableAmountLabel: 'summary.applicableAmount',
      columnLabels: {
        name: 'column.name',
        contract: 'column.contract',
        settlementAmount: 'column.settlementAmount',
        applied: 'column.applied',
        remaining: 'column.remaining',
        state: 'column.state',
      },
      stateAppliedLabel: 'state.applied',
      stateApplicableLabel: 'state.applicable',
      allAppliedLabel: 'state.allApplied',
      historyTitle: 'history.title',
      historyCountSuffix: 'history.countSuffix',
      historyExpandLabel: 'history.expand',
      historyCollapseLabel: 'history.collapse',
      ratioModeLabel: 'apply.ratio',
      amountModeLabel: 'apply.amount',
      ratioPlaceholder: 'apply.ratioPlaceholder',
      totalPlaceholder: 'apply.totalPlaceholder',
      ratioHint: 'apply.ratioHint',
      amountHint: 'apply.amountHint',
      applyTotalLabel: 'apply.total',
      cancelLabel: 'footer.cancel',
      confirmLabel: 'footer.confirm',
      recordRequiredMessage: 'message.recordRequired',
      payloadFields: {
        record: 'payload.record',
        source: 'payload.source',
        sourceLines: 'payload.sourceLines',
        applyMode: 'payload.applyMode',
        ratio: 'payload.ratio',
        totalAmount: 'payload.totalAmount',
        searchKeyword: 'payload.searchKeyword',
      },
    },
  },
};

let cases = 0;

// 1. A bare field is a reported gap, not a dialog built from guesses.
const empty = resolveSettlementIntroduceContract({ componentConfig: {} });
assert.equal(empty.ready, false);
if (empty.ready) throw new Error('unreachable');
assert.deepEqual([...empty.missing], [...SETTLEMENT_INTRODUCE_REQUIRED_PATHS]);
assert.ok(empty.missing.length > 40, `expected the full vocabulary to be required, got ${empty.missing.length}`);
cases += 3;

// 2. Missing component config entirely is still a gap, never a throw at resolve time.
const noConfig = resolveSettlementIntroduceContract({});
assert.equal(noConfig.ready, false);
cases += 1;

// 3. Every single declared path is individually required.
for (const path of SETTLEMENT_INTRODUCE_REQUIRED_PATHS) {
  const clone = JSON.parse(JSON.stringify(declaredField)) as typeof declaredField;
  const segments = path.split('.');
  let cursor: Record<string, unknown> = clone.componentConfig as unknown as Record<string, unknown>;
  for (const segment of segments.slice(0, -1)) {
    cursor = cursor[segment] as Record<string, unknown>;
  }
  delete cursor[segments[segments.length - 1]];
  const resolved = resolveSettlementIntroduceContract(clone as never);
  assert.equal(resolved.ready, false, `dropping ${path} must fail closed`);
  if (resolved.ready) throw new Error('unreachable');
  assert.ok(resolved.missing.includes(path), `dropping ${path} must name ${path}`);
  cases += 1;
}

// 4. Blank values are gaps: whitespace must not pass as a business term.
const blanked = JSON.parse(JSON.stringify(declaredField)) as typeof declaredField;
(blanked.componentConfig.introduceDialog as Record<string, unknown>).title = '   ';
const blankResolved = resolveSettlementIntroduceContract(blanked as never);
assert.equal(blankResolved.ready, false);
if (blankResolved.ready) throw new Error('unreachable');
assert.ok(blankResolved.missing.includes('introduceDialog.title'));
cases += 1;

// 5. A complete declaration resolves to the declared terms, actions and payload keys.
const ready = resolveSettlementIntroduceContract(declaredField as never);
assert.equal(ready.ready, true);
if (!ready.ready) throw new Error('unreachable');
assert.equal(ready.contract.buttonLabel, '从结算单引入');
assert.equal(ready.contract.purpose, 'introduce-purpose');
assert.equal(ready.contract.title, 'title.term');
assert.equal(ready.contract.columnLabels.settlementAmount, 'column.settlementAmount');
assert.equal(ready.contract.actions.introduce, 'introduce.ref');
assert.equal(ready.contract.payloadFields.record, 'payload.record');
assert.equal(ready.contract.payloadFields.sourceLines, 'payload.sourceLines');
assert.equal(ready.contract.recordRequiredMessage, 'message.recordRequired');
cases += 8;

// 6. requireSettlementIntroduceContract fails closed with the missing paths named.
assert.throws(
  () => requireSettlementIntroduceContract({ componentConfig: {} }),
  new RegExp(`^Error: ${COMPONENT_CONTRACT_SEMANTIC_MISSING}:introduceLabel,introduceDialog.purpose`),
);
assert.equal(requireSettlementIntroduceContract(declaredField as never).title, 'title.term');
cases += 2;

// 7. The gap diagnostic names what is missing so the surface can report it.
const gap = settlementIntroduceContractGapLabel(['introduceDialog.title']);
assert.ok(gap.includes('introduceDialog.title'), gap);
cases += 1;

console.log(`[payment_settlement_introduce_dialog_contract_test] PASS cases=${cases}`);
