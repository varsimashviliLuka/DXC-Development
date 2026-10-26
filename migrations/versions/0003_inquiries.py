"""contact form inquiries

Revision ID: 0003_inquiries
Revises: 0002_billing_day
Create Date: 2026-10-26 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_inquiries'
down_revision = '0002_billing_day'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "inquiries" in inspector.get_table_names():
        return

    op.create_table(
        'inquiries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('service', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=5), nullable=False),
        sa.Column(
            'status',
            sa.Enum('NEW', 'IN_PROGRESS', 'DONE', 'SPAM', name='inquirystatus'),
            nullable=False,
        ),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('inquiries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_inquiries_status'), ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('inquiries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_inquiries_status'))
    op.drop_table('inquiries')
