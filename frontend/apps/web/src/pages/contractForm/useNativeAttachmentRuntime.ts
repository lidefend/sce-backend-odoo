import { ref, type Ref } from 'vue';
import { deleteChatterAttachment, type ChatterTimelineEntry } from '../../api/chatter';
import { fileToBase64, uploadFile } from '../../api/files';
import { canDeleteCollaborationAttachment } from './professionalCollaborationModel';

export type PendingNativeAttachment = {
  key: string;
  name: string;
  size: number;
  file: File;
};

export type NativeAttachmentViewerLike = {
  open: (target: { id: number }, name?: string) => Promise<void> | void;
};

export function useNativeAttachmentRuntime(params: {
  model: () => string;
  recordId: () => number;
  maxBytes: () => number;
  canUpload: () => boolean;
  resolveLabel: (key: string, fallback: string) => string;
  reloadTimeline: (resId?: number, model?: string) => Promise<void>;
  viewerRef: Ref<NativeAttachmentViewerLike | null>;
  onPendingUploadFailed: (message: string) => void;
}) {
  const uploading = ref(false);
  const deletingIds = ref<number[]>([]);
  const error = ref('');
  const pendingAttachments = ref<PendingNativeAttachment[]>([]);

  function clearError() {
    error.value = '';
  }

  function clearPendingAttachments() {
    pendingAttachments.value = [];
  }

  async function onAttachmentSelected(file: File | null) {
    if (!file || !params.model() || uploading.value || !params.canUpload()) return;
    error.value = '';
    if (file.size > params.maxBytes()) {
      error.value = params.resolveLabel('size_exceeded', '文件过大');
      return;
    }
    const recordId = params.recordId();
    if (!recordId) {
      pendingAttachments.value = [
        ...pendingAttachments.value,
        {
          key: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          name: file.name,
          size: file.size,
          file,
        },
      ];
      return;
    }
    uploading.value = true;
    try {
      const { data, mimetype } = await fileToBase64(file);
      await uploadFile({
        model: params.model(),
        res_id: recordId,
        name: file.name,
        mimetype,
        data,
      });
      await params.reloadTimeline();
    } catch (err) {
      error.value = err instanceof Error ? err.message : params.resolveLabel('upload_failed', '附件上传失败');
    } finally {
      uploading.value = false;
    }
  }

  function removePendingAttachment(key: string) {
    pendingAttachments.value = pendingAttachments.value.filter((item) => item.key !== key);
  }

  async function uploadPendingAttachments(resId: number): Promise<boolean> {
    const modelName = params.model();
    if (!pendingAttachments.value.length || !modelName) return true;
    if (!params.canUpload()) return false;
    error.value = '';
    uploading.value = true;
    try {
      for (const item of pendingAttachments.value) {
        const { data, mimetype } = await fileToBase64(item.file);
        await uploadFile({
          model: modelName,
          res_id: resId,
          name: item.name,
          mimetype,
          data,
        });
      }
      pendingAttachments.value = [];
      await params.reloadTimeline(resId, modelName);
      return true;
    } catch (err) {
      error.value = err instanceof Error ? err.message : params.resolveLabel('upload_failed', '附件上传失败');
      params.onPendingUploadFailed(error.value);
      return false;
    } finally {
      uploading.value = false;
    }
  }

  async function openAttachment(att: { id?: number; name?: string; mimetype?: string; can_download?: boolean }) {
    if (!att?.id || att.can_download !== true) return;
    error.value = '';
    try {
      await params.viewerRef.value?.open({ id: Number(att.id) }, att.name);
    } catch (err) {
      error.value = err instanceof Error ? err.message : params.resolveLabel('download_failed', '附件下载失败');
    }
  }

  async function deleteAttachment(entry: ChatterTimelineEntry) {
    const attachmentId = Number(entry.attachment?.id || entry.id || 0);
    const modelName = params.model();
    const recordId = params.recordId();
    if (!modelName || !recordId || !attachmentId || !canDeleteCollaborationAttachment(entry) || deletingIds.value.includes(attachmentId)) return;
    error.value = '';
    deletingIds.value = [...deletingIds.value, attachmentId];
    try {
      await deleteChatterAttachment({ model: modelName, res_id: recordId, attachment_id: attachmentId });
      await params.reloadTimeline(recordId, modelName);
    } catch (err) {
      error.value = err instanceof Error ? err.message : params.resolveLabel('delete_failed', '附件删除失败');
    } finally {
      deletingIds.value = deletingIds.value.filter((id) => id !== attachmentId);
    }
  }

  return {
    uploading,
    deletingIds,
    error,
    pendingAttachments,
    clearError,
    clearPendingAttachments,
    onAttachmentSelected,
    removePendingAttachment,
    uploadPendingAttachments,
    openAttachment,
    deleteAttachment,
  };
}
