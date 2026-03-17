from fastapi.testclient import TestClient

from services.api.app.main import app


def test_diagnostics_endpoints_shape():
    c = TestClient(app)
    assert c.get('/diagnostics/health').status_code == 200
    perf = c.get('/diagnostics/performance').json()
    assert 'module_timings_s' in perf
    caches = c.get('/diagnostics/caches').json()
    assert 'snapshot_count' in caches
    run = c.get('/diagnostics/run').json()
    assert 'metadata' in run


def test_scenario_load_and_tuning_visibility():
    c = TestClient(app)
    scenarios = c.get('/scenarios').json()
    assert scenarios
    sid = scenarios[0]['scenario_id']
    out = c.post('/scenarios/load', json={'scenario_id': sid}).json()
    assert out['loaded'] == sid

    t = c.get('/tuning').json()
    assert 'media' in t
    upd = c.post('/tuning', json={'config': {'media': {'issue_interval': 4}}}).json()
    assert upd['updated'] is True
    assert upd['tuning']['media']['issue_interval'] == 4


def test_description_scheduler_queue_and_status():
    c = TestClient(app)
    queued = c.post('/descriptions/queue', json={'items': [{'entity_id': 'n1', 'role': 'nation', 'name': 'N1'}]}).json()
    assert queued['queued'] == 1
    processed = c.post('/descriptions/process?limit=5').json()
    assert processed['processed'] >= 1
    status = c.get('/descriptions/status').json()
    assert 'cache_size' in status


def test_replay_status_and_snapshot_endpoints():
    c = TestClient(app)
    c.post('/simulation/step', json={'ticks': 1})
    save = c.post('/snapshots/save').json()
    assert 'snapshot_id' in save
    lst = c.get('/snapshots').json()
    assert isinstance(lst, list) and lst
    load = c.post('/snapshots/load', json={'snapshot_id': save['snapshot_id']}).json()
    assert load.get('loaded') == save['snapshot_id']
    rep = c.get('/replay/status').json()
    assert 'replay_mode' in rep
