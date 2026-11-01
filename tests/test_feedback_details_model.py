"""
Feedback detail columns (questionnaire answers) - storage level only; the API is tested in test_feedback_details.py
"""
import importlib.util
import uuid
from pathlib import Path

from app.core.database import SessionLocal
from app.models.detection import DetectionRecord, Feedback
from app.models.user import UserAccount

DETAIL_COLUMNS = {
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


def _new_feedback(**details) -> str:
    """Insert a user + detection + feedback directly. Returns the feedback id"""
    tag = uuid.uuid4().hex[:10]
    with SessionLocal() as db:
        user = UserAccount(email=f"{tag}@example.com", password_hash="not-a-real-hash")
        db.add(user)
        db.flush()
        record = DetectionRecord(
            user_id=user.id,
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
        db.add(record)
        db.flush()
        feedback = Feedback(detection_id=record.id, user_id=user.id, user_agrees=False, **details)
        db.add(feedback)
        db.commit()
        return str(feedback.id)


def _load(feedback_id: str) -> Feedback:
    with SessionLocal() as db:
        return db.get(Feedback, feedback_id)


def test_feedback_without_details_keeps_every_detail_column_null(client):
    feedback = _load(_new_feedback())

    for column in DETAIL_COLUMNS:
        assert getattr(feedback, column) is None, column


def test_feedback_details_are_stored_and_read_back(client):
    feedback = _load(
        _new_feedback(
            audio_source="speaker_replay",
            input_method="recorded_in_app",
            environment="noisy_indoor",
            mic_distance="far",
            audio_issues=["echo", "uneven_volume"],
            recording_device="Galaxy A54",
            playback_device="iPhone 12",
            truth_basis="self_recorded",
            speaker_accent="northern",
            speaker_age_group="60_plus",
            comment="ก" * 300,
        )
    )

    assert feedback.audio_source == "speaker_replay"
    assert feedback.audio_issues == ["echo", "uneven_volume"]
    assert feedback.recording_device == "Galaxy A54"
    assert feedback.comment == "ก" * 300


def test_audio_issues_distinguishes_not_answered_from_no_issues(client):
    no_answer = _load(_new_feedback())
    no_issues = _load(_new_feedback(audio_issues=[]))

    assert no_answer.audio_issues is None
    assert no_issues.audio_issues == []
    with SessionLocal() as db:  # "not answered" must be a real SQL NULL, not the JSON value null
        assert db.query(Feedback).filter(Feedback.id == no_answer.id, Feedback.audio_issues.is_(None)).count() == 1
        assert db.query(Feedback).filter(Feedback.id == no_issues.id, Feedback.audio_issues.is_(None)).count() == 0


def test_migration_adds_exactly_the_columns_the_model_has(client):
    path = next(Path("alembic/versions").glob("*_add_feedback_detail_columns.py"))
    spec = importlib.util.spec_from_file_location("feedback_detail_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    migrated = {name for name, _ in migration.STRING_COLUMNS} | {"audio_issues"}
    assert migrated == DETAIL_COLUMNS
    assert DETAIL_COLUMNS <= set(Feedback.__table__.columns.keys())
    for name, length in migration.STRING_COLUMNS:
        assert Feedback.__table__.columns[name].type.length == length, name
