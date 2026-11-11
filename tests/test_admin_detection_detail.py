"""
GET /admin/detections/{id} - admin views every detail of one detection result (any user's, guests included)

Reuses the row-inserting helpers of test_admin_detections.py
"""

import uuid
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.detection import SegmentScore
from tests.conftest import (
    admin_login_headers,
    predict_and_get_detection_id,
    register_and_get_headers,
)
from tests.test_admin_detections import _add_feedback, _insert, _make_user, _tag


def _get(client, detection_id: str, expected_status: int = 200):
    res = client.get(
        f"/admin/detections/{detection_id}", headers=admin_login_headers(client)
    )
    assert res.status_code == expected_status, res.text
    return res.json()


def test_detail_of_a_guest_result_has_all_record_fields(client):
    tag = _tag()
    detection_id = _insert(
        tag,
        original_filename="call.wav",
        duration_seconds=4.5,
        sample_rate=16000,
        file_size_bytes=144044,
        audio_format="wav",
        num_segments=1,
        mean_probability=0.82,
        max_probability=0.9,
        threshold_used=0.5,
        verdict="spoof",
        possible_partial_spoof=True,
        processing_ms=600,
        created_at=datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc),
    )

    body = _get(client, detection_id)

    assert body["id"] == detection_id
    assert body["original_filename"] == "call.wav"
    assert body["duration_seconds"] == 4.5
    assert body["sample_rate"] == 16000
    assert body["file_size_bytes"] == 144044
    assert body["audio_format"] == "wav"
    assert body["num_segments"] == 1
    assert body["mean_probability"] == 0.82
    assert body["max_probability"] == 0.9
    assert body["threshold_used"] == 0.5
    assert body["verdict"] == "spoof"
    assert body["possible_partial_spoof"] is True
    assert body["model_version"] == tag
    assert body["processing_ms"] == 600
    assert body["created_at"].startswith("2026-10-01T03:00:00")
    assert body["user_id"] is None  # guest
    assert body["user_email"] is None
    assert body["feedback"] is None
    assert body["feedback_created_at"] is None
    assert body["feedback_updated_at"] is None


def test_detail_shows_the_owner_of_a_logged_in_result(client):
    tag = _tag()
    user_id, email = _make_user(tag, "somchai")
    detection_id = _insert(tag, user_id=user_id)

    body = _get(client, detection_id)

    assert body["user_id"] == user_id
    assert body["user_email"] == email


def test_detail_shows_feedback_and_when_it_was_given(client):
    tag = _tag()
    user_id, _ = _make_user(tag, "somchai")
    agreed = _insert(tag, user_id=user_id)
    disagreed = _insert(tag, user_id=user_id)
    _add_feedback(agreed, user_id, True)
    _add_feedback(disagreed, user_id, False)

    body = _get(client, agreed)
    assert body["feedback"] == "agree"
    assert body["feedback_created_at"] is not None
    assert body["feedback_updated_at"] is None  # never edited

    assert _get(client, disagreed)["feedback"] == "disagree"


def test_detail_shows_when_feedback_was_edited(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, headers)
    assert (
        client.post(
            f"/history/{detection_id}/feedback",
            json={"user_agrees": True},
            headers=headers,
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"/history/{detection_id}/feedback",
            json={"user_agrees": False},
            headers=headers,
        ).status_code
        == 200
    )

    body = _get(client, detection_id)

    assert body["feedback"] == "disagree"
    assert body["feedback_updated_at"] is not None


def test_detail_matches_the_list_item_for_the_same_result(client):
    tag = _tag()
    user_id, _ = _make_user(tag, "napat")
    detection_id = _insert(tag, user_id=user_id, original_filename="same.wav")
    _add_feedback(detection_id, user_id, True)

    detail = _get(client, detection_id)
    listed = client.get(
        "/admin/detections",
        params={"model_version": tag},
        headers=admin_login_headers(client),
    ).json()["items"][0]

    assert {
        key: detail[key] for key in listed
    } == listed  # detail = list item + extra fields


def test_detail_unknown_id_is_404_and_malformed_id_is_422(client):
    assert _get(client, str(uuid.uuid4()), expected_status=404) == {
        "detail": "Detection not found"
    }
    _get(client, "not-a-uuid", expected_status=422)


def test_detail_requires_admin_token(client):
    detection_id = _insert(_tag())

    assert client.get(f"/admin/detections/{detection_id}").status_code == 401
    user_headers = register_and_get_headers(client)
    assert (
        client.get(
            f"/admin/detections/{detection_id}", headers=user_headers
        ).status_code
        == 401
    )


# ---------- segments ----------


def _add_segments(
    detection_id: str, rows: list[tuple[int, float, float, float]]
) -> None:
    """rows = (segment_index, start_seconds, end_seconds, spoof_probability)"""
    with SessionLocal() as db:
        for index, start, end, probability in rows:
            db.add(
                SegmentScore(
                    detection_id=detection_id,
                    segment_index=index,
                    start_seconds=start,
                    end_seconds=end,
                    spoof_probability=probability,
                )
            )
        db.commit()


def test_detail_lists_segments_in_order_with_is_spoof_from_the_records_threshold(
    client,
):
    tag = _tag()
    detection_id = _insert(tag, num_segments=4, threshold_used=0.7)
    # inserted out of order on purpose; 0.7 sits exactly on the threshold, 0.69 just under it
    _add_segments(
        detection_id,
        [
            (2, 4.0, 6.0, 0.7),
            (0, 0.0, 2.0, 0.1),
            (3, 6.0, 8.0, 0.95),
            (1, 2.0, 4.0, 0.69),
        ],
    )

    segments = _get(client, detection_id)["segments"]

    assert [s["index"] for s in segments] == [0, 1, 2, 3]
    assert [s["is_spoof"] for s in segments] == [
        False,
        False,
        True,
        True,
    ]  # probability >= threshold_used
    assert segments[0] == {
        "index": 0,
        "start_seconds": 0.0,
        "end_seconds": 2.0,
        "spoof_probability": 0.1,
        "is_spoof": False,
    }


def test_detail_segments_do_not_mix_between_results(client):
    tag = _tag()
    first = _insert(tag)
    second = _insert(tag)
    _add_segments(first, [(0, 0.0, 2.0, 0.2)])
    _add_segments(second, [(0, 0.0, 2.0, 0.9), (1, 2.0, 4.0, 0.8)])

    assert [s["spoof_probability"] for s in _get(client, first)["segments"]] == [0.2]
    assert [s["spoof_probability"] for s in _get(client, second)["segments"]] == [
        0.9,
        0.8,
    ]


def test_detail_without_segments_returns_an_empty_list(client):
    assert _get(client, _insert(_tag()))["segments"] == []


def test_detail_of_a_real_prediction_has_one_segment_per_num_segments(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, headers)

    body = _get(client, detection_id)

    assert len(body["segments"]) == body["num_segments"] >= 1
    history = client.get(f"/history/{detection_id}", headers=headers).json()
    assert body["segments"] == history["segments"]  # same view the owner sees
