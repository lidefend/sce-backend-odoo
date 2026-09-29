import { computed, defineComponent, h, type PropType } from 'vue';
import { TDesignTree } from '../../components/design-system/tdesignPrimitiveBridge';
import type { MenuConfigMenu } from '../../api/menuConfig';
import { menuDropPosition, menuTreeExpandedIds, type MenuConfigDropPosition, type MenuConfigDropRequest } from './menuTreeContract';

type MenuConfigTreeNode = {
  value: number;
  label: string;
  pathLabel: string;
  stateClass: string;
  stateLabel: string;
  deletable: boolean;
  children?: MenuConfigTreeNode[];
};

type DropContext = {
  dragNode: { value?: unknown };
  dropNode: { value?: unknown };
  dropPosition: number;
};

export function createMenuConfigTree(options: {
  menuPathLabel: (menu: MenuConfigMenu) => string;
  menuDisplayLabel: (menu: MenuConfigMenu) => string;
  menuHandlingStateClass: (menu: MenuConfigMenu) => string;
  menuTreeStateLabel: (menu: MenuConfigMenu) => string;
  isUserCreatedMenu: (menu: MenuConfigMenu) => boolean;
}) {
  const MenuConfigTree = defineComponent({
    name: 'MenuConfigTree',
    props: {
      nodes: { type: Array as PropType<MenuConfigMenu[]>, required: true },
      selectedMenuId: { type: Number, required: true },
      dragEnabled: { type: Boolean, default: true },
      searchActive: { type: Boolean, default: false },
      collapsedMenuIds: { type: Object as PropType<Set<number>>, required: true },
      allowDrop: {
        type: Function as PropType<(request: MenuConfigDropRequest) => boolean>,
        default: () => false,
      },
    },
    emits: ['select', 'reorder', 'toggle-collapse'],
    setup(props, { emit }) {
      const toTreeNode = (menu: MenuConfigMenu): MenuConfigTreeNode => ({
        value: Number(menu.id),
        label: options.menuDisplayLabel(menu),
        pathLabel: options.menuPathLabel(menu),
        stateClass: options.menuHandlingStateClass(menu),
        stateLabel: options.menuTreeStateLabel(menu),
        deletable: options.isUserCreatedMenu(menu),
        children: menu.children?.length ? menu.children.map(toTreeNode) : undefined,
      });
      const nodeIndex = computed(() => {
        const index = new Map<number, MenuConfigTreeNode>();
        const walk = (rows: MenuConfigTreeNode[]) => {
          rows.forEach((row) => {
            index.set(row.value, row);
            if (row.children?.length) walk(row.children);
          });
        };
        walk(props.nodes.map(toTreeNode));
        return index;
      });
      const treeData = computed(() => props.nodes.map(toTreeNode));
      const activedIds = computed(() => (props.selectedMenuId ? [Number(props.selectedMenuId)] : []));
      const expandedIds = computed(() => (props.searchActive
        ? menuTreeExpandedIds(props.nodes, new Set<number>())
        : menuTreeExpandedIds(props.nodes, props.collapsedMenuIds)));
      const renderNode = (value: unknown) => {
        const node = nodeIndex.value.get(Number(value));
        if (!node) return null;
        return h('span', {
          class: ['tree-node', { 'tree-node--deletable': node.deletable }],
          'data-menu-id': String(node.value),
          title: node.pathLabel,
        }, [
          h('span', { class: 'tree-node-label' }, node.label),
          h('span', { class: ['menu-origin-badge', 'tree-origin-badge', node.stateClass] }, node.stateLabel),
          node.deletable
            ? h('span', { class: ['menu-origin-badge', 'deletable', 'tree-origin-badge'] }, '可删除')
            : null,
        ]);
      };
      return () => h(TDesignTree, {
        class: 'config-menu-tree',
        data: treeData.value,
        label: true,
        hover: true,
        activable: true,
        expandOnClickNode: false,
        actived: activedIds.value,
        expanded: expandedIds.value,
        draggable: props.dragEnabled,
        allowDrop: (context: DropContext) => props.allowDrop({
          sourceId: Number(context.dragNode?.value || 0),
          targetId: Number(context.dropNode?.value || 0),
          position: menuDropPosition(context.dropPosition),
        }),
        onActive: (value: unknown[]) => emit('select', Number(value?.[0] || 0)),
        onExpand: (_value: unknown[], context: { node?: { value?: unknown } }) => emit('toggle-collapse', Number(context?.node?.value || 0)),
        onDrop: (context: DropContext) => emit('reorder', {
          sourceId: Number(context.dragNode?.value || 0),
          targetId: Number(context.dropNode?.value || 0),
          position: menuDropPosition(context.dropPosition),
        }),
      }, {
        label: (slot: { node?: { value?: unknown } }) => renderNode(slot?.node?.value),
      });
    },
  });
  return MenuConfigTree;
}
