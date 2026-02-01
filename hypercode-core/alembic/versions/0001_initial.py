from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'health_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('event', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('health_events')
