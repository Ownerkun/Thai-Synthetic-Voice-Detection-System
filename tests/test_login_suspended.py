import uuid

from tests.conftest import admin_login_headers

PASSWORD = "Password1234"


def _register(client) -> tuple[str, str]:
    """Returns (email, user id)"""
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    res = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert res.status_code == 201, res.text
    found = client.get(
        "/admin/users", params={"q": email}, headers=admin_login_headers(client)
    ).json()
    return email, found["items"][0]["id"]


def _set_active(client, user_id: str, active: bool) -> None:
    res = client.patch(
        f"/admin/users/{user_id}",
        json={"is_active": active},
        headers=admin_login_headers(client),
    )
    assert res.status_code == 200, res.text


def test_suspended_user_cannot_log_in_but_can_after_reactivation(client):
    email, user_id = _register(client)
    credentials = {"email": email, "password": PASSWORD}

    _set_active(client, user_id, False)
    res = client.post("/auth/login", json=credentials)
    assert res.status_code == 403
    assert res.json() == {"detail": "Account suspended"}

    _set_active(client, user_id, True)
    assert client.post("/auth/login", json=credentials).status_code == 200


def test_wrong_password_on_a_suspended_account_still_looks_like_any_wrong_password(
    client,
):
    email, user_id = _register(client)
    _set_active(client, user_id, False)

    res = client.post(
        "/auth/login", json={"email": email, "password": "not-the-password"}
    )
    assert res.status_code == 401
    assert res.json() == {"detail": "Invalid email or password"}


def test_login_of_a_suspended_account_does_not_touch_last_login_at(client):
    email, user_id = _register(client)
    _set_active(client, user_id, False)
    client.post("/auth/login", json={"email": email, "password": PASSWORD})

    found = client.get(
        "/admin/users", params={"q": email}, headers=admin_login_headers(client)
    ).json()
    assert found["items"][0]["last_login_at"] is None
