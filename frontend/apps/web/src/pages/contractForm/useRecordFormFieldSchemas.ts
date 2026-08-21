/* eslint-disable @typescript-eslint/no-explicit-any, prefer-const */
import { computed, type ComputedRef, type Ref } from 'vue';
import type { FieldDescriptor } from '@sc/schema';
import { resolveContractV2ValueSource, type ContractV2NormalizedStore } from '../../app/contracts/v2';
import type { NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import type { FormSectionFieldSchema } from '../../components/template/formSection.types';
import { createFormSectionFieldSchemaBuilder } from '../../components/template/formSection.adapter';
import { resolveInputPlaceholder } from '../../components/template/placeholder.mapper';
import { resolveFieldSpanClass } from '../../components/template/fieldSpan.mapper';
import { mapDescriptorSelectionOptions, mapRelationOptions } from '../../components/template/option.mapper';
import { evaluateFieldPolicy } from '../../app/contractPolicies';
import {
  applyReadonlyFieldValues, buildNativeFieldSchemas, nativeFieldPresentation,
  resolveNativeRelationActiveActions,
  nativeNodeFieldDescriptor as nativeNodeFieldDescriptorFromNode, nativeNodeWidget, nativeNodeWidgetSemantics,
  type NativeLayoutLikeNode,
} from './nativeLayoutUtils';
import { fieldType } from './fieldUtils';
import type { LayoutNode, LowCodeFieldSize } from './types';

export function useRecordFormFieldSchemas(context: {
  v2ContractStore: Ref<ContractV2NormalizedStore|null>;
  nativeFormLayoutNodes: ComputedRef<NativeFormLayoutNode[]>; isNativeFieldVisible:(name:string,node?:NativeFormLayoutNode)=>boolean;
  isNativeLayoutNodeVisible:(node:NativeFormLayoutNode)=>boolean; runtimeState:(name:string)=>{readonly:boolean;required:boolean};
  recordId:ComputedRef<number|null>; rights:ComputedRef<{create:boolean;write:boolean}>;
  contractFieldLabel:(name:string)=>string; isContractFieldOrderEditable:ComputedRef<boolean>;
  effectiveFieldSize:(name:string)=>LowCodeFieldSize; rememberFormConfigFieldLabel:(name:string,label:string)=>void;
  fieldOrderPreviewActive:Ref<boolean>; fieldOrderDraft:Ref<string[]>; formData:Record<string,unknown>;
  isFieldVisible:(name:string)=>boolean; contractVisibleFields:ComputedRef<string[]>; coreFieldNames:ComputedRef<string[]>;
  advancedFieldNames:ComputedRef<string[]>; evaluatePolicyContext:ComputedRef<any>; runtimeFieldStates:ComputedRef<Record<string,any>>;
  validationErrors:Ref<string[]>;
  relationOptionsForField:(name:string)=>any[]; relationCreateMode:(descriptor?:FieldDescriptor)=>'none'|'quick'|'page';
  relationInlineCreate:(descriptor?:FieldDescriptor)=>{enabled:boolean;createOnNoMatch:boolean;nameField:string;match?:string};
  relationKeyword:(name:string)=>string; canOpenRelationRecordForm:(name:string,descriptor?:FieldDescriptor)=>boolean;
  relationUiLabel:(descriptor:FieldDescriptor|undefined,key:string,fallback?:string)=>string;
  inputFieldValue:(name:string)=>string; many2oneValue:(name:string)=>string;
  toDateInputValue:(value:unknown)=>string; toDatetimeInputValue:(value:unknown)=>string;
  evaluateNativeModifierValue:(value:unknown)=>boolean;
  runtimeOccurrenceState:(node:NativeFormLayoutNode)=>Record<string,unknown>;
}) {
  const nativeNodeFieldDescriptor=(node:NativeFormLayoutNode,fallback?:FieldDescriptor)=>nativeNodeFieldDescriptorFromNode(node as NativeLayoutLikeNode,fallback,context.contractFieldLabel);
  const nativeLayoutNodeToFieldNode=(node:NativeFormLayoutNode,index:number):LayoutNode|null=>{
    const name=String(node?.name||'').trim(); if(!name||!context.isNativeFieldVisible(name,node))return null;
    const source=node as Record<string,unknown>; const widgetId=String(source.widgetId||'').trim();
    const strictDescriptor=context.v2ContractStore.value?.widgetsById.get(widgetId)?.fieldDescriptor as FieldDescriptor|undefined;
    const nativeLocator=String(source.nativeLocator||source.native_locator||'').trim();
    const occurrenceIndex=Number(source.occurrenceIndex||source.occurrence_index||0);
    const isOccurrence=Boolean(nativeLocator&&Number.isInteger(occurrenceIndex)&&occurrenceIndex>0);
    const descriptor=nativeNodeFieldDescriptor(node,strictDescriptor);
    if(!descriptor||isOccurrence&&!strictDescriptor)return null;
    const state=context.runtimeOccurrenceState(node);
    const nativeRelationActiveActions=resolveNativeRelationActiveActions(source,context.evaluateNativeModifierValue);
    const occurrenceDescriptor={...descriptor,native_relation_active_actions:nativeRelationActiveActions} as FieldDescriptor;
    const resolved=evaluateFieldPolicy(null,name,{required:Boolean(descriptor.required),readonly:Boolean(descriptor.readonly)},context.evaluatePolicyContext.value);
    const presentation=nativeFieldPresentation({node:source,descriptor,resolveFieldLabel:context.contractFieldLabel,
      editable:context.isContractFieldOrderEditable.value,effectiveFieldSize:context.effectiveFieldSize});
    context.rememberFormConfigFieldLabel(name,presentation.label);
    const occurrenceKey=nativeLocator||`${name}[${occurrenceIndex>0?occurrenceIndex:index+1}]`;
    return {key:String(source.widgetId||'').trim()||`native_field:${occurrenceKey}`,kind:'field',name,label:presentation.label,
      readonly:Boolean(resolved.readonly||state.readonly||(context.recordId.value?!context.rights.value.write:!context.rights.value.create)),
      required:Boolean(state.required||resolved.required),widget:nativeNodeWidget(source),
      widgetSemantics:nativeNodeWidgetSemantics(source),spanClass:presentation.spanClass,descriptor:occurrenceDescriptor};
  };
  const v2FieldValue=(name:string)=>{const key=String(name||'').trim();if(!key||!context.v2ContractStore.value?.widgetsByFieldCode.has(key))return{found:false,value:undefined};
    const source=resolveContractV2ValueSource(context.v2ContractStore.value).values;if(!Object.prototype.hasOwnProperty.call(source,key))return{found:false,value:undefined};return{found:true,value:source[key]};};
  let buildSectionFieldSchemas:(fields:any[])=>FormSectionFieldSchema[];
  const nativeFieldSchemasForNodes=(nodes:NativeFormLayoutNode[])=>buildNativeFieldSchemas({
    nodes:nodes as NativeLayoutLikeNode[],
    mapNode:(node,index)=>nativeLayoutNodeToFieldNode(node as NativeFormLayoutNode,index),
    buildSchemas:buildSectionFieldSchemas,
    applyReadonlyValues:(schemas)=>applyReadonlyFieldValues(schemas,v2FieldValue).map((field)=>{
      const type=String(field.type||'').trim().toLowerCase();
      if (field.readonly && type==='binary') {
        const filenameField=String((field.descriptor as Record<string,unknown>|undefined)?.filename||'').trim();
        const filename=filenameField?String(context.formData[filenameField]||'').trim():'';
        if (filename) return {...field,value:filename};
      }
      if (!field.readonly || type!=='many2one') return field;
      const label=String(context.relationKeyword(field.name)||'').trim();
      const id=Number(context.formData[field.name]||0);
      if (!label||!Number.isFinite(id)||id<=0) return field;
      return {...field,value:[Math.trunc(id),label]};
    }),
    orderActive:context.isContractFieldOrderEditable.value&&context.fieldOrderPreviewActive.value,
    fieldOrder:context.fieldOrderDraft.value,
    favoriteActive:(name)=>Boolean(context.formData[name]),
    favoriteReadonly:(field)=>Boolean(field.readonly),
  });
  const strictLayoutNodes=()=>{const output:LayoutNode[]=[];const visit=(nodes:NativeFormLayoutNode[])=>nodes.forEach((node,index)=>{const type=String(node.type||(node as any).containerType||'').toLowerCase();if(type==='field'){const mapped=nativeLayoutNodeToFieldNode(node,index);if(mapped)output.push(mapped);}for(const key of ['children','pages','tabs','nodes','items'] as const){const rows=(node as any)[key];if(Array.isArray(rows))visit(rows);}});visit(context.nativeFormLayoutNodes.value);return output;};
  const layoutNodes=computed<LayoutNode[]>(strictLayoutNodes);
  buildSectionFieldSchemas=createFormSectionFieldSchemaBuilder({
    resolveFieldType:(descriptor)=>fieldType(descriptor)||'char',resolveRequired:(field)=>Boolean((field as LayoutNode).required),
    resolveSpanClass:(field)=>(field as LayoutNode).spanClass||resolveFieldSpanClass({fieldType:fieldType(field.descriptor)}),
    resolveRawValue:(name)=>context.formData[name],resolveMany2oneValue:context.many2oneValue,
    normalizeDateInputValue:context.toDateInputValue,normalizeDatetimeInputValue:context.toDatetimeInputValue,
    resolveTextInputValue:context.inputFieldValue,resolveInputPlaceholder,
    resolveHelpText:(field)=>String((field.descriptor as Record<string,unknown>|undefined)?.help||'').trim(),
    resolveErrorText:(field)=>context.validationErrors.value.find(message=>String(message||'').includes(String(field.label||'').trim()))||'',
    resolveSelectionOptions:mapDescriptorSelectionOptions,resolveRelationOptions:(name)=>mapRelationOptions(context.relationOptionsForField(name)),
    resolveRelationCreateMode:(_name,descriptor)=>((descriptor as Record<string,unknown>|undefined)?.native_relation_active_actions as Record<string,unknown>|undefined)?.create===false?'none':context.relationCreateMode(descriptor),
    resolveRelationInlineCreate:(_name,descriptor)=>{
      const configured=context.relationInlineCreate(descriptor);
      return ((descriptor as Record<string,unknown>|undefined)?.native_relation_active_actions as Record<string,unknown>|undefined)?.create===false
        ? {...configured,enabled:false,createOnNoMatch:false}
        : configured;
    },resolveRelationTextValue:context.relationKeyword,
    resolveCanOpenRelationRecord:context.canOpenRelationRecordForm,
    resolveRelationRecordOpenLabel:(_name,descriptor)=>context.relationUiLabel(descriptor,'open_existing','维护当前项'),
    resolveRelationSearchLabel:(_name,descriptor)=>context.relationUiLabel(descriptor,'search_more'),
    resolveRelationCreateLabel:(_name,descriptor)=>{const mode=((descriptor as Record<string,unknown>|undefined)?.native_relation_active_actions as Record<string,unknown>|undefined)?.create===false?'none':context.relationCreateMode(descriptor);return mode==='page'?context.relationUiLabel(descriptor,'create_and_edit'):mode==='quick'?context.relationUiLabel(descriptor,'quick_create'):'';},
    resolveRelationInlineCreateLabel:(_name,descriptor,keyword)=>{const template=context.relationUiLabel(descriptor,'inline_create');const label=String(keyword||'').trim();return template.includes('%s')?template.replace('%s',label):template||label;},
    many2oneCreateToken:'__create__',many2oneSearchToken:'__search_more__',many2oneOpenToken:'__open_record__',
  });
  return { layoutNodes, nativeFieldSchemasForNodes };
}
