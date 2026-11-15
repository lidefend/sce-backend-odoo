import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import { bootstrapApp } from './app/init';
import { useSessionStore } from './stores/session';
import App from './App.vue';
import './styles/design-system.css';
import './styles/accessibility.css';
import './styles/product-patterns.css';
import { bootTheme, bootThemeProfile } from './styles/theme';
import { startThemeApplicationRuntime, stopThemeApplicationRuntime } from './styles/themeApplicationRuntime';
import { installStaleAssetRecovery } from './app/staleAssetRecovery';
import {
  registerIndustryRenderers,
  unregisterIndustryRenderers,
} from './extensions/industryRenderers';
import { installSessionPersistenceLifecycle } from './stores/sessionPersistence';

installStaleAssetRecovery();
registerIndustryRenderers();

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

bootTheme();
bootThemeProfile();
startThemeApplicationRuntime();

// Synchronously restore session (token, user, etc.) before mounting.
// Without this, the router guard sees token=null on first paint and
// redirects to /login, then bootstrapApp() restores the token and the
// guard redirects back — causing visible page flicker on every reload.
const session = useSessionStore();
session.restore();
const disposeSessionPersistenceLifecycle = installSessionPersistenceLifecycle({
  windowTarget: window,
  documentTarget: document,
  flush: () => {
    session.flushDurablePersist();
  },
});

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    session.flushDurablePersist();
    disposeSessionPersistenceLifecycle();
    unregisterIndustryRenderers();
    stopThemeApplicationRuntime();
  });
}

const initialRoute = router.resolve(window.location.href);
bootstrapApp({ initialRouteName: initialRoute.name, initialPath: window.location.pathname });

app.mount('#app');
