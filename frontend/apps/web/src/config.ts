import { isPlatformAdminEntryRuntime, resolveConfiguredDb } from './services/dbContext';
import { runtimeOdooDb, runtimeOdooDbLocked } from './services/runtimeConfig';
import { resolveEntryBasePath } from './services/entryNamespace';

const appEnv = String(import.meta.env.VITE_APP_ENV ?? 'dev').trim();
// Batch C: the entry namespace is a runtime property of the URL, not a build
// artifact. One bundle serves /t/<alias>/ and /platform-admin/.
const entryBasePath = resolveEntryBasePath();
const envDb = runtimeOdooDb;
const platformAdminDb = '';
const envDbLocked = runtimeOdooDbLocked;
const startupRootXmlid = String(import.meta.env.VITE_STARTUP_ROOT_XMLID ?? '').trim();
const appTitle = String(import.meta.env.VITE_APP_TITLE ?? '企业业务管理平台').trim();
const appBrand = {
  name: String(import.meta.env.VITE_BRAND_NAME ?? appTitle).trim(),
  subtitle: String(import.meta.env.VITE_BRAND_SUBTITLE ?? '统一业务工作平台').trim(),
  slogan: String(import.meta.env.VITE_BRAND_SLOGAN ?? '').trim(),
  productBadge: String(import.meta.env.VITE_PRODUCT_BADGE ?? '').trim(),
  kicker: String(import.meta.env.VITE_BRAND_KICKER ?? '').trim(),
  footerPrimary: String(import.meta.env.VITE_FOOTER_PRIMARY ?? '').trim(),
  footerSecondary: String(import.meta.env.VITE_FOOTER_SECONDARY ?? '').trim(),
  shellLogoText: String(import.meta.env.VITE_SHELL_LOGO_TEXT ?? 'S').trim(),
  valueLines: [
    String(import.meta.env.VITE_VALUE_LINE_1 ?? '').trim(),
    String(import.meta.env.VITE_VALUE_LINE_2 ?? '').trim(),
    String(import.meta.env.VITE_VALUE_LINE_3 ?? '').trim(),
    String(import.meta.env.VITE_VALUE_LINE_4 ?? '').trim(),
  ].filter(Boolean),
};
const isPlatformAdminEntry = isPlatformAdminEntryRuntime();
// Batch C: a physical database name is never a build artifact.  The only
// database value here can come from the runtime entry contract written by
// nginx, and it is display state only -- requests never carry it as a hint.
const pinnedDb = isPlatformAdminEntry && platformAdminDb ? platformAdminDb : envDbLocked ? envDb : '';

export const config = {
  // Batch C: the entry namespace owns the API base.  A build-time absolute base
  // would escape `/t/<alias>/` and `/platform-admin/`, so it is not accepted.
  apiBaseUrl: entryBasePath,
  entryBasePath,
  appEnv,
  tenant: import.meta.env.VITE_TENANT ?? 'default',
  featureFlags: (import.meta.env.VITE_FEATURE_FLAGS ?? '')
    .split(',')
    .map((flag: string) => flag.trim())
    .filter(Boolean),
  odooDb: pinnedDb || resolveConfiguredDb(''),
  odooDbPinned: Boolean(pinnedDb),
  platformAdminDb,
  isPlatformAdminEntry,
  startupRootXmlid,
  appTitle,
  appBrand,
};

// Batch C: no build-time database or base override is logged or consumed.  The
// entry namespace is the only routing input, so there is nothing here to dump.
