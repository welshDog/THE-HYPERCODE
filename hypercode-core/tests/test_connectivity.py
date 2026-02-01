import os
import time
import pytest
from sqlalchemy import create_engine, text
import redis
from celery import Celery

def test_database_connection():
    url = os.getenv('HYPERCODE_DB_URL')
    assert url
    eng = create_engine(url)
    with eng.connect() as conn:
        conn.execute(text('SELECT 1'))

def test_redis_broker():
    r = redis.Redis.from_url(os.getenv('HYPERCODE_REDIS_URL', 'redis://localhost:6379/0'))
    assert r.ping()

def test_celery_worker_ping():
    broker = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    app = Celery('hypercode', broker=broker, backend=backend)
    res = app.send_task('hypercode.ping', args=[1])
    val = res.get(timeout=10)
    assert val == 1
