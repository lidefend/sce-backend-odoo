import { resolveUnifiedPageContractV2 } from './unifiedPageContractV2';
import { formatMonetaryDisplayValue, normalizeMonetaryDigits, resolveCurrencyDisplayLabel } from '../../components/template/formSection.mapper';

type Dict = Record<string, unknown>;

export type ActivitySurfaceField = {
  key: string;
  name: string;
  label: string;
  widget: string;
  nativeLocator: string;
  occurrenceIndex: number;
  attributes: Dict;
  decorations: Dict[];
  fieldType: string;
  currencyField: string;
  digits?: [number, number];
};

export type ActivityTemplateNode = {
  key: string;
  tag: string;
  classes: string;
  text: string;
  tail: string;
  field?: ActivitySurfaceField;
  children: ActivityTemplateNode[];
};

export type ActivitySurfaceModel = {
  ok: boolean;
  reasonCode: string;
  fields: ActivitySurfaceField[];
  requestedFields: string[];
  records: Dict[];
  templateNames: string[];
  templateNodes: ActivityTemplateNode[];
  sourceAuthority: Dict;
};

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Dict : {};
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.entries(value as Dict).sort(([left], [right]) => left.localeCompare(right)).map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function sameOccurrence(source: Dict | undefined, candidate: Dict, expectedTag = ''): boolean {
  if (!source) return false;
  const sourceTag = text(source.tag).toLowerCase();
  const candidateTag = text(candidate.tag).toLowerCase();
  return Boolean(sourceTag)
    && (!expectedTag || sourceTag === expectedTag)
    && (!candidateTag || sourceTag === candidateTag)
    && text(source.native_locator) === text(candidate.native_locator)
    && Number(source.occurrence_index) === Number(candidate.occurrence_index)
    && Number(source.source_position) === Number(candidate.source_position)
    && stableJson(asDict(source.attributes)) === stableJson(asDict(candidate.attributes))
    && text(source.text) === text(candidate.text)
    && text(source.tail) === text(candidate.tail);
}

function slotFields(value: unknown): string[] {
  return Object.values(asDict(value)).map(text).filter((item) => /^[A-Za-z_][A-Za-z0-9_]*$/.test(item));
}

function staticInvisible(attributes: Dict, modifiers: unknown): { hidden: boolean; unsupported: boolean } {
  const value = attributes.invisible ?? asDict(modifiers).invisible;
  if (value === undefined || value === null || value === '' || value === false || value === 0 || value === '0' || value === 'False' || value === 'false') {
    return { hidden: false, unsupported: false };
  }
  if (value === true || value === 1 || value === '1' || value === 'True' || value === 'true') {
    return { hidden: true, unsupported: false };
  }
  return { hidden: false, unsupported: true };
}

