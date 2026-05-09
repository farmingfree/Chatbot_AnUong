"""Add name_normalized and source_data columns to places

Revision ID: add_crawler_columns
Revises:
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_crawler_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add name_normalized column
    op.add_column('places', sa.Column('name_normalized', sa.String(255), nullable=True))

    # Add source_data JSON column
    op.add_column('places', sa.Column('source_data', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # Create index on name_normalized for faster deduplication
    op.create_index('idx_places_name_normalized', 'places', ['name_normalized'])


def downgrade():
    op.drop_index('idx_places_name_normalized', table_name='places')
    op.drop_column('places', 'source_data')
    op.drop_column('places', 'name_normalized')
