import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import { bootstrapApp } from './app/init';
import { useSessionStore } from './stores/session';
import App from './App.vue';
import './styles/design-system.css';
import './styles/product-patterns.css';
import { bootTheme, bootThemeProfile } from './styles/theme';
import { installStaleAssetRecovery } from './app/staleAssetRecovery';

installStaleAssetRecovery();

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

bootTheme();
bootThemeProfile();

// Synchronously restore session (token, user, etc.) before mounting.
// Without this, the router guard sees token=null on first paint and
// redirects to /login, then bootstrapApp() restores the token and the
// guard redirects back — causing visible page flicker on every reload.
const session = useSessionStore();
session.restore();

bootstrapApp();

app.mount('#app');
