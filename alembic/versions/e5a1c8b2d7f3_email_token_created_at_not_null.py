"""email_token.created_at NOT NULL

โมเดล EmailToken.created_at เป็น NOT NULL เหมือนตารางอื่น แต่ migration c9d4f2a7b1e6 สร้างคอลัมน์นี้แบบ nullable
ทำให้ `alembic check` เจอความต่างระหว่างโมเดลกับฐานข้อมูล (ฐานข้อมูลที่สร้างด้วย create_all เป็น NOT NULL อยู่แล้ว ไม่เปลี่ยนอะไร)

Revision ID: e5a1c8b2d7f3
Revises: c9d4f2a7b1e6
Create Date: 2026-11-18 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a1c8b2d7f3"
down_revision: Union[str, None] = "c9d4f2a7b1e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE email_token SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    # batch_alter_table: PostgreSQL ใช้ ALTER COLUMN ตรง ๆ ส่วน SQLite (ที่ใช้ในเทสต์) ไม่รองรับ จึงสร้างตารางใหม่ให้
    with op.batch_alter_table("email_token") as batch:
        batch.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.func.now(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("email_token") as batch:
        batch.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_server_default=sa.func.now(),
            nullable=True,
        )
