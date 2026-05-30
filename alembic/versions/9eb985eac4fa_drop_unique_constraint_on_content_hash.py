"""drop unique constraint on content hash

Revision ID: 9eb985eac4fa
Revises: d1b412ebafcf
Create Date: 2026-05-29 21:21:42.643563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9eb985eac4fa'
down_revision: Union[str, Sequence[str], None] = 'd1b412ebafcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_regulatory_documents_content_hash",
        "regulatory_documents",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_regulatory_documents_content_hash",
        "regulatory_documents",
        ["content_hash"],
    )
