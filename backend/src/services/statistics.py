"""
竞争风险寿命表（Aalen-Johansen 累计发生函数）。

时间原点：出厂日；时间尺度：出厂后天数 day = 事件日 - 出厂日。
每个事件日的处理顺序（需求硬性口径）：
  1. 先入组：enroll_day == day 的批次当日进入在险集（同日入组即承担当日风险）；
  2. 再用同一在险批数 n_risk 累计返修与报废风险（竞争事件同日并列，分母相同）；
  3. 最后移除随访结束的批次（删失在当日事件核算之后才离开）。
查账日仍未发生结局的批次，在查账日做行政删失（只影响在险数，不计入 n_censor 业务列）。
"""
from collections import defaultdict
from datetime import date


def _days(ship, target):
    return (target - ship).days


def build_line_curve(batches, audit_date):
    """
    batches: build_snapshot 中属于同一条线的条目列表。
    返回寿命表行列表，每行含 day/n_risk/n_repair/n_scrap/n_censor/cif_*。
    """
    enroll_at = defaultdict(list)   # day -> [batch]
    events = []                     # (day, outcome, reason)
    censor_days = defaultdict(int)
    admin_censor_days = defaultdict(int)  # 查账日行政删失：离开在险集但不计入业务随访结束列
    reason_counter = defaultdict(int)
    day_set = set()

    for b in batches:
        ship = b['ship_date']
        enroll_day = _days(ship, b['enroll_date'])
        if enroll_day < 0:
            raise ValueError(f"批次 {b['batch_no']} 入组早于出厂，数据不合法")
        enroll_at[enroll_day].append(b)
        day_set.add(enroll_day)
        audit_day = _days(ship, audit_date)
        if b['outcome'] in ('repair', 'scrap'):
            if b['event_date'] < b['enroll_date']:
                raise ValueError(f"批次 {b['batch_no']} 结局早于入组，数据不合法")
            day = _days(ship, b['event_date'])
            if day > audit_day:
                # 结局发生日晚于查账日：查账日尚不可见，查账日行政删失
                admin_censor_days[audit_day] += 1
                day_set.add(audit_day)
                continue
            events.append((day, b['outcome'], b.get('reason') or '未填写原因'))
            day_set.add(day)
        elif b['outcome'] == 'censor':
            if b['event_date'] < b['enroll_date']:
                raise ValueError(f"批次 {b['batch_no']} 随访结束早于入组，数据不合法")
            day = _days(ship, b['event_date'])
            censor_days[day] += 1
            day_set.add(day)
        else:
            # 无任何结局登记：行政删失于查账日
            admin_censor_days[audit_day] += 1
            day_set.add(audit_day)

    repair_at = defaultdict(int)
    scrap_at = defaultdict(int)
    for day, outcome, reason in events:
        if outcome == 'repair':
            repair_at[day] += 1
            reason_counter[('repair', reason)] += 1
        else:
            scrap_at[day] += 1
            reason_counter[('scrap', reason)] += 1

    in_risk = 0
    cif_repair = 0.0
    cif_scrap = 0.0
    rows = []
    for day in sorted(day_set):
        # 1) 先入组
        in_risk += len(enroll_at.get(day, ()))
        n_risk = in_risk
        n_repair = repair_at.get(day, 0)
        n_scrap = scrap_at.get(day, 0)
        n_censor = censor_days.get(day, 0)
        n_admin = admin_censor_days.get(day, 0)
        if n_risk <= 0:
            continue
        # 2) 同一在险批数下并列累计两类竞争事件
        h_repair = n_repair / n_risk
        h_scrap = n_scrap / n_risk
        survival_prev = 1.0 - cif_repair - cif_scrap
        cif_repair += survival_prev * h_repair
        cif_scrap += survival_prev * h_scrap
        # 3) 最后移除随访结束与当日终止事件批次；行政删失同样离开在险集（不计业务删失列）
        in_risk -= (n_repair + n_scrap + n_censor + n_admin)
        rows.append({
            'day': day,
            'n_risk': n_risk,
            'n_repair': n_repair,
            'n_scrap': n_scrap,
            'n_censor': n_censor,
            'cif_repair': round(cif_repair, 10),
            'cif_scrap': round(cif_scrap, 10),
            'survival': round(1.0 - cif_repair - cif_scrap, 10),
        })
    reasons = [{'outcome': k[0], 'reason': k[1], 'n_batches': v}
               for k, v in sorted(reason_counter.items(), key=lambda kv: (-kv[1], kv[0]))]
    return rows, reasons


def build_curves(snapshot, audit_date):
    """按线分组构建全部曲线，返回 {line_code: {rows, reasons, batch_count}}。"""
    grouped = defaultdict(list)
    names = {}
    for item in snapshot:
        grouped[item['line_code']].append(item)
        names[item['line_code']] = item['line_name']
    result = {}
    for line_code, items in sorted(grouped.items()):
        rows, reasons = build_line_curve(items, audit_date)
        result[line_code] = {
            'line_name': names[line_code],
            'batch_count': len(items),
            'rows': rows,
            'reasons': reasons,
        }
    return result


def earliest_changed_day(prev_rows, new_rows):
    """
    两版曲线首个发生数值差异的天数；无差异返回 None。
    增量重算从该天数起切换，之前的点沿用上一版。
    """
    prev_map = {r['day']: r for r in prev_rows}
    new_map = {r['day']: r for r in new_rows}
    for day in sorted(set(prev_map) | set(new_map)):
        p, n = prev_map.get(day), new_map.get(day)
        if p is None or n is None or any(p[k] != n[k] for k in
                                          ('n_risk', 'n_repair', 'n_scrap', 'n_censor')):
            return day
    return None
