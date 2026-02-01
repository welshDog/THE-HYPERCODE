from alembic import op
import sqlalchemy as sa

revision = '0003_retention'
down_revision = '0002_task_audit'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE celery_task_audit SET (autovacuum_vacuum_scale_factor=0.2)")
    op.execute("ALTER TABLE celery_task_audit SET (autovacuum_analyze_scale_factor=0.1)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prune_celery_task_audit(ttl_days integer)
        RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
          DELETE FROM celery_task_audit WHERE timestamp < NOW() - (ttl_days || ' days')::interval;
        END;
        $$
        """
    )

def downgrade():
    op.execute("DROP FUNCTION IF EXISTS prune_celery_task_audit(integer)")
