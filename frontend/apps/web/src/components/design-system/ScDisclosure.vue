<template>
  <TDesignCollapse v-bind="semanticPrimitiveIdentity('ScDisclosure')" :value="expanded" :borderless="borderless" @change="onChange">
    <TDesignCollapsePanel value="content" :header="title" :disabled="disabled"><slot /></TDesignCollapsePanel>
  </TDesignCollapse>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { TDesignCollapse, TDesignCollapsePanel } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
const props=withDefaults(defineProps<{title:string;open?:boolean;disabled?:boolean;borderless?:boolean}>(),{open:false,disabled:false,borderless:true});
const emit=defineEmits<{ 'update:open':[value:boolean] }>();
const localOpen=ref(props.open); watch(()=>props.open,(value)=>{localOpen.value=value;});
const expanded=computed(() => localOpen.value ? ['content'] : []);
function onChange(value:Array<string|number>){localOpen.value=value.map(String).includes('content');emit('update:open',localOpen.value);}
</script>
