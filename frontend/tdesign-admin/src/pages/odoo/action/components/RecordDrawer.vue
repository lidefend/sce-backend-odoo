<template>
  <record-presentation-shell :visible="visible" :presentation="presentation" @close="close">
    <div class="record-drawer" :class="{ 'record-drawer--page': presentation === 'page' }">
      <div class="record-toolbar">
        <div class="record-toolbar__identity">
          <h2>{{ drawerTitle }}</h2>
          <div class="record-toolbar__status">
            <field-display
              v-if="statusField && statusLabel && statusLabel !== '—'"
              :value="formValues[statusField.name]"
              :field-code="statusField.name"
              :field-label="statusField.label"
              :field-type="statusField.type"
              :config="{ selection: statusField.selection }"
            />
            <span v-if="workflowLabel" class="workflow-label">{{ workflowLabel }}</span>
          </div>
        </div>
        <div class="record-toolbar__right">
          <t-space class="record-toolbar__actions" break-line>
            <t-button
              v-for="action in businessActions"
              :key="action.key"
              :theme="action.theme"
              :variant="action.variant"
              :disabled="action.enabled === false || Boolean(actionBusyKey)"
              :title="action.reasonCode || undefined"
              :loading="actionBusyKey === action.key"
              @click="runBusinessAction(action)"
            >
              {{ action.label }}
            </t-button>
            <template v-if="mode === 'view'">
              <t-button variant="outline" :disabled="!canEdit" @click="mode = 'edit'">
                <template #icon><t-icon name="edit" /></template>
                编辑
              </t-button>
              <t-button
                v-if="activeRecordId && canDuplicate"
                variant="outline"
                :loading="duplicating"
                @click="duplicateRecord"
              >
                <template #icon><t-icon name="file-copy" /></template>复制
              </t-button>
            </template>
            <template v-else>
              <t-button variant="outline" :disabled="saving" @click="cancelEdit">取消</t-button>
              <t-button theme="primary" :loading="saving" @click="save">
                <template #icon><t-icon name="save" /></template>
                保存
              </t-button>
            </template>
            <t-popconfirm
              v-if="activeRecordId && deletePolicy.allowed"
              :content="deletePolicy.message || '确认删除当前记录？此操作不可恢复。'"
              @confirm="remove"
            >
              <t-button theme="danger" variant="outline" :disabled="!canDelete || saving">
                <template #icon><t-icon name="delete" /></template>
                删除
              </t-button>
            </t-popconfirm>
          </t-space>
          <t-button class="record-toolbar__close" shape="square" variant="text" title="关闭" @click="close">
            <template #icon><t-icon name="close" /></template>
          </t-button>
        </div>
      </div>

      <t-alert v-if="error" class="record-error" theme="error" :message="error" close @close="error = ''" />
      <suggested-action-bar
        v-if="error"
        :action="suggestedAction"
        :trace-id="errorTraceId"
        :reason-code="errorReasonCode"
        :message="error"
        :on-retry="retryLoad"
      />

      <t-dialog
        v-model:visible="conflictVisible"
        header="记录已被其他操作更新"
        width="760px"
        :confirm-btn="{
          content: '使用本地内容覆盖保存',
          theme: 'danger',
          loading: conflictResolving,
          disabled: !conflictLatestToken,
        }"
        :cancel-btn="{ content: '保留本地继续核对' }"
        @confirm="overwriteConflict"
      >
        <t-alert
          theme="warning"
          message="服务器版本已变化。请核对下列字段，再选择加载最新数据或以最新版本令牌提交本地内容。"
        />
        <t-table
          class="conflict-table"
          row-key="field"
          size="small"
          :columns="conflictColumns"
          :data="conflictRows"
          bordered
        />
        <template #footer>
          <t-space>
            <t-button variant="outline" :loading="conflictResolving" @click="reloadConflictLatest"
              >加载服务器最新值</t-button
            >
            <t-button variant="outline" @click="conflictVisible = false">保留本地继续核对</t-button>
            <t-button
              theme="danger"
              :loading="conflictResolving"
              :disabled="!conflictLatestToken"
              @click="overwriteConflict"
              >使用本地内容覆盖保存</t-button
            >
          </t-space>
        </template>
      </t-dialog>

      <t-dialog
        v-model:visible="relationCreateVisible"
        header="快速新建关联记录"
        :confirm-btn="{ content: '创建', loading: relationCreateSaving }"
        @confirm="createRelation"
      >
        <t-form :data="{ name: relationCreateName }">
          <t-form-item label="名称"><t-input v-model="relationCreateName" placeholder="请输入名称" /></t-form-item>
        </t-form>
      </t-dialog>

      <t-dialog
        v-model:visible="actionConfirmVisible"
        header="确认执行操作"
        :confirm-btn="{
          content: '确认执行',
          theme: 'danger',
          loading: Boolean(actionBusyKey),
          disabled: pendingAction?.requiresReason && !actionConfirmReason.trim(),
        }"
        @confirm="confirmBusinessAction"
      >
        <t-alert theme="warning" :message="`即将执行：${pendingAction?.label || '业务操作'}`" />
        <t-textarea
          v-model="actionConfirmReason"
          class="action-confirm-reason"
          placeholder="如后端要求，请填写操作原因（可选）"
          :autosize="{ minRows: 3, maxRows: 6 }"
        />
      </t-dialog>

      <div v-if="loading" class="record-loading">
        <t-skeleton animation="gradient" :row-col="skeletonRows" />
      </div>

      <template v-else>
        <t-tabs v-model="activeTab" class="record-tabs">
          <t-tab-panel value="fields" label="字段详情">
            <t-tabs v-if="formTabs.length > 1" v-model="activeFormTab" class="form-notebook">
              <t-tab-panel v-for="tab in formTabs" :key="tab.key" :value="tab.key" :label="tab.label" />
            </t-tabs>
            <section v-for="section in visibleSections" :key="section.key" class="form-section">
              <div class="form-section__heading">
                <h3>{{ section.label }}</h3>
                <span>{{ section.fields.length }} 项</span>
              </div>
              <div class="form-grid" :class="{ 'form-grid--single': section.columns === 1 }">
                <div
                  v-for="field in section.fields.filter((item) => !fieldRuntimeState(item).invisible)"
                  :key="field.name"
                  class="form-field"
                  :class="{
                    'form-field--wide':
                      field.type === 'text' ||
                      field.type === 'html' ||
                      field.type === 'one2many' ||
                      field.type === 'many2many',
                  }"
                >
                  <label :for="`field-${field.name}`">
                    {{ field.label }}
                    <span v-if="fieldRuntimeState(field).required" class="required-mark">*</span>
                  </label>

                  <div v-if="mode === 'view' || fieldRuntimeState(field).readonly" class="field-value">
                    <field-display
                      :value="formValues[field.name]"
                      :field-code="field.name"
                      :field-label="field.label"
                      :field-type="field.type"
                      :config="{ selection: field.selection }"
                      :relation-options="relationOptionMap[field.name] || []"
                    />
                  </div>

                  <template v-else>
                    <t-textarea
                      v-if="field.type === 'text' || field.type === 'html'"
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      :autosize="{ minRows: 3, maxRows: 8 }"
                      :placeholder="`请输入${field.label}`"
                    />
                    <t-input-number
                      v-else-if="isNumberField(field)"
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      :decimal-places="field.type === 'integer' ? 0 : undefined"
                      theme="normal"
                      :placeholder="`请输入${field.label}`"
                      @change="onFieldChange(field.name)"
                    />
                    <t-switch v-else-if="field.type === 'boolean'" v-model="formValues[field.name]" />
                    <t-select
                      v-else-if="field.type === 'many2many'"
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      multiple
                      clearable
                      filterable
                      :loading="relationLoading[relationOptionKey(field)]"
                      :options="relationOptionMap[field.name] || []"
                      :placeholder="`请选择${field.label}`"
                      @focus="loadRelationOptions(field)"
                      @search="(value: string) => loadRelationOptions(field, value)"
                      @change="onFieldChange(field.name)"
                    />
                    <div v-else-if="field.type === 'one2many'" class="o2m-editor">
                      <div class="o2m-editor__toolbar">
                        <span>{{ visibleOne2manyRows(field.name).length }} 条明细</span>
                        <t-button size="small" variant="outline" @click="addOne2manyRow(field)">
                          <template #icon><t-icon name="add" /></template>
                          添加明细
                        </t-button>
                      </div>
                      <div v-if="one2manyColumns(field).length" class="o2m-editor__table">
                        <div class="o2m-editor__header" :style="one2manyGridStyle(field)">
                          <span v-for="column in one2manyColumns(field)" :key="column.name">{{ column.label }}</span>
                          <span>操作</span>
                        </div>
                        <div
                          v-for="row in visibleOne2manyRows(field.name)"
                          :key="row.key"
                          class="o2m-editor__row"
                          :style="one2manyGridStyle(field)"
                        >
                          <template v-for="column in one2manyColumns(field)" :key="`${row.key}-${column.name}`">
                            <t-select
                              v-if="column.type === 'many2one' || column.type === 'many2many'"
                              :model-value="row.values[column.name]"
                              :options="relationOptionMap[`${field.name}.${column.name}`] || []"
                              :multiple="column.type === 'many2many'"
                              :loading="relationLoading[`${field.name}.${column.name}`]"
                              :disabled="one2manyFieldRuntimeState(field, row, column).readonly"
                              filterable
                              clearable
                              @focus="loadOne2manyRelationOptions(field, row, column)"
                              @search="(value: string) => loadOne2manyRelationOptions(field, row, column, value)"
                              @change="(value: unknown) => setOne2manyRowField(field, row.key, column, value)"
                            />
                            <t-switch
                              v-else-if="column.type === 'boolean'"
                              :model-value="Boolean(row.values[column.name])"
                              :disabled="one2manyFieldRuntimeState(field, row, column).readonly"
                              @update:model-value="
                                (value: boolean) => setOne2manyRowField(field, row.key, column, value)
                              "
                            />
                            <t-select
                              v-else-if="column.type === 'selection'"
                              :model-value="row.values[column.name]"
                              :options="selectionOptions(column)"
                              :disabled="one2manyFieldRuntimeState(field, row, column).readonly"
                              clearable
                              @update:model-value="
                                (value: unknown) => setOne2manyRowField(field, row.key, column, value)
                              "
                            />
                            <t-input-number
                              v-else-if="isNumberField(column)"
                              :model-value="toOptionalNumber(row.values[column.name])"
                              :decimal-places="column.type === 'integer' ? 0 : undefined"
                              :disabled="one2manyFieldRuntimeState(field, row, column).readonly"
                              @update:model-value="
                                (value: unknown) => setOne2manyRowField(field, row.key, column, value)
                              "
                            />
                            <t-date-picker
                              v-else-if="column.type === 'date'"
                              :model-value="String(row.values[column.name] || '')"
                              :disabled="one2manyFieldRuntimeState(field, row, column).readonly"
                              clearable
                              format="YYYY-MM-DD"
                              value-type="YYYY-MM-DD"
                              @update:model-value="
                                (value: unknown) => setOne2manyRowField(field, row.key, column, value)
                              "
                            />
                            <t-input
                              v-else
                              :model-value="one2manyCellValue(row.values[column.name])"
                              :disabled="one2manyFieldRuntimeState(field, row, column).readonly"
                              :placeholder="column.label"
                              @update:model-value="
                                (value: string) => setOne2manyRowField(field, row.key, column, value)
                              "
                            />
                          </template>
                          <t-button
                            theme="danger"
                            variant="text"
                            size="small"
                            @click="removeOne2manyRow(field.name, row.key)"
                          >
                            移除
                          </t-button>
                        </div>
                      </div>
                      <t-empty v-else size="small" description="后端未返回该明细的可编辑列" />
                      <div v-if="removedOne2manyRows(field.name).length" class="o2m-editor__removed">
                        <span>已移除 {{ removedOne2manyRows(field.name).length }} 条明细</span>
                        <t-button
                          v-for="row in removedOne2manyRows(field.name)"
                          :key="`restore-${row.key}`"
                          size="small"
                          variant="text"
                          @click="restoreOne2manyRow(field.name, row.key)"
                          >撤销移除</t-button
                        >
                      </div>
                    </div>
                    <t-select
                      v-else-if="field.type === 'selection'"
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      clearable
                      :options="selectionOptions(field)"
                      :placeholder="`请选择${field.label}`"
                      @change="onFieldChange(field.name)"
                    />
                    <t-select
                      v-else-if="field.type === 'many2one'"
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      clearable
                      filterable
                      :loading="relationLoading[relationOptionKey(field)]"
                      :options="relationOptionMap[field.name] || []"
                      :placeholder="`请选择${field.label}`"
                      @focus="loadRelationOptions(field)"
                      @search="(value: string) => loadRelationOptions(field, value)"
                      @change="onFieldChange(field.name)"
                    />
                    <t-date-picker
                      v-else-if="field.type === 'date'"
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      clearable
                      format="YYYY-MM-DD"
                      value-type="YYYY-MM-DD"
                      @change="onFieldChange(field.name)"
                    />
                    <t-date-picker
                      v-else-if="field.type === 'datetime'"
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      clearable
                      enable-time-picker
                      format="YYYY-MM-DD HH:mm:ss"
                      value-type="YYYY-MM-DD HH:mm:ss"
                      @change="onFieldChange(field.name)"
                    />
                    <t-input
                      v-else
                      :id="`field-${field.name}`"
                      v-model="formValues[field.name]"
                      :placeholder="`请输入${field.label}`"
                    />

                    <div v-if="field.type === 'many2one' || field.type === 'many2many'" class="relation-actions">
                      <t-button
                        v-if="relationCanCreate(field)"
                        size="small"
                        variant="text"
                        @click="quickCreateRelation(field)"
                        >快速新建</t-button
                      >
                      <t-button
                        v-if="relationCanOpen(field) && selectedRelationId(field)"
                        size="small"
                        variant="text"
                        @click="openRelation(field)"
                        >打开关联</t-button
                      >
                    </div>
                  </template>

                  <p v-if="field.help" class="field-help">{{ field.help }}</p>
                </div>
              </div>
            </section>

            <t-empty v-if="!sections.length" description="当前表单 contract 未返回可见字段" />
          </t-tab-panel>
          <t-tab-panel v-if="activeRecordId" value="collaboration" label="协作与审计">
            <section class="followers-panel">
              <div class="collaboration-heading">
                <div>
                  <h3>关注者</h3>
                  <p>关注当前记录并接收业务动态。</p>
                </div>
                <t-select
                  v-model="newFollowerPartnerId"
                  :options="followerUserOptions"
                  filterable
                  remote
                  clearable
                  placeholder="添加关注者"
                  :on-search="searchFollowerUsers"
                  @change="addFollower"
                />
              </div>
              <t-space break-line
                ><t-tag
                  v-for="follower in followers"
                  :key="Number(follower.id)"
                  closable
                  variant="light"
                  @close="removeFollower(Number(follower.id))"
                  >{{ followerName(follower) }}</t-tag
                ><span v-if="!followers.length" class="empty-copy">暂无关注者</span></t-space
              >
            </section>
            <div class="collaboration-panel">
              <div class="collaboration-compose">
                <t-radio-group v-model="messageMode" variant="default-filled">
                  <t-radio-button value="message">消息</t-radio-button>
                  <t-radio-button value="note">内部备注</t-radio-button>
                  <t-radio-button value="activity">计划活动</t-radio-button>
                </t-radio-group>
                <template v-if="messageMode === 'activity'">
                  <div class="activity-compose-grid">
                    <t-input v-model="activitySummary" placeholder="填写计划事项" />
                    <t-date-picker
                      v-model="activityDeadline"
                      clearable
                      format="YYYY-MM-DD"
                      value-type="YYYY-MM-DD"
                      placeholder="截止日期"
                    />
                    <t-select
                      v-model="activityAssigneeId"
                      clearable
                      filterable
                      :loading="collaborationUsersLoading"
                      :options="collaborationUserOptions"
                      placeholder="负责人（默认当前用户）"
                      @search="loadCollaborationUsers"
                    />
                  </div>
                  <t-textarea
                    v-model="activityNote"
                    :autosize="{ minRows: 2, maxRows: 5 }"
                    placeholder="补充办理要求或备注"
                  />
                </template>
                <template v-else>
                  <t-select
                    v-model="mentionUserIds"
                    class="collaboration-mentions"
                    clearable
                    filterable
                    multiple
                    :loading="collaborationUsersLoading"
                    :options="collaborationUserOptions"
                    placeholder="提醒对象（可多选）"
                    @search="loadCollaborationUsers"
                  />
                  <t-textarea
                    v-model="messageDraft"
                    :autosize="{ minRows: 3, maxRows: 6 }"
                    placeholder="写下消息或备注"
                  />
                </template>
                <div class="collaboration-compose__actions">
                  <t-button
                    theme="primary"
                    :loading="messageSending"
                    :disabled="messageMode === 'activity' ? !activitySummary.trim() : !messageDraft.trim()"
                    @click="sendMessage"
                    >{{ messageMode === 'activity' ? '创建活动' : '发送' }}</t-button
                  >
                </div>
              </div>
              <div class="attachment-toolbar">
                <input ref="attachmentInput" class="attachment-input" type="file" @change="onAttachmentSelected" />
                <t-button variant="outline" :loading="attachmentUploading" @click="attachmentInput?.click()">
                  <template #icon><t-icon name="upload" /></template>
                  上传附件
                </t-button>
                <span>附件会保存到当前业务记录的协作时间线。</span>
              </div>
              <div class="collaboration-heading">
                <h3>消息、活动与审计</h3>
                <t-button variant="text" :loading="chatterLoading" @click="loadChatter">刷新</t-button>
              </div>
              <section v-if="approvalHistory.length || nextApproval" class="approval-panel">
                <div class="collaboration-heading">
                  <h3>审批流转</h3>
                  <span v-if="nextApproval">下一节点：{{ nextApproval }}</span>
                </div>
                <t-timeline v-if="approvalHistory.length">
                  <t-timeline-item
                    v-for="item in approvalHistory"
                    :key="item.key"
                    :label="item.date"
                    :dot-color="item.color"
                  >
                    <strong>{{ item.label }}</strong>
                    <p>
                      {{ item.actor }}<span v-if="item.reason"> · {{ item.reason }}</span>
                    </p>
                  </t-timeline-item>
                </t-timeline>
                <t-empty v-else description="暂无审批历史" />
              </section>
              <div v-if="chatterLoading && !chatterItems.length" class="chatter-loading">
                <t-skeleton
                  animation="gradient"
                  :row-col="[
                    [{ type: 'rect', width: '100%', height: '72px' }],
                    { type: 'rect', width: '100%', height: '72px' },
                  ]"
                />
              </div>
              <t-empty v-else-if="!chatterItems.length" description="暂无协作消息或审计记录" />
              <div v-else class="chatter-list">
                <article v-for="item in chatterItems" :key="item.key" class="chatter-item">
                  <div class="chatter-item__meta">
                    <strong>{{ item.title || item.typeLabel || item.type }}</strong
                    ><span>{{ item.at || item.meta || '' }}</span>
                  </div>
                  <p>{{ item.body || '—' }}</p>
                  <div v-if="item.activity" class="activity-meta">
                    <span v-if="item.activity.assignee_name">负责人：{{ item.activity.assignee_name }}</span>
                    <span v-if="item.activity.deadline">截止：{{ item.activity.deadline }}</span>
                    <t-space v-if="activityEntryId(item)" size="small">
                      <t-button
                        v-if="item.activity.can_complete"
                        size="small"
                        theme="success"
                        variant="outline"
                        :loading="activityBusyIds.includes(activityEntryId(item))"
                        @click="updateActivity(item, 'done')"
                        >完成</t-button
                      >
                      <t-button
                        v-if="item.activity.can_cancel"
                        size="small"
                        theme="danger"
                        variant="text"
                        :loading="activityBusyIds.includes(activityEntryId(item))"
                        @click="updateActivity(item, 'cancel')"
                        >取消</t-button
                      >
                    </t-space>
                  </div>
                  <t-link
                    v-if="item.attachment?.id"
                    class="attachment-link"
                    theme="primary"
                    :loading="downloadBusyId === item.attachment.id"
                    @click="downloadAttachment(item.attachment)"
                  >
                    <template #prefix-icon><t-icon name="file" /></template>{{ item.attachment.name || '下载附件' }}
                  </t-link>
                </article>
              </div>
            </div>
          </t-tab-panel>
        </t-tabs>
      </template>
    </div>
  </record-presentation-shell>
