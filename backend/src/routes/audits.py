from fastapi import APIRouter, Depends, HTTPException

from src.config.database import database
from src.controllers.auth import current, editor
from src.models.entities import AuditJob, CurvePoint, ReasonStat
from src.schemas.requests import AuditInput
from src.services.business import enqueue_audit
from src.services.validation import validate_audit_date
from src.utils.serialize import row

router = APIRouter()


@router.get('/audits/jobs')
def jobs(db=Depends(database), u=Depends(current)):
    return [row(x) for x in db.query(AuditJob).order_by(AuditJob.audit_date.desc()).all()]


@router.post('/audits/jobs')
def create_job(b: AuditInput, db=Depends(database), u=Depends(editor)):
    audit_date = validate_audit_date(b.audit_date)
    obj, created = enqueue_audit(db, u, audit_date)
    return {**row(obj), 'created': created}


@router.post('/audits/jobs/{job_id}/retry')
def retry_job(job_id: int, db=Depends(database), u=Depends(editor)):
    # 仅失败任务可重试；沿用原 job_id，重新入队，不产生重复曲线
    obj = db.get(AuditJob, job_id)
    if not obj:
        raise HTTPException(404, '查账任务不存在')
    if obj.status != 'failed':
        raise HTTPException(409, '仅失败任务允许重试')
    obj.status = 'queued'
    obj.error = None
    db.commit()
    from src.utils.queue import push
    from src.services.business import QUEUE_NAME
    push(QUEUE_NAME, obj.id)
    return row(obj)


@router.get('/audits/jobs/{job_id}/curves')
def curves(job_id: int, db=Depends(database), u=Depends(current)):
    job = db.get(AuditJob, job_id)
    if not job:
        raise HTTPException(404, '查账任务不存在')
    if job.status != 'completed':
        raise HTTPException(409, '该查账日尚未核算完成')
    points = db.query(CurvePoint).filter_by(job_id=job_id).order_by(
        CurvePoint.line_code, CurvePoint.day).all()
    by_line = {}
    for p in points:
        by_line.setdefault(p.line_code, []).append(row(p))
    return {'job': row(job), 'lines': by_line}


@router.get('/audits/jobs/{job_id}/reasons')
def reasons(job_id: int, db=Depends(database), u=Depends(current)):
    job = db.get(AuditJob, job_id)
    if not job:
        raise HTTPException(404, '查账任务不存在')
    if job.status != 'completed':
        raise HTTPException(409, '该查账日尚未核算完成')
    rows = db.query(ReasonStat).filter_by(job_id=job_id).order_by(
        ReasonStat.line_code, ReasonStat.outcome, ReasonStat.n_batches.desc()).all()
    return [row(x) for x in rows]
