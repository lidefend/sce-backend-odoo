import assert from 'node:assert/strict';
import {
  productMyWorkIdentityDisplay,
  productMyWorkTaskFacts,
} from '../../frontend/apps/web/src/app/presentation/productMyWorkPresentation.ts';
import type { ProductMyWorkFact } from '../../frontend/apps/web/src/api/myWork.ts';

const amount: ProductMyWorkFact = {
  key: 'amount',
  label: '金额',
  display_role: 'money',
  money: {
    value: 10000,
    currency: 'CNY',
    currency_symbol: '¥',
    digits: 2,
  },
};

const project: ProductMyWorkFact = {
  key: 'project',
  label: '项目',
  value: '支付台账项目',
  display_role: 'text',
};

assert.equal(
  productMyWorkIdentityDisplay(
    '付款申请 / 支付台账项目 / 德阳蓉钢供应链有限公司 / ¥10,000.00 / PRQ-2026-004',
    amount,
  ),
  '付款申请 / 支付台账项目 / 德阳蓉钢供应链有限公司 / PRQ-2026-004',
  'an amount already present in the authoritative identity must be removed once',
);

assert.equal(
  productMyWorkIdentityDisplay('付款申请 / PRQ-2026-004', amount),
  '付款申请 / PRQ-2026-004',
  'an amount absent from the identity must not trigger string rewriting',
);

assert.equal(
  productMyWorkIdentityDisplay(
    '付款申请 / ¥10,000.00 / PRQ-2026-004',
    { ...amount, money: { ...amount.money!, value: 20000 } },
  ),
  '付款申请 / ¥10,000.00 / PRQ-2026-004',
  'only the exact contract-provided amount is de-duplicated',
);

assert.deepEqual(
  productMyWorkTaskFacts([project, amount], true).map((fact) => fact.key),
  ['project'],
  'an explicit amount chip owns the money presentation',
);

assert.deepEqual(
  productMyWorkTaskFacts([project, amount], false).map((fact) => fact.key),
  ['project', 'amount'],
  'money remains in facts when no amount chip is rendered',
);

console.log('[OK] FE-POLISH-B1 presentation unit: 5 cases');