</template>
<script setup lang="ts">
import { DialogPlugin, MessagePlugin } from 'tdesign-vue-next';
import { computed, onBeforeUnmount, onMounted, reactive, ref, toRaw, watch } from 'vue';
import { onBeforeRouteLeave, useRouter } from 'vue-router';

import type { ChatterTimelineEntry, CollaborationUserOption } from '@/api/odoo';
import {
  addRecordFollower,
  createRecord,
  deleteRecords,
  downloadFile,
  executeButton,
  fetchChatterTimeline,
  intent,
  listRecordFollowers,
  OdooApiError,
  postChatterMessage,
  relationOptions,
  removeRecordFollower,
  scheduleChatterActivity,
  searchCollaborationUsers,
  triggerOnchange,
  updateChatterActivity,
  updateRecord,
  uploadFile,
} from '@/api/odoo';
import SuggestedActionBar from '@/components/result/SuggestedActionBar.vue';
import type { NormalizedContractStore } from '@/runtime/contract';
import { createNormalizedContractStore, loadFormContract } from '@/runtime/contract';
import { isNumericFieldType, normalizeFieldType } from '@/runtime/fieldType';

import { resolveRuntimeDomain, runtimeFieldState } from '../modifier';
import FieldDisplay from './FieldDisplay.vue';
import RecordPresentationShell from './RecordPresentationShell.vue';

type Dict = Record<string, any>;
type DrawerMode = 'view' | 'edit' | 'create';
interface Option {
  label: string;
  value: string | number;
}
interface SkeletonRowColObj {
  type?: 'text' | 'circle' | 'rect';
  width?: string;
  height?: string;
  marginLeft?: string;
}
type SkeletonRowCol = Array<number | SkeletonRowColObj | SkeletonRowColObj[]>;
interface FormField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  readonly: boolean;
  help: string;
  selection: unknown[];
  relation: string;
  domain: unknown[];
  config?: Dict;
}
interface One2ManyRow {
  key: string;
  id?: number;
  values: Dict;
  originalValues: Dict;
  isNew?: boolean;
  removed?: boolean;
}
interface ConflictRow {
  field: string;
  label: string;
  serverValue: string;
  localValue: string;
}
interface FormSection {
  key: string;
  label: string;
  columns: number;
  fields: FormField[];
  tabKey?: string;
  tabLabel?: string;
}

