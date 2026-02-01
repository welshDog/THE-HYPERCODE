import os
import sys
from sqlalchemy import create_engine, text

def prune(ttl_days: int) -> int:
    url = os.getenv('HYPERCODE_DB_URL')
    if not url:
        raise RuntimeError('HYPERCODE_DB_URL not set')
    eng = create_engine(url)
    with eng.connect() as conn:
        res = conn.execute(text('SELECT prune_celery_task_audit(:ttl)'), {'ttl': ttl_days})
        conn.commit()
    # Function does not return count; approximate via affected rows is not available.
    return 0

def main():
    ttl = int(os.getenv('AUDIT_TTL_DAYS', '30'))
    prune(ttl)
    print(f'pruned older than {ttl} days')

if __name__ == '__main__':
    main()
