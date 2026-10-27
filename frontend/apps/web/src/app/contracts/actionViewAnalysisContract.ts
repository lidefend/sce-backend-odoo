import { resolveUnifiedPageContractV2 } from './unifiedPageContractV2';
import { FIELD_VALUE_EMPTY_TEXT } from '../../utils/fieldSemantics.ts';

type Dict = Record<string, unknown>;
export type AnalysisViewType = 'pivot' | 'graph';
export type AnalysisField = { name: string; label: string; axis: string; fieldType: string; selection: unknown };
export type AnalysisRow = Dict & { __key: string; __label: string };

export type AnalysisSurfaceModel = {
  ok: boolean;
  reasonCode: string;
  viewType: AnalysisViewType;
  measures: AnalysisField[];
  dimensions: AnalysisField[];
  rows: AnalysisRow[];
  graphType: string;
  sourceAuthority: Dict;
};

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Dict : {};
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function fields(value: unknown): AnalysisField[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  return value.map(asDict).map((row) => ({
    name: text(row.name), label: text(row.label), axis: text(row.axis),
    fieldType: text(row.fieldType), selection: row.selection,
  })).filter((row) => {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(row.name) || seen.has(row.name)) return false;
    seen.add(row.name);
    return true;
  });
}

function validMetadata(field: AnalysisField): boolean {
  if (!field.label || !field.fieldType) return false;
  if (field.fieldType !== 'selection') return true;
  if (!Array.isArray(field.selection) || !field.selection.length) return false;
  const keys = new Set<unknown>();
  return field.selection.every((choice) => {
    if (!Array.isArray(choice) || choice.length !== 2 || typeof choice[0] !== 'string'
      || !text(choice[1]) || keys.has(choice[0])) return false;
    keys.add(choice[0]);
    return true;
  });
}

function displayValue(value: unknown, field: AnalysisField): string {
  if (field.fieldType === 'selection' && value !== null && value !== undefined && value !== false && value !== '') {
    const choices = Array.isArray(field.selection) ? field.selection : [];
    return text(choices.find((choice) => Array.isArray(choice) && choice[0] === value)?.[1]);
  }
  if (Array.isArray(value)) return String(value[1] ?? value[0] ?? FIELD_VALUE_EMPTY_TEXT);
  if (value === null || value === undefined || value === false || value === '') return FIELD_VALUE_EMPTY_TEXT;
  return String(value);
}

function numericValue(value: unknown): number {
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? number : 0;
}

export function resolveAnalysisSurfaceModelFromProfile(
  profileRaw: unknown,
  viewType: AnalysisViewType,
  records: Dict[],
): AnalysisSurfaceModel {
  const profile = asDict(profileRaw);
  const authority = asDict(profile.sourceAuthority);
  const measures = fields(profile.measures);
  const dimensions = fields(profile.dimensions);
  const expectedKind = `native_${viewType}_view_projection`;
  const expectedCarrier = `ui.contract.v2.layoutContract.${viewType}Profile`;
  const authorityNames = Array.isArray(authority.authorities)
    ? authority.authorities.map(text).filter(Boolean).sort().join('|') : '';
  const authorityOk = text(authority.kind) === expectedKind
    && text(authority.runtime_carrier) === expectedCarrier
    && authorityNames === 'ir.actions.act_window|ir.model.fields|ir.ui.view'
    && authority.projection_only === true
    && authority.no_business_fact_authority === true;
  const metadataOk = [...dimensions, ...measures].every(validMetadata)
    && Array.isArray(profile.dimensions) && dimensions.length === profile.dimensions.length
    && Array.isArray(profile.measures) && measures.length === profile.measures.length;
  let valuesOk = true;
  const grouped = new Map<string, AnalysisRow>();
  records.forEach((record) => {
    const dimensionValues = dimensions.map((field) => displayValue(record[field.name], field));
    if (dimensionValues.some((value) => value === '')) valuesOk = false;
    const key = JSON.stringify(dimensions.map((field) => {
      const value = record[field.name];
      return Array.isArray(value) ? value[0] : value ?? null;
    }));
    const current = grouped.get(key) || {
      __key: key,
      __label: dimensionValues.join(' / '),
      ...Object.fromEntries(dimensions.map((field, index) => [field.name, dimensionValues[index]])),
      ...Object.fromEntries(measures.map((field) => [field.name, 0])),
    };
    measures.forEach((field) => { current[field.name] = numericValue(current[field.name]) + numericValue(record[field.name]); });
    grouped.set(key, current);
  });
  const profilePresent = Object.keys(profile).length > 0;
  const ok = profilePresent && authorityOk && dimensions.length > 0 && metadataOk && valuesOk;
  return {
    ok,
    reasonCode: !profilePresent ? 'ANALYSIS_PROFILE_MISSING'
      : !authorityOk ? 'ANALYSIS_SOURCE_AUTHORITY_MISSING'
        : !dimensions.length ? 'ANALYSIS_DIMENSIONS_MISSING'
          : !metadataOk ? 'ANALYSIS_FIELD_METADATA_INVALID'
            : !valuesOk ? 'ANALYSIS_SELECTION_VALUE_UNDECLARED' : '',
    viewType,
    measures,
    dimensions,
    rows: ok ? [...grouped.values()] : [],
    graphType: viewType === 'graph' ? text(profile.typeDefault) || 'bar' : '',
    sourceAuthority: authority,
  };
}

export function resolveAnalysisSurfaceModel(
  contract: unknown,
  viewType: AnalysisViewType,
  records: Dict[],
): AnalysisSurfaceModel {
  const v2 = resolveUnifiedPageContractV2(contract);
  return resolveAnalysisSurfaceModelFromProfile(
    viewType === 'pivot' ? v2?.layoutContract?.pivotProfile : v2?.layoutContract?.graphProfile,
    viewType,
    records,
  );
}
