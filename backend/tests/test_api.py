"""HTTP 层冒烟：登录、录入、查账任务、曲线查看与角色权限。"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.config.database import Base, engine


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from scripts.seed_demo import seed
    seed()
    return TestClient(app)


def _token(client, role):
    r = client.post('/auth/login', json={'email': f'{role}@demo.local', 'password': 'Demo2026!'})
    assert r.status_code == 200
    return r.json()['token']


def _h(token):
    return {'Authorization': f'Bearer {token}'}


def test_full_flow_and_viewer_readonly(client):
    admin = _token(client, 'admin')
    viewer = _token(client, 'viewer')
    # viewer 不可写入
    r = client.post('/lines', json={'data': {'code': 'LX', 'name': '新线'}}, headers=_h(viewer))
    assert r.status_code == 403
    # 录入新线与批次
    r = client.post('/lines', json={'data': {'code': 'LX', 'name': '三号线'}}, headers=_h(admin))
    assert r.status_code == 200
    r = client.post('/batches', json={'data': {
        'batch_no': 'BX1', 'line_code': 'LX', 'ship_date': '2026-01-01',
        'enroll_date': '2026-01-02', 'record_date': '2026-01-03'}}, headers=_h(admin))
    assert r.status_code == 200
    r = client.post('/outcomes/report', json={'data': {
        'batch_no': 'BX1', 'outcome': 'repair', 'event_date': '2026-02-01',
        'reason': '装配松动', 'record_date': '2026-02-03'}}, headers=_h(admin))
    assert r.status_code == 200
    # 非法日期 422
    r = client.post('/batches', json={'data': {
        'batch_no': 'BX2', 'line_code': 'LX', 'ship_date': 'bad',
        'enroll_date': '2026-01-02', 'record_date': '2026-01-03'}}, headers=_h(admin))
    assert r.status_code == 422
    # 创建查账日任务并直接同步核算（测试中手动触发 service）
    r = client.post('/audits/jobs', json={'audit_date': '2026-05-01'}, headers=_h(admin))
    assert r.status_code == 200 and r.json()['status'] == 'queued'
    job_id = r.json()['id']
    from src.config.database import Session
    from src.services.audit_compute import run_audit
    with Session() as db:
        run_audit(db, job_id)
    r = client.get(f'/audits/jobs/{job_id}/curves', headers=_h(viewer))
    assert r.status_code == 200
    body = r.json()
    assert 'LX' in body['lines']
    r = client.get(f'/audits/jobs/{job_id}/reasons', headers=_h(viewer))
    assert r.status_code == 200 and any(x['reason'] == '装配松动' for x in r.json())
    # 同查账日重复创建不产生新任务
    r2 = client.post('/audits/jobs', json={'audit_date': '2026-05-01'}, headers=_h(admin))
    assert r2.json()['id'] == job_id and r2.json()['created'] is False
    # 留痕可查
    r = client.get('/audits/logs', headers=_h(admin))
    assert r.status_code == 200 and len(r.json()) > 0
    # 健康检查与元数据
    assert client.get('/health').json()['status'] == 'healthy'
    assert client.get('/meta').json()['slug'] == 'aftersales-cif'


def test_analyst_can_write_but_not_admin_only(client):
    analyst = _token(client, 'analyst')
    r = client.post('/batches', json={'data': {
        'batch_no': 'BA1', 'line_code': 'L-A', 'ship_date': '2026-01-01',
        'enroll_date': '2026-01-01', 'record_date': '2026-01-02'}}, headers=_h(analyst))
    assert r.status_code == 200
    # 未登录被拒
    assert client.get('/lines').status_code == 401
