# -*- coding: utf-8 -*-
"""Declared showcase project catalogue.

Single source of truth shared by the release seed and the cockpit seeding
model.  Names are user-visible business names; no demo/showroom marker is
written into them.
"""


SHOWROOM_PROJECTS = [
    {"code": "DEMO-PJ-201", "name": "德阳经开区智能制造产业园项目", "state": "in_progress", "with_chain": True},
    {"code": "DEMO-PJ-202", "name": "旌阳区市政道路提档升级工程", "state": "closing", "with_chain": True},
    {"code": "DEMO-PJ-203", "name": "罗江工业园区标准厂房一期", "state": "warranty", "with_chain": True},
    {"code": "DEMO-PJ-204", "name": "广汉绿色建材产业基地项目", "state": "in_progress", "with_chain": True},
    {"code": "DEMO-PJ-205", "name": "天府数谷智慧园区运营中心", "state": "in_progress", "with_chain": False},
    {"code": "DEMO-PJ-206", "name": "东汽数字化产线改造工程", "state": "done", "with_chain": False},
    {"code": "DEMO-PJ-207", "name": "旌湖片区城市更新综合体", "state": "closing", "with_chain": False},
    {"code": "DEMO-PJ-208", "name": "德阳高新区科技研发中心", "state": "warranty", "with_chain": False},
    {"code": "DEMO-PJ-209", "name": "岷江路海绵城市示范区工程", "state": "done", "with_chain": False},
    {"code": "DEMO-PJ-210", "name": "中江装配式住宅试点项目", "state": "in_progress", "with_chain": False},
    {"code": "DEMO-PJ-211", "name": "什邡产业园区停缓建整改项目", "state": "paused", "with_chain": False},
]


SHOWROOM_PROJECT_NAMES = tuple(spec["name"] for spec in SHOWROOM_PROJECTS)
