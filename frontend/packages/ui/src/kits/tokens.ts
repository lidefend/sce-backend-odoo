export type SceneDesignTokenProfileId = 'enterprise-neutral' | 'business-soft' | 'accessible-contrast';

export interface SceneDesignTokenProfile {
  id: SceneDesignTokenProfileId;
  label: string;
  description: string;
  tokens: {
    background: string;
    surface: string;
    border: string;
    mutedText: string;
    text: string;
    brand: string;
    accentSoft: string;
    warning: string;
    success: string;
    focus: string;
    controlRadius: string;
    surfaceRadius: string;
  };
}

export const SCENE_DESIGN_TOKEN_PROFILES: Record<SceneDesignTokenProfileId, SceneDesignTokenProfile> = {
  'enterprise-neutral': {
    id: 'enterprise-neutral',
    label: '企业中性',
    description: '清晰、克制的企业业务默认主题。',
    tokens: {
      background: '#f4f6f8',
      surface: '#ffffff',
      border: '#dfe5ec',
      mutedText: '#5f6b7a',
      text: '#1d2d3e',
      brand: '#0a6ed1',
      accentSoft: '#eaf3fc',
      warning: '#9a4f00',
      success: '#107e3e',
      focus: '#0a6ed1',
      controlRadius: '7px',
      surfaceRadius: '12px',
    },
  },
  'business-soft': {
    id: 'business-soft',
    label: '柔和商务',
    description: '降低边界锐度，适合长时间数据办理。',
    tokens: {
      background: '#f2f5f4',
      surface: '#ffffff',
      border: '#d5dfdc',
      mutedText: '#596963',
      text: '#18302a',
      brand: '#087f6a',
      accentSoft: '#e4f4f0',
      warning: '#8f4b00',
      success: '#087a43',
      focus: '#006fbb',
      controlRadius: '10px',
      surfaceRadius: '14px',
    },
  },
  'accessible-contrast': {
    id: 'accessible-contrast',
    label: '高对比',
    description: '强化文字、边界和焦点，服务低视力与键盘用户。',
    tokens: {
      background: '#ffffff',
      surface: '#ffffff',
      border: '#263746',
      mutedText: '#2f4050',
      text: '#071526',
      brand: '#004f9e',
      accentSoft: '#d9ecff',
      warning: '#7a3500',
      success: '#00652e',
      focus: '#d44900',
      controlRadius: '5px',
      surfaceRadius: '8px',
    },
  },
};

export function isSceneDesignTokenProfileId(value: string | null | undefined): value is SceneDesignTokenProfileId {
  return Boolean(value && Object.prototype.hasOwnProperty.call(SCENE_DESIGN_TOKEN_PROFILES, value));
}
