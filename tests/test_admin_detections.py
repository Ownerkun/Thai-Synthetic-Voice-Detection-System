"""
GET /admin/detections - admin lists / filters / sorts the detection results of every user (and guests)

Most tests insert DetectionRecord rows directly so that created_at, verdict, probabilities ... are exactly known,
and give every row a unique `model_version` tag so a test can isolate its own rows with ?model_version=<tag>
(the test database is shared by the whole test session).
"""

import uuid
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.detection import DetectionRecord, Feedback
from app.models.user import UserAccount
from tests.conftest import admin_login_headers, make_wav_bytes, register_and_get_headers


def _tag() -> str:
    return f"t-{uuid.uuid4().hex[:10]}"


def _insert(tag: str, **overrides) -> str:
    """Insert one DetectionRecord. Returns its id (as str)."""
    values = dict(
        user_id=None,
        original_filename="clip.wav",
        duration_seconds=4.0,
        sample_rate=16000,
        file_size_bytes=1000,
        audio_format="wav",
        num_segments=1,
        mean_probability=0.5,
        max_probability=0.5,
        threshold_used=0.5,
        verdict="real",
        possible_partial_spoof=False,
        model_version=tag,
        processing_ms=100,
    )
    values.update(overrides)
    with SessionLocal() as db:
        record = DetectionRecord(**values)
        db.add(record)
        db.commit()
        return str(record.id)


def _list(client, params: dict, expected_status: int = 200):
    res = client.get(
        "/admin/detections", params=params, headers=admin_login_headers(client)
    )
    assert res.status_code == expected_status, res.text
    return res.json()


def test_list_detections_requires_admin_token(client):
    assert client.get("/admin/detections").status_code == 401

    user_headers = register_and_get_headers(client)
    assert client.get("/admin/detections", headers=user_headers).status_code == 401


def test_list_detections_shows_guest_and_user_results_with_the_expected_fields(client):
    admin = admin_login_headers(client)
    email = f"{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/auth/register", json={"email": email, "password": "Password1234"}
    )
    user_headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    guest_name = f"guest-{uuid.uuid4().hex[:8]}.wav"
    user_name = f"user-{uuid.uuid4().hex[:8]}.wav"

    client.post(
        "/predict", files={"files": (guest_name, make_wav_bytes(), "audio/wav")}
    )
    client.post(
        "/predict",
        files={"files": (user_name, make_wav_bytes(), "audio/wav")},
        headers=user_headers,
    )

    items = client.get(
        "/admin/detections", params={"limit": 200}, headers=admin
    ).json()["items"]
    by_name = {item["original_filename"]: item for item in items}

    guest = by_name[guest_name]
    assert guest["user_id"] is None
    assert guest["user_email"] is None

    owner = by_name[user_name]
    assert owner["user_email"] == email
    assert owner["user_id"] is not None

    assert set(owner) == {
        "id",
        "created_at",
        "original_filename",
        "duration_seconds",
        "num_segments",
        "mean_probability",
        "max_probability",
        "threshold_used",
        "verdict",
        "possible_partial_spoof",
        "model_version",
        "processing_ms",
        "user_id",
        "user_email",
        "feedback",
    }
    assert owner["feedback"] is None


def test_list_detections_is_newest_first_and_paginates_with_a_stable_total(client):
    tag = _tag()
    for day in (1, 2, 3):  # inserted out of order on purpose
        _insert(
            tag,
            original_filename=f"day{day}.wav",
            created_at=datetime(2026, 9, day, 3, 0, tzinfo=timezone.utc),
        )

    body = _list(client, {"limit": 200})
    mine = [i for i in body["items"] if i["model_version"] == tag]
    assert [i["original_filename"] for i in mine] == [
        "day3.wav",
        "day2.wav",
        "day1.wav",
    ]

    page1 = _list(client, {"limit": 2, "offset": 0})
    page2 = _list(client, {"limit": 2, "offset": 2})
    assert page1["total"] == page2["total"] == body["total"]
    assert (page1["limit"], page1["offset"]) == (2, 0)
    assert len(page1["items"]) == 2
    assert not {i["id"] for i in page1["items"]} & {
        i["id"] for i in page2["items"]
    }  # no repeats across pages


def test_list_detections_rejects_bad_paging_values(client):
    for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}):
        _list(client, params, expected_status=422)


