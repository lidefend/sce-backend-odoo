/* eslint-disable @typescript-eslint/no-explicit-any */
import type { ComputedRef, Ref } from 'vue';
import type { FieldDescriptor } from '@sc/schema';
import { createContractFormRecord, writeContractFormRecord } from '../../app/runtime/contractFormDataRuntime';
import { triggerOnchange } from '../../api/onchange';
import { fieldRequiresServerOnchange } from './contractActionRules';
import { fieldType, normalizeRelationIds, sanitizeUiErrorMessage } from './fieldUtils';
import { normalizeComparable, normalizeContractFieldValue } from './valueUtils';
import { buildOnchangeRequestPayload, normalizeOnchangeFieldPatch, normalizeOnchangeResponse } from './onchangeNormalization';
import { shouldWriteFieldValue } from './saveRecordHelpers';
import { buildFormRequestContext } from './formRequestContext';
import { buildOnchangeDraftSnapshot, createOnchangeRoundtripTicket, onchangeRecordKey, planOnchangeApplication } from './onchangeRoundtripIdentity';
import {
  hasAmbiguousRelationMatches, relationEntry, relationInlineCreate, resolveRelationQuickFillOption,
} from './relationDescriptor';
import {
  resolveProfessionalMany2oneQueryKey, resolveProfessionalMany2oneSearchInput,
} from '../../components/professional-fields/professionalRelationFieldModel';
import { MANY2ONE_CREATE_OPTION, MANY2ONE_OPEN_RECORD_OPTION, MANY2ONE_SEARCH_MORE_OPTION, type LayoutNode, type RelationOption } from './types';
import type { BusinessFieldError } from '../../app/businessValidationError';
import type { FieldOccurrenceDecision } from './fieldOccurrenceWritability';

