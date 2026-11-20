"""业务录入：随访线、批次版本（append-only）、结局流水（report/correct/void）。"""
import time

from fastapi import HTTPException

from src.models.entities import Line, BatchVersion, OutcomeVersion, AuditJob
from src.services.audit import log
from src.services.validation import validate_line, validate_batch, validate_outcome
from src.utils.queue import push

QUEUE_NAME = 'audit-jobs'


def create_line(db, user, data):
    data = validate_line(data)
    if db.query(Line).filter_by(code=data['code']).first():
        raise HTTPException(409, '随访线编号已存在')
    obj = Line(code=data['code'], name=data['name'], created=time.time())
    db.add(obj)
    log(db, user.email, 'line.create', f"{data['code']}/{data['name']}")
    db.commit()
    return obj


def save_batch(db, user, data):
    """批次录入或更正：一律新增有效日期版本，不覆盖旧版本。"""
    data = validate_batch(data)
    if not db.query(Line).filter_by(code=data['line_code']).first():
        raise HTTPException(422, '随访线不存在，请先建档')
    latest = db.query(BatchVersion).filter_by(batch_no=data['batch_no'])\
        .order_by(BatchVersion.id.desc()).first()
    if latest and latest.line_code != data['line_code']:
        raise HTTPException(422, '批次所属随访线不可通过更正变更')
    obj = BatchVersion(
        batch_no=data['batch_no'], line_code=data['line_code'],
        ship_date=data['ship_date'], enroll_date=data['enroll_date'],
        record_date=data['record_date'], superseded_id=latest.id if latest else 0,
        actor=user.email, created=time.time())
    db.add(obj)
    log(db, user.email, 'batch.version',
        f"{data['batch_no']} 版本到账日 {data['record_date']}")
    db.commit()
    return obj


def _require_batch(db, batch_no):
    obj = db.query(BatchVersion).filter_by(batch_no=batch_no)\
        .order_by(BatchVersion.id.desc()).first()
    if not obj:
        raise HTTPException(422, '批次不存在，请先录入出厂与入组信息')
    return obj


def register_outcome(db, user, data, action):
    """report 首报 / correct 更正 / void 作废，均追加一条结局流水。"""
    void = action == 'void'
    data = validate_outcome(data, void=void)
    batch = _require_batch(db, data['batch_no'])
    latest = db.query(OutcomeVersion).filter_by(batch_no=data['batch_no'])\
        .order_by(OutcomeVersion.id.desc()).first()
    if action == 'report' and latest and latest.action != 'void':
        raise HTTPException(409, '该批次已有有效结局登记，请使用更正而非重复首报')
    if action in ('correct', 'void') and (not latest or latest.action == 'void'):
        raise HTTPException(409, '该批次没有可更正/作废的有效结局登记')
    if not void and data['event_date'] < batch.ship_date:
        raise HTTPException(422, '结局发生日期不能早于出厂日期')
    if not void and data['event_date'] < batch.enroll_date:
        raise HTTPException(422, '结局发生日期不能早于入组日期')
    if not void and data['record_date'] < data['event_date']:
        raise HTTPException(422, '到账日期不能早于结局发生日期（不允许倒签）')
    obj = OutcomeVersion(
        batch_no=data['batch_no'], action=action,
        outcome=None if void else data['outcome'],
        event_date=None if void else data['event_date'],
        reason=None if void else data['reason'],
        record_date=data['record_date'], actor=user.email, created=time.time())
    db.add(obj)
    log(db, user.email, f'outcome.{action}',
        f"{data['batch_no']} 到账日 {data['record_date']}")
    db.commit()
    return obj


def enqueue_audit(db, user, audit_date):
    """同一查账日任务唯一：已存在则原样返回（中断恢复原单，重试不重复出曲线）。"""
    existing = db.query(AuditJob).filter_by(audit_date=audit_date).first()
    if existing:
        return existing, False
    obj = AuditJob(audit_date=audit_date, status='queued', mode='',
                   changed_lines=[], created=time.time(), actor=user.email)
    db.add(obj)
    log(db, user.email, 'audit.enqueue', f'查账日 {audit_date}')
    db.commit()
    push(QUEUE_NAME, obj.id)
    return obj, True
