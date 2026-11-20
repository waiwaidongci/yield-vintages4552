"""
查账日核算编排：
- 按查账日可见版本构建快照并核算各线 Aalen-Johansen 曲线；
- 存在上一查账日时，仅对有变动的线从「最早变动天数」起重算，其余沿用旧点；
- 所有曲线点在同一事务内写入，整条曲线一次性切换，无中间态；
- 同一查账日任务唯一，中断重试只更新原任务，绝不重复出曲线。
"""
import time

from sqlalchemy import delete

from src.models.entities import AuditJob, CurvePoint, ReasonStat
from src.services.snapshot import build_snapshot, changed_line_codes
from src.services.statistics import build_curves, earliest_changed_day


def _latest_job(db, audit_date):
    return db.query(AuditJob).filter(AuditJob.audit_date < audit_date)\
        .order_by(AuditJob.audit_date.desc()).first()


def _persist(db, job_id, curves, prev_points, changed_codes, full_mode):
    points, reasons = [], []
    for line_code, payload in curves.items():
        new_rows = payload['rows']
        if not full_mode and line_code not in changed_codes:
            # 未受影响线：整线沿用上一查账日的点
            rows = [r for r in prev_points.get(line_code, ())]
        elif not full_mode and line_code in prev_points:
            cut = earliest_changed_day(prev_points[line_code], new_rows)
            if cut is None:
                rows = prev_points[line_code]
            else:
                prefix = [r for r in prev_points[line_code] if r['day'] < cut]
                suffix = [r for r in new_rows if r['day'] >= cut]
                rows = prefix + suffix
        else:
            rows = new_rows
        for r in rows:
            points.append(CurvePoint(
                job_id=job_id, line_code=line_code, day=r['day'], n_risk=r['n_risk'],
                n_repair=r['n_repair'], n_scrap=r['n_scrap'], n_censor=r['n_censor'],
                cif_repair=r['cif_repair'], cif_scrap=r['cif_scrap'], survival=r['survival']))
        for rs in payload['reasons']:
            reasons.append(ReasonStat(
                job_id=job_id, line_code=line_code, outcome=rs['outcome'],
                reason=rs['reason'], n_batches=rs['n_batches']))
    # 同事务先清后写：失败整体回滚，外部永远只看到完整的一版曲线
    db.execute(delete(CurvePoint).where(CurvePoint.job_id == job_id))
    db.execute(delete(ReasonStat).where(ReasonStat.job_id == job_id))
    db.add_all(points)
    db.add_all(reasons)


def run_audit(db, job_id):
    job = db.get(AuditJob, job_id)
    if not job:
        raise ValueError('查账任务不存在')
    job.status = 'running'
    job.started = time.time()
    db.commit()
    try:
        audit_date = job.audit_date
        snapshot = build_snapshot(db, audit_date)
        if not snapshot:
            raise ValueError('该查账日尚无可视批次，无法核算曲线')
        curves = build_curves(snapshot, audit_date)

        prev = _latest_job(db, audit_date)
        prev_points = {}
        changed_codes = set()
        full_mode = True
        if prev and prev.status == 'completed':
            for p in db.query(CurvePoint).filter_by(job_id=prev.id).all():
                prev_points.setdefault(p.line_code, []).append({
                    'day': p.day, 'n_risk': p.n_risk, 'n_repair': p.n_repair,
                    'n_scrap': p.n_scrap, 'n_censor': p.n_censor,
                    'cif_repair': p.cif_repair, 'cif_scrap': p.cif_scrap,
                    'survival': p.survival})
            changed_codes = set(changed_line_codes(db, prev.audit_date, audit_date))
            # 出现上一版没有的全新随访线时，无法沿用，退化为整体重算
            full_mode = bool(changed_codes - set(prev_points))

        _persist(db, job_id, curves, prev_points, changed_codes, full_mode)
        job.mode = 'full' if full_mode else 'incremental'
        job.changed_lines = sorted(changed_codes)
        job.status = 'completed'
        job.error = None
        job.finished = time.time()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(AuditJob, job_id)
        job.status = 'failed'
        job.error = str(exc)
        job.finished = time.time()
        db.commit()
        raise