const props = defineProps<{
  visible: boolean;
  model: string;
  actionId?: number;
  menuId?: number;
  recordId?: number | null;
  initialMode?: DrawerMode;
  title?: string;
  presentation?: 'drawer' | 'page';
}>();

const emit = defineEmits<{
  'update:visible': [value: boolean];
  saved: [recordId: number];
  deleted: [recordId: number];
}>();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const duplicating = ref(false);
const error = ref('');
const errorReasonCode = ref('');
const errorTraceId = ref('');
const suggestedAction = ref('');
const contract = ref<Dict>({});
const normalizedStore = ref<NormalizedContractStore | null>(null);
const mode = ref<DrawerMode>('view');
const activeRecordId = ref<number | null>(null);
const formValues = reactive<Dict>({});
const originalValues = ref<Dict>({});
const recordVersionToken = ref('');
const conflictVisible = ref(false);
const conflictResolving = ref(false);
const conflictLatestToken = ref('');
const conflictPendingValues = ref<Dict>({});
const conflictRows = ref<ConflictRow[]>([]);
const conflictColumns = [
  { colKey: 'label', title: '字段', width: 180 },
  { colKey: 'serverValue', title: '服务器最新值', ellipsis: true },
  { colKey: 'localValue', title: '本地待保存值', ellipsis: true },
];
const relationOptionMap = reactive<Record<string, Option[]>>({});
const relationLoading = reactive<Record<string, boolean>>({});
const relationCreateVisible = ref(false);
const relationCreateSaving = ref(false);
const relationCreateName = ref('');
const relationCreateField = ref<FormField | null>(null);
const activeTab = ref('fields');
const activeFormTab = ref('');
const chatterItems = ref<ChatterTimelineEntry[]>([]);
const chatterLoading = ref(false);
const messageDraft = ref('');
const messageMode = ref<'message' | 'note' | 'activity'>('message');
const messageSending = ref(false);
const activitySummary = ref('');
const activityDeadline = ref('');
const activityNote = ref('');
const activityAssigneeId = ref<number | undefined>();
const activityBusyIds = ref<number[]>([]);
const collaborationUsers = ref<CollaborationUserOption[]>([]);
const followers = ref<Dict[]>([]);
const followerUsers = ref<CollaborationUserOption[]>([]);
const newFollowerPartnerId = ref<number>();
const collaborationUsersLoading = ref(false);
const mentionUserIds = ref<number[]>([]);
const actionBusyKey = ref('');
const actionConfirmVisible = ref(false);
const actionConfirmReason = ref('');
const pendingAction = ref<(typeof businessActions.value)[number] | null>(null);
const attachmentInput = ref<HTMLInputElement | null>(null);
const attachmentUploading = ref(false);
const downloadBusyId = ref<number | null>(null);
const onchangeSequence = ref(0);
const onchangeModifierPatch = reactive<Record<string, Dict>>({});
const draftHydrated = ref(false);
let draftSaveTimer: ReturnType<typeof setTimeout> | undefined;
const skeletonRows: SkeletonRowCol = [
  [
    { type: 'text', width: '28%', height: '20px' },
    { type: 'text', width: '18%', height: '20px', marginLeft: 'auto' },
  ],
  [
    { type: 'rect', width: '48%', height: '38px' },
    { type: 'rect', width: '48%', height: '38px', marginLeft: '4%' },
  ],
  [
    { type: 'rect', width: '48%', height: '38px' },
    { type: 'rect', width: '48%', height: '38px', marginLeft: '4%' },
  ],
  [{ type: 'rect', width: '100%', height: '96px' }],
];

const drawerTitle = computed(() => {
  const subject = props.title || '记录';
  if (mode.value === 'create') return `新建${subject}`;
  if (mode.value === 'edit') return `编辑${subject}`;
  return `${subject}详情`;
});

const sections = computed(() => parseSections(contract.value));
function fieldRuntimeState(field: FormField) {
  const config = field.config || {};
  const node = (config.node || {}) as Dict;
  const info = (config.fieldInfo || config.field_info || {}) as Dict;
  const modifiers = {
    ...((info.modifiers || {}) as Dict),
    ...((node.modifiers || {}) as Dict),
  };
  const dynamic = runtimeFieldState(modifiers, onchangeModifierPatch[field.name] || {}, formValues);
  const hasDynamicInvisible =
    modifiers.invisible !== undefined || onchangeModifierPatch[field.name]?.invisible !== undefined;
  const hasDynamicReadonly =
    modifiers.readonly !== undefined || onchangeModifierPatch[field.name]?.readonly !== undefined;
  const hasDynamicRequired =
    modifiers.required !== undefined || onchangeModifierPatch[field.name]?.required !== undefined;
  return {
    invisible: dynamic.invisible || (!hasDynamicInvisible && field.config?.initialInvisible === true),
    readonly: (hasDynamicReadonly ? field.config?.staticReadonly === true : field.readonly) || dynamic.readonly,
    required: (hasDynamicRequired ? field.config?.staticRequired === true : field.required) || dynamic.required,
  };
}
const formTabs = computed(() => {
  const seen = new Set<string>();
  return sections.value.flatMap((section) => {
    if (!section.tabKey || seen.has(section.tabKey)) return [];
    seen.add(section.tabKey);
    return [{ key: section.tabKey, label: section.tabLabel || '明细' }];
  });
});
const visibleSections = computed(() => {
  if (formTabs.value.length <= 1) return sections.value;
  const selected = activeFormTab.value || formTabs.value[0]?.key || '';
  return sections.value.filter((section) => !section.tabKey || section.tabKey === selected);
});
const businessActions = computed(() => {
  const source = (contract.value.actionContract || contract.value.action_contract || {}) as Dict;
  const raw = [
    ...(Array.isArray(source.buttons) ? source.buttons : []),
    ...(Array.isArray(source.actions) ? source.actions : []),
    ...(Array.isArray(source.actionRuleList) ? source.actionRuleList : []),
    ...(Array.isArray((contract.value.runtimeContract as Dict | undefined)?.buttons)
      ? ((contract.value.runtimeContract as Dict).buttons as unknown[])
      : []),
  ];
  const seen = new Set<string>();
  return raw.flatMap((item: unknown) => {
    if (!item || typeof item !== 'object') return [];
    const row = item as Dict;
    const key = String(row.key || row.name || row.button || row.method || '').trim();
    if (!key || seen.has(key)) return [];
    const normalizedKey = key.toLowerCase();
    const intentName = String(row.intent || row.backend_intent || '')
      .trim()
      .toLowerCase();
    const sourceChannel = String(row.sourceChannel || row.source_channel || '')
      .trim()
      .toLowerCase();
    const visibleProfiles = Array.isArray(row.visibleProfiles)
      ? row.visibleProfiles.map(String)
      : Array.isArray(row.visible_profiles)
        ? row.visible_profiles.map(String)
        : [];
    const currentProfile = mode.value === 'view' ? 'readonly' : mode.value;
    if (visibleProfiles.length && !visibleProfiles.includes(currentProfile)) return [];
    if (normalizedKey === 'form.save' || sourceChannel === 'platform_form_action' || intentName === 'ui.local_mode') {
      return [];
    }
    if (!actionAllowedByRecordRights(row)) return [];
    seen.add(key);
    const semantic = String(row.semantic || row.type || row.presentation?.tier || '').toLowerCase();
    const visible = actionIsVisible(row);
    const buttonStatus = actionButtonStatus(row);
    if (buttonStatus?.visible === false || row.allowed === false) return [];
    return [
      {
        key,
        label: String(row.label || row.string || row.title || key),
        theme:
          semantic.includes('danger') || semantic.includes('cancel')
            ? 'danger'
            : semantic.includes('primary') || semantic.includes('submit')
              ? 'primary'
              : 'default',
        variant: semantic.includes('primary') ? 'base' : 'outline',
        enabled:
          row.enabled !== false &&
          row.invisible !== true &&
          row.disabled !== true &&
          visible &&
          buttonStatus?.disabled !== true &&
          buttonStatus?.allowed !== false,
        reasonCode: String(buttonStatus?.reasonCode || row.reason_code || row.reasonCode || '').trim(),
        requiresReason:
          row.requires_reason === true ||
          row.requiresReason === true ||
          row.actionSafety?.requires_reason === true ||
          row.action_safety?.requires_reason === true ||
          /reject|驳回|拒绝/.test(String(row.semantic || row.label || key).toLowerCase()),
        intent: String(row.intent || row.backend_intent || '').trim(),
        params: (row.params && typeof row.params === 'object' ? row.params : {}) as Dict,
        button: (row.button && typeof row.button === 'object'
          ? row.button
          : { name: String(row.name || row.method || key), type: String(row.type || 'object') }) as Record<
          string,
          unknown
        >,
      },
    ] as const;
  });
});

function actionButtonStatus(row: Dict) {
  const key = String(row.key || row.name || row.button || row.method || '').trim();
  const identity = String(row.backendIdentity || row.backend_identity || '').trim();
  const indexed =
    normalizedStore.value?.buttonStatusByKey.get(key) ||
    normalizedStore.value?.buttonStatusByKey.get(`btn.${key}`) ||
    (identity ? normalizedStore.value?.buttonStatusByKey.get(identity) : undefined);
  if (indexed) return indexed as Dict;
  const status = (contract.value.statusContract || contract.value.status_contract || {}) as Dict;
  const statuses = Array.isArray(status.buttonStatus)
    ? status.buttonStatus
    : Array.isArray(status.button_status)
      ? status.button_status
      : [];
  const backendIdentity = String(row.backendIdentity || row.backend_identity || '').trim();
  return statuses.find((item: Dict) => {
    const statusKey = String(item.btnId || item.btn_id || item.buttonId || item.button_id || item.key || '').trim();
    const statusIdentity = String(item.backendIdentity || item.backend_identity || '').trim();
    return (
      statusKey === key || statusKey === `btn.${key}` || Boolean(backendIdentity && statusIdentity === backendIdentity)
    );
  }) as Dict | undefined;
}

function actionAllowedByRecordRights(row: Dict) {
  const rights = (normalizedStore.value?.effectiveRights || effectiveRecordRights(contract.value)) as Dict;
  const writeAllowed = rights.write !== false;
  if (writeAllowed) return true;
  const intentName = String(row.intent || row.backend_intent || '')
    .trim()
    .toLowerCase();
  const key = String(row.key || row.name || row.method || '')
    .trim()
    .toLowerCase();
  const kind = String(row.kind || row.type || row.triggerType || row.trigger_type || '')
    .trim()
    .toLowerCase();
  const mutation = row.mutation === true || row.mutation_required === true || row.actionSafety?.mutation === true;
  const readOnlyAction =
    intentName === 'open' || intentName.startsWith('open_') || kind === 'open' || key.startsWith('open_');
  if (readOnlyAction && !mutation) return true;
  return false;
}

function actionRequiresConfirmation(action: (typeof businessActions.value)[number]) {
  const safety = action.button as Dict;
  return (
    action.theme === 'danger' ||
    safety.confirm === true ||
    safety.confirm_required === true ||
    safety.confirmation === true
  );
}

