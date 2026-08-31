import type { FieldDescriptor } from '@sc/schema';
import type { CanonicalFormPresentationMode, CanonicalFormRenderMode } from '../../app/presentation/canonicalFormRenderModel';

export type TemplateFieldType =
  | 'char'
  | 'text'
  | 'selection'
  | 'many2one'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'many2many'
  | 'one2many'
  | string;

export type TemplateSelectOption = {
  id?: string | number;
  value: string | number;
  label: string;
};

export type FormSectionFieldSchema = {
  key: string;
  name: string;
  label: string;
  hideLabel?: boolean;
  type: TemplateFieldType;
  widget?: string;
  nativeLocator?: string;
  occurrenceIndex?: number;
  sourcePosition?: number;
  widgetSemantics?: Record<string, unknown>;
  componentKey?: string;
  componentReadiness?: 'ready' | 'readable_fallback' | 'fail_closed';
  componentRenderer?: string;
  contractAdapter?: string;
  contractVersion?: string;
  componentFallback?: string | null;
  presentationMode?: CanonicalFormPresentationMode;
  renderProfile?: CanonicalFormRenderMode;
  required: boolean;
  readonly: boolean;
  auth?: string;
  invalid?: boolean;
  helpText?: string;
  errorText?: string;

  // Presentational override for current template stage.
  // Prefer replacing with semantic span in later phases.
  spanClass?: string;

  favoriteToggle?: {
    name: string;
    label: string;
    active: boolean;
    readonly: boolean;
    descriptor?: FieldDescriptor;
  };

  // Raw value for readonly display or unsupported-field input usage.
  value?: unknown;

  // Value normalized by page layer for direct control binding.
  // For date/datetime, this must already match native input format.
  inputValue?: string | number | boolean | null;
  dateRangeEndField?: string;
  dateRangeEndInputValue?: string | number | boolean | null;

  inputPlaceholder?: string;
  selectionOptions?: TemplateSelectOption[];
  relationOptions?: TemplateSelectOption[];

  // many2one-only relation entry extension
  relationCreateMode?: 'none' | 'quick' | 'page' | 'dialog';
  relationInlineCreate?: {
    enabled: boolean;
    createOnNoMatch: boolean;
    nameField: string;
    match?: string;
  };
  many2oneCreateToken?: string;
  many2oneSearchToken?: string;
  many2oneOpenToken?: string;
  many2oneTextValue?: string;
  many2oneOpenLabel?: string;
  many2oneSearchLabel?: string;
  many2oneCreateLabel?: string;
  many2oneInlineCreateLabel?: string;
  descriptor?: FieldDescriptor;
  fileName?: string;
  digits?: [number, number];
  currencyField?: string;
  currencyLabel?: string;
};

export type FormSectionFieldChange = {
  occurrenceKey?: string;
  name: string;
  type: TemplateFieldType;
  widget?: string;
  value: string | number | boolean | null;
  action?: 'change' | 'query' | 'commit';
  descriptor?: FieldDescriptor;
  fileName?: string;
};

export type FormSectionFieldAction = {
  key: string;
  label: string;
  value: string;
  checked?: boolean;
  disabled?: boolean;
  title?: string;
  raw?: Record<string, unknown>;
};

export type FormSectionFieldActionPayload = {
  field: FormSectionFieldSchema;
  action: FormSectionFieldAction;
};
