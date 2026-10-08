import { one2manyRelationDependencyKey } from '../../components/template/one2manyRelationQuery';
import type { RelationOption } from './types';

export type One2manyColumnOptionsDependencies = {
  dynamicDomainDependencyFields: typeof import('./relationDescriptor').dynamicDomainDependencyFields;
  dynamicRelationDomainFromDescriptor: typeof import('./relationDescriptor').dynamicRelationDomainFromDescriptor;
  relationDomainFromDescriptor: typeof import('./relationDescriptor').relationDomainFromDescriptor;
  relationEntry: typeof import('./relationDescriptor').relationEntry;
  relationOptionsFromRecords: typeof import('./relationDescriptor').relationOptionsFromRecords;
  relationOrder: typeof import('./relationDescriptor').relationOrder;
  relationReadFields: typeof import('./relationDescriptor').relationReadFields;
  relationModelFromDescriptor: typeof import('./relationDescriptor').relationModel;
  relationOptionsLimit: typeof import('./relationDescriptor').relationOptionsLimit;
  relationOptionsSearchLimit: typeof import('./relationDescriptor').relationOptionsSearchLimit;
  fieldType: typeof import('./fieldUtils').fieldType;
  normalizeRelationIds: typeof import('./fieldUtils').normalizeRelationIds;
  formData: Record<string, unknown>;
  route: Pick<import('vue-router').RouteLocationNormalizedLoaded, 'query'>;
  pickContractNavQuery: typeof import('../../app/navigationContext').pickContractNavQuery;
  listContractFormRecords: typeof import('../../app/runtime/contractFormDataRuntime').listContractFormRecords;
  fetchRelationOptionsFromRuntime: ReturnType<typeof import('./useRelationRuntime').useRelationRuntime>['fetchRelationOptions'];
  one2manyFieldRows: ReturnType<typeof import('./useOne2manyRuntime').useOne2manyRuntime>['fieldRows'];
  ensureRelationFieldDescriptors: (fieldName: string) => Promise<void>;
  one2manyRelationFieldDescriptor: (fieldName: string, columnName: string) => import('@sc/schema').FieldDescriptor | undefined;
};

export function createOne2manyColumnOptionsRuntime(
  dependencies: One2manyColumnOptionsDependencies,
) {
  const {
    dynamicDomainDependencyFields,
    dynamicRelationDomainFromDescriptor,
    ensureRelationFieldDescriptors,
    fetchRelationOptionsFromRuntime,
    fieldType,
    formData,
    listContractFormRecords,
    normalizeRelationIds,
    one2manyFieldRows,
    one2manyRelationFieldDescriptor,
    pickContractNavQuery,
    relationDomainFromDescriptor,
    relationEntry,
    relationModelFromDescriptor,
    relationOptionsFromRecords,
    relationOptionsLimit,
    relationOptionsSearchLimit,
    relationOrder,
    relationReadFields,
    route,
  } = dependencies;

  const rowValuesFor = (fieldName: string, rowKey: string) => {
    const row = one2manyFieldRows(fieldName).find(
      (item: { key?: string }) => item.key === rowKey,
    );
    return row?.values && typeof row.values === 'object' ? row.values : {};
  };

  async function queryOne2manyColumnOptions(
    fieldName: string,
    rowKey: string,
    column: { name: string },
    keyword = '',
  ): Promise<RelationOption[]> {
    await ensureRelationFieldDescriptors(fieldName);
    const descriptor = one2manyRelationFieldDescriptor(fieldName, column.name);
    const relation = relationModelFromDescriptor(descriptor);
    const entry = relationEntry(descriptor);
    if (!relation || entry?.canRead !== true) return [];
    const rowValues = rowValuesFor(fieldName, rowKey);
    const dynamicDomain = dynamicRelationDomainFromDescriptor({
      descriptor,
      resolveDependencyValue: (dependencyName: string) => {
        const normalized = String(dependencyName || '').trim();
        if (normalized.startsWith('parent.')) return formData[normalized.slice('parent.'.length)];
        return rowValues[normalized] ?? formData[normalized];
      },
      normalizeDependencyValue: (dependencyName: string, value: unknown) => {
        const dependency = one2manyRelationFieldDescriptor(fieldName, dependencyName);
        return ['many2many', 'one2many'].includes(fieldType(dependency))
          ? normalizeRelationIds(value)
          : value;
      },
      currentFieldValue: (dependencyName: string) => rowValues[dependencyName],
    });
    const domain = relationDomainFromDescriptor({
      descriptor,
      dynamicDomain,
      routeDefaultType: String(route.query.default_type || '').trim(),
    });
    return fetchRelationOptionsFromRuntime({
      relation,
      canRead: entry.canRead,
      keyword,
      optionsLimit: relationOptionsLimit(entry),
      optionsSearchLimit: relationOptionsSearchLimit(entry),
      fetchOptions: async (search: string, limit: number) => {
        const listed = await listContractFormRecords({
          model: relation,
          fields: relationReadFields(descriptor),
          limit,
          order: relationOrder(descriptor),
          domain,
          search_term: search || undefined,
          context: pickContractNavQuery(route.query as Record<string, unknown>),
          silentErrors: true,
        });
        return relationOptionsFromRecords(listed?.records, descriptor);
      },
    });
  }

  function one2manyColumnQueryScope(
    fieldName: string,
    rowKey: string,
    column: { name: string; relationDomainSupported?: boolean },
  ) {
    const descriptor = one2manyRelationFieldDescriptor(fieldName, column.name);
    const relation = relationModelFromDescriptor(descriptor);
    const entry = relationEntry(descriptor);
    const dependencies = dynamicDomainDependencyFields(descriptor);
    const rowValues = rowValuesFor(fieldName, rowKey);
    const resolveDependencyValue = (dependencyName: string) => {
      const normalized = String(dependencyName || '').trim();
      return normalized.startsWith('parent.')
        ? formData[normalized.slice('parent.'.length)]
        : rowValues[normalized] ?? formData[normalized];
    };
    return one2manyRelationDependencyKey({
      relation,
      canRead: entry?.canRead === true,
      domainSupported: column.relationDomainSupported !== false,
      dependencies,
      resolveValue: resolveDependencyValue,
    });
  }

  return { one2manyColumnQueryScope, queryOne2manyColumnOptions };
}
