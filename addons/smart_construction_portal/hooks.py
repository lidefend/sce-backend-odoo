# -*- coding: utf-8 -*-


def uninstall_hook(env):
    from odoo.addons.smart_core.core.extension_loader import unregister_extension_module

    unregister_extension_module(env, "smart_construction_portal")
