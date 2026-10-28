import { intentRequest } from './intents';
import { contractGapError } from '../app/contract/contractGap';

export type StageRequirements = {
  title: string;
  project: { id: number; name: string };
  stage: { value: string; label: string };
  labels: Record<'project' | 'stage' | 'required' | 'optional' | 'done' | 'pending' | 'empty' | 'back', string>;
  items: Array<{ title: string; required: boolean; done: boolean }>;
  return_path: string;
};

export function decodeStageRequirements(value: unknown, projectId: number): StageRequirements {
  const d = value as StageRequirements | undefined;
  const text = (v: unknown) => typeof v === 'string' && v.trim().length > 0;
  if (!d || !text(d.title) || d.project?.id !== projectId || !text(d.project?.name)
    || !text(d.stage?.value) || !text(d.stage?.label)
    || !['project', 'stage', 'required', 'optional', 'done', 'pending', 'empty', 'back'].every(k => text(d.labels?.[k as keyof StageRequirements['labels']]))
    || !Array.isArray(d.items) || !d.items.every(i => i && text(i.title) && typeof i.required === 'boolean' && typeof i.done === 'boolean')
    || typeof d.return_path !== 'string' || !/^\/(?!\/)[^\\\s?#]+$/.test(d.return_path)) {
    throw contractGapError({ kind: 'contract_defect', missing: 'project.stage.requirements.read', requiredDeclarationLayer: 'P1:smart_construction_core' }, 'Invalid stage requirements response');
  }
  return d;
}

export async function readProjectStageRequirements(projectId: number): Promise<StageRequirements> {
  const result = await intentRequest<unknown>({ intent: 'project.stage.requirements.read', params: { project_id: projectId } });
  return decodeStageRequirements(result, projectId);
}
