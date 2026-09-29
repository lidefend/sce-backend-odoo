<template>
  <ScFooter class="shell-content-footer" data-semantic-component="ProductShellContentFooter">
    <span class="shell-content-footer__text">{{ footerText }}</span>
  </ScFooter>
</template>

<script setup lang="ts">
import { PRODUCT_APP_TITLE } from '../../app/pageIdentity';
import ScFooter from '../design-system/ScFooter.vue';

const footerText = `© ${new Date().getFullYear()} ${PRODUCT_APP_TITLE}`;
</script>
