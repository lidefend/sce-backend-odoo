import assert from 'node:assert/strict';
import { formatProductMyWorkFact, partitionProductMyWorkFacts } from '../src/app/presentation/productMyWorkPresentation.ts';

const facts = [
  { key: 'project', label: '项目', value: '城市更新项目', field_group: 'business', display_role: 'text' },
  { key: 'amount', label: '申请金额', field_group: 'business', display_role: 'money', money: { value: 50, currency: 'CNY', currency_symbol: '¥', digits: 2 } },
  { key: 'partner', label: '收款单位', value: '示例供应商', field_group: 'business', display_role: 'text' },
  { key: 'created_at', label: '创建时间', value: '2026-09-09T08:30:45', field_group: 'audit', display_role: 'datetime' },
] as const;

assert.equal(formatProductMyWorkFact(facts[1]), '¥50.00 CNY');
assert.equal(formatProductMyWorkFact(facts[3]), '2026-09-09 08:30');

const presentation = partitionProductMyWorkFacts([...facts], 2);
assert.deepEqual(presentation.primary.map((entry) => entry.fact.key), ['project', 'amount']);
assert.deepEqual(presentation.supplementary.map((entry) => entry.fact.key), ['partner', 'created_at']);
assert.equal(
  presentation.primary.some((entry) => entry.fact.display_role === 'money'),
  true,
  'the authoritative money fact must remain in the compact summary even when it is not first',
);
assert.equal(
  [...presentation.primary, ...presentation.supplementary].length,
  facts.length,
  'progressive disclosure must keep every contract fact accessible',
);

console.log('[product_my_work_presentation_test] PASS cases=4');
