"""Add password, role and status fields to users; allow guest orders."""
from alembic import op
import sqlalchemy as sa

revision = "20261105_auth_roles"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("role", sa.String(length=20), nullable=False, server_default="buyer"))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("orders") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=True)

def downgrade():
    with op.batch_alter_table("orders") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("users") as batch:
        batch.drop_column("created_at")
        batch.drop_column("is_active")
        batch.drop_column("role")
        batch.drop_column("password_hash")