def test_list_detections_rejects_unknown_query_parameters(client):
    _list(
        client, {"verdit": "spoof"}, expected_status=422
    )  # typo must not be silently ignored


# ---------- filters: verdict / date range / filename ----------
# (a file name that contains the test's tag is used with ?q=<tag> to isolate the rows of one test)


def _names(body: dict) -> list[str]:
    return [item["original_filename"] for item in body["items"]]


def test_filter_by_verdict(client):
    tag = _tag()
    _insert(tag, original_filename=f"{tag}-r1.wav", verdict="real")
    _insert(tag, original_filename=f"{tag}-s1.wav", verdict="spoof")
    _insert(tag, original_filename=f"{tag}-s2.wav", verdict="spoof")

    spoof = _list(client, {"q": tag, "verdict": "spoof"})
    assert spoof["total"] == 2
    assert {i["verdict"] for i in spoof["items"]} == {"spoof"}

    real = _list(client, {"q": tag, "verdict": "real"})
    assert _names(real) == [f"{tag}-r1.wav"]

    assert _list(client, {"q": tag})["total"] == 3  # no verdict filter = all of them


def test_filter_by_verdict_rejects_other_values(client):
    _list(client, {"verdict": "maybe"}, expected_status=422)


def test_filter_by_date_range_counts_whole_days_in_thai_time(client):
    tag = _tag()
    # Thai time is UTC+7, so  2026-10-02 17:30 UTC  =  2026-10-03 00:30 in Thailand
    _insert(
        tag,
        original_filename=f"{tag}-oct01.wav",
        created_at=datetime(2026, 10, 1, 5, 0, tzinfo=timezone.utc),
    )
    _insert(
        tag,
        original_filename=f"{tag}-oct02-late.wav",
        created_at=datetime(2026, 10, 2, 16, 30, tzinfo=timezone.utc),
    )
    _insert(
        tag,
        original_filename=f"{tag}-oct03-early.wav",
        created_at=datetime(2026, 10, 2, 17, 30, tzinfo=timezone.utc),
    )
    _insert(
        tag,
        original_filename=f"{tag}-oct04.wav",
        created_at=datetime(2026, 10, 4, 5, 0, tzinfo=timezone.utc),
    )

    day2 = _list(client, {"q": tag, "date_from": "2026-10-02", "date_to": "2026-10-02"})
    assert _names(day2) == [
        f"{tag}-oct02-late.wav"
    ]  # the whole Thai day, nothing from the next day

    day3 = _list(client, {"q": tag, "date_from": "2026-10-03", "date_to": "2026-10-03"})
    assert _names(day3) == [
        f"{tag}-oct03-early.wav"
    ]  # 00:30 Thai time belongs to the 3rd

    from_only = _list(client, {"q": tag, "date_from": "2026-10-03"})
    assert _names(from_only) == [f"{tag}-oct04.wav", f"{tag}-oct03-early.wav"]

    to_only = _list(client, {"q": tag, "date_to": "2026-10-01"})
    assert _names(to_only) == [f"{tag}-oct01.wav"]


def test_filter_by_date_rejects_bad_values(client):
    _list(client, {"date_from": "not-a-date"}, expected_status=422)
    _list(
        client,
        {"date_from": "2026-10-05", "date_to": "2026-10-01"},
        expected_status=422,
    )


def test_filter_by_filename_ignores_case_and_treats_wildcards_literally(client):
    tag = _tag()
    _insert(tag, original_filename=f"{tag}-Call_From_Bank.WAV")
    _insert(tag, original_filename=f"{tag}-other.wav")

    assert _names(_list(client, {"q": "call_from_bank"})) == [
        f"{tag}-Call_From_Bank.WAV"
    ]
    assert (
        _list(client, {"q": f"{tag}%"})["total"] == 0
    )  # "%" is just a character here, not "match anything"
    assert (
        _list(client, {"q": f"{tag}-oth_r"})["total"] == 0
    )  # "_" is not "any single character" either
    _list(client, {"q": ""}, expected_status=422)


