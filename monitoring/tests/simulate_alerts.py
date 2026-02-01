import time
import requests
import os

ALERTMGR = os.getenv('ALERTMANAGER_URL', 'http://localhost:9093')

def fire(label, duration=120):
    payload = [{
        "labels": {"alertname": label, "severity": "critical"},
        "startsAt": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }]
    r = requests.post(f"{ALERTMGR}/api/v1/alerts", json=payload, timeout=5)
    return r.status_code

def recover(label):
    payload = [{
        "labels": {"alertname": label, "severity": "critical"},
        "endsAt": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }]
    r = requests.post(f"{ALERTMGR}/api/v1/alerts", json=payload, timeout=5)
    return r.status_code

if __name__ == '__main__':
    print('Fire:', fire('TestCritical'))
    time.sleep(5)
    print('Recover:', recover('TestCritical'))
