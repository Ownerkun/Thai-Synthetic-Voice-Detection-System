"""add email verification and email_token table

- user_account.email_verified_at: บัญชีที่มีอยู่แล้วถือว่ายืนยันแล้ว (ตั้งเป็นเวลาที่รัน migration) เพื่อไม่ล็อกผู้ใช้เดิม
- user_account.password_changed_at: ใช้ทำให้ token เก่าใช้ไม่ได้หลังรีเซ็ตรหัสผ่าน
- email_token: โทเคนใช้ครั้งเดียวสำหรับยืนยันอีเมล/รีเซ็ตรหัสผ่าน (เก็บเฉพาะ hash)

Revision ID: c9d4f2a7b1e6
Revises: b7c3e1f4a9d2
Create Date: 2026-11-12 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

# revision identifiers, used by Alembic.
revision: str = "c9d4f2a7b1e6"
down_revision: Union[str, None] = "b7c3e1f4a9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ตรวจก่อนสร้าง: app/main.py เรียก create_all ตอนสตาร์ท ซึ่งสร้างตารางใหม่ (email_token) ให้เองถ้าโค้ดใหม่รันก่อน migration
    # แต่ไม่เติมคอลัมน์ให้ตารางเดิม (user_account) → ฐานข้อมูลบนเครื่อง dev ที่เคยสตาร์ทด้วยโค้ดใหม่จะมี email_token แล้ว
    inspector = sa.inspect(op.get_bind())
    user_columns = {column["name"] for column in inspector.get_columns("user_account")}

    if "email_verified_at" not in user_columns:
        op.add_column("user_account", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        # ผู้ใช้เดิมสมัครก่อนมีระบบยืนยันอีเมล ให้ใช้งานต่อได้ทันที (ทำเฉพาะตอนที่เพิ่งเพิ่มคอลัมน์ ไม่ทับค่าที่มีอยู่แล้ว)
        op.execute("UPDATE user_account SET email_verified_at = CURRENT_TIMESTAMP")
    if "password_changed_at" not in user_columns:
        op.add_column("user_account", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))

    if not inspector.has_table("email_token"):  # ตารางที่ create_all สร้างไว้มีดัชนีชื่อเดียวกันนี้ครบอยู่แล้ว
        op.create_table(
            "email_token",
            sa.Column("id", GUID(), primary_key=True),
            sa.Column("user_id", GUID(), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False),
            sa.Column("purpose", sa.String(20), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_email_token_user_id", "email_token", ["user_id"])
        op.create_index("ix_email_token_token_hash", "email_token", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_email_token_token_hash", table_name="email_token")
    op.drop_index("ix_email_token_user_id", table_name="email_token")
    op.drop_table("email_token")
    op.drop_column("user_account", "password_changed_at")
    op.drop_column("user_account", "email_verified_at")