export function activityCellText(value: unknown, field?: ActivitySurfaceField, record: Dict = {}): string {
  if (value === null || value === undefined || value === false || value === '') return '-';
  if (field?.widget === 'monetary') {
    const currencyLabel = resolveCurrencyDisplayLabel(record[field.currencyField]);
    return formatMonetaryDisplayValue(value, field.digits, currencyLabel);
  }
  if (Array.isArray(value) && field?.fieldType === 'many2one') return value.length > 1 ? text(value[1]) || String(value[0] ?? '-') : String(value[0] ?? '-');
  if (Array.isArray(value)) return JSON.stringify(value);
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function resolveActivitySurfaceModelFromProfile(profileRaw: unknown, records: Dict[]): ActivitySurfaceModel {
  const profile = asDict(profileRaw);
  const authority = asDict(profile.sourceAuthority);
  const rawFields = Array.isArray(profile.fieldOccurrences) ? profile.fieldOccurrences : [];
  const allFields: ActivitySurfaceField[] = [];
  const fieldsByLocator = new Map<string, ActivitySurfaceField>();
  const hiddenLocators = new Set<string>();
  let invalidIdentity = false;
  let unsupportedModifier = false;
  rawFields.forEach((raw) => {
    const row = asDict(raw);
    const name = text(row.name);
    const locator = text(row.native_locator);
    const occurrenceIndex = Number(row.occurrence_index);
    const attributes = asDict(row.attributes);
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name) || !locator || !Number.isInteger(occurrenceIndex) || occurrenceIndex < 1) {
      invalidIdentity = true;
      return;
    }
    const key = `${locator}#${occurrenceIndex}`;
    if (fieldsByLocator.has(locator) || allFields.some((field) => field.key === key)) {
      invalidIdentity = true;
      return;
    }
    const invisible = staticInvisible(attributes, row.modifiers);
    if (invisible.unsupported) unsupportedModifier = true;
    const field: ActivitySurfaceField = {
      key,
      name,
      label: text(row.label) || name,
      widget: text(row.widget),
      nativeLocator: locator,
      occurrenceIndex,
      attributes,
      decorations: Array.isArray(row.decorations) ? row.decorations.map(asDict) : [],
      fieldType: text(row.field_type),
      currencyField: text(row.currency_field),
      digits: normalizeMonetaryDigits(row.digits),
    };
    allFields.push(field);
    if (invisible.hidden) hiddenLocators.add(locator);
    else fieldsByLocator.set(locator, field);
  });

  const flatNodes = Array.isArray(profile.nodeOccurrences) ? profile.nodeOccurrences.map(asDict) : [];
  const nodesByLocator = new Map<string, Dict>();
  let invalidEvidence = flatNodes.length === 0;
  flatNodes.forEach((node) => {
    const locator = text(node.native_locator);
    const tag = text(node.tag).toLowerCase();
    const occurrenceIndex = Number(node.occurrence_index);
    const sourcePosition = Number(node.source_position);
    if (!locator || !tag || !Number.isInteger(occurrenceIndex) || occurrenceIndex < 1 || !Number.isInteger(sourcePosition) || sourcePosition < 0 || nodesByLocator.has(locator)) {
      invalidEvidence = true;
      return;
    }
    nodesByLocator.set(locator, node);
  });
  const roots = flatNodes.filter((node) => text(node.tag).toLowerCase() === 'activity');
  const nativeAttrs = asDict(profile.nativeAttrs);
  if (roots.length !== 1 || stableJson(asDict(roots[0]?.attributes)) !== stableJson(nativeAttrs)) invalidEvidence = true;
  allFields.forEach((field) => {
    const source = nodesByLocator.get(field.nativeLocator);
    const row = rawFields.find((candidate) => text(asDict(candidate).native_locator) === field.nativeLocator);
    if (!row || !sameOccurrence(source, asDict(row), 'field') || text(field.attributes.name) !== field.name) invalidEvidence = true;
  });

  const template = asDict(profile.template);
  const seenNodes = new Set<string>();
  let invalidTemplate = false;
  let unsupportedTemplate = false;
  const buildNode = (raw: unknown): ActivityTemplateNode | null => {
    const row = asDict(raw);
    const tag = text(row.tag).toLowerCase();
    const locator = text(row.native_locator);
    const occurrenceIndex = Number(row.occurrence_index);
    if (!tag || !locator || !Number.isInteger(occurrenceIndex) || occurrenceIndex < 1 || seenNodes.has(locator)) {
      invalidTemplate = true;
      return null;
    }
    seenNodes.add(locator);
    const attributes = asDict(row.attributes);
    const source = nodesByLocator.get(locator);
    if (!sameOccurrence(source, row, tag)) {
      invalidEvidence = true;
    }
    const directives = Object.keys(attributes).filter((key) => key.startsWith('t-') && key !== 't-name');
    if (directives.length || !['div', 'span', 'strong', 'p', 'field', 't'].includes(tag)) unsupportedTemplate = true;
    const containerInvisible = tag === 'field' ? { hidden: false, unsupported: false } : staticInvisible(attributes, {});
    if (containerInvisible.unsupported) unsupportedTemplate = true;
    if (containerInvisible.hidden) return null;
    const childrenRaw = Array.isArray(row.children) ? row.children : [];
    const children = childrenRaw.map(buildNode).filter((node): node is ActivityTemplateNode => Boolean(node));
    const node: ActivityTemplateNode = {
      key: `${locator}#${occurrenceIndex}`,
      tag,
      classes: text(attributes.class),
      text: text(row.text),
      tail: text(row.tail),
      children,
    };
    if (tag === 'field') {
      if (hiddenLocators.has(locator)) return null;
      const field = fieldsByLocator.get(locator);
      if (!field) {
        invalidTemplate = true;
        return null;
      }
      node.field = field;
    }
    return node;
  };
  const templateNodes = (Array.isArray(template.nodes) ? template.nodes : [])
    .map(buildNode)
    .filter((node): node is ActivityTemplateNode => Boolean(node));

  const actions = Array.isArray(profile.actions) ? profile.actions.map(asDict) : [];
  const actionCount = Number(profile.actionCount);
  const actionsValid = Number.isInteger(actionCount) && actionCount >= 0 && actionCount === actions.length && actions.every((action) => {
    const identity = asDict(action.native_identity);
    return identity.authoritative === true && Boolean(text(identity.native_locator)) && Boolean(text(identity.name)) && ['object', 'action'].includes(text(identity.type));
  });
  const templateNames = Array.isArray(template.names) ? template.names.map(text).filter(Boolean) : [];
  const evidencedTemplateNames = [...new Set(flatNodes.map((node) => text(asDict(node.attributes)['t-name'])).filter(Boolean))];
  const templateLocator = text(template.native_locator);
  const templateOccurrenceIndex = Number(template.occurrence_index);
  const templateSource = nodesByLocator.get(templateLocator);
  const templateValid = Boolean(templateLocator) && Number.isInteger(templateOccurrenceIndex) && templateOccurrenceIndex > 0
    && Boolean(templateSource) && text(templateSource?.tag).toLowerCase() === 'templates'
    && Number(templateSource?.occurrence_index) === templateOccurrenceIndex
    && templateNames.length > 0 && stableJson([...templateNames].sort()) === stableJson([...evidencedTemplateNames].sort())
    && templateNodes.length > 0;
  const authorityNames = Array.isArray(authority.authorities) ? authority.authorities.map(text).filter(Boolean).sort() : [];
  const authorityOk = text(authority.kind) === 'native_activity_view_projection'
    && stableJson(authorityNames) === stableJson(['ir.actions.act_window', 'ir.model.fields', 'ir.ui.view'])
    && text(authority.runtime_carrier) === 'ui.contract.v2.layoutContract.activityProfile'
    && authority.projection_only === true
    && authority.no_business_fact_authority === true;
  let unsupportedMonetary = false;
  allFields.forEach((field) => {
    if (field.widget !== 'monetary') return;
    if (field.fieldType !== 'monetary' || !field.currencyField) unsupportedMonetary = true;
  });
  const requestedFields = [...new Set([
    'id',
    ...allFields.map((field) => field.name),
    ...allFields.map((field) => field.currencyField).filter(Boolean),
    ...slotFields(profile.activityTypeSlots),
    ...slotFields(profile.deadlineSlots),
    ...slotFields(profile.assigneeSlots),
  ])];
  const ok = authorityOk && !invalidIdentity && !invalidEvidence && !unsupportedModifier && !unsupportedTemplate
    && !unsupportedMonetary && !invalidTemplate && templateValid && actionsValid && actionCount === 0;
  const reasonCode = !authorityOk
    ? 'ACTIVITY_SOURCE_AUTHORITY_MISSING'
    : invalidIdentity
      ? 'ACTIVITY_OCCURRENCE_IDENTITY_INVALID'
      : invalidEvidence
        ? 'ACTIVITY_NATIVE_EVIDENCE_INVALID'
      : unsupportedModifier
        ? 'ACTIVITY_DYNAMIC_MODIFIER_UNSUPPORTED'
        : unsupportedTemplate
          ? 'ACTIVITY_QWEB_DIRECTIVE_UNSUPPORTED'
          : unsupportedMonetary
            ? 'ACTIVITY_MONETARY_RENDERER_UNSUPPORTED'
        : invalidTemplate || !templateValid
          ? 'ACTIVITY_TEMPLATE_INVALID'
          : !actionsValid
            ? 'ACTIVITY_ACTION_IDENTITY_INVALID'
            : actionCount > 0
              ? 'ACTIVITY_ACTION_RENDERER_UNSUPPORTED'
            : '';
  const displayedLocators = new Set<string>();
  const collectFields = (nodes: ActivityTemplateNode[]) => nodes.forEach((node) => {
    if (node.field) displayedLocators.add(node.field.nativeLocator);
    collectFields(node.children);
  });
  collectFields(templateNodes);
  return {
    ok,
    reasonCode,
    fields: allFields.filter((field) => displayedLocators.has(field.nativeLocator)),
    requestedFields,
    records: Array.isArray(records) ? records : [],
    templateNames,
    templateNodes,
    sourceAuthority: authority,
  };
}

export function resolveActivitySurfaceModel(contract: unknown, records: Dict[]): ActivitySurfaceModel {
  const v2 = resolveUnifiedPageContractV2(contract);
  return resolveActivitySurfaceModelFromProfile(v2?.layoutContract?.activityProfile, records);
}

export function resolveActivityRequestedFields(contract: unknown): string[] {
  return resolveActivitySurfaceModel(contract, []).requestedFields;
}
