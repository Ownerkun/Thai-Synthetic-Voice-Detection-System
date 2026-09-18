"""initial schema

สร้างตารางทั้ง 6 ตามที่ออกแบบไว้ใน Class Diagram (UML):
user_account, admin_account, threshold_setting, detection_record, segment_score, feedback

Revision ID: a2aea0a21377
Revises:
Create Date: 2026-09-14 12:04:45.547938

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import GUID

# revision identifiers, used by Alembic.
revision: str = "a2aea0a21377"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_account",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_user_account_email", "user_account", ["email"], unique=True)

    op.create_table(
        "admin_account",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_account_username", "admin_account", ["username"], unique=True)

    op.create_table(
        "threshold_setting",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "changed_by_admin_id", GUID(), sa.ForeignKey("admin_account.id"), nullable=False
        ),
        sa.Column("note", sa.Text(), nullable=True),
    )

    op.create_table(
        "detection_record",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "user_id", GUID(), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("sample_rate", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("audio_format", sa.String(20), nullable=False),
        sa.Column("num_segments", sa.Integer(), nullable=False),
        sa.Column("mean_probability", sa.Float(), nullable=False),
        sa.Column("max_probability", sa.Float(), nullable=False),
        sa.Column("threshold_used", sa.Float(), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("possible_partial_spoof", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("processing_ms", sa.Integer(), nullable=False),
    )
    op.create_index("ix_detection_record_user_id", "detection_record", ["user_id"])

    op.create_table(
        "segment_score",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "detection_id",
            GUID(),
            sa.ForeignKey("detection_record.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("spoof_probability", sa.Float(), nullable=False),
    )
    op.create_index("ix_segment_score_detection_id", "segment_score", ["detection_id"])

    op.create_table(
        "feedback",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "detection_id",
            GUID(),
            sa.ForeignKey("detection_record.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "user_id", GUID(), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_agrees", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("segment_score")
    op.drop_table("detection_record")
    op.drop_table("threshold_setting")
    op.drop_index("ix_admin_account_username", table_name="admin_account")
    op.drop_table("admin_account")
    op.drop_index("ix_user_account_email", table_name="user_account")
    op.drop_table("user_account")
