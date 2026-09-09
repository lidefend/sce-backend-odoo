import type { BusinessConfigChangeSet, BusinessConfigChangeSetState } from '../../api/businessConfig';

export type BusinessConfigChangeSetPresentationKind = 'loading' | 'empty' | 'draft' | 'failed' | 'published';

export type BusinessConfigChangeSetPresentation = {
  kind: BusinessConfigChangeSetPresentationKind;
  title: string;
  statusLabel: string;
  statusSemantic: 'default' | 'info' | 'success' | 'warning' | 'danger';
  description: string;
  showItems: boolean;
  canValidate: boolean;
  canPreview: boolean;
  canPublish: boolean;
  canRollback: boolean;
  canDiscard: boolean;
  canRetryLoad: boolean;
};

const ACTIVE_STATE_LABELS: Record<BusinessConfigChangeSetState, string> = {
  draft: '有未发布修改',
  validating: '正在检查',
  ready: '可以发布',
  publishing: '发布中',
  published: '已发布',
  failed: '检查失败',
  discarded: '已放弃',
  superseded: '已回滚',
};

export function resolveBusinessConfigChangeSetPresentation(
  changeSet: BusinessConfigChangeSet | null,
  options: { loading?: boolean; publishing?: boolean; requestError?: string } = {},
): BusinessConfigChangeSetPresentation {
  const count = Math.max(0, Number(changeSet?.item_count || 0));
  const state = changeSet?.state;
  const requestError = String(options.requestError || '').trim();
  const failureMessage = String(changeSet?.failure_message || requestError).trim();
  const failed = state === 'failed' || Boolean(requestError);
  const published = state === 'published';
  const activeDraft = count > 0 && !published && state !== 'discarded' && state !== 'superseded';

  if (failed) {
    return {
      kind: 'failed',
      title: count ? `${count} 项配置检查失败` : '待发布变更读取失败',
      statusLabel: state === 'failed' ? ACTIVE_STATE_LABELS.failed : '读取失败',
      statusSemantic: 'danger',
      description: failureMessage || '未能读取或检查待发布变更，请重试。',
      showItems: count > 0,
      canValidate: count > 0,
      canPreview: false,
      canPublish: false,
      canRollback: false,
      canDiscard: count > 0,
      canRetryLoad: !changeSet,
    };
  }

  if (options.loading && !changeSet) {
    return {
      kind: 'loading',
      title: '正在读取待发布变更',
      statusLabel: '读取中',
      statusSemantic: 'info',
      description: '正在核对当前管理员会话中的可逆配置。',
      showItems: false,
      canValidate: false,
      canPreview: false,
      canPublish: false,
      canRollback: false,
      canDiscard: false,
      canRetryLoad: false,
    };
  }

  if (published) {
    return {
      kind: 'published',
      title: count ? `${count} 项配置已发布` : '配置已发布',
      statusLabel: ACTIVE_STATE_LABELS.published,
      statusSemantic: 'success',
      description: '该批次已经发布，可按现有权限查看结果或执行批次回滚。',
      showItems: count > 0,
      canValidate: false,
      canPreview: false,
      canPublish: false,
      canRollback: true,
      canDiscard: false,
      canRetryLoad: false,
    };
  }

  if (activeDraft) {
    const activeState = options.publishing ? 'publishing' : state || 'draft';
    return {
      kind: 'draft',
      title: `${count} 项可逆配置`,
      statusLabel: ACTIVE_STATE_LABELS[activeState],
      statusSemantic: activeState === 'ready' ? 'success' : activeState === 'validating' || activeState === 'publishing' ? 'info' : 'warning',
      description: '检查无误后可预览并发布当前可逆配置。',
      showItems: true,
      canValidate: activeState !== 'publishing',
      canPreview: activeState !== 'validating' && activeState !== 'publishing',
      canPublish: activeState !== 'validating' && activeState !== 'publishing',
      canRollback: false,
      canDiscard: activeState !== 'publishing',
      canRetryLoad: false,
    };
  }

  return {
    kind: 'empty',
    title: '当前没有未发布修改',
    statusLabel: state === 'discarded' ? ACTIVE_STATE_LABELS.discarded : state === 'superseded' ? ACTIVE_STATE_LABELS.superseded : '无待发布修改',
    statusSemantic: 'default',
    description: '表单、列表、搜索、分析和菜单的可逆修改会汇总到这里。',
    showItems: false,
    canValidate: false,
    canPreview: false,
    canPublish: false,
    canRollback: false,
    canDiscard: false,
    canRetryLoad: false,
  };
}
