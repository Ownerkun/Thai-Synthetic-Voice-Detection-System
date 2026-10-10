import uuid

from app.core.database import SessionLocal
from app.models.user import UserAccount
from tests.conftest import make_wav_bytes


def _register(client) -> tuple[str, dict]:
    """Return (email, auth headers) of a brand-new user"""
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    res = client.post(
        "/auth/register", json={"email": email, "password": "Password1234"}
    )
    assert res.status_code == 201, res.text
    return email, {"Authorization": f"Bearer {res.json()['access_token']}"}


def _predict(client, headers: dict):
    return client.post(
        "/predict",
        files={"files": ("clip.wav", make_wav_bytes(), "audio/wav")},
        headers=headers,
    )


def test_predict_still_saves_history_for_an_active_user(client):
    _email, headers = _register(client)
    res = _predict(client, headers)
    assert res.status_code == 200
    assert res.json()["results"][0]["saved_to_history"] is True


def test_predict_treats_a_suspended_user_as_guest(client):
    email, headers = _register(client)

    with SessionLocal() as db:
        user = db.query(UserAccount).filter(UserAccount.email == email).one()
        user.is_active = False
        db.commit()

    res = _predict(client, headers)
    assert res.status_code == 200
    body = res.json()
    assert len(body["results"]) == 1  # the audio is still analysed
    assert body["results"][0]["saved_to_history"] is False


def test_predict_treats_a_deleted_user_as_guest(client):
    email, headers = _register(client)

    with SessionLocal() as db:
        user = db.query(UserAccount).filter(UserAccount.email == email).one()
        db.delete(user)
        db.commit()

    res = _predict(client, headers)
    assert res.status_code == 200
    body = res.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["saved_to_history"] is False
