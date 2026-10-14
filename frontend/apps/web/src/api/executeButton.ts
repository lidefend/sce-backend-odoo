import { decodeNativeActionNotification } from '../app/contract/nativeActionNotification';
import { intentRequest } from './intents';
import type { ExecuteButtonRequest, ExecuteButtonResponse } from '@sc/schema';

export async function executeButton(params: ExecuteButtonRequest) {
  const response = await intentRequest<ExecuteButtonResponse>({
    intent: 'execute_button',
    params: {
      model: params.model,
      res_id: params.res_id,
      button: params.button,
    },
    context: params.context ?? {},
    meta: params.meta ?? {},
  });
  decodeNativeActionNotification(response.result);
  return response;
}
