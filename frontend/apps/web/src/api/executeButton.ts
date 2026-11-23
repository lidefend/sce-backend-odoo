import { decodeNativeActionNotification } from '../app/contract/nativeActionNotification';
import { decodeActionFeedbackRuntimePatch } from '../app/contract/actionFeedback';
import { ApiError } from './client';
import { intentRequest } from './intents';
import type { ExecuteButtonRequest, ExecuteButtonResponse } from '@sc/schema';

export async function executeButton(params: ExecuteButtonRequest) {
  try {
    const response = await intentRequest<ExecuteButtonResponse>({
      intent: 'execute_button',
      params: {
        model: params.model,
        res_id: params.res_id,
        button: params.button,
        action_params: params.action_params,
      },
      context: params.context ?? {},
      meta: params.meta ?? {},
    });
    decodeNativeActionNotification(response.result);
    return {
      ...response,
      actionFeedback: decodeActionFeedbackRuntimePatch(response.runtimePatch),
    };
  } catch (error) {
    if (error instanceof ApiError) {
      const feedback = decodeActionFeedbackRuntimePatch(error.details?.runtimePatch);
      if (feedback.length) {
        error.details = { ...(error.details || {}), actionFeedback: feedback };
      }
    }
    throw error;
  }
}
