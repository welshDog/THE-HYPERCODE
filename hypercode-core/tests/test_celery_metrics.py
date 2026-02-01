import time
from types import SimpleNamespace

class FakeRedis:
  def __init__(self):
    self.store = {}
  def incr(self, k):
    self.store[k] = int(self.store.get(k, 0)) + 1
  def expire(self, k, ttl):
    pass
  def set(self, k, v, ex=None):
    self.store[k] = v
  def get(self, k):
    return self.store.get(k)
  def keys(self, pattern):
    return [bytes(k, 'utf-8') for k in self.store.keys() if 'success' in k]

def test_signal_counters(monkeypatch):
  import hypercode.worker as w
  fake = FakeRedis()
  monkeypatch.setattr(w, 'r', fake)
  sender = SimpleNamespace(request=SimpleNamespace(hostname='workerA'))
  w.on_task_success(sender=sender)
  w.on_task_failure(sender=sender)
  w.on_task_retry(sender=sender)
  assert fake.get('celery:worker:workerA:success') == 1
  assert fake.get('celery:worker:workerA:failure') == 1
  assert fake.get('celery:worker:workerA:retries') == 1

def test_health_response(monkeypatch):
  import hypercode.server as s
  import redis
  fake = FakeRedis()
  fake.set('celery:worker:workerA:success', 2)
  fake.set('celery:worker:workerA:failure', 1)
  fake.set('celery:worker:workerA:retries', 3)
  fake.set('celery:worker:workerA:last_task_ts', int(time.time()))
  monkeypatch.setattr(redis, 'Redis', SimpleNamespace(from_url=lambda *_: fake))
  import asyncio, json
  resp = asyncio.run(s.celery_health())
  assert resp.status_code == 200
  data = json.loads(resp.body)
  assert data['cluster_total']['success'] >= 0
  assert data['workers'][0]['name'] == 'workerA'
