import { registerI18nLoader } from '@ui5/webcomponents-base/dist/asset-registries/i18n.js';
import { registerLocaleDataLoader } from '@ui5/webcomponents-base/dist/asset-registries/LocaleData.js';
import { setDefaultFontLoading } from '@ui5/webcomponents-base/dist/config/Fonts.js';
import webcomponentsEn from '@ui5/webcomponents/dist/generated/assets/i18n/messagebundle_en.json';
import webcomponentsZhCN from '@ui5/webcomponents/dist/generated/assets/i18n/messagebundle_zh_CN.json';
import fioriEn from '@ui5/webcomponents-fiori/dist/generated/assets/i18n/messagebundle_en.json';
import fioriZhCN from '@ui5/webcomponents-fiori/dist/generated/assets/i18n/messagebundle_zh_CN.json';
import cldrEn from '@ui5/webcomponents-localization/dist/generated/assets/cldr/en.json';
import cldrZhCN from '@ui5/webcomponents-localization/dist/generated/assets/cldr/zh_CN.json';

// Enterprise delivery cannot depend on third-party font CDNs. The scene shell
// already defines a system-font fallback; UI5 must therefore avoid its default
// remote font-face registration before any component module is evaluated.
setDefaultFontLoading(false);

type Ui5CldrData = Record<string, object | boolean | string>;

registerLocaleDataLoader('en', async () => cldrEn as unknown as Ui5CldrData);
registerLocaleDataLoader('zh_CN', async () => cldrZhCN as unknown as Ui5CldrData);
registerI18nLoader('@ui5/webcomponents', 'en', async () => webcomponentsEn);
registerI18nLoader('@ui5/webcomponents', 'zh_CN', async () => webcomponentsZhCN);
registerI18nLoader('@ui5/webcomponents-fiori', 'en', async () => fioriEn);
registerI18nLoader('@ui5/webcomponents-fiori', 'zh_CN', async () => fioriZhCN);