function actionIsVisible(row: Dict) {
  const visible = (row.visible || row.constraints?.visible || {}) as Dict;
  if (visible.invisible === true) return false;
  const attrs = (visible.attrs || {}) as Dict;
  const expression = attrs.invisible || visible.modifier?.invisible;
  if (!expression || typeof expression !== 'object') return true;
  if (Array.isArray(expression) || (expression as Dict).kind || (expression as Dict).parsed) {
    return !runtimeFieldState({ invisible: expression }, {}, formValues).invisible;
  }
  const field = String(expression.field || '').trim();
  const operator = String(expression.operator || '')
    .trim()
    .toLowerCase();
  if (!field || !operator) return true;
  const actual = formValues[field];
  const expected = expression.value;
  const left = Array.isArray(actual) ? actual[0] : actual;
  const values = Array.isArray(expected) ? expected.map(String) : [String(expected ?? '')];
  if (operator === '=' || operator === '==') return String(left ?? '') !== values[0];
  if (operator === '!=' || operator === '<>') return String(left ?? '') === values[0];
  if (operator === 'in') return !values.includes(String(left ?? ''));
  if (operator === 'not in') return values.includes(String(left ?? ''));
  return true;
}
const workflow = computed(
  () =>
    (contract.value.workflowContract ||
      (contract.value.runtimeContract as Dict | undefined)?.workflowContract ||
      {}) as Dict,
);
const workflowLabel = computed(() => {
  const value = String(workflow.value.businessPhase || workflow.value.approvalPhase || '');
  const labels: Record<string, string> = {
    draft: '草稿',
    submitted: '已提交',
    under_review: '审批中',
    approved: '已批准',
    effective: '执行中',
    done: '已完成',
    cancelled: '已取消',
  };
  return labels[value] || '';
});
const nextApproval = computed(() =>
  String(
    workflow.value.nextNode ||
      workflow.value.next_node ||
      workflow.value.nextApproval ||
      workflow.value.next_approval ||
      '',
  ),
);
const approvalHistory = computed(() => {
  const raw = workflow.value.history || workflow.value.approvalHistory || workflow.value.approval_history || [];
  return (Array.isArray(raw) ? raw : []).map((item: Dict, index) => ({
    key: String(item.id || item.key || index),
    date: String(item.date || item.at || item.created_at || ''),
    label: String(item.label || item.action_label || item.state_label || item.state || '审批动作'),
    actor: String(item.actor_name || item.user_name || item.actor || ''),
    reason: String(item.reason || item.reject_reason || item.note || ''),
    color: /reject|驳回|拒绝/i.test(String(item.state || item.action || item.label || '')) ? 'red' : 'blue',
  }));
});
const statusField = computed(() =>
  sections.value
    .flatMap((item) => item.fields)
    .find((item) => /(?:^|[._-])(?:state|status|stage|approval_state|workflow_state)(?:[._-]|$)/.test(item.name)),
);
const statusLabel = computed(() =>
  statusField.value ? displayValue(formValues[statusField.value.name], statusField.value) : '',
);
const canEdit = computed(() => {
  if (mode.value === 'create') return true;
  const rights = modelRights(contract.value);
  const recordRights = effectiveRecordRights(contract.value);
  if (rights.write === false || recordRights.write === false) return false;
  if (workflow.value.editability === 'readonly') return false;
  return sections.value.some((section) => section.fields.some((field) => !field.readonly));
});
const deletePolicy = computed(() => ((contract.value.actionContract as Dict | undefined)?.deletePolicy || {}) as Dict);
const canDelete = computed(() => {
  if (!deletePolicy.value.allowed || !activeRecordId.value) return false;
  const allowedStates = Array.isArray(deletePolicy.value.allowed_states)
    ? deletePolicy.value.allowed_states
    : Array.isArray(deletePolicy.value.allowedStates)
      ? deletePolicy.value.allowedStates
      : [];
  return !allowedStates.length || allowedStates.map(String).includes(String(formValues.state || ''));
});
const canDuplicate = computed(() => modelRights(contract.value).duplicate === true && canCreate.value);
const canCreate = computed(() => modelRights(contract.value).create === true);
const followerUserOptions = computed(() =>
  followerUsers.value
    .filter((user) => user.partner_id)
    .map((user) => ({ value: Number(user.partner_id), label: user.partner_name || user.name })),
);
const collaborationUserOptions = computed(() =>
  collaborationUsers.value.map((user) => ({
    value: user.id,
    label: [user.name, user.login && user.login !== user.name ? user.login : ''].filter(Boolean).join(' · '),
  })),
);

function relationEntry(field: FormField) {
  const config = field.config || {};
  return (config.relationEntry || config.relation_entry || {}) as Dict;
}

function relationCanCreate(field: FormField) {
  return relationEntry(field).can_create === true || relationEntry(field).canCreate === true;
}

function relationCanOpen(field: FormField) {
  return (
    relationEntry(field).can_read !== false && Boolean(relationEntry(field).action_id || relationEntry(field).menu_id)
  );
}

function relationOptionKey(field: FormField) {
  return `${field.name}::${field.relation}`;
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) void open();
  },
  { immediate: true },
);

watch(messageMode, (nextMode) => {
  if (nextMode === 'activity' && !activityDeadline.value) activityDeadline.value = nextBusinessDateInputValue();
  if (!collaborationUsers.value.length && !collaborationUsersLoading.value) void loadCollaborationUsers('');
});

watch(
  formValues,
  () => {
    if (!props.visible || mode.value !== 'create' || !draftHydrated.value) return;
    if (draftSaveTimer) clearTimeout(draftSaveTimer);
    draftSaveTimer = setTimeout(saveCreateDraft, 500);
  },
  { deep: true },
);

async function open() {
  activeRecordId.value = props.recordId || null;
  mode.value = props.initialMode || (activeRecordId.value ? 'view' : 'create');
  activeTab.value = 'fields';
  activeFormTab.value = '';
  chatterItems.value = [];
  resetCollaborationDrafts();
  await loadRecord(activeRecordId.value, mode.value);
  if (activeRecordId.value) void loadChatter();
  if (activeRecordId.value) void loadFollowers();
}

async function loadRecord(recordId: number | null, requestedMode: DrawerMode) {
  activeRecordId.value = recordId;
  mode.value = requestedMode;
  loading.value = true;
  error.value = '';
  clearReactive(formValues);
  draftHydrated.value = false;
  clearReactive(relationOptionMap);
  try {
    const result = await loadFormContract({
      model: props.model,
      actionId: props.actionId,
      menuId: props.menuId,
      recordId: recordId || undefined,
      renderProfile: requestedMode === 'view' ? 'readonly' : requestedMode,
    });
    contract.value = result;
    normalizedStore.value = createNormalizedContractStore(result);
    const parsedSections = parseSections(result);
    activeFormTab.value = parsedSections.find((section) => section.tabKey)?.tabKey || '';
    const nextWorkflow = (result.workflowContract ||
      (result.runtimeContract as Dict | undefined)?.workflowContract ||
      {}) as Dict;
    if (requestedMode === 'edit' && nextWorkflow.editability === 'readonly') {
      mode.value = 'view';
      MessagePlugin.warning('当前记录为只读状态，已切换到详情模式');
    }
    const mainData = ((result.dataContract as Dict | undefined)?.mainData || result.record || {}) as Dict;
    Object.assign(formValues, normalizeInitialValues(mainData, parsedSections));
    originalValues.value = cloneFormValues(formValues);
    if (!recordId && requestedMode === 'create') restoreCreateDraft();
    draftHydrated.value = true;
    recordVersionToken.value = String(
      mainData.record_version || mainData.write_date || mainData.__last_update || result.record_version || '',
    ).trim();
    seedRelationOptions(parsedSections);
  } catch (cause) {
    captureError(cause, '表单加载失败');
  } finally {
    loading.value = false;
  }
}

function captureError(cause: unknown, fallback: string) {
  error.value = cause instanceof Error ? cause.message : fallback;
  if (cause instanceof OdooApiError) {
    errorReasonCode.value = cause.reasonCode || cause.code;
    errorTraceId.value = cause.traceId;
    suggestedAction.value = cause.suggestedAction;
  }
}

function retryLoad() {
  void loadRecord(activeRecordId.value, mode.value);
}

function close() {
  if ((mode.value === 'edit' || mode.value === 'create') && hasUnsavedChanges()) {
    void confirmDiscard().then((confirmed) => {
      if (confirmed) {
        if (mode.value === 'create') clearCreateDraft();
        emit('update:visible', false);
      }
    });
    return;
  }
  emit('update:visible', false);
}

function cancelEdit() {
  if (activeRecordId.value) {
    clearReactive(formValues);
    Object.assign(formValues, cloneFormValues(originalValues.value));
    mode.value = 'view';
    return;
  }
  close();
}

async function save() {
  const editableFields = sections.value
    .flatMap((section) => section.fields)
    .filter((field) => !fieldRuntimeState(field).readonly && !fieldRuntimeState(field).invisible);
  const missing = editableFields.find((field) => fieldRuntimeState(field).required && isEmpty(formValues[field.name]));
  if (missing) {
    error.value = `请填写${missing.label}`;
    return;
  }

  const vals: Dict = {};
  editableFields.forEach((field) => {
    vals[field.name] = normalizeWriteValue(formValues[field.name], field, 'write');
  });
  saving.value = true;
  error.value = '';
  try {
    const creating = !activeRecordId.value;
    const result = !creating
      ? await updateRecord(props.model, activeRecordId.value as number, vals, {}, recordVersionToken.value)
      : await createRecord(props.model, vals);
    const recordId = Number(result.id || activeRecordId.value || 0);
    activeRecordId.value = recordId;
    if (creating) clearCreateDraft();
    MessagePlugin.success(creating ? '创建成功' : '保存成功');
    emit('saved', recordId);
    await loadRecord(recordId, 'view');
  } catch (cause) {
    if (cause instanceof OdooApiError && (cause.status === 409 || /CONFLICT|STALE|VERSION/.test(cause.code))) {
      await prepareConflict(vals);
    } else {
      captureError(cause, '保存失败');
    }
  } finally {
    saving.value = false;
  }
}

async function prepareConflict(vals: Dict) {
  conflictPendingValues.value = cloneFormValues(vals);
  conflictLatestToken.value = '';
  conflictRows.value = [];
  error.value = '当前记录已发生变化，本次输入尚未写入。';
  try {
    const latest = await loadFormContract({
      model: props.model,
      actionId: props.actionId,
      menuId: props.menuId,
      recordId: activeRecordId.value || undefined,
    });
    const mainData = ((latest.dataContract as Dict | undefined)?.mainData || latest.record || {}) as Dict;
    conflictLatestToken.value = String(
      mainData.record_version || mainData.write_date || mainData.__last_update || latest.record_version || '',
    ).trim();
    const latestValues = normalizeInitialValues(mainData, sections.value);
    conflictRows.value = sections.value
      .flatMap((section) => section.fields)
      .filter((field) => Object.hasOwn(vals, field.name))
      .filter(
        (field) =>
          JSON.stringify(latestValues[field.name]) !== JSON.stringify(originalValues.value[field.name]) ||
          JSON.stringify(formValues[field.name]) !== JSON.stringify(originalValues.value[field.name]),
      )
      .map((field) => ({
        field: field.name,
        label: field.label,
        serverValue: conflictDisplayValue(latestValues[field.name]),
        localValue: conflictDisplayValue(formValues[field.name]),
      }));
  } catch {
    conflictRows.value = Object.keys(vals).map((field) => ({
      field,
      label: sections.value.flatMap((section) => section.fields).find((item) => item.name === field)?.label || field,
      serverValue: '无法读取最新值',
      localValue: conflictDisplayValue(formValues[field]),
    }));
  }
  conflictVisible.value = true;
}

