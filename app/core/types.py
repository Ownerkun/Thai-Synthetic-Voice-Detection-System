"""
Custom column type: เก็บเป็น native UUID บน PostgreSQL
แต่ fallback เป็น CHAR(36) บน SQLite ได้ด้วย ทำให้เขียน unit test ด้วย sqlite in-memory
ได้โดยไม่ต้องพึ่ง PostgreSQL container ทุกครั้งที่รันเทส
"""

import uuid

from sqlalchemy import CHAR, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        return str(value) if isinstance(value, uuid.UUID) else str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
