# 初始结构

SQLAlchemy 启动创建以下表：users、audits、lines、batch_versions、outcome_versions、audit_jobs、curve_points、reason_stats。

- `lines` 随访线字典；各线随访长短不一，曲线按线分别核算。
- `batch_versions` 批次有效日期版本（append-only）：录入与更正均新增行，`record_date` 决定查账日可见性；查账日 T 仅取 `record_date<=T` 的每个批次最新版本。
- `outcome_versions` 结局流水（report/correct/void，append-only）：查账日 T 取每批次 `record_date<=T` 最新流水，最新为 void 则无有效结局。迟报与更正只影响新查账日，历史曲线不被改写。
- `audit_jobs` 查账日任务：`audit_date` 唯一，中断重试复用原任务；mode 记录 full/incremental，changed_lines 记录受影响线。
- `curve_points` 查账日×线×出厂后天数的寿命表点（n_risk/n_repair/n_scrap/n_censor 与两条 CIF），随任务在同一事务内一次性切换。
- `reason_stats` 查账日×线×结局×失败原因的累计批数。

口径：同日先入组，再以同一在险批数并列核算返修/报废风险，最后移除随访结束批次；Aalen-Johansen CIF 增量 = 上一步存活占比 × 当日在险事件率。已有数据库升级需先备份，后续字段演进以独立迁移执行。
