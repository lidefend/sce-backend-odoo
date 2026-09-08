<template>
  <TDesignCollapse v-bind="semanticPrimitiveIdentity('ScDisclosure')" :value="expanded" :borderless="borderless" @change="onChange">
    <TDesignCollapsePanel value="content" :disabled="disabled">
      <template #header>
        <ScButton
          type="button"
          variant="ghost"
          size="small"
          appearance="context-action"
          data-disclosure-trigger
          :data-state="localOpen ? 'expanded' : 'collapsed'"
          :aria-expanded="String(localOpen)"
          :aria-controls="contentId"
          :disabled="disabled"
          @click.stop="toggle"
        >{{ title }}</ScButton>
      </template>
      <div :id="contentId"><slot /></div>
    </TDesignCollapsePanel>
  </TDesignCollapse>
</template>
<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue';
import { TDesignCollapse, TDesignCollapsePanel } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
import ScButton from './ScButton.vue';
const props=withDefaults(defineProps<{title:string;open?:boolean;disabled?:boolean;borderless?:boolean}>(),{open:false,disabled:false,borderless:true});
const emit=defineEmits<{ 'update:open':[value:boolean] }>();
const contentId=`sc-disclosure-${useId()}`;
const localOpen=ref(props.open); watch(()=>props.open,(value)=>{localOpen.value=value;});
const expanded=computed(() => localOpen.value ? ['content'] : []);
function onChange(value:Array<string|number>){localOpen.value=value.map(String).includes('content');emit('update:open',localOpen.value);}
function toggle(){if(props.disabled)return;localOpen.value=!localOpen.value;emit('update:open',localOpen.value);}
</script>
