from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0002_task_audit'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    status_enum = sa.Enum('success', 'failure', 'retry', name='task_status')
    status_enum.create(op.get_bind())
    op.create_table(
        'celery_task_audit',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('task_id', sa.String(155), nullable=False),
        sa.Column('name', sa.String(125), nullable=False),
        sa.Column('status', status_enum, nullable=False),
        sa.Column('runtime_ms', sa.Integer, nullable=False),
        sa.Column('args', JSONB, nullable=True),
        sa.Column('kwargs', JSONB, nullable=True),
        sa.Column('result', JSONB, nullable=True),
        sa.Column('traceback', sa.Text, nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('worker_name', sa.String(65), nullable=False),
    )
    op.create_index('ix_task_timestamp', 'celery_task_audit', ['task_id', 'timestamp'], unique=False, postgresql_concurrently=True)

def downgrade():
    op.drop_index('ix_task_timestamp', table_name='celery_task_audit')
    op.drop_table('celery_task_audit')
    sa.Enum(name='task_status').drop(op.get_bind())