def test_filters_combine_with_and(client):
    tag = _tag()
    _insert(
        tag,
        original_filename=f"{tag}-a.wav",
        verdict="spoof",
        created_at=datetime(2026, 10, 1, 5, 0, tzinfo=timezone.utc),
    )
    _insert(
        tag,
        original_filename=f"{tag}-b.wav",
        verdict="spoof",
        created_at=datetime(2026, 10, 9, 5, 0, tzinfo=timezone.utc),
    )
    _insert(
        tag,
        original_filename=f"{tag}-c.wav",
        verdict="real",
        created_at=datetime(2026, 10, 9, 5, 0, tzinfo=timezone.utc),
    )

    body = _list(client, {"q": tag, "verdict": "spoof", "date_from": "2026-10-05"})
    assert _names(body) == [f"{tag}-b.wav"]
    assert body["total"] == 1


# ---------- filters: user / guest / model version / partial spoof / probability range ----------


def _make_user(tag: str, name: str) -> tuple[str, str]:
    """Create a user directly in the database. Returns (user_id, email)"""
    email = f"{tag}-{name}@example.com"
    with SessionLocal() as db:
        user = UserAccount(email=email, password_hash="not-a-real-hash")
        db.add(user)
        db.commit()
        return str(user.id), email


def test_filter_by_user_guest_and_email(client):
    tag = _tag()
    somchai_id, somchai_email = _make_user(tag, "somchai")
    napat_id, _ = _make_user(tag, "napat")
    _insert(tag, original_filename="a.wav", user_id=somchai_id)
    _insert(tag, original_filename="b.wav", user_id=somchai_id)
    _insert(tag, original_filename="c.wav", user_id=napat_id)
    _insert(tag, original_filename="d.wav", user_id=None)

    def names(**params) -> list[str]:
        return sorted(_names(_list(client, {"model_version": tag, **params})))

    assert names(user_id=somchai_id) == ["a.wav", "b.wav"]
    assert names(user_email="SOMCHAI") == [
        "a.wav",
        "b.wav",
    ]  # part of the email, any case
    assert names(user_email=somchai_email) == ["a.wav", "b.wav"]
    assert names(guest="true") == ["d.wav"]
    assert names(guest="false") == ["a.wav", "b.wav", "c.wav"]
    assert names(user_id=somchai_id, guest="true") == []  # a guest has no user id
    assert names(user_email="nobody-" + tag) == []


def test_filter_by_user_rejects_a_malformed_user_id(client):
    _list(client, {"user_id": "not-a-uuid"}, expected_status=422)


def test_filter_by_model_version_is_an_exact_match(client):
    tag = _tag()
    _insert(tag, original_filename="v1.wav")
    _insert(tag + "-other", original_filename="v2.wav")

    assert _names(_list(client, {"model_version": tag})) == ["v1.wav"]
    assert (
        _list(client, {"model_version": tag[:-1]})["total"] == 0
    )  # a prefix is not enough


def test_filter_by_partial_spoof(client):
    tag = _tag()
    _insert(tag, original_filename="partial.wav", possible_partial_spoof=True)
    _insert(tag, original_filename="whole.wav", possible_partial_spoof=False)

    assert _names(_list(client, {"model_version": tag, "partial_spoof": "true"})) == [
        "partial.wav"
    ]
    assert _names(_list(client, {"model_version": tag, "partial_spoof": "false"})) == [
        "whole.wav"
    ]


def test_filter_by_probability_range_includes_both_ends(client):
    tag = _tag()
    for prob in (0.1, 0.5, 0.9):
        _insert(tag, original_filename=f"p{prob}.wav", mean_probability=prob)

    def names(**params) -> list[str]:
        return sorted(_names(_list(client, {"model_version": tag, **params})))

    assert names(min_prob=0.5) == ["p0.5.wav", "p0.9.wav"]
    assert names(max_prob=0.5) == ["p0.1.wav", "p0.5.wav"]
    assert names(min_prob=0.2, max_prob=0.8) == ["p0.5.wav"]
    assert names(min_prob=0.5, max_prob=0.5) == ["p0.5.wav"]


def test_filter_by_probability_rejects_bad_values(client):
    for params in (
        {"min_prob": -0.1},
        {"max_prob": 1.5},
        {"min_prob": 0.8, "max_prob": 0.2},
        {"min_prob": "high"},
    ):
        _list(client, params, expected_status=422)


# ---------- filter: feedback ----------


def _add_feedback(detection_id: str, user_id: str, agrees: bool) -> None:
    with SessionLocal() as db:
        db.add(Feedback(detection_id=detection_id, user_id=user_id, user_agrees=agrees))
        db.commit()


