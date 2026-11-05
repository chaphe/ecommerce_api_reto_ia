"""Add commercial catalog, categories, order lifecycle and snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "20261105_commerce_modules"
down_revision = "20261105_auth_roles"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="confirmed"))
        batch.add_column(sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("cancellation_reason", sa.String(length=255), nullable=True))
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.UniqueConstraint("slug"),
    )
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("sku", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("image_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_products_category_id", "categories", ["category_id"], ["id"])
        batch.create_unique_constraint("uq_products_sku", ["sku"])
    with op.batch_alter_table("order_items") as batch:
        batch.add_column(sa.Column("product_name", sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table("order_items") as batch:
        batch.drop_column("product_name")
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("fk_products_category_id", type_="foreignkey")
        batch.drop_constraint("uq_products_sku", type_="unique")
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("category_id")
        batch.drop_column("is_archived")
        batch.drop_column("image_url")
        batch.drop_column("description")
        batch.drop_column("sku")
    op.drop_table("categories")
    with op.batch_alter_table("orders") as batch:
        batch.drop_column("cancellation_reason")
        batch.drop_column("cancelled_at")
        batch.drop_column("is_archived")
        batch.drop_column("status")
        batch.drop_column("updated_at")
