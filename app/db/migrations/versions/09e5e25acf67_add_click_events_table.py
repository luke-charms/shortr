"""add click_events table

Revision ID: 09e5e25acf67
Revises: 6678193d0996
Create Date: 2026-04-22 09:16:37.532477

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09e5e25acf67'
down_revision: Union[str, Sequence[str], None] = '6678193d0996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "click_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("link_id", sa.Integer, sa.ForeignKey("links.id", ondelete="CASCADE")),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
