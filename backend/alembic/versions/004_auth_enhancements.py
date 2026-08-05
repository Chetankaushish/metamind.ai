"""Auth Enhancements Schema Migration for MetaMind AI

Revision ID: 004_auth_enhancements
Revises: 003_billing
Create Date: 2026-07-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_auth_enhancements'
down_revision = '003_billing'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'reset_token_expires')
    op.drop_column('users', 'reset_token')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
