from fastapi import APIRouter, Depends

from src.config.database import database
from src.controllers.auth import current, editor
from src.models.entities import Line, BatchVersion, OutcomeVersion
from src.services.business import create_line, save_batch, register_outcome
from src.utils.serialize import row

router = APIRouter()


@router.get('/lines')
def lines(db=Depends(database), u=Depends(current)):
    return [row(x) for x in db.query(Line).order_by(Line.code).all()]


@router.post('/lines')
def create(b: dict, db=Depends(database), u=Depends(editor)):
    return row(create_line(db, u, b['data']))


@router.get('/batches')
def batches(db=Depends(database), u=Depends(current)):
    # 返回每个批次的最新版本及其版本数，便于页面查看更正历史
    latest = {}
    for v in db.query(BatchVersion).order_by(BatchVersion.id).all():
        latest[v.batch_no] = v
    versions = {}
    for v in db.query(BatchVersion).all():
        versions[v.batch_no] = versions.get(v.batch_no, 0) + 1
    out = []
    for v in sorted(latest.values(), key=lambda x: (x.line_code, x.batch_no)):
        d = row(v)
        d['version_count'] = versions[v.batch_no]
        out.append(d)
    return out


@router.get('/batches/{batch_no}/versions')
def batch_versions(batch_no: str, db=Depends(database), u=Depends(current)):
    rows = db.query(BatchVersion).filter_by(batch_no=batch_no).order_by(BatchVersion.id).all()
    return [row(x) for x in rows]


@router.post('/batches')
def save(b: dict, db=Depends(database), u=Depends(editor)):
    return row(save_batch(db, u, b['data']))


@router.get('/outcomes')
def outcomes(db=Depends(database), u=Depends(current)):
    return [row(x) for x in db.query(OutcomeVersion).order_by(OutcomeVersion.id.desc()).limit(500).all()]


@router.post('/outcomes/report')
def report(b: dict, db=Depends(database), u=Depends(editor)):
    return row(register_outcome(db, u, b['data'], 'report'))


@router.post('/outcomes/correct')
def correct(b: dict, db=Depends(database), u=Depends(editor)):
    return row(register_outcome(db, u, b['data'], 'correct'))


@router.post('/outcomes/void')
def void(b: dict, db=Depends(database), u=Depends(editor)):
    return row(register_outcome(db, u, b['data'], 'void'))
