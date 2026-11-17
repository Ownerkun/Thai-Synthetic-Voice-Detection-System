"""add feedback detail columns

Revision ID: b7c3e1f4a9d2
Revises: d1da0423eaba
Create Date: 2026-11-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7c3e1f4a9d2'
down_revision: Union[str, None] = 'd1da0423eaba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (ชื่อคอลัมน์, ความยาว) ของคอลัมน์ string ทั้งหมด — ทุกตัว nullable ไม่ต้องมีค่าเริ่มต้น แถว feedback เดิมจึงไม่กระทบ
STRING_COLUMNS = [
    ("audio_source", 30),
    ("input_method", 30),
    ("environment", 30),
    ("mic_distance", 30),
    ("recording_device", 100),
    ("playback_device", 100),
    ("truth_basis", 30),
    ("speaker_accent", 30),
    ("speaker_age_group", 30),
    ("comment", 300),
]


def upgrade() -> None:
    for name, length in STRING_COLUMNS:
        op.add_column('feedback', sa.Column(name, sa.String(length=length), nullable=True))
    op.add_column('feedback', sa.Column('audio_issues', sa.JSON(none_as_null=True), nullable=True))


def downgrade() -> None:
    op.drop_column('feedback', 'audio_issues')
    for name, _ in reversed(STRING_COLUMNS):
        op.drop_column('feedback', name)
