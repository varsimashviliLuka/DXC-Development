"""subscription billing day

Revision ID: 0002_billing_day
Revises: 0001_baseline
Create Date: 2026-10-26 14:57:16.175955

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_billing_day'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('billing_day', sa.SmallInteger(), nullable=True))

    subscriptions = sa.table(
        'subscriptions',
        sa.column('id', sa.Integer),
        sa.column('next_payment_due', sa.Date),
        sa.column('billing_day', sa.SmallInteger),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(subscriptions.c.id, subscriptions.c.next_payment_due)
        .where(subscriptions.c.next_payment_due.isnot(None))
    ).all()
    for subscription_id, due in rows:
        connection.execute(
            subscriptions.update()
            .where(subscriptions.c.id == subscription_id)
            .values(billing_day=due.day)
        )


def downgrade():
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('billing_day')
