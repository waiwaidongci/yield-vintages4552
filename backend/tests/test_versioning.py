"""查账日 as-of 版本、迟报更正边界、增量重算与幂等。"""
from datetime import date

import pytest

from src.models.entities import AuditJob, CurvePoint, BatchVersion, OutcomeVersion
from src.services.business import (create_line, save_batch, register_outcome,
                                   enqueue_audit, QUEUE_NAME)
from src.services.audit_compute import run_audit
from src.services.snapshot import build_snapshot
from src.utils import queue as q


class _U:
    def __init__(self, email):
        self.email = email


ADMIN = _U('admin@demo.local')


def _line(db):
    create_line(db, ADMIN, {'code': 'L1', 'name': '一号线'})
    create_line(db, ADMIN, {'code': 'L2', 'name': '二号线'})


def _batch(db, no, line='L1', ship='2026-01-01', enroll='2026-01-01', record='2026-01-02'):
    save_batch(db, ADMIN, {'batch_no': no, 'line_code': line, 'ship_date': ship,
                           'enroll_date': enroll, 'record_date': record})


def _drain():
    while q.pop(QUEUE_NAME) is not None:
        pass


def _job(db, audit_day):
    job, created = enqueue_audit(db, ADMIN, date.fromisoformat(audit_day))
    _drain()
    run_audit(db, job.id)
    return db.get(AuditJob, job.id)


def _points(db, job_id, line='L1'):
    return db.query(CurvePoint).filter_by(job_id=job_id, line_code=line)\
        .order_by(CurvePoint.day).all()


def test_asof_visibility_late_report_only_affects_new_audit(db):
    _line(db)
    _batch(db, 'B1')
    # 查账日 T1=01-31：无结局，B1 行政删失，曲线无事件
    j1 = _job(db, '2026-01-31')
    p1 = _points(db, j1.id)
    assert all(p.n_repair == 0 and p.n_scrap == 0 for p in p1)
    # 迟报：02-05 才到账，事件发生在 01-20
    register_outcome(db, ADMIN, {'batch_no': 'B1', 'outcome': 'repair',
                                 'event_date': '2026-01-20', 'reason': '控制板故障',
                                 'record_date': '2026-02-05'}, 'report')
    # T1 快照不被改写
    snap_old = build_snapshot(db, date(2026, 1, 31))
    assert snap_old[0]['outcome'] is None
    # 新查账日 T2 才能看到返修
    j2 = _job(db, '2026-02-10')
    p2 = _points(db, j2.id)
    assert any(p.n_repair == 1 for p in p2)
    assert p2[-1].cif_repair > 0
    # 旧曲线点物理上保持冻结
    frozen = _points(db, j1.id)
    assert all(p.n_repair == 0 for p in frozen)


def test_correction_incremental_recompute_and_whole_switch(db):
    _line(db)
    _batch(db, 'B1')
    _batch(db, 'B2', line='L2')
    register_outcome(db, ADMIN, {'batch_no': 'B1', 'outcome': 'repair',
                                 'event_date': '2026-01-15', 'reason': '密封件老化',
                                 'record_date': '2026-01-18'}, 'report')
    j1 = _job(db, '2026-02-01')
    assert j1.mode == 'full'
    old_l1 = [(p.day, p.cif_repair, p.cif_scrap) for p in _points(db, j1.id, 'L1')]
    old_l2 = [(p.day, p.cif_repair, p.cif_scrap) for p in _points(db, j1.id, 'L2')]

    # 02-08 更正：B1 返修→报废
    register_outcome(db, ADMIN, {'batch_no': 'B1', 'outcome': 'scrap',
                                 'event_date': '2026-01-15', 'reason': '结构断裂',
                                 'record_date': '2026-02-08'}, 'correct')
    j2 = _job(db, '2026-02-15')
    # 只有 L1 变动 → 增量模式
    assert j2.mode == 'incremental'
    assert j2.changed_lines == ['L1']
    new_l1 = [(p.day, p.cif_repair, p.cif_scrap) for p in _points(db, j2.id, 'L1')]
    new_l2 = [(p.day, p.cif_repair, p.cif_scrap) for p in _points(db, j2.id, 'L2')]
    # 受影响线从最早变动天数起重算：day14 前沿用（无点则整体一致），之后报废 CIF 抬升
    assert new_l1 != old_l1
    day14 = next(p for p in _points(db, j2.id, 'L1') if p.day == 14)
    assert day14.n_scrap == 1 and day14.n_repair == 0
    # 未受影响线整线沿用，逐点完全一致
    assert new_l2 == old_l2


