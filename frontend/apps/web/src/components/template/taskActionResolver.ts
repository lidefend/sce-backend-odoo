/* Task-action readonly resolver.
 *
 * Some readonly facts are not plain values but a hint at the next business
 * action (e.g. 下一步办理 = "提交审批" / "审批处理" on payment.request). The
 * ObjectTaskPage "当前任务" card used to render them as dead text: the value
 * named an action nobody could press from the page.
 *
 * This resolver lets the page layer (ContractFormPage) turn such a fact into a
 * clickable entry point. FormSection injects it and, when a matching action is
 * returned, renders the readonly value as an action link that runs the handler.
 * It is optional by design - FormSection stays a generic form renderer and
 * defaults to plain readonly text when no resolver is provided.
 */
import type { InjectionKey } from 'vue';
import type { FormSectionFieldSchema } from './formSection.types';

export type ScTaskActionDescriptor = {
  /** Text shown on the clickable readonly value (e.g. "提交审批"). */
  label: string;
  /** Invokes the backend action for the current record. */
  run: () => void | Promise<void>;
};

export type ScTaskActionResolver = (field: FormSectionFieldSchema) => ScTaskActionDescriptor | null;

export const ScTaskActionResolverKey: InjectionKey<ScTaskActionResolver | null> = Symbol('sc-task-action-resolver');