def test_filter_by_feedback_and_feedback_field_in_items(client):
    tag = _tag()
    user_id, _ = _make_user(tag, "somchai")
    agreed = _insert(tag, original_filename="agreed.wav", user_id=user_id)
    disagreed = _insert(tag, original_filename="disagreed.wav", user_id=user_id)
    _insert(tag, original_filename="silent.wav", user_id=user_id)
    _insert(tag, original_filename="guest.wav")  # a guest cannot leave feedback
    _add_feedback(agreed, user_id, True)
    _add_feedback(disagreed, user_id, False)

    def names(**params) -> list[str]:
        return sorted(_names(_list(client, {"model_version": tag, **params})))

    assert names(feedback="agree") == ["agreed.wav"]
    assert names(feedback="disagree") == ["disagreed.wav"]
    assert names(feedback="none") == ["guest.wav", "silent.wav"]
    assert len(names()) == 4  # the feedback join must not drop or duplicate rows

    items = {
        i["original_filename"]: i
        for i in _list(client, {"model_version": tag})["items"]
    }
    assert items["agreed.wav"]["feedback"] == "agree"
    assert items["disagreed.wav"]["feedback"] == "disagree"
    assert items["silent.wav"]["feedback"] is None


def test_filter_by_feedback_rejects_other_values(client):
    _list(client, {"feedback": "maybe"}, expected_status=422)


# ---------- sort / order ----------


def _sorted_names(client, tag: str, **params) -> list[str]:
    return _names(_list(client, {"model_version": tag, **params}))


def test_sort_by_each_column_in_both_directions(client):
    tag = _tag()
    # (name, created day, mean_probability, processing_ms) - every column ranks the rows in a different order
    rows = [("a.wav", 2, 0.9, 300), ("b.wav", 3, 0.1, 100), ("c.wav", 1, 0.5, 200)]
    for name, day, prob, ms in rows:
        _insert(
            tag,
            original_filename=name,
            created_at=datetime(2026, 9, day, 3, 0, tzinfo=timezone.utc),
            mean_probability=prob,
            processing_ms=ms,
        )

    assert _sorted_names(client, tag) == [
        "b.wav",
        "a.wav",
        "c.wav",
    ]  # default: newest first
    assert _sorted_names(client, tag, sort="created_at", order="asc") == [
        "c.wav",
        "a.wav",
        "b.wav",
    ]
    assert _sorted_names(client, tag, sort="mean_probability") == [
        "a.wav",
        "c.wav",
        "b.wav",
    ]
    assert _sorted_names(client, tag, sort="mean_probability", order="asc") == [
        "b.wav",
        "c.wav",
        "a.wav",
    ]
    assert _sorted_names(client, tag, sort="processing_ms") == [
        "a.wav",
        "c.wav",
        "b.wav",
    ]
    assert _sorted_names(client, tag, sort="processing_ms", order="asc") == [
        "b.wav",
        "c.wav",
        "a.wav",
    ]


def test_sort_keeps_filters_and_total(client):
    tag = _tag()
    _insert(tag, original_filename="x.wav", verdict="spoof", mean_probability=0.7)
    _insert(tag, original_filename="y.wav", verdict="spoof", mean_probability=0.9)
    _insert(tag, original_filename="z.wav", verdict="real", mean_probability=0.1)

    body = _list(
        client,
        {
            "model_version": tag,
            "verdict": "spoof",
            "sort": "mean_probability",
            "limit": 1,
        },
    )
    assert _names(body) == ["y.wav"]
    assert body["total"] == 2


def test_sort_paginates_stably_when_values_tie(client):
    tag = _tag()
    for i in range(5):
        _insert(
            tag, original_filename=f"tie{i}.wav", mean_probability=0.5
        )  # identical sort value on purpose

    seen = []
    for offset in range(5):
        seen += _names(
            _list(
                client,
                {
                    "model_version": tag,
                    "sort": "mean_probability",
                    "limit": 1,
                    "offset": offset,
                },
            )
        )
    assert sorted(seen) == [
        f"tie{i}.wav" for i in range(5)
    ]  # each row exactly once across the pages


def test_sort_rejects_other_columns_and_directions(client):
    _list(client, {"sort": "user_email"}, expected_status=422)
    _list(client, {"sort": "id; drop table detection_record"}, expected_status=422)
    _list(client, {"order": "up"}, expected_status=422)
