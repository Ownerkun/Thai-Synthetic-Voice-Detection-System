"""
GET /admin/detections/filter-options  - every model_version and the threshold_used range that exist in the data
?min_threshold= / ?max_threshold=     - filter GET /admin/detections by threshold_used

Why the endpoint exists: GET /admin/detections returns at most 200 rows per call, so a frontend that builds its
filter dropdown from the rows it loaded never sees values that only appear in older rows.
Most tests insert rows directly and tag them with a unique model_version (the test database is shared by the whole
session); the exact-value tests use their own empty database.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, SessionLocal
from app.features.admin.detections_router import filter_options
from app.models.detection import DetectionRecord
from tests.conftest import admin_login_headers, register_and_get_headers
from tests.test_admin_detections import _insert, _list, _tag


def _options(client) -> dict:
    res = client.get("/admin/detections/filter-options", headers=admin_login_headers(client))
    assert res.status_code == 200, res.text
    return res.json()


def _record(version: str, threshold: float, created_at: datetime) -> DetectionRecord:
    return DetectionRecord(
        original_filename="clip.wav", duration_seconds=4.0, sample_rate=16000, file_size_bytes=1000, audio_format="wav",
        num_segments=1, mean_probability=0.5, max_probability=0.5, threshold_used=threshold, verdict="real",
        possible_partial_spoof=False, model_version=version, processing_ms=100, created_at=created_at,
    )


def _at(year: int, month: int = 1) -> datetime:
    return datetime(year, month, 1, 12, 0, tzinfo=timezone.utc)


# ---------- access ----------


def test_filter_options_requires_admin_token(client):
    assert client.get("/admin/detections/filter-options").status_code == 401
    user_headers = register_and_get_headers(client)
    assert client.get("/admin/detections/filter-options", headers=user_headers).status_code == 401


def test_filter_options_is_not_mistaken_for_a_detection_id(client):
    # ถ้าประกาศ route หลัง /{detection_id} จะได้ 422 (อ่าน "filter-options" เป็น UUID)
    res = client.get("/admin/detections/filter-options", headers=admin_login_headers(client))
    assert res.status_code == 200
    assert set(res.json()) == {"total", "model_versions", "threshold_used"}


# ---------- the point of the endpoint: nothing is lost behind the 200-row limit ----------


def test_model_version_older_than_the_newest_200_rows_is_still_listed(client):
    old_tag, new_tag = _tag(), _tag()
    # ทุกแถวที่เทสต์นี้เพิ่มลงฐานข้อมูลที่ใช้ร่วมกันทั้งชุดเทสต์ ต้อง "เก่ากว่า" แถวของเทสต์อื่น (ปี 2026) ไม่งั้นจะดันแถวของเทสต์อื่น
    # ออกนอก 200 แถวแรกของรายการ แล้วเทสต์ที่รันหลังจากนี้พัง
    with SessionLocal() as db:
        db.add(_record(old_tag, 0.5, _at(2000)))  # เก่าที่สุดในฐานข้อมูล
        db.add_all([_record(new_tag, 0.5, _at(2001, 1 + i % 12)) for i in range(201)])  # 201 แถวที่ใหม่กว่า → old_tag ตกขอบ
        db.commit()

    newest_200 = _list(client, {"limit": 200})["items"]
    assert old_tag not in {item["model_version"] for item in newest_200}  # ปัญหาเดิมของ frontend

    options = {o["value"]: o for o in _options(client)["model_versions"]}
    assert options[old_tag]["count"] == 1
    assert options[new_tag]["count"] == 201
    # และใส่ค่านั้นใน filter ต่อได้จริง
    assert _list(client, {"model_version": old_tag})["total"] == 1


def test_model_versions_are_ordered_by_last_use_newest_first_with_counts(client):
    older, newer = _tag(), _tag()
    with SessionLocal() as db:
        db.add_all([_record(older, 0.5, _at(2002)), _record(older, 0.5, _at(2003)), _record(newer, 0.5, _at(2004))])
        db.commit()

    versions = _options(client)["model_versions"]
    values = [v["value"] for v in versions]
    assert values.index(newer) < values.index(older)
    by_value = {v["value"]: v for v in versions}
    assert by_value[older]["count"] == 2
    assert by_value[older]["last_used_at"].startswith("2003-01-01T12:00:00")
    assert by_value[newer]["count"] == 1


def test_threshold_range_covers_the_lowest_and_highest_value_inserted(client):
    tag = _tag()
    _insert(tag, threshold_used=0.0123)
    _insert(tag, threshold_used=0.9876)
    threshold = _options(client)["threshold_used"]
    assert threshold["min"] <= 0.0123
    assert threshold["max"] >= 0.9876


# ---------- exact values on an empty database ----------


@pytest.fixture
def empty_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'options.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        yield db
    engine.dispose()


def test_empty_database_has_no_options(empty_db):
    out = filter_options(db=empty_db, _admin=None)
    assert out.total == 0
    assert out.model_versions == []
    assert out.threshold_used.min is None and out.threshold_used.max is None


def test_exact_counts_order_and_threshold_range(empty_db):
    empty_db.add_all(
        [
            _record("v1", 0.4, _at(2026, 1)),
            _record("v1", 0.5, _at(2026, 2)),
            _record("v2", 0.7, _at(2026, 3)),
            _record("v0", 0.6, _at(2025, 12)),
        ]
    )
    empty_db.commit()

    out = filter_options(db=empty_db, _admin=None)
    assert out.total == 4
    assert [(v.value, v.count) for v in out.model_versions] == [("v2", 1), ("v1", 2), ("v0", 1)]
    assert (out.threshold_used.min, out.threshold_used.max) == (0.4, 0.7)


def test_versions_with_the_same_last_use_are_sorted_by_name(empty_db):
    empty_db.add_all([_record("b", 0.5, _at(2026)), _record("a", 0.5, _at(2026))])
    empty_db.commit()
    assert [v.value for v in filter_options(db=empty_db, _admin=None).model_versions] == ["a", "b"]


# ---------- ?min_threshold= / ?max_threshold= on /admin/detections ----------


def _by_threshold(client, tag: str, **params) -> list[float]:
    body = _list(client, {"model_version": tag, **params})
    return sorted(item["threshold_used"] for item in body["items"])


def test_threshold_filters_are_inclusive_at_both_ends(client):
    tag = _tag()
    for value in (0.3, 0.5, 0.7):
        _insert(tag, threshold_used=value)
    assert _by_threshold(client, tag) == [0.3, 0.5, 0.7]
    assert _by_threshold(client, tag, min_threshold=0.5) == [0.5, 0.7]
    assert _by_threshold(client, tag, max_threshold=0.5) == [0.3, 0.5]
    assert _by_threshold(client, tag, min_threshold=0.3, max_threshold=0.5) == [0.3, 0.5]
    assert _by_threshold(client, tag, min_threshold=0.5, max_threshold=0.5) == [0.5]
    assert _by_threshold(client, tag, min_threshold=0.71) == []


def test_threshold_filter_value_taken_from_filter_options_matches_its_rows(client):
    # ค่าที่ frontend อ่านจาก filter-options เอามาใส่ filter ต้องเจอแถวนั้นจริง (ไม่พลาดจากทศนิยม)
    tag = _tag()
    _insert(tag, threshold_used=0.37)
    threshold = _options(client)["threshold_used"]
    assert threshold["min"] <= 0.37 <= threshold["max"]
    assert _by_threshold(client, tag, min_threshold=0.37, max_threshold=0.37) == [0.37]


@pytest.mark.parametrize(
    "params",
    [{"min_threshold": 0.8, "max_threshold": 0.2}, {"min_threshold": -0.1}, {"max_threshold": 1.5}, {"min_threshold": "abc"}],
)
def test_invalid_threshold_filters_are_rejected(client, params):
    _list(client, params, expected_status=422)
