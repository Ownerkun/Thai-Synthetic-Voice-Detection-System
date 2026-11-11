"""
Feedback questionnaire: POST / PUT /history/{id}/feedback accept the optional detail answers,
GET /history/{id}/feedback and GET /feedback return them
"""
from tests.conftest import predict_and_get_detection_id, register_and_get_headers

FULL_ANSWERS = {
    "audio_source": "speaker_replay",
    "input_method": "recorded_in_app",
    "environment": "noisy_indoor",
    "mic_distance": "far",
    "audio_issues": ["echo", "uneven_volume"],
    "recording_device": "Galaxy A54",
    "playback_device": "iPhone 12",
    "truth_basis": "self_recorded",
    "speaker_accent": "northern",
    "speaker_age_group": "60_plus",
    "comment": "เปิดจากโทรศัพท์อีกเครื่องวางบนโต๊ะ",
}
DETAIL_KEYS = set(FULL_ANSWERS)


def _new_detection(client):
    headers = register_and_get_headers(client)
    return headers, predict_and_get_detection_id(client, headers)


def _post(client, headers, detection_id, body, expected_status=201):
    res = client.post(f"/history/{detection_id}/feedback", json=body, headers=headers)
    assert res.status_code == expected_status, res.text
    return res.json()


def _put(client, headers, detection_id, body, expected_status=200):
    res = client.put(f"/history/{detection_id}/feedback", json=body, headers=headers)
    assert res.status_code == expected_status, res.text
    return res.json()


def test_feedback_without_details_still_works_and_all_detail_fields_are_null(client):
    headers, detection_id = _new_detection(client)

    created = _post(client, headers, detection_id, {"user_agrees": True})

    assert created["user_agrees"] is True
    for key in DETAIL_KEYS:
        assert created[key] is None, key


def test_post_stores_every_answer_and_returns_them(client):
    headers, detection_id = _new_detection(client)

    created = _post(client, headers, detection_id, {"user_agrees": False, **FULL_ANSWERS})

    for key, value in FULL_ANSWERS.items():
        assert created[key] == value, key
    fetched = client.get(f"/history/{detection_id}/feedback", headers=headers).json()
    for key, value in FULL_ANSWERS.items():
        assert fetched[key] == value, key


def test_partial_answers_leave_the_rest_null_and_empty_issue_list_is_kept(client):
    headers, detection_id = _new_detection(client)

    created = _post(client, headers, detection_id, {"user_agrees": True, "environment": "quiet_room", "audio_issues": []})

    assert created["environment"] == "quiet_room"
    assert created["audio_issues"] == []  # answered "no problems" - different from not answering
    assert created["audio_source"] is None


def test_agreeing_users_can_answer_too(client):
    headers, detection_id = _new_detection(client)
    created = _post(client, headers, detection_id, {"user_agrees": True, "audio_source": "direct_voice"})
    assert created["audio_source"] == "direct_voice"


def test_put_replaces_all_answers_and_omitted_ones_are_cleared(client):
    headers, detection_id = _new_detection(client)
    _post(client, headers, detection_id, {"user_agrees": False, **FULL_ANSWERS})

    edited = _put(client, headers, detection_id, {"user_agrees": False, "environment": "outdoors"})

    assert edited["environment"] == "outdoors"
    for key in DETAIL_KEYS - {"environment"}:
        assert edited[key] is None, key
    assert client.get(f"/history/{detection_id}/feedback", headers=headers).json()["audio_source"] is None


def test_put_with_identical_answers_does_not_bump_updated_at(client):
    headers, detection_id = _new_detection(client)
    body = {"user_agrees": False, **FULL_ANSWERS}
    _post(client, headers, detection_id, body)

    first = _put(client, headers, detection_id, {**body, "comment": "แก้คำอธิบาย"})
    assert first["updated_at"] is not None
    again = _put(client, headers, detection_id, {**body, "comment": "แก้คำอธิบาย"})

    assert again["updated_at"] == first["updated_at"]


def test_text_answers_are_trimmed_and_blank_means_not_answered(client):
    headers, detection_id = _new_detection(client)

    created = _post(
        client,
        headers,
        detection_id,
        {"user_agrees": False, "recording_device": "  Pixel 8  ", "comment": "   "},
    )

    assert created["recording_device"] == "Pixel 8"
    assert created["comment"] is None


def test_feedback_list_includes_the_answers(client):
    headers, detection_id = _new_detection(client)
    _post(client, headers, detection_id, {"user_agrees": False, **FULL_ANSWERS})

    item = client.get("/feedback", headers=headers).json()[0]

    for key, value in FULL_ANSWERS.items():
        assert item[key] == value, key


def test_invalid_answers_are_rejected_and_nothing_is_saved(client):
    headers, detection_id = _new_detection(client)
    bad_bodies = [
        {"user_agrees": True, "audio_source": "telepathy"},  # not one of the options
        {"user_agrees": True, "environment": "QUIET_ROOM"},  # codes are case-sensitive
        {"user_agrees": True, "audio_issues": ["echo", "echo"]},  # duplicates
        {"user_agrees": True, "audio_issues": ["smell"]},
        {"user_agrees": True, "audio_issues": "echo"},  # must be a list
        {"user_agrees": True, "recording_device": "x" * 101},
        {"user_agrees": True, "comment": "x" * 301},
        {"user_agrees": True, "audio_sorce": "direct_voice"},  # typo in a field name must not be silently dropped
        {"user_agrees": True, "playback_device": "iPhone 12"},  # only meaningful with speaker_replay
        {"user_agrees": True, "audio_source": "direct_voice", "playback_device": "iPhone 12"},
        {"audio_source": "direct_voice"},  # user_agrees is still required
    ]
    for body in bad_bodies:
        _post(client, headers, detection_id, body, expected_status=422)

    assert client.get(f"/history/{detection_id}/feedback", headers=headers).status_code == 404  # nothing created


def test_put_validates_the_same_way(client):
    headers, detection_id = _new_detection(client)
    _post(client, headers, detection_id, {"user_agrees": True, "environment": "quiet_room"})

    _put(client, headers, detection_id, {"user_agrees": False, "mic_distance": "very_far"}, expected_status=422)

    unchanged = client.get(f"/history/{detection_id}/feedback", headers=headers).json()
    assert unchanged["user_agrees"] is True
    assert unchanged["environment"] == "quiet_room"


def test_playback_device_is_accepted_for_speaker_replay(client):
    headers, detection_id = _new_detection(client)
    created = _post(
        client, headers, detection_id,
        {"user_agrees": False, "audio_source": "speaker_replay", "playback_device": "JBL Flip 5"},
    )
    assert created["playback_device"] == "JBL Flip 5"
