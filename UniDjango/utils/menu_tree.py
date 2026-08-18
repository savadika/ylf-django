"""菜单树构建工具。

统一 ``SysUser`` / ``SysRole`` / 菜单管理三处重复的树形构建逻辑。
"""


def build_menu_tree(menus, include_perms=True):
    """把扁平菜单列表构建成树形结构。

    Args:
        menus: ``SysMenu`` 查询集或列表（调用方负责按 ``order_num`` 排序）。
        include_perms: 是否在每个节点中附带 ``perms`` 字段。用户侧菜单树由前端
            单独接收权限列表、节点里不需要 ``perms`` 时可传 ``False``；角色授权、
            菜单管理页面需要，保持默认 ``True``。

    Returns:
        ``(roots, permissions)``：树根节点列表，以及去重后的权限标识列表。
    """
    nodes_by_id = {}
    roots = []
    permissions = set()

    for m in menus:
        node = {
            'id': m.id,
            'name': m.name,
            'icon': m.icon,
            'parent_id': m.parent_id,
            'order_num': m.order_num,
            'path': m.path,
            'component': m.component,
            'menu_type': m.menu_type,
            'remark': m.remark,
            'children': [],
        }
        if include_perms:
            node['perms'] = m.perms
        if m.perms:
            permissions.add(m.perms)
        nodes_by_id[m.id] = node

    for node in nodes_by_id.values():
        pid = node['parent_id']
        # 顶级：parent_id 为 0/None，或父级不在本次菜单集合中（防断链）。
        if pid in (None, 0) or pid not in nodes_by_id:
            roots.append(node)
        else:
            nodes_by_id[pid]['children'].append(node)

    def _sort_key(n):
        return (n['order_num'] is None, n['order_num'], n['id'])

    def _sort_children(n):
        n['children'].sort(key=_sort_key)
        for child in n['children']:
            _sort_children(child)

    roots.sort(key=_sort_key)
    for root in roots:
        _sort_children(root)

    return roots, list(permissions)
