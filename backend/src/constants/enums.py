# 角色沿用骨架：admin 负责人 / analyst 售后分析员 / viewer 只读阅读者
ROLES = ('admin', 'analyst', 'viewer')
# 查账任务状态沿用骨架枚举
STATUSES = ('queued', 'running', 'completed', 'failed')
# 批次首个结局：返修与报废互为竞争事件，随访结束为删失
OUTCOMES = ('repair', 'scrap', 'censor')
OUTCOME_LABELS = {'repair': '返修', 'scrap': '报废', 'censor': '随访结束'}
# 结局登记的更正类型
OUTCOME_ACTIONS = ('report', 'correct', 'void')