function conflictDisplayValue(value: unknown) {
  if (value === undefined || value === null || value === '') return '—';
  if (Array.isArray(value)) return value.map((item) => (Array.isArray(item) ? (item[1] ?? item[0]) : item)).join('、');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

async function reloadConflictLatest() {
  if (!activeRecordId.value) return;
  conflictResolving.value = true;
  try {
    conflictVisible.value = false;
    await loadRecord(activeRecordId.value, 'edit');
    MessagePlugin.info('已加载服务器最新版本，请重新核对后保存');
  } finally {
    conflictResolving.value = false;
  }
}

async function overwriteConflict() {
  if (!activeRecordId.value || !conflictLatestToken.value || conflictResolving.value) return;
  conflictResolving.value = true;
  error.value = '';
  try {
    await updateRecord(
      props.model,
      activeRecordId.value,
      cloneFormValues(conflictPendingValues.value),
      {},
      conflictLatestToken.value,
    );
    conflictVisible.value = false;
    MessagePlugin.success('已基于服务器最新版本保存本地内容');
    emit('saved', activeRecordId.value);
    await loadRecord(activeRecordId.value, 'view');
  } catch (cause) {
    if (cause instanceof OdooApiError && (cause.status === 409 || /CONFLICT|STALE|VERSION/.test(cause.code))) {
      await prepareConflict(conflictPendingValues.value);
    } else {
      error.value = cause instanceof Error ? cause.message : '冲突处理失败';
    }
  } finally {
    conflictResolving.value = false;
  }
}

async function duplicateRecord() {
  if (!activeRecordId.value || duplicating.value) return;
  duplicating.value = true;
  error.value = '';
  try {
    const vals: Dict = {};
    sections.value
      .flatMap((section) => section.fields)
      .filter(
        (field) =>
          !fieldRuntimeState(field).readonly &&
          !fieldRuntimeState(field).invisible &&
          !['id', 'create_uid', 'create_date', 'write_uid', 'write_date'].includes(field.name),
      )
      .forEach((field) => {
        vals[field.name] = normalizeWriteValue(formValues[field.name], field, 'write');
      });
    const result = await createRecord(props.model, vals);
    const id = Number(result.id || 0);
    MessagePlugin.success('记录已复制');
    if (id) {
      activeRecordId.value = id;
      emit('saved', id);
      await loadRecord(id, 'view');
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '复制失败';
  } finally {
    duplicating.value = false;
  }
}

function modelRights(source: Dict) {
  const status = (source.statusContract || source.status_contract || {}) as Dict;
  return (status.globalStatus?.modelRights || status.global_status?.model_rights || {}) as Dict;
}

function effectiveRecordRights(source: Dict) {
  const status = (source.statusContract || source.status_contract || {}) as Dict;
  return (status.globalStatus?.effectiveRecordCapabilities ||
    status.global_status?.effective_record_capabilities ||
    status.globalStatus?.recordRights ||
    status.global_status?.record_rights ||
    {}) as Dict;
}
async function loadFollowers() {
  if (!activeRecordId.value) return;
  try {
    followers.value = await listRecordFollowers(props.model, activeRecordId.value);
  } catch {
    followers.value = [];
  }
}
async function searchFollowerUsers(value: string) {
  const result = await searchCollaborationUsers(value, 20);
  followerUsers.value = result.items || [];
}
async function addFollower(value: unknown) {
  const partnerId = Number(value || 0);
  if (!partnerId || !activeRecordId.value) return;
  try {
    await addRecordFollower(props.model, activeRecordId.value, partnerId);
    newFollowerPartnerId.value = undefined;
    await loadFollowers();
    MessagePlugin.success('关注者已添加');
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '添加关注者失败');
  }
}
async function removeFollower(id: number) {
  try {
    await removeRecordFollower(id);
    await loadFollowers();
    MessagePlugin.success('关注者已移除');
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '移除关注者失败');
  }
}
function followerName(row: Dict) {
  const partner = row.partner_id;
  return Array.isArray(partner)
    ? String(partner[1] || partner[0])
    : String(partner?.display_name || partner?.name || partner || '关注者');
}

async function remove() {
  if (!activeRecordId.value || !canDelete.value) return;
  saving.value = true;
  error.value = '';
  try {
    const deletedId = activeRecordId.value;
    await deleteRecords(props.model, [deletedId]);
    MessagePlugin.success('删除成功');
    emit('deleted', deletedId);
    close();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '删除失败';
  } finally {
    saving.value = false;
  }
}

async function loadRelationOptions(field: FormField, searchTerm = '') {
  if (!field.relation || relationLoading[relationOptionKey(field)]) return;
  relationLoading[relationOptionKey(field)] = true;
  try {
    const runtimeDomain = onchangeModifierPatch[field.name]?.domain;
    const domain = resolveRuntimeDomain(Array.isArray(runtimeDomain) ? runtimeDomain : field.domain, formValues);
    const rows = await relationOptions({
      model: field.relation,
      searchTerm,
      domain,
    });
    const next = rows.map((row) => ({ value: Number(row.id), label: String(row.display_name || row.name || row.id) }));
    const current = relationOptionMap[field.name] || [];
    relationOptionMap[field.name] = [...current, ...next].filter(
      (item, index, list) => list.findIndex((candidate) => candidate.value === item.value) === index,
    );
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : `${field.label}选项加载失败`;
  } finally {
    relationLoading[relationOptionKey(field)] = false;
  }
}

function selectedRelationId(field: FormField) {
  const value = formValues[field.name];
  if (field.type === 'many2many') return normalizeRelationIds(value)[0] || 0;
  return Number(Array.isArray(value) ? value[0] : value || 0);
}

function openRelation(field: FormField) {
  const entry = relationEntry(field);
  const recordId = selectedRelationId(field);
  if (!recordId || !field.relation) return;
  const query: Record<string, string> = { relation_model: field.relation };
  if (entry.action_id) query.action_id = String(entry.action_id);
  if (entry.menu_id) query.menu_id = String(entry.menu_id);
  void router.push({ path: `/r/${encodeURIComponent(field.relation)}/${recordId}`, query });
}

function quickCreateRelation(field: FormField) {
  relationCreateField.value = field;
  relationCreateName.value = '';
  relationCreateVisible.value = true;
}

async function createRelation() {
  const field = relationCreateField.value;
  const name = relationCreateName.value.trim();
  if (!field || !name) {
    MessagePlugin.warning('请输入关联记录名称');
    return;
  }
  relationCreateSaving.value = true;
  try {
    const result = await createRecord(field.relation, { name }, {});
    const id = Number(result.id || 0);
    if (!id) throw new Error('快速创建未返回记录 ID');
    const option = { value: id, label: name };
    relationOptionMap[field.name] = [...(relationOptionMap[field.name] || []), option];
    if (field.type === 'many2many') formValues[field.name] = [...normalizeRelationIds(formValues[field.name]), id];
    else formValues[field.name] = id;
    relationCreateVisible.value = false;
    await onFieldChange(field.name);
    MessagePlugin.success('关联记录已创建');
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '快速创建失败');
  } finally {
    relationCreateSaving.value = false;
  }
}

async function onFieldChange(fieldName: string) {
  if (!fieldName || loading.value || mode.value === 'view' || !props.model) return;
  const sequence = ++onchangeSequence.value;
  try {
    const result = await triggerOnchange({
      model: props.model,
      recordId: activeRecordId.value,
      values: serializeFormValues('onchange'),
      changedFields: [fieldName],
    });
    if (sequence !== onchangeSequence.value) return;
    if (result.patch) Object.assign(formValues, result.patch);
    if (result.modifiers_patch) Object.assign(onchangeModifierPatch, result.modifiers_patch);
    for (const linePatch of result.line_patches || []) applyLinePatch(linePatch as Dict);
    // A backend onchange can alter the domain of another relation field. Clear
    // stale choices and reload only fields whose domain references the changed value.
    const dependentFields = sections.value
      .flatMap((section) => section.fields)
      .filter((field) => field.relation && JSON.stringify(field.domain || []).includes(fieldName));
    await Promise.all(
      dependentFields.map(async (field) => {
        relationOptionMap[field.name] = [];
        await loadRelationOptions(field);
      }),
    );
    for (const warning of result.warnings || []) {
      if (warning.message) MessagePlugin.warning(warning.message);
    }
  } catch (cause) {
    // onchange is contract-driven and optional for simple models; surface a warning without blocking edits.
    if (import.meta.env.DEV) console.warn('[onchange] ignored', cause);
  }
}

function applyLinePatch(patch: Dict) {
  const fieldName = String(patch.field || patch.field_name || patch.parent_field || '').trim();
  if (!fieldName) return;
  const rows = one2manyRows(fieldName);
  const rowId = Number(patch.id || patch.row_id || patch.res_id || 0);
  const rowIndex = Number(patch.index ?? patch.row_index ?? -1);
  const target = rowId ? rows.find((row) => row.id === rowId) : rowIndex >= 0 ? rows[rowIndex] : undefined;
  const values = (patch.values || patch.patch || patch.value || {}) as Dict;
  if (target && values && typeof values === 'object') Object.assign(target.values, values);
}

async function loadChatter() {
  if (!activeRecordId.value || !props.model) return;
  chatterLoading.value = true;
  try {
    const result = await fetchChatterTimeline({ model: props.model, recordId: activeRecordId.value });
    chatterItems.value = Array.isArray(result.items) ? result.items : [];
  } catch (cause) {
    if (import.meta.env.DEV) console.warn('[chatter] unavailable', cause);
  } finally {
    chatterLoading.value = false;
  }
}

async function sendMessage() {
  if (!activeRecordId.value || !props.model) return;
  const isActivity = messageMode.value === 'activity';
  if (isActivity ? !activitySummary.value.trim() : !messageDraft.value.trim()) return;
  messageSending.value = true;
  try {
    if (isActivity) {
      await scheduleChatterActivity({
        model: props.model,
        recordId: activeRecordId.value,
        summary: activitySummary.value.trim(),
        dateDeadline: activityDeadline.value || undefined,
        note: activityNote.value.trim() || undefined,
        userId: activityAssigneeId.value || undefined,
      });
      activitySummary.value = '';
      activityDeadline.value = '';
      activityNote.value = '';
      activityAssigneeId.value = undefined;
      MessagePlugin.success('计划活动已创建');
    } else {
      await postChatterMessage({
        model: props.model,
        recordId: activeRecordId.value,
        body: messageDraft.value.trim(),
        mode: messageMode.value === 'note' ? 'note' : 'message',
        mentionUserIds: mentionUserIds.value,
      });
      messageDraft.value = '';
      mentionUserIds.value = [];
      MessagePlugin.success(messageMode.value === 'note' ? '内部备注已发送' : '消息已发送');
    }
    await loadChatter();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : isActivity ? '计划活动创建失败' : '消息发送失败');
  } finally {
    messageSending.value = false;
  }
}

function activityEntryId(item: ChatterTimelineEntry) {
  return Number(item.activity?.id || item.id || 0);
}

