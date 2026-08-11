<template>
  <component :is="iconComponent" class="sc-icon" :size="`${size}px`" data-ui-engine="tdesign-icons" aria-hidden="true" />
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue';
import {
  AddIcon,
  AppIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  BuildingIcon,
  ChartBarIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ChevronUpIcon,
  CloseIcon,
  ColumnLayoutIcon,
  FileIcon,
  FilePasteIcon,
  FolderIcon,
  HomeIcon,
  MenuFoldIcon,
  MenuUnfoldIcon,
  NotificationIcon,
  SearchIcon,
  SettingIcon,
  StarFilledIcon,
  StarIcon,
  SunnyIcon,
  ToolsIcon,
  UserIcon,
  WorkIcon,
} from './tdesignAdapter';

export type ScIconName = 'apps' | 'arrow-left' | 'arrow-right' | 'bell' | 'briefcase' | 'building' | 'chevron-down' | 'chevron-right' | 'chevron-up' | 'clipboard' | 'close' | 'columns' | 'construction' | 'contract' | 'file-text' | 'folder' | 'home' | 'menu' | 'panel-left' | 'plus' | 'project' | 'search' | 'settings' | 'star' | 'star-outline' | 'sun' | 'user';

const props = withDefaults(defineProps<{
  name: ScIconName;
  size?: 14 | 16 | 18 | 20 | 24;
}>(), { size: 20 });

const icons: Record<ScIconName, Component> = {
  apps: AppIcon,
  'arrow-left': ArrowLeftIcon,
  'arrow-right': ArrowRightIcon,
  bell: NotificationIcon,
  briefcase: WorkIcon,
  building: BuildingIcon,
  'chevron-down': ChevronDownIcon,
  'chevron-right': ChevronRightIcon,
  'chevron-up': ChevronUpIcon,
  clipboard: FilePasteIcon,
  close: CloseIcon,
  columns: ColumnLayoutIcon,
  construction: ToolsIcon,
  contract: FilePasteIcon,
  'file-text': FileIcon,
  folder: FolderIcon,
  home: HomeIcon,
  menu: MenuUnfoldIcon,
  'panel-left': MenuFoldIcon,
  plus: AddIcon,
  project: ChartBarIcon,
  search: SearchIcon,
  settings: SettingIcon,
  star: StarFilledIcon,
  'star-outline': StarIcon,
  sun: SunnyIcon,
  user: UserIcon,
};
const iconComponent = computed(() => icons[props.name]);
</script>

<style scoped>
.sc-icon { display: inline-block; flex: 0 0 auto; }
</style>
