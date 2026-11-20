"""
查账日快照：按 record_date 可见性规则还原某个查账日能看到的批次与结局版本。
迟报与更正只影响新查账日——历史查账日的曲线已冻结，永不被改写。
"""
from collections import defaultdict

from src.models.entities import BatchVersion, OutcomeVersion, Line


def visible_batches(db, audit_date):
    """每个 batch_no 取 record_date<=audit_date 的最新批次版本。"""
    rows = db.query(BatchVersion).filter(BatchVersion.record_date <= audit_date).all()
    latest = {}
    for row in rows:  # 同批次后写入的版本 id 更大，天然为更新版本
        prev = latest.get(row.batch_no)
        if prev is None or row.id > prev.id:
            latest[row.batch_no] = row
    return list(latest.values())


def visible_outcomes(db, audit_date):
    """
    每个 batch_no 取 record_date<=audit_date 的最新流水：
    最新为 void 则该批次在该查账日无有效结局；否则取其 report/correct 内容。
    """
    rows = db.query(OutcomeVersion).filter(OutcomeVersion.record_date <= audit_date).all()
    latest = {}
    for row in rows:
        prev = latest.get(row.batch_no)
        if prev is None or row.id > prev.id:
            latest[row.batch_no] = row
    return [row for row in latest.values() if row.action != 'void']


def line_map(db):
    return {x.code: x for x in db.query(Line).all()}


def build_snapshot(db, audit_date):
    """组装查账日全量快照：批次（含出厂/入组日）与其有效首个结局。"""
    batches = visible_batches(db, audit_date)
    outcomes = {row.batch_no: row for row in visible_outcomes(db, audit_date)}
    lines = line_map(db)
    items = []
    for b in batches:
        o = outcomes.get(b.batch_no)
        items.append({
            'batch_no': b.batch_no,
            'line_code': b.line_code,
            'line_name': lines.get(b.line_code).name if b.line_code in lines else b.line_code,
            'ship_date': b.ship_date,
            'enroll_date': b.enroll_date,
            'outcome': o.outcome if o else None,
            'event_date': o.event_date if o else None,
            'reason': o.reason if o else None,
        })
    return items


def changed_line_codes(db, prev_audit_date, audit_date):
    """
    两个查账日之间发生过批次版本或结局流水变动的线。
    增量重算只重算这些线，其余线沿用上一版曲线。
    """
    q1 = db.query(BatchVersion.line_code).filter(
        BatchVersion.record_date > prev_audit_date,
        BatchVersion.record_date <= audit_date)
    # 结局流水本身不带线，先取变动批次号，再映射到其最新批次版本所属线
    changed_batches = {r[0] for r in db.query(OutcomeVersion.batch_no).filter(
        OutcomeVersion.record_date > prev_audit_date,
        OutcomeVersion.record_date <= audit_date).all()}
    codes = {r[0] for r in q1.all()}
    if changed_batches:
        mapped = db.query(BatchVersion.line_code, BatchVersion.batch_no).filter(
            BatchVersion.batch_no.in_(changed_batches)).all()
        latest_line = {}
        for line_code, batch_no in mapped:
            latest_line[batch_no] = line_code
        codes.update(latest_line.values())
    return sorted(c for c in codes if c)
