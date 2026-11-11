"""
Admin sees the questionnaire answers of a feedback (GET /admin/detections/{id}) and filters the list by them
(GET /admin/detections?audio_source=...&audio_issue=...)

Reuses the row-inserting helpers of test_admin_detections.py
"""
from app.core.database import SessionLocal
from app.models.detection import Feedback
from tests.conftest import admin_login_headers, predict_and_get_detection_id, register_and_get_headers
from tests.test_admin_detections import _insert, _list, _make_user, _names, _tag

ANSWER_KEYS = {
    "audio_source",
    "input_method",
    "environment",
    "mic_distance",
    "audio_issues",
    "recording_device",
    "playback_device",
    "truth_basis",
    "speaker_accent",
    "speaker_age_group",
    "comment",
}


def _feedback_with(detection_id: str, user_id: str, agrees: bool = False, **answers) -> None:
    with SessionLocal() as db:
        db.add(Feedback(detection_id=detection_id, user_id=user_id, user_agrees=agrees, **answers))
        db.commit()


def _detail(client, detection_id: str) -> dict:
    res = client.get(f"/admin/detections/{detection_id}", headers=admin_login_headers(client))
    assert res.status_code == 200, res.text
    return res.json()


# ---------- detail ----------


def test_detail_shows_the_answers_a_user_submitted(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, headers)
    answers = {
        "audio_source": "speaker_replay",
        "environment": "noisy_indoor",
        "audio_issues": ["echo", "uneven_volume"],
        "playback_device": "iPhone 12",
        "speaker_accent": "northern",
        "comment": "เปิดจากโทรศัพท์อีกเครื่อง",
    }
    client.post(f"/history/{detection_id}/feedback", json={"user_agrees": False, **answers}, headers=headers)

    details = _detail(client, detection_id)["feedback_details"]

    assert set(details) == ANSWER_KEYS
    for key, value in answers.items():
        assert details[key] == value, key
    assert details["mic_distance"] is None  # not answered


def test_detail_feedback_details_is_null_without_feedback_and_all_null_when_unanswered(client):
    tag = _tag()
    user_id, _ = _make_user(tag, "somchai")
    no_feedback = _insert(tag, user_id=user_id)
    unanswered = _insert(tag, user_id=user_id)
    _feedback_with(unanswered, user_id, agrees=True)

    assert _detail(client, no_feedback)["feedback_details"] is None
    assert _detail(client, unanswered)["feedback_details"] == {key: None for key in ANSWER_KEYS}


# ---------- filters ----------


def _seed(tag: str) -> dict[str, str]:
    """4 results with different answers + 1 without feedback + 1 guest. Returns {filename: detection_id}"""
    user_id, _ = _make_user(tag, "somchai")
    rows = {
        "replay.wav": dict(
            audio_source="speaker_replay",
            environment="noisy_indoor",
            audio_issues=["echo", "uneven_volume"],
            truth_basis="self_recorded",
            speaker_accent="northern",
            speaker_age_group="60_plus",
        ),
        "direct.wav": dict(
            audio_source="direct_voice",
            environment="quiet_room",
            audio_issues=[],
            truth_basis="know_the_speaker",
            speaker_accent="central",
            speaker_age_group="20_39",
        ),
        "call.wav": dict(
            audio_source="phone_call",
            environment="in_vehicle",
            audio_issues=["background_noise"],
            truth_basis="not_sure",
            speaker_accent="northern",
            speaker_age_group="40_59",
        ),
        "unanswered.wav": dict(),  # feedback but no questionnaire answers
    }
    ids = {}
    for name, answers in rows.items():
        ids[name] = _insert(tag, original_filename=name, user_id=user_id)
        _feedback_with(ids[name], user_id, **answers)
    ids["no_feedback.wav"] = _insert(tag, original_filename="no_feedback.wav", user_id=user_id)
    ids["guest.wav"] = _insert(tag, original_filename="guest.wav")
    return ids


def test_each_questionnaire_filter_selects_only_matching_results(client):
    tag = _tag()
    _seed(tag)

    def names(**params) -> list[str]:
        return sorted(_names(_list(client, {"model_version": tag, **params})))

    assert names(audio_source="speaker_replay") == ["replay.wav"]
    assert names(audio_source="phone_call") == ["call.wav"]
    assert names(environment="quiet_room") == ["direct.wav"]
    assert names(truth_basis="not_sure") == ["call.wav"]
    assert names(speaker_accent="northern") == ["call.wav", "replay.wav"]
    assert names(speaker_age_group="60_plus") == ["replay.wav"]
    assert names(audio_source="other") == []  # a valid option nobody picked


def test_audio_issue_filter_matches_ticked_issues_among_several(client):
    tag = _tag()
    _seed(tag)

    def names(**params) -> list[str]:
        return sorted(_names(_list(client, {"model_version": tag, **params})))

    assert names(audio_issue="echo") == ["replay.wav"]
    assert names(audio_issue="uneven_volume") == ["replay.wav"]  # second item of the list
    assert names(audio_issue="background_noise") == ["call.wav"]
    assert names(audio_issue="distorted") == []  # nobody ticked it
    assert names(audio_issue="echo", audio_source="phone_call") == []  # combined with AND


def test_results_without_answers_never_match_a_questionnaire_filter(client):
    tag = _tag()
    _seed(tag)

    for params in ({"audio_source": "direct_voice"}, {"audio_issue": "echo"}, {"speaker_accent": "central"}):
        names = _names(_list(client, {"model_version": tag, **params}))
        assert "unanswered.wav" not in names and "no_feedback.wav" not in names and "guest.wav" not in names


def test_questionnaire_filters_combine_with_the_feedback_filter(client):
    tag = _tag()
    _seed(tag)  # every seeded feedback uses user_agrees=False

    assert sorted(_names(_list(client, {"model_version": tag, "feedback": "disagree", "speaker_accent": "northern"}))) == [
        "call.wav",
        "replay.wav",
    ]
    assert _names(_list(client, {"model_version": tag, "feedback": "agree", "speaker_accent": "northern"})) == []


def test_questionnaire_filters_reject_unknown_values(client):
    for params in (
        {"audio_source": "telepathy"},
        {"environment": "moon"},
        {"audio_issue": "smell"},
        {"truth_basis": "guess"},
        {"speaker_accent": "martian"},
        {"speaker_age_group": "ancient"},
    ):
        _list(client, params, expected_status=422)
