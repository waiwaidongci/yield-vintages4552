"""查账核算 worker：轮询队列，中断后重启自动恢复 running 原单，重试不重复出曲线。"""
import time
import traceback
from pathlib import Path

from src.config.database import Base, engine, Session
from src.models.entities import AuditJob
from src.services.audit_compute import run_audit
from src.services.business import QUEUE_NAME
from src.utils.queue import pop

Base.metadata.create_all(engine)


def main():
    while True:
        try:
            Path('/tmp/worker-heartbeat').write_text(str(time.time()))
        except Exception:
            pass
        try:
            # 恢复中断：重启前卡在 running 的任务按原单继续，不新建任务
            with Session() as db:
                stuck = db.query(AuditJob).filter_by(status='running').all()
                for job in stuck:
                    try:
                        run_audit(db, job.id)
                    except Exception:
                        traceback.print_exc()
            item = pop(QUEUE_NAME)
            if item is not None:
                with Session() as db:
                    job = db.get(AuditJob, int(item))
                    # queued 才执行；completed/failed 的重复消息直接丢弃，保证幂等
                    if job and job.status == 'queued':
                        try:
                            run_audit(db, job.id)
                        except Exception:
                            traceback.print_exc()
        except Exception:
            traceback.print_exc()
        time.sleep(1)


if __name__ == '__main__':
    main()
