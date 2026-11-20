from fastapi import APIRouter, Depends

from src.config.database import database
from src.controllers.auth import current
from src.models.entities import Audit
from src.utils.serialize import row

router = APIRouter()


@router.get('/audits/logs')
def logs(db=Depends(database), u=Depends(current)):
    return [row(x) for x in db.query(Audit).order_by(Audit.id.desc()).limit(200).all()]
