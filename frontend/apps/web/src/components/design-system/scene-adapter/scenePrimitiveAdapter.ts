import type { ScenePrimitiveAdapter } from '@sc/ui/primitive-port';
import { scSceneButtonBinding } from './buttonContract';
import { scSceneIconBinding, scSceneTableBinding } from './collectionContracts';
import { scSceneDateFieldBinding, scSceneSelectBinding } from './selectionContracts';
import { scSceneInputBinding, scSceneTextareaBinding } from './textControlContracts';

export const scenePrimitiveAdapter: ScenePrimitiveAdapter = {
  Button: scSceneButtonBinding,
  Input: scSceneInputBinding,
  Select: scSceneSelectBinding,
  DateField: scSceneDateFieldBinding,
  Textarea: scSceneTextareaBinding,
  Table: scSceneTableBinding,
  Icon: scSceneIconBinding,
};
