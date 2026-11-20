"""
确定性演示数据（固定随机源，不依赖外部系统）。
自然键幂等：重复执行不产生重复版本，也不覆盖用户已录入的数据。
场景覆盖：两条随访线随访长短不一；含迟报（record_date 晚于 event_date 很久）、
更正（correct 替换首报）、作废（void）以及随访结束删失。
"""
import json
import random
from datetime import date, timedelta

from src.config.database import Base, engine, Session
from src.models.entities import User, Line, BatchVersion, OutcomeVersion
from src.services.business import save_batch, register_outcome, create_line
from src.services.validation import validate_line
from src.utils.security import password_hash

LINES = [
    {'code': 'L-A', 'name': '一号随访线'},
    {'code': 'L-B', 'name': '二号随访线'},
]
REPAIR_REASONS = ['密封件老化', '控制板故障', '装配松动', '异响复检']
SCRAP_REASONS = ['结构断裂', '腐蚀穿孔', '烧机报废']


def _batch_rows():
    rng = random.Random(42)
    rows = []
    base = date(2026, 1, 5)
    for i in range(1, 41):
        line = LINES[i % 2]
        ship = base + timedelta(days=i * 2 + rng.randint(0, 3))
        enroll = ship + timedelta(days=rng.randint(0, 4))
        record = enroll + timedelta(days=rng.randint(0, 2))
        rows.append({'batch_no': f'B{i:03d}', 'line_code': line['code'],
                     'ship_date': ship.isoformat(), 'enroll_date': enroll.isoformat(),
                     'record_date': record.isoformat(), '_rng': rng.random()})
    return rows


def _outcome_rows(batches):
    rng = random.Random(7)
    out = []
    for idx, b in enumerate(batches, start=1):
        ship = date.fromisoformat(b['ship_date'])
        r = rng.random()
        if r < 0.45:  # 返修
            event = ship + timedelta(days=rng.randint(5, 90))
            out.append({'batch_no': b['batch_no'], 'action': 'report', 'outcome': 'repair',
                        'event_date': event.isoformat(),
                        'reason': REPAIR_REASONS[rng.randrange(len(REPAIR_REASONS))],
                        # 部分迟报：到账日比发生日晚 10 天以上
                        'record_date': (event + timedelta(days=rng.choice([1, 2, 12, 20]))).isoformat()})
        elif r < 0.6:  # 报废
            event = ship + timedelta(days=rng.randint(10, 120))
            out.append({'batch_no': b['batch_no'], 'action': 'report', 'outcome': 'scrap',
                        'event_date': event.isoformat(),
                        'reason': SCRAP_REASONS[rng.randrange(len(SCRAP_REASONS))],
                        'record_date': (event + timedelta(days=rng.choice([1, 15]))).isoformat()})
        elif r < 0.8:  # 随访结束删失
            event = ship + timedelta(days=rng.randint(60, 150))
            out.append({'batch_no': b['batch_no'], 'action': 'report', 'outcome': 'censor',
                        'event_date': event.isoformat(), 'reason': None,
                        'record_date': (event + timedelta(days=1)).isoformat()})
        # 其余批次尚无结局：在查账日行政删失
    # 演示一条更正流水：挑选事件日较早的返修批次，更改为报废（新到账日）
    target = next(x for x in out if x['outcome'] == 'repair'
                  and x['event_date'] < '2026-03-10')
    event_day = date.fromisoformat(target['event_date'])
    fixed = dict(target)
    fixed['action'] = 'correct'
    fixed['outcome'] = 'scrap'
    fixed['reason'] = '复检确认结构断裂'
    fixed['record_date'] = (event_day + timedelta(days=25)).isoformat()
    out.append(fixed)
    # 演示一条作废：B010 的登记被作废（批次回到无有效结局）
    if any(x['batch_no'] == 'B010' for x in out):
        out.append({'batch_no': 'B010', 'action': 'void',
                    'record_date': '2026-04-15'})
    return out


class _DemoUser:
    def __init__(self, email):
        self.email = email


def seed():
    Base.metadata.create_all(engine)
    with Session() as db:
        for role in ('admin', 'analyst', 'viewer'):
            email = f'{role}@demo.local'
            if not db.query(User).filter_by(email=email).first():
                db.add(User(email=email, role=role, password=password_hash('Demo2026!')))
        for data in LINES:
            validate_line(data)
            if not db.query(Line).filter_by(code=data['code']).first():
                create_line(db, _DemoUser('seed'), data)
        batches = _batch_rows()
        for data in batches:
            payload = {k: v for k, v in data.items() if k != '_rng'}
            if not db.query(BatchVersion).filter_by(batch_no=payload['batch_no']).first():
                save_batch(db, _DemoUser('seed'), payload)
        for data in _outcome_rows(batches):
            exists = db.query(OutcomeVersion).filter_by(
                batch_no=data['batch_no'], record_date=date.fromisoformat(data['record_date']),
                action=data['action']).first()
            if not exists:
                payload = {k: v for k, v in data.items() if k != 'action'}
                register_outcome(db, _DemoUser('seed'), payload, data['action'])
        db.commit()
        print(json.dumps({
            'users': db.query(User).count(), 'lines': db.query(Line).count(),
            'batch_versions': db.query(BatchVersion).count(),
            'outcome_versions': db.query(OutcomeVersion).count(),
        }, ensure_ascii=False))


if __name__ == '__main__':
    seed()
