"""手算 oracle：同日先入组、再并列累计返修/报废、最后移除随访结束。"""
from datetime import date

from src.services.statistics import build_line_curve, earliest_changed_day

SHIP = date(2026, 1, 1)
AUDIT = date(2026, 2, 1)


def _b(no, enroll_off, outcome=None, event_off=None, reason=None):
    return {
        'batch_no': no, 'line_code': 'L1', 'line_name': '一号线',
        'ship_date': SHIP, 'enroll_date': SHIP + __import__('datetime').timedelta(days=enroll_off),
        'outcome': outcome,
        'event_date': SHIP + __import__('datetime').timedelta(days=event_off) if event_off is not None else None,
        'reason': reason,
    }


def test_ordering_and_competing_risks_hand_calc():
    # B1 day0 入组，day10 返修；B2 day5 入组，day20 随访结束；
    # B3 day10 入组且 day10 报废（同日入组即承担当日风险）
    rows, reasons = build_line_curve([
        _b('B1', 0, 'repair', 10, '密封件老化'),
        _b('B2', 5, 'censor', 20),
        _b('B3', 10, 'scrap', 10, '结构断裂'),
    ], AUDIT)
    by_day = {r['day']: r for r in rows}
    assert by_day[0]['n_risk'] == 1 and by_day[0]['n_repair'] == 0
    assert by_day[5]['n_risk'] == 2
    d10 = by_day[10]
    # 同日入组先发生：3 批同在险；返修与报废共用同一分母 3
    assert d10['n_risk'] == 3 and d10['n_repair'] == 1 and d10['n_scrap'] == 1
    assert abs(d10['cif_repair'] - 1 / 3) < 1e-9
    assert abs(d10['cif_scrap'] - 1 / 3) < 1e-9
    assert abs(d10['survival'] - 1 / 3) < 1e-9
    # 随访结束最后移除：day20 在险只剩 B2，删失不改变 CIF
    d20 = by_day[20]
    assert d20['n_risk'] == 1 and d20['n_censor'] == 1
    assert abs(d20['cif_repair'] - 1 / 3) < 1e-9 and abs(d20['cif_scrap'] - 1 / 3) < 1e-9
    assert {(r['outcome'], r['reason'], r['n_batches']) for r in reasons} == {
        ('repair', '密封件老化', 1), ('scrap', '结构断裂', 1)}


def test_aj_multi_step_accumulation():
    # day5：4 批在险，1 返修 1 报废 → 各 CIF=0.25，存活 0.5
    # day10：剩 2 批，1 返修 → CIF_repair += 0.5*0.5=0.25 → 0.5
    batches = [
        _b('B1', 0, 'repair', 5), _b('B2', 0, 'scrap', 5),
        _b('B3', 0, 'repair', 10), _b('B4', 0),
    ]
    rows, _ = build_line_curve(batches, AUDIT)
    by_day = {r['day']: r for r in rows}
    assert abs(by_day[5]['cif_repair'] - 0.25) < 1e-9
    assert abs(by_day[5]['cif_scrap'] - 0.25) < 1e-9
    assert abs(by_day[10]['cif_repair'] - 0.5) < 1e-9
    assert abs(by_day[10]['cif_scrap'] - 0.25) < 1e-9
    assert abs(by_day[10]['survival'] - 0.25) < 1e-9


def test_administrative_censoring_removes_from_risk():
    # B1 出厂 01-01，day30 返修；B2 出厂 01-11，无结局，查账日 01-31 为其 day20 行政删失。
    # B1 返修时 B2 已离场：day30 在险只剩 B1，n_risk=1，返修 CIF 直接到 1，
    # 若行政删失未正确移除则会被 B2 稀释成 0.5。
    rows, _ = build_line_curve([
        _b('B1', 0, 'repair', 30, '控制板故障'),
        {'batch_no': 'B2', 'line_code': 'L1', 'line_name': '一号线',
         'ship_date': date(2026, 1, 11), 'enroll_date': date(2026, 1, 11),
         'outcome': None, 'event_date': None, 'reason': None},
    ], date(2026, 1, 31))
    by_day = {r['day']: r for r in rows}
    d20, d30 = by_day[20], by_day[30]
    assert d20['n_risk'] == 2 and d20['n_censor'] == 0  # 行政删失不计业务随访结束列
    assert d30['n_risk'] == 1 and d30['n_repair'] == 1
    assert abs(d30['cif_repair'] - 1.0) < 1e-9


def test_earliest_changed_day():
    old = [{'day': 0, 'n_risk': 1, 'n_repair': 0, 'n_scrap': 0, 'n_censor': 0}]
    new = [{'day': 0, 'n_risk': 1, 'n_repair': 0, 'n_scrap': 0, 'n_censor': 0},
           {'day': 3, 'n_risk': 2, 'n_repair': 1, 'n_scrap': 0, 'n_censor': 0}]
    assert earliest_changed_day(old, new) == 3
    assert earliest_changed_day(old, [dict(old[0])]) is None
