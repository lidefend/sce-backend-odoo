/* eslint-disable @typescript-eslint/no-explicit-any */
import { computed, watch, type ComputedRef, type Ref } from 'vue';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2';
import type { NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import { buildRuntimeFieldStates } from '../../app/modifierEngine';
import {
  collectContractV2FieldStatusByCode, resolveContractV2ContainerTree, resolveContractV2MainData,
} from '../../app/contracts/v2';
import { evaluateFieldPolicy } from '../../app/contractPolicies';
import {
  applyNativeFieldOrderPreview as applyNativeFieldOrderPreviewFromTree,
  collectFormDataFieldNames, collectNativeFavoriteFieldNames, collectNativeFormDesignFields,
  collectNativeVisibleFieldNames, collectNativeVisibleFieldOrder, collectNativeVisibleSectionTitles,
  countNativeNodesByType, evaluateNativeModifierValue as evaluateNativeModifierValueWithResolver,
  filterVisibleNativeLayoutNodes as filterVisibleNativeLayoutNodesFromTree, isCreateWorkflowStateField,
  isNativeActionVisible, isNativeFieldVisible as isNativeFieldVisibleFromNativeLayout,
  isNativeLayoutNodeVisible as isNativeLayoutNodeVisibleFromNativeLayout,
  normalizeContractV2ContainersForNativeForm as normalizeContractV2ContainersForNativeFormFromTree,
  resolveNativeOccurrenceBehavior,
  resolveNativeButtonLabel as resolveNativeButtonLabelFromNode, resolveNativeFormRootColumns,
  resolveNativeModifierFieldValue,
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
  const fieldModifierMap = computed<Record<string, Record<string, unknown>>>(() => {
    // V1 views.form.field_modifiers is name-keyed and cannot represent
    // duplicate native occurrences. Only the V2 status projection and the
    // formal runtime onchange overlay may participate here.
    const output: Record<string, Record<string, unknown>> = {};
    const statuses = collectContractV2FieldStatusByCode(context.v2ContractStore.value);
    Object.entries(statuses).forEach(([name, status]) => {
      output[name] = { ...(output[name] || {}), ...(status.visible === false ? { invisible: true } : {}),
        ...(status.readonly === true || status.disabled === true ? { readonly: true } : {}),
        ...(status.required === true ? { required: true } : {}) };
    });
    return output;
  });
  const runtimeFieldStates = computed(() => {
    const storeNames = Array.from(context.v2ContractStore.value?.widgetsByFieldCodeAll.keys() || []);
    return buildRuntimeFieldStates({
      fieldNames: Array.from(new Set(storeNames)),
      fieldModifiers: fieldModifierMap.value, modifierPatch: context.onchangeModifiersPatch.value,
      values: context.formData,
    });
  });
  const runtimeState = (name: string) => runtimeFieldStates.value[name] || { invisible:false, readonly:false, required:false };
  const runtimeOccurrenceState = (node: NativeFormLayoutNode) => {
    const source = node as Record<string, unknown>;
    const widgetId = String(source.widgetId || '').trim();
    const nativeLocator = String(source.nativeLocator || source.native_locator || '').trim();
    const occurrenceIndex = Number(source.occurrenceIndex || source.occurrence_index || 0);
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
    const invisible = unresolved ? true : Boolean(live.invisible);
    return { invisible, visible:!invisible,
      readonly:Boolean(live.readonly||authorityReadonly||unresolved), required:Boolean(live.required||unresolved),
      disabled:Boolean(authorityReadonly||unresolved), reasonCode };
  };
  const isNativeOccurrenceEditable = (occurrenceKey: string) => {
    const key=String(occurrenceKey||'').trim(); if(!key)return false;
    let matched: NativeFormLayoutNode | null = null;
    const visit=(nodes:NativeFormLayoutNode[])=>{for(const node of nodes){if(String((node as Record<string,unknown>).widgetId||'').trim()===key){matched=node;return;}for(const branch of ['children','pages','tabs','nodes','items']){const rows=(node as Record<string,unknown>)[branch];if(Array.isArray(rows))visit(rows as NativeFormLayoutNode[]);if(matched)return;}}};
    visit(rawNativeFormLayoutNodes.value);
    if(!matched)return false;
    const state=runtimeOccurrenceState(matched);
    return state.visible!==false&&state.readonly!==true&&state.disabled!==true;
  };
  const isFieldVisible = (name: string) => {
    const descriptor = strictFieldDescriptorMap()[String(name || '').trim()];
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
    const containers = storeContainers;
    return containers.length ? normalizeContractV2ContainersForNativeFormFromTree(containers as NativeLayoutLikeNode[]) as NativeFormLayoutNode[] : [];
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
  const strictFieldDescriptorMap=()=>Array.from(context.v2ContractStore.value?.widgetsById.values()||[]).reduce<Record<string,any>>((output,widget)=>{if(widget.fieldCode&&widget.fieldDescriptor&&!output[widget.fieldCode])output[widget.fieldCode]=widget.fieldDescriptor;return output;},{});
  const strictFieldDescriptorForNode=(name:string,node?:NativeFormLayoutNode)=>{const widgetId=String((node as Record<string,unknown>|undefined)?.widgetId||'').trim();const exact=widgetId?context.v2ContractStore.value?.widgetsById.get(widgetId)?.fieldDescriptor:undefined;if(exact)return exact;return strictFieldDescriptorMap()[String(name||'').trim()];};
  const nativeStatusbar=computed<NativeStatusbarVm>(()=>{
    const main=resolveContractV2MainData(context.v2ContractStore.value);
    return normalizeNativeFormStatusbar({recordId:context.recordId.value,formView:undefined,
      fields:strictFieldDescriptorMap(),formData:context.formData,mainData:main,fieldReadonly:(field)=>runtimeState(field).readonly,
      readonly:context.renderProfile.value==='readonly'||(context.recordId.value?!context.rights.value.write:!context.rights.value.create),
      fallback:{visible:false,field:'',current:'',states:[],reachedValues:[],readonly:true}});
  });
  const setStatusbarValue=(value:string)=>{const field=nativeStatusbar.value.field;if(!field||nativeStatusbar.value.readonly)return;
    context.formData[field]=resolveStatusbarSelectionValue(strictFieldDescriptorForNode(field),value);context.markFieldChanged(field);};
  const modifierMainData=()=>resolveContractV2MainData(context.v2ContractStore.value);
  const evaluateNativeModifierValue=(value:unknown)=>evaluateNativeModifierValueWithResolver(value,(field)=>resolveNativeModifierFieldValue(context.formData,modifierMainData(),field));
  const evaluateNativeActionVisibility=(row:Record<string,unknown>)=>isNativeActionVisible({row,currentState:String(context.formData.state||'').trim(),evaluateModifier:evaluateNativeModifierValue,resolveAction:context.contractActionFromNativeRow});
  function isNativeLayoutNodeVisible(node:NativeFormLayoutNode){const source=node as Record<string,unknown>;const locator=String(source.nativeLocator||source.native_locator||'').trim();const ordinal=Number(source.occurrenceIndex||source.occurrence_index||0);if(locator&&Number.isInteger(ordinal)&&ordinal>0&&runtimeOccurrenceState(node).visible===false)return false;return isNativeLayoutNodeVisibleFromNativeLayout({node,editable:context.isContractFieldOrderEditable.value,evaluateModifier:evaluateNativeModifierValue,normalizeGroupTitle:normalizeFieldGroupTitle,isGroupVisible:context.effectiveGroupVisible,isFieldVisibleInDraft:(name)=>Object.prototype.hasOwnProperty.call(context.fieldVisibilityDraft,name)?context.fieldVisibilityDraft[name]:undefined,resolveAction:context.contractActionFromNativeRow});}
  function isNativeFieldVisible(name:string,node?:NativeFormLayoutNode){return isNativeFieldVisibleFromNativeLayout({name,node,statusField:nativeStatusbar.value.field,showHud:context.showHud.value,renderProfile:context.renderProfile.value,isCreate:!context.recordId.value,isNodeVisible:(item)=>isNativeLayoutNodeVisible(item as NativeFormLayoutNode),resolveDescriptor:(field,item)=>(item as any)?.descriptor||strictFieldDescriptorForNode(field,item as NativeFormLayoutNode|undefined),resolveFieldLabel:context.contractFieldLabel,semantic:context.fieldSemanticMeta,runtimeState:(field)=>node?runtimeOccurrenceState(node):runtimeState(field),evaluatePolicy:(field,descriptor)=>evaluateFieldPolicy(null,field,{required:Boolean(descriptor?.required),readonly:Boolean(descriptor?.readonly)},context.policyContext.value)});}
  const isWritableFieldVisible=(name:string)=>useNativeFormTree.value?nativeVisibleFieldNames.value.has(String(name||'').trim()):isFieldVisible(name);
  const nativeFieldAccess=(name:string)=>{const key=String(name||'').trim();if(!key)return undefined;const states:Array<Record<string,unknown>>=[];const visit=(nodes:NativeFormLayoutNode[],ancestorVisible=true)=>{for(const node of nodes){const visible=ancestorVisible&&isNativeLayoutNodeVisible(node);if(String(node.type||'').toLowerCase()==='field'&&String(node.name||'').trim()===key)states.push({...runtimeOccurrenceState(node),visible});for(const branch of ['children','pages','tabs','nodes','items']){const rows=(node as Record<string,unknown>)[branch];if(Array.isArray(rows))visit(rows as NativeFormLayoutNode[],visible);}}};visit(rawNativeFormLayoutNodes.value);if(!states.length)return undefined;return{visible:states.some(state=>state.visible!==false),writable:states.some(state=>state.visible!==false&&state.readonly!==true&&state.disabled!==true),required:states.some(state=>state.visible!==false&&state.readonly!==true&&state.disabled!==true&&state.required===true)};};
  const currentNativeFieldOrder=()=>collectNativeVisibleFieldOrder(nativeFormLayoutNodes.value as NativeLayoutLikeNode[],(name,node)=>isNativeFieldVisible(name,node as NativeFormLayoutNode));
  const ensureFieldOrderDraftStartsFromCurrentLayout=()=>{if(!useNativeFormTree.value||context.fieldOrderPreviewActive.value)return;const current=currentNativeFieldOrder();if(!current.length)return;const known=new Set(current);context.fieldOrderDraft.value=[...current,...context.fieldOrderDraft.value.filter(name=>name&&!known.has(name))];};
  const formDataFieldNames=()=>{const main=resolveContractV2MainData(context.v2ContractStore.value);const strictWidgets=Array.from(context.v2ContractStore.value?.widgetsById.values()||[]);const strictFields=strictFieldDescriptorMap();return collectFormDataFieldNames({fields:strictFields,rawNativeLayoutNodes:rawNativeFormLayoutNodes.value as NativeLayoutLikeNode[],layoutFieldNames:strictWidgets.map(widget=>widget.fieldCode),visibleFields:[],statusField:nativeStatusbar.value.field,mainData:main});};
  return {baseNativeFormLayoutNodes,currentNativeFieldOrder,ensureFieldOrderDraftStartsFromCurrentLayout,evaluateNativeActionVisibility,evaluateNativeModifierValue,fieldModifierMap,formDataFieldNames,isFieldVisible,isNativeFavoriteField:(name:string)=>nativeFavoriteFieldNames.value.has(String(name||'').trim()),isNativeFieldVisible,isNativeLayoutNodeVisible,isNativeOccurrenceEditable,isWritableFieldVisible,nativeFieldAccess,nativeFormLayoutNodes,nativeFormRootColumns,nativeGroupCount,nativeNotebookPageCount,nativeStatusbar,nativeVisibleFieldNames,nativeVisibleSectionTitles,rawNativeFormLayoutNodes,resolveNativeButtonLabel,runtimeFieldStates,runtimeNativeFormLayoutNodes,runtimeOccurrenceState,runtimeState,setStatusbarValue,showNativeDefaultSectionTitle,useNativeFormTree};
}