def test_void_removes_effective_outcome(db):
    _line(db)
    _batch(db, 'B1')
    register_outcome(db, ADMIN, {'batch_no': 'B1', 'outcome': 'scrap',
                                 'event_date': '2026-01-10', 'reason': '腐蚀穿孔',
                                 'record_date': '2026-01-12'}, 'report')
    j1 = _job(db, '2026-02-01')
    assert any(p.n_scrap == 1 for p in _points(db, j1.id))
    register_outcome(db, ADMIN, {'batch_no': 'B1',
                                 'record_date': '2026-02-05'}, 'void')
    snap = build_snapshot(db, date(2026, 2, 10))
    assert snap[0]['outcome'] is None
    j2 = _job(db, '2026-02-10')
    assert all(p.n_scrap == 0 and p.n_repair == 0 for p in _points(db, j2.id))


def test_idempotent_audit_job_and_retry(db):
    _line(db)
    _batch(db, 'B1')
    j1, created1 = enqueue_audit(db, ADMIN, date(2026, 2, 1))
    j2, created2 = enqueue_audit(db, ADMIN, date(2026, 2, 1))
    assert j1.id == j2.id and created1 and not created2
    _drain()
    run_audit(db, j1.id)
    # 队列里重复消息不会产生第二条曲线
    q.push(QUEUE_NAME, j1.id)
    before = db.query(CurvePoint).filter_by(job_id=j1.id).count()
    item = q.pop(QUEUE_NAME)
    job = db.get(AuditJob, item)
    assert job.status == 'completed'  # worker 对 completed 消息直接丢弃
    assert db.query(CurvePoint).filter_by(job_id=j1.id).count() == before

    # 失败任务重试沿用原 job_id，曲线点先清后写不重复
    job.status = 'failed'
    db.commit()
    # 模拟 worker 重试：状态回 queued 并重新入队
    job.status = 'queued'
    db.commit()
    q.push(QUEUE_NAME, job.id)
    _drain()
    run_audit(db, job.id)
    assert db.get(AuditJob, j1.id).status == 'completed'
    ids = {p.id for p in db.query(CurvePoint).filter_by(job_id=j1.id).all()}
    assert len(ids) == db.query(CurvePoint).filter_by(job_id=j1.id).count()


def test_batch_correction_is_append_only(db):
    _line(db)
    _batch(db, 'B1', enroll='2026-01-03', record='2026-01-04')
    save_batch(db, ADMIN, {'batch_no': 'B1', 'line_code': 'L1', 'ship_date': '2026-01-01',
                           'enroll_date': '2026-01-02', 'record_date': '2026-02-01'})
    versions = db.query(BatchVersion).filter_by(batch_no='B1').order_by(BatchVersion.id).all()
    assert len(versions) == 2 and versions[1].superseded_id == versions[0].id
    # 旧查账日仍看到旧入组日
    old = build_snapshot(db, date(2026, 1, 31))
    assert old[0]['enroll_date'] == date(2026, 1, 3)
    new = build_snapshot(db, date(2026, 2, 10))
    assert new[0]['enroll_date'] == date(2026, 1, 2)


def test_validation_rejects_bad_dates_and_duplicate_report(db):
    _line(db)
    with pytest.raises(ValueError):
        save_batch(db, ADMIN, {'batch_no': 'X', 'line_code': 'L1', 'ship_date': '2026-01-05',
                               'enroll_date': '2026-01-01', 'record_date': '2026-01-06'})
    _batch(db, 'B9')
    register_outcome(db, ADMIN, {'batch_no': 'B9', 'outcome': 'repair',
                                 'event_date': '2026-01-10', 'reason': '异响复检',
                                 'record_date': '2026-01-11'}, 'report')
    with pytest.raises(Exception):
        register_outcome(db, ADMIN, {'batch_no': 'B9', 'outcome': 'scrap',
                                     'event_date': '2026-01-12', 'reason': '烧机报废',
                                     'record_date': '2026-01-13'}, 'report')
    # 删失不允许填失败原因
    with pytest.raises(ValueError):
        register_outcome(db, ADMIN, {'batch_no': 'B9', 'outcome': 'censor',
                                     'event_date': '2026-01-12', 'reason': '不应填写',
                                     'record_date': '2026-01-13'}, 'correct')
    # 任何结局不得早于入组日
    _batch(db, 'B8', enroll='2026-01-08', record='2026-01-09')
    with pytest.raises(Exception):
        register_outcome(db, ADMIN, {'batch_no': 'B8', 'outcome': 'censor',
                                     'event_date': '2026-01-05',
                                     'record_date': '2026-01-10'}, 'report')
    # 随访结束允许空原因（空字符串与 None 等价通过）
    _batch(db, 'B7', enroll='2026-01-02', record='2026-01-03')
    register_outcome(db, ADMIN, {'batch_no': 'B7', 'outcome': 'censor',
                                 'event_date': '2026-03-01', 'reason': '',
                                 'record_date': '2026-03-02'}, 'report')
    # 返修空原因仍被拒绝
    _batch(db, 'B6', enroll='2026-01-02', record='2026-01-03')
    with pytest.raises(ValueError):
        register_outcome(db, ADMIN, {'batch_no': 'B6', 'outcome': 'repair',
                                     'event_date': '2026-02-01', 'reason': '   ',
                                     'record_date': '2026-02-02'}, 'report')
