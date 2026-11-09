/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LITE_CONTRACT_PILOT?: string;
  readonly VITE_LITE_CONTRACT_ROLLOUT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare const __SC_BUILD_SHA__: string;
declare const __SC_BUILD_TIME__: string;
declare const __SC_BUILD_ENV__: string;
declare const __SC_BUILD_VERSION__: string;

declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>;
  export default component;
}
