import type { FormSectionFieldSchema } from '../template/formSection.types';

export const PAYMENT_SETTLEMENT_DETAIL_COLLECTION_COMPONENT_KEY = 'sc.payment.settlement_detail_collection' as const;

export function isPaymentSettlementDetailCollectionField(field: FormSectionFieldSchema): boolean {
  return field.componentKey === PAYMENT_SETTLEMENT_DETAIL_COLLECTION_COMPONENT_KEY
    && field.componentRenderer === 'PaymentSettlementDetailCollectionControl'
    && String(field.type || '').trim().toLowerCase() === 'one2many';
}
