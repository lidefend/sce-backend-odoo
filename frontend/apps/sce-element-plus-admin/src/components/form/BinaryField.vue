<template>
  <div class="binary-field">
    <el-upload
      :auto-upload="false"
      :show-file-list="false"
      :disabled="disabled || !recordId"
      :on-change="selectFile"
      ><el-button :disabled="disabled || !recordId" :icon="Upload"
        >上传附件</el-button
      ></el-upload
    >
    <span v-if="!recordId" class="binary-hint">保存记录后可上传</span
    ><span v-else-if="uploading" class="binary-hint">正在上传...</span>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue";
import type { UploadFile } from "element-plus";
import { ElMessage } from "element-plus";
import { Upload } from "@element-plus/icons-vue";
import { uploadFile } from "@/api/odoo";
const props = defineProps<{
  model: string;
  recordId?: number | null;
  disabled?: boolean;
}>();
const emit = defineEmits<{ uploaded: [result: Record<string, unknown>] }>();
const uploading = ref(false);
async function selectFile(file: UploadFile) {
  if (!props.recordId || !file.raw) return;
  uploading.value = true;
  try {
    const data = await base64(file.raw);
    const result = await uploadFile({
      model: props.model,
      recordId: props.recordId,
      name: file.name,
      mimetype: file.raw.type || "application/octet-stream",
      data,
    });
    ElMessage.success("附件上传成功");
    emit("uploaded", result);
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : "附件上传失败");
  } finally {
    uploading.value = false;
  }
}
function base64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () =>
      resolve(String(reader.result || "").split(",")[1] || "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
</script>
<style scoped>
.binary-field {
  display: flex;
  align-items: center;
  gap: 10px;
}
.binary-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
