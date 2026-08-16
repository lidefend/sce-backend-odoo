import { defineAsyncComponent } from 'vue';
import 'tdesign-vue-next/es/style/index.css';
import 'tdesign-vue-next/es/button/style/index.css';
import 'tdesign-vue-next/es/date-picker/style/index.css';
import 'tdesign-vue-next/es/input/style/index.css';
import 'tdesign-vue-next/es/select/style/index.css';
import 'tdesign-vue-next/es/tabs/style/index.css';
import 'tdesign-vue-next/es/textarea/style/index.css';
import './theme.css';
import { Button } from 'tdesign-vue-next/es/button';
import { DatePicker } from 'tdesign-vue-next/es/date-picker';
import { Input } from 'tdesign-vue-next/es/input';
import { Select } from 'tdesign-vue-next/es/select';
import { TabPanel, Tabs } from 'tdesign-vue-next/es/tabs';
import { Textarea } from 'tdesign-vue-next/es/textarea';
import type { SceneUiDriverRuntime } from '../types';

const Alert = defineAsyncComponent(async () => {
  await import('tdesign-vue-next/es/alert/style/index.css');
  return (await import('tdesign-vue-next/es/alert')).Alert;
});
const Drawer = defineAsyncComponent(async () => {
  await import('tdesign-vue-next/es/drawer/style/index.css');
  return (await import('tdesign-vue-next/es/drawer')).Drawer;
});
const Table = defineAsyncComponent(async () => {
  await import('tdesign-vue-next/es/table/style/index.css');
  return (await import('tdesign-vue-next/es/table')).Table;
});

export const tdesignRuntime: SceneUiDriverRuntime = {
  id: 'tdesign-modern',
  componentModel: 'vue',
  components: {
    alert: Alert,
    button: Button,
    drawer: Drawer,
    input: Input,
    select: Select,
    table: Table,
    date: DatePicker,
    textarea: Textarea,
    tabs: Tabs,
    'tab-panel': TabPanel,
  },
};
