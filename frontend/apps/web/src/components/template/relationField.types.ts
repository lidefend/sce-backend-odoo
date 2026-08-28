import type { FormSectionFieldSchema } from './formSection.types';

export type RelationFieldOption = {
  id: number;
  label: string;
  color?: number | null;
};

export type RelationFieldRow = {
  key: string;
  values: Record<string, unknown>;
};

export type RelationFieldColumn = {
  name: string;
  label: string;
  ttype: string;
  required: boolean;
  readonly?: boolean;
  selection?: Array<[string, string]>;
};

export type RelationFieldInputType = 'text' | 'search' | 'number' | 'url' | 'tel' | 'password' | 'email' | 'date' | 'datetime-local' | 'time';

export type RelationFieldAdapter = {
  busy: boolean;
  showOne2manyErrors: boolean;
  relationKeyword: (name: string) => string;
  setRelationKeyword: (name: string, value: string) => void;
  relationIds: (name: string) => number[];
  selectedRelationOptions: (name: string) => RelationFieldOption[];
  filteredRelationOptions: (name: string) => RelationFieldOption[];
  setRelationMultiField: (name: string, target: HTMLSelectElement) => void;
  setRelationIds: (name: string, ids: number[]) => void;
  /** Current record context (model + res_id) for attachment-field uploads. */
  currentModel?: string;
  currentRecordId?: number;
  /** Resolve the target model of a relation field (e.g. 'ir.attachment'). */
  relationModelOf?: (name: string) => string;
  relationCreateMode: (name: string) => 'none' | 'quick' | 'page' | 'dialog';
  relationInlineCreate: (name: string) => FormSectionFieldSchema['relationInlineCreate'];
  relationCreateLabel: (name: string) => string;
  relationInlineCreateLabel: (name: string) => string;
  canOpenRelationRecord: (name: string) => boolean;
  relationOpenLabel: (name: string) => string;
  relationSearchLabel: (name: string) => string;
  canInlineCreateRelation: (name: string) => boolean;
  openRelationCreate: (name: string) => void;
  /** 级联维护：按当前关键词创建目标字典记录并勾选关联（many2many）。 */
  quickCreateRelationMany: (name: string) => Promise<void>;
  one2manyCanCreate: (name: string) => boolean;
  one2manyCreateLabel: (name: string, fieldLabel?: string) => string;
  addOne2manyRow: (name: string) => void;
  one2manySummary: (name: string) => string;
  visibleOne2manyRows: (name: string) => RelationFieldRow[];
  one2manyRowStateLabel: (row: RelationFieldRow) => string;
  one2manyColumns: (name: string) => RelationFieldColumn[];
  setOne2manyRowField: (name: string, rowKey: string, column: RelationFieldColumn, value: unknown) => void;
  removeOne2manyRow: (name: string, rowKey: string) => void;
  one2manyRowErrors: (name: string, rowKey: string) => string[];
  one2manyRowHints: (name: string, row: RelationFieldRow) => string[];
  removedOne2manyRows: (name: string) => RelationFieldRow[];
  restoreOne2manyRow: (name: string, rowKey: string) => void;
  one2manyRowLabel: (name: string, row: RelationFieldRow) => string;
  selectPlaceholder: (label: string) => string;
  one2manyColumnInputType: (column: RelationFieldColumn) => RelationFieldInputType;
  one2manyColumnDisplayValue: (column: RelationFieldColumn, value: unknown) => string;
  inputFieldValue: (name: string) => string;
  fieldInputType: (type: string) => RelationFieldInputType;
  inputPlaceholder: (label: string) => string;
  setTextField: (name: string, value: string) => void;
};

export type X2ManyRelationRendererProps = {
  field: FormSectionFieldSchema;
  adapter: RelationFieldAdapter;
};
