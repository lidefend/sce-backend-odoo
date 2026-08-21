/* eslint-disable @typescript-eslint/no-explicit-any */
import { computed, watch, type ComputedRef, type Ref } from 'vue';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2';
import type { NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import { buildRuntimeFieldStates } from '../../app/modifierEngine';
import {
  collectContractV2FieldStatusByCode, resolveContractV2ContainerTree, resolveContractV2FormFieldMap, resolveContractV2MainData,
} from '../../app/contracts/v2';
import {
  applyNativeFieldOrderPreview as applyNativeFieldOrderPreviewFromTree,
  collectFormDataFieldNames, collectNativeFavoriteFieldNames, collectNativeFormDesignFields,
  collectNativeVisibleFieldNames, collectNativeVisibleFieldOrder, collectNativeVisibleSectionTitles,
  countNativeNodesByType, evaluateNativeModifierValue as evaluateNativeModifierValueWithResolver,
  filterVisibleNativeLayoutNodes as filterVisibleNativeLayoutNodesFromTree, isCreateWorkflowStateField,
  isNativeActionVisible, isNativeFieldVisible as isNativeFieldVisibleFromNativeLayout,
  isNativeLayoutNodeVisible as isNativeLayoutNodeVisibleFromNativeLayout,
  normalizeContractV2ContainersForNativeForm as normalizeContractV2ContainersForNativeFormFromTree,
  resolveNativeButtonLabel as resolveNativeButtonLabelFromNode, resolveNativeFormRootColumns,
  resolveNativeModifierFieldValue, resolveNativeOccurrenceBehavior,
  type NativeLayoutLikeNode, type FieldSemanticMeta,
} from './nativeLayoutUtils';
import { normalizeNativeFormStatusbar, resolveStatusbarSelectionValue } from './workflowContract';
import type { NativeStatusbarVm } from './types';
import {
  fieldGroupTitleMatches, isReadableFieldGroupTitle, layoutHasReadableFieldGroups,
  mergeLowCodeLayoutWithRuntimeGroupShells, normalizeFieldGroupTitle,
} from './formConfigHelpers';

export function useRecordFormLayout(context: {
  v2ContractStore: Ref<ContractV2NormalizedStore | null>;
  contractVisibleFields: ComputedRef<string[]>; onchangeModifiersPatch: Ref<Record<string, Record<string, unknown>>>;
  formData: Record<string, unknown>; isQuickIntakeMode: ComputedRef<boolean>;
  contractFieldLabel: (name: string) => string; fieldSemanticMeta: (name: string) => FieldSemanticMeta;
  showHud: ComputedRef<boolean>; advancedExpanded: Ref<boolean>; coreFieldNames: ComputedRef<string[]>;
  advancedFieldNames: ComputedRef<string[]>; renderProfile: ComputedRef<string>; recordId: ComputedRef<number | null>;
  isContractFieldOrderEditable: ComputedRef<boolean>; fieldOrderDraft: Ref<string[]>; fieldOrderPreviewActive: Ref<boolean>;
  changedFieldGroupDraft: () => Record<string, string>; fieldMoveTargetDraft: Record<string, string>;
  fieldGroupBase: Ref<Record<string, string>>; fieldGroupDraft: Record<string, string>;
  effectiveGroupVisible: (title: string) => boolean; lowCodeFormLayoutBase: Ref<NativeLayoutLikeNode[]>;
  nativeLayoutVisibilityRevision: Ref<number>; nativeFormDesignFieldKeys: Ref<string[]>;
  nativeFormDesignFieldLabels: Ref<Record<string, string>>; formLayoutColumnsDraft: Ref<1|2|3>;
  fieldVisibilityDraft: Record<string, boolean>; contractActionFromNativeRow: (row: Record<string, unknown>) => unknown;
  policyContext: ComputedRef<any>; rights: ComputedRef<{create:boolean;write:boolean}>;
  markFieldChanged: (name: string) => void;
  layoutNodes: () => Array<{kind:string;name:string}>;
}) {
  const formFields = computed(() => resolveContractV2FormFieldMap(context.v2ContractStore.value));
  const fieldModifierMap = computed<Record<string, Record<string, unknown>>>(() => {
    const output: Record<string, Record<string, unknown>> = {};
    const fromStore = collectContractV2FieldStatusByCode(context.v2ContractStore.value);
    Object.entries(fromStore).forEach(([name, status]) => {
      output[name] = { ...(output[name] || {}), ...(status.visible === false ? { invisible: true } : {}),
        ...(status.readonly === true || status.disabled === true ? { readonly: true } : {}),
        ...(status.required === true ? { required: true } : {}) };
    });
    return output;
  });
  const runtimeFieldStates = computed(() => {
    const contractNames = Array.from(context.v2ContractStore.value?.widgetsByFieldCode.keys() || []);
    return buildRuntimeFieldStates({
      fieldNames: Array.from(new Set([...Object.keys(formFields.value), ...contractNames])),
      fieldModifiers: fieldModifierMap.value, modifierPatch: context.onchangeModifiersPatch.value,
      values: context.formData,
    });
  });
  const runtimeState = (name: string) => runtimeFieldStates.value[name] || { invisible:false, readonly:false, required:false };
  const runtimeOccurrenceState = (node: NativeFormLayoutNode) => {
    const source = node as Record<string, unknown>;
    const widgetId = String(source.widgetId || '').trim();
    const nativeLocator = String(source.nativeLocator || '').trim();
    const occurrenceIndex = Number(source.occurrenceIndex || 0);
    const isOccurrence = Boolean(nativeLocator && Number.isInteger(occurrenceIndex) && occurrenceIndex > 0);
    if (!isOccurrence) return runtimeState(String(node.name || '').trim());
    const status = context.v2ContractStore.value?.widgetStatusById.get(widgetId);
    if (!status) return { invisible:true, visible:false, readonly:true, required:true, disabled:true, reasonCode:'V2_OCCURRENCE_STATUS_MISSING' };
    const name = String(node.name || '').trim();
    const runtimePatch = context.onchangeModifiersPatch.value[name] || {};
    const liveSource = { ...source, modifiers: { ...((source.modifiers as Record<string, unknown>) || {}), ...runtimePatch } };
    const live = resolveNativeOccurrenceBehavior(liveSource, evaluateNativeModifierValue);
    const reasonCode = String(status.reasonCode || '').trim();
    const unresolved = /UNRESOLVED|UNSUPPORTED|INVALID|MISSING/.test(reasonCode);
    const authorityReadonly = status.auth !== 'edit' || (status.disabled === true && unresolved);
    const invisible = unresolved ? true : Boolean(live.invisible || status.visible === false);
    return { invisible, visible:!invisible,
      readonly:Boolean(live.readonly||status.readonly||authorityReadonly||unresolved),
      required:Boolean(live.required||status.required||unresolved),
      disabled:Boolean(authorityReadonly||unresolved), reasonCode };
  };
  const isFieldVisible = (name: string) => {
    const descriptor = formFields.value[String(name || '').trim()];
    if (isCreateWorkflowStateField(name, context.contractFieldLabel(name) || descriptor?.string || '', !context.recordId.value)) return false;
    if (nativeStatusbar.value.field === String(name || '').trim()) return false;
    const semantic = context.fieldSemanticMeta(name);
    if ((semantic.technical || semantic.semantic_type === 'technical') && !context.showHud.value) return false;
    if (semantic.surface_role === 'hidden' && !context.showHud.value) return false;
    if (runtimeState(name).invisible) return false;
    if (context.contractVisibleFields.value.length && !context.contractVisibleFields.value.includes(name)) return false;
    if (semantic.surface_role === 'core') return true;
    if (semantic.surface_role === 'advanced') return context.advancedExpanded.value;
    const core = context.coreFieldNames.value; const advanced = context.advancedFieldNames.value;
    if (!core.length && !advanced.length) return true;
    if (core.includes(name)) return true;
    if (advanced.includes(name)) return context.advancedExpanded.value;
    if (!core.length) return true;
    return context.renderProfile.value !== 'create';
  };
  const filterVisibleNativeLayoutNodes = (nodes: NativeFormLayoutNode[]) => filterVisibleNativeLayoutNodesFromTree({
    nodes, isNodeVisible: isNativeLayoutNodeVisible, groupVisibilityEditable: context.isContractFieldOrderEditable.value,
    normalizeGroupTitle: normalizeFieldGroupTitle, isGroupVisible: context.effectiveGroupVisible,
  });
  const applyNativeFieldOrderPreview = (nodes: NativeFormLayoutNode[]) => applyNativeFieldOrderPreviewFromTree({
    nodes, fieldOrder: context.fieldOrderDraft.value, movedGroups: context.changedFieldGroupDraft(),
    moveTargetDraft: context.fieldMoveTargetDraft, normalizeGroupTitle: normalizeFieldGroupTitle,
    isReadableGroupTitle: isReadableFieldGroupTitle, groupTitleMatches: fieldGroupTitleMatches,
    baseGroupTitleForField: (name) => context.fieldGroupBase.value[name] || context.fieldGroupDraft[name] || '',
  });
  const runtimeNativeFormLayoutNodes = () => {
    const storeContainers = resolveContractV2ContainerTree(context.v2ContractStore.value);
    return storeContainers.length
      ? normalizeContractV2ContainersForNativeFormFromTree(storeContainers as unknown as NativeLayoutLikeNode[]) as NativeFormLayoutNode[]
      : [];
  };
  const rawNativeFormLayoutNodes = computed<NativeFormLayoutNode[]>(() => {
    if (context.isContractFieldOrderEditable.value && layoutHasReadableFieldGroups(context.lowCodeFormLayoutBase.value)) {
      return mergeLowCodeLayoutWithRuntimeGroupShells(context.lowCodeFormLayoutBase.value, runtimeNativeFormLayoutNodes()) as NativeFormLayoutNode[];
    }
    return runtimeNativeFormLayoutNodes();
  });
  const baseNativeFormLayoutNodes = computed(() => { void context.nativeLayoutVisibilityRevision.value; return filterVisibleNativeLayoutNodes(rawNativeFormLayoutNodes.value); });
  const nativeFormLayoutNodes = computed(() => context.isContractFieldOrderEditable.value
    && context.fieldOrderPreviewActive.value && context.fieldOrderDraft.value.length
    ? applyNativeFieldOrderPreview(baseNativeFormLayoutNodes.value) : baseNativeFormLayoutNodes.value);
  const useNativeFormTree = computed(() => nativeFormLayoutNodes.value.length > 0);
  const nativeFormRootColumns = computed<1|2|3>(() => context.isContractFieldOrderEditable.value
    ? context.formLayoutColumnsDraft.value : resolveNativeFormRootColumns(nativeFormLayoutNodes.value as NativeLayoutLikeNode[]));
  watch(baseNativeFormLayoutNodes, (nodes) => {
    const {keys,labels}=collectNativeFormDesignFields(nodes as NativeLayoutLikeNode[]);
    context.nativeFormDesignFieldKeys.value=keys; context.nativeFormDesignFieldLabels.value=labels;
  }, {immediate:true});
  const nativeNotebookPageCount=computed(()=>countNativeNodesByType(nativeFormLayoutNodes.value as NativeLayoutLikeNode[],'page'));
  const nativeGroupCount=computed(()=>countNativeNodesByType(nativeFormLayoutNodes.value as NativeLayoutLikeNode[],'group'));
  const nativeVisibleSectionTitles=computed(()=>collectNativeVisibleSectionTitles(nativeFormLayoutNodes.value as NativeLayoutLikeNode[]));
  const nativeVisibleFieldNames=computed(()=>collectNativeVisibleFieldNames(nativeFormLayoutNodes.value as NativeLayoutLikeNode[],(name,node)=>isNativeFieldVisible(name,node as NativeFormLayoutNode)));
  const showNativeDefaultSectionTitle=computed(()=>useNativeFormTree.value&&nativeVisibleFieldNames.value.size>0&&!nativeVisibleSectionTitles.value.length);
  const resolveNativeButtonLabel=(node:NativeFormLayoutNode)=>resolveNativeButtonLabelFromNode(node as NativeLayoutLikeNode,(field)=>context.formData[field]);
  const nativeFavoriteFieldNames=computed(()=>{const names=new Set<string>();collectNativeFavoriteFieldNames(rawNativeFormLayoutNodes.value,names);return names;});
  const canonicalNativeStatusbar=computed(()=>{
    const queue=[...(resolveContractV2ContainerTree(context.v2ContractStore.value) as NativeFormLayoutNode[])];
    while(queue.length){
      const node=queue.shift() as NativeFormLayoutNode;
      const source=node as Record<string,unknown>;
      const attrs=source.attributes&&typeof source.attributes==='object'&&!Array.isArray(source.attributes)
        ? source.attributes as Record<string,unknown>:{};
      const fieldInfo=source.fieldInfo&&typeof source.fieldInfo==='object'&&!Array.isArray(source.fieldInfo)
        ? source.fieldInfo as Record<string,unknown>:{};
      const field=String(source.name||source.fieldCode||attrs.name||fieldInfo.name||'').trim();
      if(field&&String(attrs.widget||source.widget||fieldInfo.widget||'').trim()==='statusbar'){
        const visible=String(attrs.statusbar_visible||source.statusbarVisible||source.statusbar_visible||fieldInfo.statusbar_visible||'')
          .split(',').map(item=>item.trim()).filter(Boolean);
        const descriptor=formFields.value[field];
        const selection=Array.isArray(descriptor?.selection)
          ? descriptor.selection
          : Array.isArray(fieldInfo.selection) ? fieldInfo.selection as Array<[string,string]> : [];
        const states=(visible.length?visible:selection.map(item=>String(item[0]??'')))
          .map(value=>{const match=selection.find(item=>String(item[0]??'')===value);return {value,label:String(match?.[1]??value)};});
        return {field,states};
      }
      for(const key of ['children','pages','tabs','nodes','items'] as const){
        const children=source[key];if(Array.isArray(children))queue.push(...children as NativeFormLayoutNode[]);
      }
    }
    const fallback=Object.entries(formFields.value).find(([,descriptor])=>String(descriptor.widget||'').trim()==='statusbar');
    if(fallback){
      const [field,descriptor]=fallback;
      const selection=Array.isArray(descriptor.selection)?descriptor.selection:[];
      return {field,states:selection.map(item=>({value:String(item[0]??''),label:String(item[1]??item[0]??'')}))};
    }
    return {field:'',states:[] as Array<{value:string;label:string}>};
  });
  const nativeStatusbar=computed<NativeStatusbarVm>(()=>{
    const main=resolveContractV2MainData(context.v2ContractStore.value);
    return normalizeNativeFormStatusbar({recordId:context.recordId.value,formView:{statusbar:canonicalNativeStatusbar.value},
      fields:formFields.value,formData:context.formData,mainData:main,fieldReadonly:(field)=>runtimeState(field).readonly,
      readonly:context.renderProfile.value==='readonly'||(context.recordId.value?!context.rights.value.write:!context.rights.value.create),
      fallback:{visible:false,field:'',current:'',states:[],reachedValues:[],readonly:true}});
  });
  const setStatusbarValue=(value:string)=>{const field=nativeStatusbar.value.field;if(!field||nativeStatusbar.value.readonly)return;
    context.formData[field]=resolveStatusbarSelectionValue(formFields.value[field],value);context.markFieldChanged(field);};
  const modifierMainData=()=>resolveContractV2MainData(context.v2ContractStore.value);
  const evaluateNativeModifierValue=(value:unknown)=>evaluateNativeModifierValueWithResolver(value,(field)=>resolveNativeModifierFieldValue(context.formData,modifierMainData(),field));
  const evaluateNativeActionVisibility=(row:Record<string,unknown>)=>isNativeActionVisible({row,currentState:String(context.formData.state||'').trim(),evaluateModifier:evaluateNativeModifierValue,resolveAction:context.contractActionFromNativeRow});
  function isNativeLayoutNodeVisible(node:NativeFormLayoutNode){const source=node as Record<string,unknown>;if(String(source.nativeLocator||'').trim()&&runtimeOccurrenceState(node).invisible===true)return false;return isNativeLayoutNodeVisibleFromNativeLayout({node,editable:context.isContractFieldOrderEditable.value,evaluateModifier:evaluateNativeModifierValue,normalizeGroupTitle:normalizeFieldGroupTitle,isGroupVisible:context.effectiveGroupVisible,isFieldVisibleInDraft:(name)=>Object.prototype.hasOwnProperty.call(context.fieldVisibilityDraft,name)?context.fieldVisibilityDraft[name]:undefined,resolveAction:context.contractActionFromNativeRow});}
  function isNativeFieldVisible(name:string,node?:NativeFormLayoutNode){return isNativeFieldVisibleFromNativeLayout({name,node,statusField:nativeStatusbar.value.field,showHud:context.showHud.value,renderProfile:context.renderProfile.value,isCreate:!context.recordId.value,isNodeVisible:(item)=>isNativeLayoutNodeVisible(item as NativeFormLayoutNode),resolveDescriptor:(field,item)=>item?(item as any).descriptor||formFields.value[field]:formFields.value[field],resolveFieldLabel:context.contractFieldLabel,semantic:context.fieldSemanticMeta,runtimeState:(field)=>node?runtimeOccurrenceState(node):runtimeState(field),evaluatePolicy:(_field,descriptor)=>({visible:true,required:Boolean(descriptor?.required),readonly:Boolean(descriptor?.readonly)})});}
  const isWritableFieldVisible=(name:string)=>useNativeFormTree.value?nativeVisibleFieldNames.value.has(String(name||'').trim()):isFieldVisible(name);
  const currentNativeFieldOrder=()=>collectNativeVisibleFieldOrder(nativeFormLayoutNodes.value as NativeLayoutLikeNode[],(name,node)=>isNativeFieldVisible(name,node as NativeFormLayoutNode));
  const ensureFieldOrderDraftStartsFromCurrentLayout=()=>{if(!useNativeFormTree.value||context.fieldOrderPreviewActive.value)return;const current=currentNativeFieldOrder();if(!current.length)return;const known=new Set(current);context.fieldOrderDraft.value=[...current,...context.fieldOrderDraft.value.filter(name=>name&&!known.has(name))];};
  const formDataFieldNames=()=>{const main=resolveContractV2MainData(context.v2ContractStore.value);return collectFormDataFieldNames({fields:formFields.value,rawNativeLayoutNodes:rawNativeFormLayoutNodes.value as NativeLayoutLikeNode[],layoutFieldNames:context.layoutNodes().filter(node=>node.kind==='field').map(node=>node.name),visibleFields:context.contractVisibleFields.value,statusField:nativeStatusbar.value.field,mainData:main});};
  return {baseNativeFormLayoutNodes,currentNativeFieldOrder,ensureFieldOrderDraftStartsFromCurrentLayout,evaluateNativeActionVisibility,evaluateNativeModifierValue,fieldModifierMap,formDataFieldNames,isFieldVisible,isNativeFavoriteField:(name:string)=>nativeFavoriteFieldNames.value.has(String(name||'').trim()),isNativeFieldVisible,isNativeLayoutNodeVisible,isWritableFieldVisible,nativeFormLayoutNodes,nativeFormRootColumns,nativeGroupCount,nativeNotebookPageCount,nativeStatusbar,nativeVisibleFieldNames,nativeVisibleSectionTitles,rawNativeFormLayoutNodes,resolveNativeButtonLabel,runtimeFieldStates,runtimeNativeFormLayoutNodes,runtimeOccurrenceState,runtimeState,setStatusbarValue,showNativeDefaultSectionTitle,useNativeFormTree};
}
