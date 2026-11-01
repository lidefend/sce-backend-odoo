# 253 · BNVA-02C-02B-01 · Retired 配置复核（6 条）

6 条 active=False：sc.payment.execution / sc.receipt.income / sc.invoice.registration /
sc.labor.usage / sc.subcontract.register / sc.equipment.usage。

结论：保持 retired，不恢复、不删除。运行时消费者引用未做真实验证（`not_run`，
需隔离库查询），只登记退役原因与历史引用，留待 02B-03 首次安装验证一并核实。

