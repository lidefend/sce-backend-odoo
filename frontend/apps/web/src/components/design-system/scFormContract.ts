/**
 * The capabilities the Sc form adapters expose to callers.
 *
 * These mirror the official form engine the wrapper sits on, so a page consumes
 * the mature behaviour through one project-owned boundary instead of importing
 * the vendor package. A capability that is not listed here is not offered, and a
 * listed one is forwarded as declared - never re-implemented in the wrapper.
 */

export type ScFormProps = {
  data?: Record<string, unknown>;
  disabled?: boolean;
  /**
   * Render the slot without a form container. An unadopted surface keeps the
   * exact DOM it had before this adapter existed; it is not a silent downgrade
   * of an adopted surface, which always declares its bindings.
   */
  bare?: boolean;
  layout?: 'vertical' | 'inline';
  labelAlign?: 'left' | 'right' | 'top';
  labelWidth?: string | number;
  requiredMark?: boolean;
  rules?: Record<string, ScFormRule[]>;
  scrollToFirstError?: '' | 'smooth' | 'auto';
  showErrorMessage?: boolean;
  resetType?: 'empty' | 'initial';
  preventSubmitDefault?: boolean;
};

export type ScFormItemProps = {
  /**
   * Render the slot in a plain element carrying the caller's attributes.
   * A surface that is not adopted keeps the exact DOM it had before this
   * adapter existed instead of receiving a half-applied form item.
   */
  bare?: boolean;
  label?: string;
  name?: string;
  rules?: ScFormRule[];
  status?: 'error' | 'warning' | 'success';
  help?: string;
  showErrorMessage?: boolean;
  labelAlign?: 'left' | 'right' | 'top';
  labelWidth?: string | number;
  requiredMark?: boolean;
};

/**
 * A generic field rule as this boundary declares it: a synthesised answer plus
 * the message the caller already shows for that field. It is a structural
 * subset of the engine's own rule shape, so the wrapper stays a pass-through
 * and a caller never imports the vendor package to describe a rule.
 */
export type ScFormRule = {
  validator?: () => boolean;
  message?: string;
  required?: boolean;
};

/** The engine methods a caller may reach through the wrapper instance. */
export type ScFormInstance = {
  clearValidate: (fields?: string[]) => void;
  reset: (params?: Record<string, unknown>) => void;
  setValidateMessage: (message: Record<string, unknown>) => void;
  submit: (params?: Record<string, unknown>) => void;
  validate: (params?: Record<string, unknown>) => Promise<unknown>;
  validateOnly: (params?: Record<string, unknown>) => Promise<unknown>;
};