export function useRecordFormState(context: {
  formFields:ComputedRef<Record<string,FieldDescriptor>>; model:ComputedRef<string>; recordId:ComputedRef<number|null>;
  rights:ComputedRef<{write:boolean}>; formData:Record<string,unknown>; originalValues:Ref<Record<string,unknown>>;
  submissionFeedback:Ref<any>; relationKeywords:Record<string,string>; invalidatedRelationKeywords:Record<string,string>;
  clearedDynamicRelationFields:Record<string,boolean>; relationQueryTimers:Record<string,ReturnType<typeof setTimeout>>;
  relationOptions:Ref<Record<string,RelationOption[]>>; validationErrors:Ref<string[]>; validationFieldErrors:Ref<Record<string,BusinessFieldError>>;
  onchangeModifiersPatch:Ref<Record<string,Record<string,unknown>>>; onchangeWarnings:Ref<any[]>; onchangeLinePatches:Ref<any[]>;
  applyingOnchangePatch:Ref<boolean>; changedFieldSet:Set<string>; dirtyFieldSet:Set<string>;
  getOnchangeTimer:()=>ReturnType<typeof setTimeout>|null; setOnchangeTimer:(timer:ReturnType<typeof setTimeout>|null)=>void;
  contractV2ActionRules:ComputedRef<any[]>; layoutNodes:ComputedRef<LayoutNode[]>; nativeStatusbar:ComputedRef<any>;
  route:any;
  isNativeFavoriteField:(name:string)=>boolean; clearDynamicRelationDependents:(name:string)=>void;
  openRelationCreateForm:(name:string,descriptor?:FieldDescriptor)=>Promise<unknown>; openRelationSearchDialog:(name:string,descriptor?:FieldDescriptor)=>Promise<unknown>;
  openRelationRecordForm:(name:string,descriptor?:FieldDescriptor)=>Promise<unknown>; relationOptionsForField:(name:string)=>RelationOption[];
  switchFormByRelationOption:(name:string,option:RelationOption)=>Promise<unknown>; queryRelationOptions:(name:string,keyword:string)=>Promise<RelationOption[]>;
  setRelationKeyword:(name:string,keyword:string)=>void; setMany2oneOption:(name:string,option:RelationOption)=>void;
  relationKeyword:(name:string)=>string; quickCreateRelation:(name:string,descriptor:FieldDescriptor|undefined,label:string)=>Promise<unknown>;
  relationUiLabel:(descriptor:FieldDescriptor|undefined,key:string,fallback?:string)=>string; relationModel:(name:string)=>string;
  relationIds:(name:string)=>number[]; upsertRelationOption:(name:string,option:RelationOption|null)=>void;
  buildOne2manyCommandValue:(name:string,mode:'write'|'onchange')=>unknown; one2manyFieldRows:(name:string)=>any[];
  initOne2manyRows:(name:string,value:unknown)=>void; applyOnchangeLinePatches:(patches:any[])=>void;
  isWritableFieldVisible:(name:string)=>boolean;
  canonicalFieldWritable?:(name:string)=>boolean|undefined;
  fieldOccurrenceDecision?:(name:string,occurrenceKey:string)=>FieldOccurrenceDecision;
  pendingInlineCreateFields?: Ref<string[]>;
}) {
  const inputFieldValue=(name:string)=>{const raw=context.formData[name];return raw===false||raw===null||raw===undefined?'':String(raw);};
  const comparableFieldValue=(name:string,value:unknown)=>{const type=fieldType(context.formFields.value[name]);
    if(type==='many2many')return JSON.stringify(normalizeRelationIds(value).sort((a,b)=>a-b));
    if(type==='one2many')return JSON.stringify(context.one2manyFieldRows(name).map(row=>({id:row.id||0,isNew:row.isNew,removed:row.removed,dirty:row.dirty,dirtyFields:row.dirtyFields||[],values:row.values||{}})));
    return normalizeComparable(value);};
  // A keyed edit is judged by its own occurrence. An identity the contract
  // cannot resolve is refused outright: searching for a writable same-name
  // position is the exact bypass this guard exists to close.
  const isFieldWritable=(name:string,occurrenceKey?:string)=>{const key=String(occurrenceKey??'').trim();if(key)return context.fieldOccurrenceDecision?.(name,key)==='writable';const canonical=context.canonicalFieldWritable?.(name);if(typeof canonical==='boolean')return canonical;const node=context.layoutNodes.value.find(item=>item.kind==='field'&&item.name===name);if(node)return !node.readonly;return Boolean(context.nativeStatusbar.value.field===name&&!context.nativeStatusbar.value.readonly);};
  const normalizeFieldValue=(name:string,value:unknown)=>normalizeContractFieldValue({name,value,descriptor:context.formFields.value[name],originalValue:context.originalValues.value[name],buildOne2manyValue:context.buildOne2manyCommandValue});
  let onchangeTimer:ReturnType<typeof setTimeout>|null=context.getOnchangeTimer();
  const markFieldChanged=(name:string)=>{const key=String(name||'').trim();if(!key||context.applyingOnchangePatch.value)return;delete context.validationFieldErrors.value[key];if(!Object.keys(context.validationFieldErrors.value).length)context.validationErrors.value=[];context.dirtyFieldSet.add(key);
    if(!fieldRequiresServerOnchange(context.contractV2ActionRules.value,key))return;context.changedFieldSet.add(key);if(onchangeTimer)clearTimeout(onchangeTimer);
    onchangeTimer=setTimeout(()=>void runOnchangeRoundtrip(),300);context.setOnchangeTimer(onchangeTimer);};
  // A value setter can receive a value identical to the delivered record baseline
  // (for example a relation component writing its selection back on mount). That is
  // not a change: it must not fabricate dirty state or onchange dispatch. This
  // compares only against the delivered record baseline; it infers no permission or
  // field policy. The explicit intent path (commitMany2oneInline) keeps using
  // markFieldChanged directly.
  const syncFieldDirty=(name:string)=>{const key=String(name||'').trim();if(!key||context.applyingOnchangePatch.value)return;
    if(comparableFieldValue(key,context.formData[key])!==comparableFieldValue(key,context.originalValues.value[key])){markFieldChanged(key);return;}
    context.dirtyFieldSet.delete(key);if(context.changedFieldSet.delete(key)&&!context.changedFieldSet.size&&onchangeTimer){clearTimeout(onchangeTimer);onchangeTimer=null;context.setOnchangeTimer(null);}};
  const persistNativeFavoriteField=async(name:string,checked:boolean,previous:unknown)=>{try{await writeContractFormRecord({model:context.model.value,ids:[context.recordId.value],vals:{[name]:checked},context:{}});context.originalValues.value={...context.originalValues.value,[name]:checked};context.changedFieldSet.delete(name);context.dirtyFieldSet.delete(name);}catch{context.formData[name]=previous;context.submissionFeedback.value={kind:'error',message:'保存失败，请稍后重试。'};}};
  const setBooleanField=(name:string,checked:boolean,occurrenceKey?:string)=>{if(!isFieldWritable(name,occurrenceKey))return;const previous=context.formData[name];context.formData[name]=checked;if(context.isNativeFavoriteField(name)&&context.recordId.value&&context.rights.value.write){void persistNativeFavoriteField(name,checked,previous);return;}syncFieldDirty(name);};
  const setMany2oneField=(name:string,descriptor:FieldDescriptor|undefined,value:string,occurrenceKey?:string)=>{const normalized=String(value||'').trim();if(normalized===MANY2ONE_OPEN_RECORD_OPTION){void context.openRelationRecordForm(name,descriptor);return;}if(!isFieldWritable(name,occurrenceKey))return;if(!normalized){forgetPendingInlineCreate(name);context.formData[name]=false;context.relationKeywords[name]='';context.clearDynamicRelationDependents(name);syncFieldDirty(name);return;}
    if(normalized===MANY2ONE_CREATE_OPTION){void context.openRelationCreateForm(name,descriptor);return;}if(normalized===MANY2ONE_SEARCH_MORE_OPTION){void context.openRelationSearchDialog(name,descriptor);return;}
    const id=Number(normalized);if(!Number.isFinite(id)||id<=0){context.formData[name]=false;context.relationKeywords[name]='';context.clearDynamicRelationDependents(name);syncFieldDirty(name);return;}
    const normalizedId=Math.trunc(id);forgetPendingInlineCreate(name);context.formData[name]=normalizedId;const selected=context.relationOptionsForField(name).find(option=>option.id===normalizedId);if(selected){context.relationKeywords[name]=selected.label;void context.switchFormByRelationOption(name,selected);}context.clearDynamicRelationDependents(name);syncFieldDirty(name);};
  // The search keyword is the controlled value of the official Select's input, so
  // the text the user typed must be stored exactly as typed: normalizing it here
  // would delete the character in flight (typing ``FE Project`` would degrade to
  // ``FEProject``). Only the request/comparison key is normalized.
  const queryMany2oneInline=(name:string,_descriptor:FieldDescriptor|undefined,value:string,occurrenceKey?:string)=>{
    if(!isFieldWritable(name,occurrenceKey))return;
    const typedKeyword=resolveProfessionalMany2oneSearchInput(value);
    const keyword=resolveProfessionalMany2oneQueryKey(value);
    if(keyword&&context.clearedDynamicRelationFields[name]){delete context.clearedDynamicRelationFields[name];delete context.invalidatedRelationKeywords[name];}
    if(keyword&&context.invalidatedRelationKeywords[name]===keyword&&!context.formData[name]){context.relationKeywords[name]='';return;}
    if(keyword&&context.invalidatedRelationKeywords[name]&&context.invalidatedRelationKeywords[name]!==keyword)delete context.invalidatedRelationKeywords[name];
    context.relationKeywords[name]=typedKeyword;
    if(!keyword){void context.queryRelationOptions(name,'');return;}
    context.setRelationKeyword(name,typedKeyword);
  };
  // A search keyword is never a create request. Only the explicit create
  // action stages an intent, bound to this record and reset by the authoritative draft lifecycle.
  // A staged create intent records the keyword to create and the relation value
  // it was staged from. It never rewrites the relation value: pretending the
  // relation was cleared would fire an empty-association onchange and would
  // make the search keyword look like a saved field value.
  const pendingInlineCreates = new Map<string, {
    keyword: string; recordKey: string; stagedValue: string; occurrenceKey?: string;
  }>();
  const relationValueSnapshot = (name: string) => String(context.formData[name] ?? '');
  const syncPendingInlineCreateFields = () => {
    if (context.pendingInlineCreateFields) context.pendingInlineCreateFields.value = [...pendingInlineCreates.keys()];
  };
  const forgetPendingInlineCreate = (name: string) => {
    pendingInlineCreates.delete(name);
    syncPendingInlineCreateFields();
  };
  const resetPendingInlineRelationCreates = () => {
    pendingInlineCreates.clear();
    syncPendingInlineCreateFields();
  };
  const relationRecordKey = () => `${context.model.value}:${context.recordId.value ?? 'new'}`;
  const commitMany2oneInline = async (name: string, descriptor: FieldDescriptor | undefined, value: string, occurrenceKey?: string) => {
    if (!isFieldWritable(name, occurrenceKey)) return;
    const keyword = String(value || '').trim();
    const inline = relationInlineCreate(descriptor);
    if (!keyword || !inline.enabled || !inline.createOnNoMatch || relationEntry(descriptor)?.canCreate !== true) return;
    pendingInlineCreates.set(name, { keyword, recordKey: relationRecordKey(), stagedValue: relationValueSnapshot(name), occurrenceKey: String(occurrenceKey ?? '').trim() || undefined });
    syncPendingInlineCreateFields();
    context.relationKeywords[name] = keyword;
    markFieldChanged(name);
  };
  const resolvePendingInlineRelationCreates = async () => {
    const issues: string[] = [];
    for (const [name, pending] of pendingInlineCreates) {
      // The intent is bound to one record and one starting relation value. Any
      // other relation write (select, clear, lifecycle navigation, reload)
      // invalidates it instead of being read as "the relation is empty".
      if (pending.recordKey !== relationRecordKey()
        || pending.stagedValue !== relationValueSnapshot(name)
        || !context.dirtyFieldSet.has(name)) {
        forgetPendingInlineCreate(name);
        continue;
      }
      const descriptor = context.formFields.value[name];
      const inline = relationInlineCreate(descriptor);
      if (!isFieldWritable(name, pending.occurrenceKey) || !inline.enabled || !inline.createOnNoMatch || relationEntry(descriptor)?.canCreate !== true) {
        issues.push(context.relationUiLabel(descriptor, 'missing_create_entry', '当前字段不允许创建关联记录'));
        continue;
      }
      // quickCreateRelation resolves exact matches and propagates an actual
      // query failure as a creation error. Never interpret query [] as consent.
      const before = context.validationErrors.value.slice();
      await context.quickCreateRelation(name, descriptor, pending.keyword);
      if (Number(context.formData[name] || 0) > 0) forgetPendingInlineCreate(name);
      else {
        issues.push(...(context.validationErrors.value.length ? context.validationErrors.value
          : [context.relationUiLabel(descriptor, 'inline_create_failed', '保存时创建失败')]));
        context.validationErrors.value = before;
      }
    }
    return Array.from(new Set(issues)).slice(0, 5);
  };
  const setRelationIds=(name:string,ids:number[])=>{if(!isFieldWritable(name))return;context.formData[name]=Array.from(new Set(ids.map(Number).filter(id=>Number.isFinite(id)&&id>0).map(Math.trunc)));syncFieldDirty(name);};
  const addRelationId=(name:string,option:RelationOption)=>{context.upsertRelationOption(name,option);setRelationIds(name,[...context.relationIds(name),option.id]);context.relationKeywords[name]='';};
  const quickCreateMany2manyTag=async(name:string)=>{const descriptor=context.formFields.value[name];const entry=relationEntry(descriptor);const relation=context.relationModel(name);const label=context.relationKeyword(name).trim();const inline=relationInlineCreate(descriptor);if(entry?.canCreate!==true||!relation||!label||!inline.enabled||!inline.createOnNoMatch)return;const existing=resolveRelationQuickFillOption(context.relationOptionsForField(name),label,inline.match);if(existing){addRelationId(name,existing);return;}try{const created=await createContractFormRecord({model:relation,vals:{...(entry.defaultVals||{}),[inline.nameField||'name']:label}});const id=Number(created?.id||0);if(id>0){addRelationId(name,{id:Math.trunc(id),label});await context.queryRelationOptions(name,'');}}catch(error){context.validationErrors.value=[sanitizeUiErrorMessage(error instanceof Error?error.message:error,context.relationUiLabel(descriptor,'quick_create_failed'))];}};
  const resolvePendingMany2manyTagCreates=async()=>{const issues:string[]=[];for(const [name,raw] of Object.entries(context.relationKeywords)){const keyword=String(raw||'').trim();if(!keyword||!isFieldWritable(name)||!Array.isArray(context.formData[name])||!context.relationModel(name))continue;const descriptor=context.formFields.value[name];const inline=relationInlineCreate(descriptor);if(!inline.enabled||!inline.createOnNoMatch)continue;const label=context.layoutNodes.value.find(node=>node.kind==='field'&&node.name===name)?.label||descriptor?.string||name;const match=resolveRelationQuickFillOption(context.relationOptionsForField(name),keyword,inline.match)||resolveRelationQuickFillOption(await context.queryRelationOptions(name,keyword),keyword,inline.match);if(match){addRelationId(name,match);continue;}const rows=await context.queryRelationOptions(name,keyword);if(hasAmbiguousRelationMatches(rows,keyword,inline.match)){issues.push(`${label}存在多个匹配记录，请选择具体记录`);continue;}const before=context.validationErrors.value.slice();await quickCreateMany2manyTag(name);if(context.relationKeyword(name).trim()){issues.push(...(context.validationErrors.value.length?context.validationErrors.value:[context.relationUiLabel(descriptor,'inline_create_failed','保存时创建失败')]));context.validationErrors.value=before;}}return Array.from(new Set(issues)).slice(0,5);};
  const setSelectionField=(name:string,value:string,occurrenceKey?:string)=>{if(!isFieldWritable(name,occurrenceKey))return;context.formData[name]=value||false;syncFieldDirty(name);};
  const setRelationMultiField=(name:string,target:HTMLSelectElement)=>setRelationIds(name,Array.from(target.selectedOptions).map(item=>Number(item.value)));
  const setTextField=(name:string,value:string,occurrenceKey?:string)=>{if(!isFieldWritable(name,occurrenceKey))return;context.formData[name]=value;syncFieldDirty(name);};
  const setTechnicalCompanionTextField=(name:string,value:string)=>{const descriptor=context.formFields.value[name];if(!descriptor||descriptor.readonly===true)return;context.formData[name]=value;syncFieldDirty(name);};
  const buildOnchangeValues=()=>buildOnchangeRequestPayload({fields:context.formFields.value,formData:context.formData,originalValues:context.originalValues.value,recordId:context.recordId.value,buildOne2manyValue:context.buildOne2manyCommandValue});
  // Onchange responses are derived data computed from an earlier draft, so every
  // roundtrip carries its identity: the record it was computed for, its issue
  // order, and the draft values it was computed from. A response that no longer
  // matches the draft on screen is dropped instead of being written back.
  let onchangeSequence=0;
  async function runOnchangeRoundtrip(){
    if(!context.model.value||!context.changedFieldSet.size)return;
    const changed=Array.from(context.changedFieldSet);context.changedFieldSet.clear();
    const ticket=createOnchangeRoundtripTicket({sequence:onchangeSequence+1,model:context.model.value,recordId:context.recordId.value,snapshot:buildOnchangeDraftSnapshot(Object.keys(context.formFields.value),name=>comparableFieldValue(name,context.formData[name]))});
    onchangeSequence=ticket.sequence;
    try{const response=await triggerOnchange({model:context.model.value,res_id:context.recordId.value,values:buildOnchangeValues(),changed_fields:changed,context:buildFormRequestContext(context.route.query)});const {patch:rawPatch,modifiersPatch,linePatches,warnings}=normalizeOnchangeResponse(response);
      const plan=planOnchangeApplication({ticket,latestSequence:onchangeSequence,currentRecordKey:onchangeRecordKey(context.model.value,context.recordId.value),patch:rawPatch,comparableValue:name=>comparableFieldValue(name,context.formData[name])});
      // A superseded or foreign response is dropped whole: its patch, row
      // patches, modifier overlay and warnings all describe an obsolete draft.
      if(plan.dropped)return;
      context.onchangeWarnings.value=warnings;context.onchangeLinePatches.value=linePatches;if(Object.keys(modifiersPatch).length)context.onchangeModifiersPatch.value={...context.onchangeModifiersPatch.value,...modifiersPatch};
      if(Object.keys(plan.patch).length){context.applyingOnchangePatch.value=true;Object.entries(plan.patch).forEach(([name,value])=>{if(!(name in context.formFields.value))return;const node=context.layoutNodes.value.find(item=>item.kind==='field'&&item.name===name);const normalized=normalizeOnchangeFieldPatch({descriptor:context.formFields.value[name],readonly:Boolean(node?.readonly||context.formFields.value[name]?.readonly),value});if(normalized.kind==='x2many'){context.formData[name]=normalized.value;if(normalized.fieldType==='one2many')context.initOne2manyRows(name,context.formData[name]);}else if(normalized.kind==='many2one'){context.upsertRelationOption(name,normalized.option);context.formData[name]=normalized.value;context.relationKeywords[name]=normalized.keyword||'';}else context.formData[name]=normalized.value;});context.applyingOnchangePatch.value=false;}
      if(linePatches.length){context.applyingOnchangePatch.value=true;context.applyOnchangeLinePatches(linePatches);context.applyingOnchangePatch.value=false;}}catch{/* Onchange preserves current values when the optional roundtrip fails. */}}
  const collectWritableValues=()=>{const values=context.layoutNodes.value.filter(node=>node.kind==='field'&&!node.readonly&&context.isWritableFieldVisible(node.name)).reduce<Record<string,unknown>>((output,node)=>{const value=normalizeFieldValue(node.name,context.formData[node.name]);const type=fieldType(node.descriptor);if((type==='many2many'||type==='one2many')&&Array.isArray(value)&&!value.length)return output;if(!shouldWriteFieldValue({recordId:context.recordId.value,dirty:context.dirtyFieldSet.has(node.name),value,descriptor:node.descriptor}))return output;output[node.name]=value;return output;},{});
    // Native forms legitimately use invisible companion fields (for example a
    // Binary field's `filename`) and onchange-updated technical values.  If the
    // UI explicitly changed such a field, persist it even though it has no
    // visible layout node; the native model/ACL remains the write authority.
    for(const name of context.dirtyFieldSet){if(name in values)continue;const descriptor=context.formFields.value[name];if(!descriptor||descriptor.readonly===true)continue;const value=normalizeFieldValue(name,context.formData[name]);if(!shouldWriteFieldValue({recordId:context.recordId.value,dirty:true,value,descriptor}))continue;values[name]=value;}
    const status=context.nativeStatusbar.value.field;if(context.recordId.value&&status&&context.dirtyFieldSet.has(status)&&!context.nativeStatusbar.value.readonly&&status in context.formFields.value&&!(status in values))values[status]=normalizeFieldValue(status,context.formData[status]);return values;};
  return {addRelationId,collectWritableValues,commitMany2oneInline,comparableFieldValue,inputFieldValue,isFieldWritable,markFieldChanged,normalizeFieldValue,queryMany2oneInline,quickCreateMany2manyTag,resetPendingInlineRelationCreates,resolvePendingInlineRelationCreates,resolvePendingMany2manyTagCreates,setBooleanField,setMany2oneField,setRelationIds,setRelationMultiField,setSelectionField,setTechnicalCompanionTextField,setTextField};
}
