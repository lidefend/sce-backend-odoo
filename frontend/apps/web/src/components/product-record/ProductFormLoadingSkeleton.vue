<template>
  <section
    class="product-form-loading"
    role="status"
    aria-live="polite"
    aria-busy="true"
    :aria-label="loadingLabel"
  >
    <header class="loading-form-header" aria-hidden="true">
      <div class="loading-form-actions">
        <i />
        <i />
        <i />
      </div>
    </header>

    <section class="loading-form-body" aria-hidden="true">
      <div class="loading-form-section-heading">
        <i />
        <i />
      </div>
      <div class="loading-form-grid">
        <div v-for="index in 8" :key="`primary-${index}`" class="loading-form-field">
          <i />
          <span />
        </div>
      </div>
      <div class="loading-form-divider" />
      <div class="loading-form-section-heading loading-form-section-heading--secondary">
        <i />
      </div>
      <div class="loading-form-grid">
        <div v-for="index in 4" :key="`secondary-${index}`" class="loading-form-field">
          <i />
          <span />
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  loadingLabel?: string;
}>(), {
  loadingLabel: '正在载入表单',
});
</script>

<style scoped>
.product-form-loading {
  display: grid;
  align-self: start;
  gap: 18px;
  width: 100%;
  min-width: 0;
}

.loading-form-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  height: 38px;
  min-height: 38px;
}

.loading-form-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 3px;
}

.loading-form-actions i,
.loading-form-section-heading i,
.loading-form-field i,
.loading-form-field span {
  display: block;
  overflow: hidden;
  position: relative;
  background: linear-gradient(
    90deg,
    var(--sc-app-muted-bg) 20%,
    var(--sc-app-border) 38%,
    var(--sc-app-muted-bg) 56%
  );
  background-size: 240% 100%;
  animation: product-form-loading-shimmer 1.35s ease-in-out infinite;
}

.loading-form-actions i {
  width: 72px;
  height: 30px;
  border-radius: 8px;
}

.loading-form-actions i:last-child {
  width: 88px;
}

.loading-form-body {
  width: 100%;
  min-width: 0;
  min-height: max(560px, calc(100vh - 265px));
  padding: 22px 24px 28px;
  box-sizing: border-box;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-panel-radius);
  background: var(--sc-app-panel);
}

.loading-form-section-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.loading-form-section-heading i:first-child {
  width: 104px;
  height: 16px;
  border-radius: 5px;
}

.loading-form-section-heading i:last-child {
  width: 46px;
  height: 12px;
  border-radius: 4px;
}

.loading-form-section-heading--secondary {
  margin-bottom: 18px;
}

.loading-form-section-heading--secondary i:first-child {
  width: 86px;
}

.loading-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px 26px;
}

.loading-form-field {
  display: grid;
  gap: 9px;
}

.loading-form-field i {
  width: 76px;
  height: 12px;
  border-radius: 4px;
}

.loading-form-field span {
  width: 100%;
  height: 36px;
  border-radius: 8px;
}

.loading-form-divider {
  height: 1px;
  margin: 28px 0 22px;
  background: var(--sc-app-border);
}

@keyframes product-form-loading-shimmer {
  from {
    background-position: 100% 0;
  }

  to {
    background-position: -100% 0;
  }
}

@media (max-width: 760px) {
  .loading-form-actions i:nth-child(2) {
    display: none;
  }

  .loading-form-body {
    padding: 18px 16px 22px;
  }

  .loading-form-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-form-actions i,
  .loading-form-section-heading i,
  .loading-form-field i,
  .loading-form-field span {
    animation: none;
  }
}
</style>