async function updateActivity(item: ChatterTimelineEntry, action: 'done' | 'cancel') {
  const activityId = activityEntryId(item);
  if (!activityId || !activeRecordId.value || !props.model || activityBusyIds.value.includes(activityId)) return;
  activityBusyIds.value = [...activityBusyIds.value, activityId];
  try {
    await updateChatterActivity({
      model: props.model,
      recordId: activeRecordId.value,
      activityId,
      action,
      note: action === 'done' ? '计划已完成。' : '计划已取消。',
    });
    MessagePlugin.success(action === 'done' ? '活动已完成' : '活动已取消');
    await loadChatter();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : action === 'done' ? '完成活动失败' : '取消活动失败');
  } finally {
    activityBusyIds.value = activityBusyIds.value.filter((id) => id !== activityId);
  }
}

async function loadCollaborationUsers(query = '') {
  if (collaborationUsersLoading.value) return;
  collaborationUsersLoading.value = true;
  try {
    const result = await searchCollaborationUsers(String(query || '').trim(), 20);
    const next = Array.isArray(result.items) ? result.items : [];
    const merged = new Map(collaborationUsers.value.map((user) => [Number(user.id), user]));
    next.forEach((user) => {
      const id = Number(user.id || 0);
      if (id > 0) merged.set(id, user);
    });
    collaborationUsers.value = [...merged.values()];
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '协作人员加载失败');
  } finally {
    collaborationUsersLoading.value = false;
  }
}

function resetCollaborationDrafts() {
  messageMode.value = 'message';
  messageDraft.value = '';
  mentionUserIds.value = [];
  activitySummary.value = '';
  activityDeadline.value = '';
  activityNote.value = '';
  activityAssigneeId.value = undefined;
  activityBusyIds.value = [];
}

function nextBusinessDateInputValue() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

async function onAttachmentSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file || !activeRecordId.value) return;
  attachmentUploading.value = true;
  try {
    const data = await fileToBase64(file);
    await uploadFile({
      model: props.model,
      recordId: activeRecordId.value,
      name: file.name,
      mimetype: file.type || 'application/octet-stream',
      data,
    });
    MessagePlugin.success('附件上传成功');
    await loadChatter();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '附件上传失败');
  } finally {
    attachmentUploading.value = false;
  }
}

async function downloadAttachment(attachment: { id?: number; name?: string; mimetype?: string }) {
  if (!attachment.id) return;
  downloadBusyId.value = attachment.id;
  try {
    const result = await downloadFile({ attachmentId: attachment.id });
    if (!result.content_b64) throw new Error('后端未返回附件内容');
    const binary = atob(result.content_b64);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const blob = new Blob([bytes], { type: result.mimetype || attachment.mimetype || 'application/octet-stream' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.filename || attachment.name || 'attachment';
    link.click();
    URL.revokeObjectURL(url);
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '附件下载失败');
  } finally {
    downloadBusyId.value = null;
  }
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = typeof reader.result === 'string' ? reader.result : '';
      resolve(value.includes(',') ? value.slice(value.indexOf(',') + 1) : value);
    };
    reader.onerror = () => reject(reader.error || new Error('文件读取失败'));
    reader.readAsDataURL(file);
  });
}

async function runBusinessAction(action: (typeof businessActions.value)[number]) {
  if (!activeRecordId.value || actionBusyKey.value) return;
  if (actionRequiresConfirmation(action)) {
    pendingAction.value = action;
    actionConfirmReason.value = '';
    actionConfirmVisible.value = true;
    return;
  }
  await executeBusinessAction(action, '');
}

async function executeBusinessAction(action: (typeof businessActions.value)[number], reason: string) {
  if (!activeRecordId.value || actionBusyKey.value) return;
  actionBusyKey.value = action.key;
  try {
    let result: Dict = {};
    if (action.intent && action.intent !== 'execute_button') {
      result = (await intent<Dict>(action.intent, {
        ...action.params,
        model: props.model,
        record_id: activeRecordId.value,
        context: action.params.context || {},
        reason,
      })) as Dict;
    } else {
      result = (await executeButton({
        model: props.model,
        recordId: activeRecordId.value,
        button: action.button,
      })) as Dict;
    }
    const navigation = (result.target || result.navigation || result.action) as Dict | undefined;
    if (navigation?.route && String(navigation.route).startsWith('/')) void router.push(String(navigation.route));
    MessagePlugin.success(String(result.message || result.notification || `${action.label}已执行`));
    await loadRecord(activeRecordId.value, 'view');
    await loadChatter();
    emit('saved', activeRecordId.value);
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : `${action.label}执行失败`);
  } finally {
    actionBusyKey.value = '';
  }
}

async function confirmBusinessAction() {
  const action = pendingAction.value;
  if (!action) return;
  if (action.requiresReason && !actionConfirmReason.value.trim()) {
    MessagePlugin.warning('请填写操作原因');
    return;
  }
  actionConfirmVisible.value = false;
  await executeBusinessAction(action, actionConfirmReason.value.trim());
  pendingAction.value = null;
}

function hasUnsavedChanges() {
  return JSON.stringify(toRaw(formValues)) !== JSON.stringify(originalValues.value);
}

function confirmDiscard() {
  return new Promise<boolean>((resolve) => {
    const dialog = DialogPlugin.confirm({
      header: '放弃未保存修改？',
      body: '当前表单有未保存的内容，离开后将无法恢复。',
      confirmBtn: { content: '放弃修改', theme: 'danger' },
      cancelBtn: '继续编辑',
      onConfirm: () => {
        dialog.destroy();
        resolve(true);
      },
      onClose: () => {
        dialog.destroy();
        resolve(false);
      },
    });
  });
}

function beforeUnload(event: BeforeUnloadEvent) {
  if (!props.visible || !hasUnsavedChanges() || saving.value) return;
  event.preventDefault();
  event.returnValue = '';
}

onMounted(() => window.addEventListener('beforeunload', beforeUnload));
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnload);
  if (draftSaveTimer) clearTimeout(draftSaveTimer);
});
onBeforeRouteLeave(async () => {
  if (!props.visible || !hasUnsavedChanges() || saving.value) return true;
  const confirmed = await confirmDiscard();
  if (confirmed && mode.value === 'create') clearCreateDraft();
  return confirmed;
});

function createDraftKey() {
  return `sc:create-draft:${props.model}:${props.actionId || 0}:${props.menuId || 0}`;
}

function saveCreateDraft() {
  try {
    localStorage.setItem(
      createDraftKey(),
      JSON.stringify({ savedAt: Date.now(), values: cloneFormValues(toRaw(formValues)) }),
    );
  } catch {
    // Browser storage can be disabled; draft recovery must not block the form.
  }
}

function restoreCreateDraft() {
  try {
    const raw = localStorage.getItem(createDraftKey());
    if (!raw) return;
    const draft = JSON.parse(raw) as { savedAt?: number; values?: Dict };
    if (!draft.values || Date.now() - Number(draft.savedAt || 0) > 7 * 24 * 60 * 60 * 1000) {
      clearCreateDraft();
      return;
    }
    Object.assign(formValues, cloneFormValues(draft.values));
    MessagePlugin.info('已恢复上次未保存的新建草稿');
  } catch {
    clearCreateDraft();
  }
}

function clearCreateDraft() {
  localStorage.removeItem(createDraftKey());
}

function parseSections(payload: Dict): FormSection[] {
  const layout = (payload.layoutContract || payload.layout_contract || payload.layout || {}) as Dict;
  const statusRows = [
    ...(((payload.runtimeContract as Dict | undefined)?.widgetStatus || []) as Dict[]),
    ...(((payload.statusContract as Dict | undefined)?.widgetStatus || []) as Dict[]),
  ];
  const statusMap = new Map(statusRows.map((item) => [String(item.widgetId || item.widget_id || ''), item]));
  const result: FormSection[] = [];
  const seen = new Set<string>();

  const fieldFromNode = (node: Dict): FormField | null => {
    const nodeType = String(node.type || node.kind || '').toLowerCase();
    const explicitFieldCode = String(node.fieldCode || node.field_code || '');
    const info = (node.fieldInfo || node.field_info || {}) as Dict;
    const config = (node.componentConfig || node.component_config || {}) as Dict;
    const name = String(node.name || node.fieldCode || node.field_code || info.name || '');
    const containerTypes = new Set([
      'column',
      'container',
      'form',
      'group',
      'header',
      'notebook',
      'page',
      'row',
      'section',
      'sheet',
      'tab',
    ]);
    const fieldTypes = new Set([
      'binary',
      'boolean',
      'char',
      'date',
      'datetime',
      'float',
      'html',
      'integer',
      'many2many',
      'many2one',
      'monetary',
      'one2many',
      'selection',
      'text',
    ]);
    const hasFieldSchema = Boolean(
      explicitFieldCode ||
      Object.keys(info).length ||
      node.fieldType ||
      node.field_type ||
      node.ttype ||
      fieldTypes.has(nodeType),
    );
    if (containerTypes.has(nodeType) || (nodeType && nodeType !== 'field' && !hasFieldSchema)) return null;
    if (!name || (!hasFieldSchema && nodeType !== 'field')) return null;
    if (!name || seen.has(name)) return null;
    const widgetId = String(node.widgetId || node.widget_id || `field.${name}`);
    const status = statusMap.get(widgetId) || statusMap.get(`field.${name}`) || statusMap.get(name);
    const modifiers = (node.modifiers || info.modifiers || config.modifiers || {}) as Dict;
    const staticFlag = (value: unknown) =>
      value === true || value === 1 || value === '1' || String(value || '').toLowerCase() === 'true';
    const initialInvisible = status
      ? status.visible === false
      : [node.invisible, info.invisible, config.invisible].some(staticFlag);
    seen.add(name);
    return {
      name,
      label: String(node.label || node.string || info.label || info.string || name),
      type: normalizeFieldType(
        config.fieldType ||
          config.field_type ||
          info.type ||
          node.fieldType ||
          node.field_type ||
          node.ttype ||
          (fieldTypes.has(nodeType) ? nodeType : 'char'),
      ),
      required: status
        ? status.required === true
        : [info.required, config.required, node.required, modifiers.required].some(staticFlag),
      readonly: status
        ? status.readonly === true || status.disabled === true
        : [info.readonly, config.readonly, node.readonly, modifiers.readonly].some(staticFlag),
      help: String(info.help || node.help || ''),
      selection: Array.isArray(config.selection)
        ? config.selection
        : Array.isArray(info.selection)
          ? info.selection
          : [],
      relation: String(config.relation || info.relation || ''),
      domain: Array.isArray(info.domain) ? info.domain : Array.isArray(config.domain) ? config.domain : [],
      config: {
        ...info,
        ...config,
        node,
        initialInvisible,
        staticReadonly: status
          ? status.readonly === true || status.disabled === true
          : [info.readonly, config.readonly, node.readonly].some(staticFlag),
        staticRequired: status
          ? status.required === true
          : [info.required, config.required, node.required].some(staticFlag),
        relationEntry: info.relationEntry || info.relation_entry || config.relationEntry || config.relation_entry || {},
      },
    };
  };

  interface WalkContext {
    tabKey?: string;
    tabLabel?: string;
    sectionKey?: string;
    sectionLabel?: string;
    columns?: number;
  }
  const nodeChildren = (node: Dict) => {
    const values = [
      'children',
      'widgetList',
      'pages',
      'tabs',
      'nodes',
      'items',
      'fields',
      'sub_groups',
      'groups',
    ].flatMap((key) => (Array.isArray(node[key]) ? (node[key] as unknown[]) : []));
    return [...new Set(values)].filter((item): item is Dict => Boolean(item && typeof item === 'object'));
  };
  const nodeType = (node: Dict) => {
    const explicit = String(node.type || node.kind || node.containerType || '')
      .trim()
      .toLowerCase();
    if (explicit) return explicit;
    if (Array.isArray(node.fields) || Array.isArray(node.sub_groups)) return 'group';
    if (Array.isArray(node.groups)) return 'page';
    if (Array.isArray(node.pages)) return 'notebook';
    return '';
  };
  const nodeLabel = (node: Dict, fallback: string) =>
    String(node.label || node.string || node.title || node.displayLabel || node.semanticTitle || fallback).trim();
  const nodeKey = (node: Dict, fallback: string) =>
    String(node.key || node.name || node.widgetId || node.widget_id || fallback).trim();
  const sectionMap = new Map<string, FormSection>();
  const ensureSection = (context: WalkContext) => {
    const tabPart = context.tabKey || 'root';
    const sectionPart = context.sectionKey || 'basic';
    const key = `${tabPart}:${sectionPart}`;
    let section = sectionMap.get(key);
    if (!section) {
      section = {
        key,
        label: context.sectionLabel || (context.tabKey ? '基本信息' : '基本信息'),
        columns: context.columns === 1 ? 1 : 2,
        fields: [],
        tabKey: context.tabKey,
        tabLabel: context.tabLabel,
      };
      sectionMap.set(key, section);
      result.push(section);
    }
    return section;
  };
  const visit = (node: Dict, context: WalkContext, index: number) => {
    const type = nodeType(node);
    const field = fieldFromNode(node);
    if (field) {
      ensureSection(context).fields.push(field);
      return;
    }
    const children = nodeChildren(node);
    if (type === 'notebook') {
      children.forEach((page, pageIndex) => {
        const pageKey = nodeKey(page, `page-${index}-${pageIndex}`);
        const pageLabel = nodeLabel(page, `页签 ${pageIndex + 1}`);
        visit(page, { ...context, tabKey: pageKey, tabLabel: pageLabel }, pageIndex);
      });
      return;
    }
    if (type === 'page' || type === 'tab') {
      const tabKey = context.tabKey || nodeKey(node, `page-${index}`);
      const tabLabel = context.tabLabel || nodeLabel(node, `页签 ${index + 1}`);
      children.forEach((child, childIndex) => visit(child, { ...context, tabKey, tabLabel }, childIndex));
      return;
    }
    const columns = Number(
      node.columns || node.cols || (node.attributes as Dict | undefined)?.col || context.columns || 2,
    );
    const createsSection = ['group', 'section', 'header'].includes(type);
    const nextContext = createsSection
      ? {
          ...context,
          sectionKey: nodeKey(node, `${type || 'section'}-${index}`),
          sectionLabel: nodeLabel(node, type === 'header' ? '状态' : '基本信息'),
          columns,
        }
      : { ...context, columns };
    children.forEach((child, childIndex) => visit(child, nextContext, childIndex));
  };

  let roots = Array.isArray(layout.containerTree)
    ? layout.containerTree
    : Array.isArray(layout.container_tree)
      ? layout.container_tree
      : Array.isArray(layout.widgetList)
        ? layout.widgetList
        : [];
  if (!roots.length) {
    roots = [
      ...(Array.isArray(layout.groups) ? layout.groups : []),
      ...(Array.isArray(layout.notebooks) ? layout.notebooks : []),
    ];
  }
  if (!roots.length) {
    const fieldSource = payload.fields || (payload.dataContract as Dict | undefined)?.fields;
    if (Array.isArray(fieldSource)) {
      roots = [{ type: 'group', label: '基本信息', fields: fieldSource }];
    } else if (fieldSource && typeof fieldSource === 'object') {
      roots = [
        {
          type: 'group',
          label: '基本信息',
          fields: Object.entries(fieldSource as Dict).map(([name, value]) => ({
            ...(value && typeof value === 'object' ? (value as Dict) : {}),
            name,
          })),
        },
      ];
    }
  }
  roots.forEach((raw: unknown, index: number) => {
    if (raw && typeof raw === 'object') visit(raw as Dict, {}, index);
  });
  return result.filter((section) => section.fields.length > 0);
}

