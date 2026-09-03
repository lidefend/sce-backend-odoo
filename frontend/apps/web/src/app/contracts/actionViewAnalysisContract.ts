import { resolveUnifiedPageContractV2 } from './unifiedPageContractV2';

type Dict = Record<string, unknown>;
export type AnalysisViewType = 'pivot' | 'graph';
export type AnalysisField = { name: string; label: string; axis: string };
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
    name: text(row.name), label: text(row.label) || text(row.name), axis: text(row.axis),
  })).filter((row) => {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(row.name) || seen.has(row.name)) return false;
    seen.add(row.name);
    return true;
  });
}

function displayValue(value: unknown): string {
  if (Array.isArray(value)) return String(value[1] ?? value[0] ?? '-');
  if (value === null || value === undefined || value === false || value === '') return '-';
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
  const grouped = new Map<string, AnalysisRow>();
  records.forEach((record) => {
    const dimensionValues = dimensions.map((field) => displayValue(record[field.name]));
    const key = JSON.stringify(dimensionValues);
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
  const ok = profilePresent && authorityOk && dimensions.length > 0;
  return {
    ok,
    reasonCode: !profilePresent ? 'ANALYSIS_PROFILE_MISSING'
      : !authorityOk ? 'ANALYSIS_SOURCE_AUTHORITY_MISSING'
        : !dimensions.length ? 'ANALYSIS_DIMENSIONS_MISSING' : '',
    viewType,
    measures,
    dimensions,
    rows: [...grouped.values()],
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
