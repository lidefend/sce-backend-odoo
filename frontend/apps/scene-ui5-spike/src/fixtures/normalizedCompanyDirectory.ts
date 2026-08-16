import type { ReadonlyNormalizedCollectionSnapshot } from '@sc/ui';

export const normalizedCompanyDirectorySnapshot: ReadonlyNormalizedCollectionSnapshot = {
  identity: {
    productName: '企业业务管理平台',
    companyName: '示范集团',
    roleName: '组织管理员',
    breadcrumbs: ['组织中心', '公司目录'],
    workTabs: [
      { id: 'workspace', label: '我的工作' },
      { id: 'company-directory', label: '公司目录', active: true },
    ],
  },
  contract: {
    pageInfo: {
      pageId: 'res-company-directory',
      sceneKey: 'organization.company.directory',
      pageName: '公司目录',
      viewType: 'tree',
      contractVersion: '2.0',
    },
    layoutContract: {
      containerTree: [
        {
          widgetList: [
            { widgetId: 'field.name', fieldCode: 'name', label: '公司名称' },
            { widgetId: 'field.country_id', fieldCode: 'country_id', label: '国家/地区' },
            { widgetId: 'field.currency_id', fieldCode: 'currency_id', label: '本位币' },
            { widgetId: 'field.active', fieldCode: 'active', label: '状态' },
            { widgetId: 'field.write_date', fieldCode: 'write_date', label: '最近更新' },
          ],
          children: [],
        },
      ],
      listProfile: {
        columns: ['name', 'country_id', 'currency_id', 'active', 'write_date'],
        column_labels: {
          name: '公司名称',
          country_id: '国家/地区',
          currency_id: '本位币',
          active: '状态',
          write_date: '最近更新',
        },
        row_primary: 'name',
        status_field: 'active',
        cross_device_critical_columns: ['name', 'country_id', 'currency_id', 'active'],
        selection_policy: { enabled: false },
        sourceAuthority: {
          formal_projection: true,
          no_business_fact_authority: true,
          source_key: 'list_profile.native_view_authoritative',
        },
      },
    },
    statusContract: {
      globalStatus: { pageVisible: true, pageAuth: 'readonly' },
      widgetStatus: [
        { widgetId: 'field.name', visible: true },
        { widgetId: 'field.country_id', visible: true },
        { widgetId: 'field.currency_id', visible: true },
        { widgetId: 'field.active', visible: true },
        { widgetId: 'field.write_date', visible: true },
      ],
      buttonStatus: [],
    },
    actionContract: { actionRuleList: [] },
  },
  records: [
    {
      id: 'company-001',
      values: {
        name: '示范集团总部',
        country_id: '中国',
        currency_id: '人民币 CNY',
        active: '启用',
        write_date: '2026-08-15 16:20',
      },
    },
    {
      id: 'company-002',
      values: {
        name: '华东区域公司',
        country_id: '中国',
        currency_id: '人民币 CNY',
        active: '启用',
        write_date: '2026-08-14 11:05',
      },
    },
    {
      id: 'company-003',
      values: {
        name: '海外业务公司',
        country_id: '新加坡',
        currency_id: '新加坡元 SGD',
        active: '停用',
        write_date: '2026-08-12 09:40',
      },
    },
  ],
  runtime: {
    description: '只读查看组织内公司主体；字段、顺序、标签与状态均来自同一 normalized collection 快照。',
    summaries: [
      { id: 'total', label: '公司主体', value: '3 家' },
      { id: 'active', label: '正常启用', value: '2 家', tone: 'Positive' },
      { id: 'inactive', label: '当前停用', value: '1 家', tone: 'Critical' },
      { id: 'currencies', label: '本位币', value: '2 种', tone: 'Information' },
    ],
    filters: [
      { id: 'scope', label: '范围', value: '当前组织', active: true },
      { id: 'record-state', label: '状态', value: '全部' },
    ],
    totalCount: 3,
    rowToneByStatus: { 启用: 'Positive', 停用: 'Critical' },
  },
};