function normalizeInitialValues(data: Dict, parsedSections: FormSection[]) {
  const result: Dict = {};
  parsedSections
    .flatMap((item) => item.fields)
    .forEach((field) => {
      const value = data[field.name];
      if (field.type === 'many2one') result[field.name] = Array.isArray(value) ? value[0] : value || undefined;
      else if (field.type === 'many2many') result[field.name] = normalizeRelationIds(value);
      else if (field.type === 'one2many') result[field.name] = normalizeOne2manyRows(value);
      else if (field.type === 'boolean') result[field.name] = Boolean(value);
      else if (isNumberField(field))
        result[field.name] = value === false || value === null || value === undefined ? undefined : Number(value);
      else result[field.name] = value === false || value === null || value === undefined ? '' : value;
    });
  return result;
}

function seedRelationOptions(parsedSections: FormSection[]) {
  const mainData = ((contract.value.dataContract as Dict | undefined)?.mainData || {}) as Dict;
  parsedSections
    .flatMap((item) => item.fields)
    .filter((field) => field.type === 'many2one' || field.type === 'many2many')
    .forEach((field) => {
      const value = mainData[field.name];
      const values = Array.isArray(value) ? value : [];
      if (field.type === 'many2one' && values[0]) {
        relationOptionMap[field.name] = [{ value: Number(values[0]), label: String(values[1] || values[0]) }];
      } else if (field.type === 'many2many') {
        relationOptionMap[field.name] = values.reduce<Option[]>((options, item) => {
          if (!Array.isArray(item)) return options;
          const id = Number(item[0]);
          if (Number.isFinite(id) && id > 0) options.push({ value: id, label: String(item[1] || item[0]) });
          return options;
        }, []);
      }
    });
}

function selectionOptions(field: FormField): Option[] {
  return field.selection.map((item) => {
    if (Array.isArray(item)) return { value: String(item[0]), label: String(item[1] ?? item[0]) };
    const row = item as Dict;
    return { value: String(row.value ?? row.key ?? ''), label: String(row.label ?? row.value ?? row.key ?? '') };
  });
}

function displayValue(value: unknown, field: FormField) {
  if (value === null || value === undefined || value === false || value === '') return '—';
  if (field.type === 'selection')
    return selectionOptions(field).find((item) => String(item.value) === String(value))?.label || String(value);
  if (field.type === 'many2one')
    return relationOptionMap[field.name]?.find((item) => String(item.value) === String(value))?.label || String(value);
  if (Array.isArray(value)) return value.map((item) => (Array.isArray(item) ? item[1] : item)).join(', ') || '—';
  if (typeof value === 'object')
    return String((value as Dict).display_name || (value as Dict).name || JSON.stringify(value));
  return String(value);
}

function normalizeWriteValue(value: unknown, field: FormField, mode: 'onchange' | 'write' = 'write') {
  if (field.type === 'many2one') return value || false;
  if (field.type === 'many2many') return [[6, 0, normalizeRelationIds(value)]];
  if (field.type === 'one2many') return buildOne2manyCommands(value, mode);
  if (field.type === 'boolean') return Boolean(value);
  if (isNumberField(field)) return value === '' || value === undefined || value === null ? false : Number(value);
  return value ?? false;
}

function isNumberField(field: FormField) {
  return isNumericFieldType(field.type);
}

function toOptionalNumber(value: unknown) {
  const numberValue = Number(value);
  return value === '' || value === null || value === undefined || !Number.isFinite(numberValue)
    ? undefined
    : numberValue;
}

function normalizeRelationIds(value: unknown): number[] {
  if (!Array.isArray(value))
    return value === undefined || value === null || value === false ? [] : [Number(value)].filter(Number.isFinite);
  return value
    .map((item) => (Array.isArray(item) ? item[0] : typeof item === 'object' && item ? (item as Dict).id : item))
    .map(Number)
    .filter((id) => Number.isFinite(id) && id > 0);
}

function serializeFormValues(mode: 'onchange' | 'write') {
  return sections.value
    .flatMap((section) => section.fields)
    .reduce<Dict>((values, field) => {
      values[field.name] = normalizeWriteValue(formValues[field.name], field, mode);
      return values;
    }, {});
}

function normalizeOne2manyRows(value: unknown): One2ManyRow[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((raw, index) => {
    if (Array.isArray(raw) && typeof raw[0] === 'number') {
      const op = Number(raw[0]);
      const id = Number(raw[1] || 0) || undefined;
      const values = raw[2] && typeof raw[2] === 'object' && !Array.isArray(raw[2]) ? { ...(raw[2] as Dict) } : {};
      if (op === 2 || op === 3) return [];
      return [
        { key: `o2m-${id || 'new'}-${index}`, id, values, originalValues: structuredClone(values), isNew: op === 0 },
      ];
    }
    const source = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Dict) : {};
    const id = Number(source.id || source.res_id || 0) || undefined;
    const values = { ...source };
    delete values.id;
    delete values.res_id;
    return [{ key: `o2m-${id || 'row'}-${index}`, id, values, originalValues: structuredClone(values), isNew: !id }];
  });
}

function one2manyRows(name: string): One2ManyRow[] {
  return Array.isArray(formValues[name]) ? (formValues[name] as One2ManyRow[]) : [];
}

function visibleOne2manyRows(name: string) {
  return one2manyRows(name).filter((row) => !row.removed);
}

function removedOne2manyRows(name: string) {
  return one2manyRows(name).filter((row) => row.removed);
}

function addOne2manyRow(field: FormField) {
  const rows = one2manyRows(field.name);
  rows.push({
    key: `o2m-new-${Date.now()}-${rows.length}`,
    values: Object.fromEntries(
      one2manyColumns(field).map((column) => [column.name, column.type === 'boolean' ? false : '']),
    ),
    originalValues: {},
    isNew: true,
  });
  formValues[field.name] = rows;
}

function removeOne2manyRow(name: string, key: string) {
  const row = one2manyRows(name).find((item) => item.key === key);
  if (!row) return;
  if (row.isNew) formValues[name] = one2manyRows(name).filter((item) => item.key !== key);
  else row.removed = true;
}

function restoreOne2manyRow(name: string, key: string) {
  const row = one2manyRows(name).find((item) => item.key === key);
  if (row) row.removed = false;
}

function setOne2manyRowField(field: FormField, key: string, column: FormField, value: unknown) {
  const row = one2manyRows(field.name).find((item) => item.key === key);
  if (!row) return;
  row.values[column.name] = normalizeOne2manyValue(value, column);
  void onFieldChange(field.name);
}

function one2manyFieldRuntimeState(parent: FormField, row: One2ManyRow, column: FormField) {
  const config = column.config || {};
  const modifiers = (config.modifiers || config.fieldInfo?.modifiers || {}) as Dict;
  const values = { ...formValues, ...row.values, parent: formValues };
  const dynamic = runtimeFieldState(modifiers, {}, values);
  return { ...dynamic, readonly: column.readonly || dynamic.readonly };
}

async function loadOne2manyRelationOptions(parent: FormField, row: One2ManyRow, column: FormField, searchTerm = '') {
  if (!column.relation) return;
  const key = `${parent.name}.${column.name}`;
  if (relationLoading[key]) return;
  relationLoading[key] = true;
  try {
    const domain = resolveRuntimeDomain(column.domain, { ...formValues, ...row.values, parent: formValues });
    const options = await relationOptions({ model: column.relation, searchTerm, domain });
    relationOptionMap[key] = options.map((item) => ({
      value: Number(item.id),
      label: String(item.display_name || item.name || item.id),
    }));
  } finally {
    relationLoading[key] = false;
  }
}

