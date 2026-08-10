{
    "name": "SC Norm Engine",
    "version": "17.0.1.4.2",
    "summary": "Regional, versioned construction norm library and import engine",
    "category": "Construction",
    "author": "lidefend",
    "depends": ["smart_construction_core", "uom"],
    "external_dependencies": {"python": ["openpyxl", "xlrd"]},
    "data": [
        "security/ir.model.access.csv",
        "data/norm_catalog_data.xml",
        "views/norm_import_views.xml",  # 导入向导
        "views/boq_import_views.xml",
        "views/norm_views.xml",         # 定义视图和 actions
        "views/norm_menu.xml",          # 菜单引用上述 actions
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