function normalizeOne2manyValue(value: unknown, field: FormField) {
  if (field.type === 'boolean') return Boolean(value);
  if (isNumberField(field)) return value === '' || value === null || value === undefined ? false : Number(value);
  return value ?? false;
}

function one2manyCellValue(value: unknown) {
  if (Array.isArray(value)) return String(value[1] ?? value[0] ?? '');
  if (value && typeof value === 'object')
    return String((value as Dict).display_name || (value as Dict).name || (value as Dict).id || '');
  return value === false || value === null || value === undefined ? '' : String(value);
}

function one2manyColumns(field: FormField): FormField[] {
  const source = field.config || {};
  const collect = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
  const subview = (source.subview || source.subView || source.relationEntry || source.relation_entry || {}) as Dict;
  const candidates = [
    ...collect(source.columns),
    ...collect(source.fields),
    ...collect(subview.columns),
    ...collect(subview.fields),
    ...collect((subview.tree as Dict | undefined)?.columns),
    ...collect((subview.tree as Dict | undefined)?.fields),
  ];
  const fromRaw = (raw: unknown): FormField | null => {
    const row = typeof raw === 'string' ? { name: raw } : raw && typeof raw === 'object' ? (raw as Dict) : {};
    const config = (row.componentConfig || row.component_config || {}) as Dict;
    const name = String(row.name || row.fieldCode || row.field_code || row.field || '').trim();
    if (!name || ['id', 'display_name'].includes(name)) return null;
    const info = (row.fieldInfo || row.field_info || {}) as Dict;
    return {
      name,
      label: String(row.label || row.string || info.label || info.string || name),
      type: normalizeFieldType(row.type || row.ttype || row.fieldType || config.fieldType || info.type || 'char'),
      required: Boolean(row.required ?? config.required ?? info.required),
      readonly: Boolean(row.readonly ?? config.readonly ?? info.readonly),
      help: '',
      selection: Array.isArray(row.selection)
        ? row.selection
        : Array.isArray(config.selection)
          ? config.selection
          : Array.isArray(info.selection)
            ? info.selection
            : [],
      relation: String(row.relation || config.relation || info.relation || ''),
      domain: Array.isArray(row.domain) ? row.domain : [],
    };
  };
  const explicit = candidates.map(fromRaw).filter((item): item is FormField => Boolean(item));
  if (explicit.length) {
    return explicit.filter(
      (item, index, list) => list.findIndex((candidate) => candidate.name === item.name) === index,
    );
  }
  const keys = one2manyRows(field.name).flatMap((row) => Object.keys(row.values));
  return [...new Set(keys)]
    .filter((name) => !['id', 'display_name'].includes(name))
    .map((name) => ({
      name,
      label: name,
      type: typeof one2manyRows(field.name)[0]?.values[name] === 'number' ? 'float' : 'char',
      required: false,
      readonly: false,
      help: '',
      selection: [],
      relation: '',

      domain: [],
    }));
}

function one2manyGridStyle(field: FormField) {
  const count = Math.max(one2manyColumns(field).length, 1);
  return { gridTemplateColumns: `repeat(${count}, minmax(120px, 1fr)) 68px` };
}

function buildOne2manyCommands(value: unknown, mode: 'onchange' | 'write') {
  if (!Array.isArray(value)) return [];
  return (value as One2ManyRow[]).flatMap((row) => {
    const values = sanitizeOne2manyValues(row.values);
    if (row.isNew) return row.removed ? [] : [[0, 0, values]];
    if (!row.id) return [];
    if (row.removed) return [[2, row.id]];
    const changed = JSON.stringify(values) !== JSON.stringify(sanitizeOne2manyValues(row.originalValues));
    return changed || mode === 'onchange' ? [[1, row.id, values]] : [];
  });
}

function sanitizeOne2manyValues(values: Dict) {
  const output = { ...values };
  delete output.id;
  delete output.res_id;
  delete output.display_name;
  return output;
}

function isEmpty(value: unknown) {
  return value === '' || value === null || value === undefined || (Array.isArray(value) && value.length === 0);
}

function clearReactive(target: Dict) {
  Object.keys(target).forEach((key) => delete target[key]);
}

function cloneFormValues(values: Dict): Dict {
  return structuredClone(toRaw(values));
}
</script>
<style scoped>
.record-drawer {
  min-height: 100%;
  margin: -24px;
  padding: 0 32px 48px;
  background: var(--td-bg-color-container);
}

.record-drawer--page {
  min-height: calc(100vh - 168px);
  margin: 0;
  padding: 0 0 40px;
}

.record-drawer--page .record-toolbar {
  top: 0;
}

.record-toolbar {
  position: sticky;
  top: -24px;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  min-height: 88px;
  padding: 16px 0;
  background: var(--td-bg-color-container);
  border-bottom: 1px solid var(--td-border-level-1-color);
}

.record-toolbar__identity {
  min-width: 0;
}
.followers-panel {
  padding: 16px 0 20px;
  border-bottom: 1px solid var(--td-border-level-1-color);
}
.conflict-table {
  margin-top: 16px;
}
.collaboration-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}
.collaboration-heading h3,
.collaboration-heading p {
  margin: 0;
}
.collaboration-heading p,
.empty-copy {
  margin-top: 4px;
  color: var(--td-text-color-secondary);
}
.collaboration-heading .t-select {
  width: 260px;
}

.record-toolbar__identity h2 {
  margin: 0 0 8px;
  color: var(--td-text-color-primary);
  font-size: 20px;
  font-weight: 600;
  line-height: 28px;
}

.record-toolbar__status {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.record-toolbar__right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex: 0 0 auto;
  max-width: 70%;
}

.record-toolbar__actions {
  justify-content: flex-end;
}

.record-toolbar__close {
  flex: 0 0 auto;
  color: var(--td-text-color-secondary);
  border-left: 1px solid var(--td-border-level-1-color);
  border-radius: 0;
}

.record-tabs {
  margin-top: 0;
}

.record-tabs :deep(.t-tabs__nav-wrap) {
  min-height: 52px;
}

.record-tabs :deep(.t-tabs__content) {
  padding-top: 0;
}

.collaboration-panel {
  padding: 20px 0 8px;
}

.collaboration-compose {
  padding: 18px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
}

.collaboration-compose__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.activity-compose-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px 240px;
  gap: 12px;
  margin: 14px 0 12px;
}

.collaboration-mentions {
  width: 100%;
  margin: 14px 0 12px;
}

.activity-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-top: 10px;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}

.attachment-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  color: var(--td-text-color-placeholder);
  font-size: 12px;
}

.attachment-input {
  display: none;
}

.attachment-link {
  display: inline-flex;
  margin-top: 10px;
}

.collaboration-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 0 12px;
}

.collaboration-heading h3 {
  margin: 0;
  font-size: 16px;
}

.chatter-list {
  display: grid;
  gap: 10px;
}

.chatter-item {
  padding: 14px 16px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
}

.chatter-item__meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}

.chatter-item__meta strong {
  color: var(--td-text-color-primary);
  font-size: 13px;
}

.chatter-item p {
  margin: 9px 0 0;
  color: var(--td-text-color-primary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.chatter-loading {
  padding: 8px 0;
}

.workflow-label {
  color: var(--td-text-color-secondary);
  font-size: 13px;
}
.approval-panel {
  padding: 14px;
  margin-bottom: 16px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  background: var(--td-bg-color-secondarycontainer);
}
.approval-panel p {
  margin: 4px 0 0;
  color: var(--td-text-color-secondary);
}

.record-error {
  margin-top: 16px;
}

.record-loading {
  padding: 32px 0;
}

.form-section {
  padding: 28px 0 32px;
  margin: 0;
  background: transparent;
  border-bottom: 1px solid var(--td-border-level-1-color);
}

.form-section:last-child {
  border-bottom: 0;
  margin-bottom: 0;
}

.form-section__heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 14px;
  margin-bottom: 22px;
  border-bottom: 1px solid var(--td-border-level-1-color);
}

.form-section__heading h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0;
}

.form-section__heading span {
  color: var(--td-text-color-placeholder);
  font-size: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px 48px;
}

.form-grid--single {
  grid-template-columns: minmax(0, 1fr);
}

.form-field {
  display: grid;
  grid-template-columns: 124px minmax(0, 1fr);
  align-items: start;
  column-gap: 16px;
  min-width: 0;
}

.form-field--wide {
  grid-column: 1 / -1;
}

.form-field label {
  display: block;
  padding-top: 2px;
  color: var(--td-text-color-secondary);
  font-size: 13px;
  line-height: 20px;
}

.required-mark {
  color: var(--td-error-color);
}

.field-value {
  min-height: 24px;
  overflow-wrap: anywhere;
  color: var(--td-text-color-primary);
  line-height: 20px;
  white-space: pre-wrap;
}

.field-help {
  margin: 4px 0 0;
  color: var(--td-text-color-placeholder);
  font-size: 12px;
  line-height: 18px;
}

.form-field :deep(.t-input-number),
.form-field :deep(.t-date-picker),
.form-field :deep(.t-select) {
  width: 100%;
}

.o2m-editor {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.o2m-editor__toolbar,
.o2m-editor__removed {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--td-text-color-secondary);
  font-size: 13px;
}

.o2m-editor__table {
  overflow-x: auto;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
}

.o2m-editor__header,
.o2m-editor__row {
  display: grid;
  min-width: max-content;
  column-gap: 0;
}

.o2m-editor__header > span {
  padding: 9px 12px;
  color: var(--td-text-color-secondary);
  background: var(--td-bg-color-secondarycontainer);
  border-bottom: 1px solid var(--td-border-level-1-color);
  font-size: 12px;
  font-weight: 600;
}

.o2m-editor__row > :deep(.t-input),
.o2m-editor__row > :deep(.t-input-number),
.o2m-editor__row > :deep(.t-date-picker),
.o2m-editor__row > :deep(.t-select) {
  width: auto;
  min-width: 120px;
  margin: 8px 6px;
}

.o2m-editor__row > :deep(.t-switch) {
  margin: 17px 12px;
}

.o2m-editor__row > :deep(.t-button) {
  align-self: center;
  justify-self: center;
}

.o2m-editor__row + .o2m-editor__row {
  border-top: 1px solid var(--td-border-level-1-color);
}

@media (width <= 720px) {
  .record-toolbar {
    align-items: flex-start;
    flex-direction: column;
    top: -16px;
    gap: 12px;
    min-height: auto;
    padding: 16px 0;
  }

  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .form-field--wide {
    grid-column: auto;
  }

  .record-drawer {
    margin: -16px;
    padding: 0 16px 32px;
  }

  .record-toolbar__right,
  .record-toolbar__actions {
    width: 100%;
    max-width: none;
    justify-content: flex-start;
  }

  .record-toolbar__right {
    align-items: flex-start;
  }

  .record-toolbar__actions :deep(.t-space-item) {
    width: auto;
  }

  .record-toolbar__close {
    margin-left: auto;
  }

  .attachment-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .activity-compose-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .form-section {
    padding: 22px 0 24px;
  }

  .form-field {
    grid-template-columns: minmax(88px, 32%) minmax(0, 1fr);
    column-gap: 12px;
  }

  .o2m-editor__table {
    border-radius: 4px;
  }
}
</style>
listRecordFollowers, removeRecordFollower,
