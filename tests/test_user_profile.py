"""
/users/me - a logged-in user views / edits their own account (display_name, password)
"""
import uuid

from tests.conftest import admin_login_headers


def _register(client, display_name: str | None = None, password: str = "Password1234") -> tuple[dict, str]:
    """Register a fresh user. Returns (auth headers, email)"""
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    body = {"email": email, "password": password}
    if display_name is not None:
        body["display_name"] = display_name
    res = client.post("/auth/register", json=body)
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, email


# ---------- GET /users/me ----------


def test_get_me_returns_own_profile_without_password_hash(client):
    headers, email = _register(client, display_name="Somchai")

    res = client.get("/users/me", headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"id", "email", "display_name", "created_at"}  # no password_hash, no is_active
    assert body["email"] == email
    assert body["display_name"] == "Somchai"


def test_get_me_shows_null_display_name_when_never_set(client):
    headers, _ = _register(client)
    assert client.get("/users/me", headers=headers).json()["display_name"] is None


def test_get_me_returns_each_user_their_own_data(client):
    headers_a, email_a = _register(client)
    headers_b, email_b = _register(client)

    assert client.get("/users/me", headers=headers_a).json()["email"] == email_a
    assert client.get("/users/me", headers=headers_b).json()["email"] == email_b


def test_get_me_requires_a_user_token(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    assert client.get("/users/me", headers=admin_login_headers(client)).status_code == 401  # admin token is not a user


def test_get_me_rejects_a_suspended_account(client):
    headers, email = _register(client)
    admin = admin_login_headers(client)
    user_id = client.get("/users/me", headers=headers).json()["id"]
    assert client.patch(f"/admin/users/{user_id}", json={"is_active": False}, headers=admin).status_code == 200

    assert client.get("/users/me", headers=headers).status_code == 401


# ---------- PATCH /users/me ----------


def test_patch_me_sets_changes_and_clears_display_name(client):
    headers, email = _register(client)

    res = client.patch("/users/me", json={"display_name": "Napat"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["display_name"] == "Napat"
    assert res.json()["email"] == email  # nothing else changes
    assert client.get("/users/me", headers=headers).json()["display_name"] == "Napat"  # really saved

    res = client.patch("/users/me", json={"display_name": "Napat K."}, headers=headers)
    assert res.json()["display_name"] == "Napat K."

    res = client.patch("/users/me", json={"display_name": None}, headers=headers)  # null = clear
    assert res.status_code == 200
    assert res.json()["display_name"] is None
    assert client.get("/users/me", headers=headers).json()["display_name"] is None


def test_patch_me_only_changes_the_callers_own_account(client):
    headers_a, _ = _register(client, display_name="A")
    headers_b, _ = _register(client, display_name="B")

    client.patch("/users/me", json={"display_name": "A2"}, headers=headers_a)

    assert client.get("/users/me", headers=headers_b).json()["display_name"] == "B"


def test_patch_me_rejects_empty_unknown_and_out_of_range_input(client):
    headers, _ = _register(client, display_name="Keep")

    for body in (
        {},  # nothing to update
        {"display_name": ""},  # 1-100 characters (send null to clear)
        {"display_name": "x" * 101},
        {"email": "new@example.com"},  # email is not editable
        {"is_active": False},  # a user cannot change their own status
        {"password_hash": "x"},
        {"display_name": "Ok", "email": "new@example.com"},  # one bad field rejects the whole request
    ):
        res = client.patch("/users/me", json=body, headers=headers)
        assert res.status_code == 422, body

    assert client.get("/users/me", headers=headers).json()["display_name"] == "Keep"  # nothing was applied


def test_patch_me_accepts_a_100_character_display_name(client):
    headers, _ = _register(client)
    res = client.patch("/users/me", json={"display_name": "ก" * 100}, headers=headers)
    assert res.status_code == 200
    assert res.json()["display_name"] == "ก" * 100


def test_patch_me_requires_a_user_token(client):
    body = {"display_name": "X"}
    assert client.patch("/users/me", json=body).status_code == 401
    assert client.patch("/users/me", json=body, headers=admin_login_headers(client)).status_code == 401


# ---------- PUT /users/me/password ----------


def _login(client, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_change_password_switches_which_password_can_log_in(client):
    headers, email = _register(client, password="OldPassword1")

    res = client.put(
        "/users/me/password",
        json={"current_password": "OldPassword1", "new_password": "NewPassword2"},
        headers=headers,
    )

    assert res.status_code == 204
    assert res.content == b""
    assert _login(client, email, "NewPassword2").status_code == 200
    assert _login(client, email, "OldPassword1").status_code == 401


def test_change_password_can_be_repeated_with_the_new_password_as_current(client):
    headers, email = _register(client, password="PasswordOne1")
    body = {"current_password": "PasswordOne1", "new_password": "PasswordTwo2"}
    assert client.put("/users/me/password", json=body, headers=headers).status_code == 204

    body = {"current_password": "PasswordTwo2", "new_password": "PasswordThree3"}
    assert client.put("/users/me/password", json=body, headers=headers).status_code == 204

    assert _login(client, email, "PasswordThree3").status_code == 200


def test_change_password_with_wrong_current_password_changes_nothing(client):
    headers, email = _register(client, password="OldPassword1")

    res = client.put(
        "/users/me/password",
        json={"current_password": "NotMyPassword9", "new_password": "NewPassword2"},
        headers=headers,
    )

    assert res.status_code == 400  # not 401: the token is fine, only the password is wrong
    assert res.json() == {"detail": "Current password is incorrect"}
    assert _login(client, email, "OldPassword1").status_code == 200
    assert _login(client, email, "NewPassword2").status_code == 401


def test_change_password_rejects_invalid_input(client):
    headers, email = _register(client, password="OldPassword1")

    for body in (
        {"current_password": "OldPassword1", "new_password": "short"},  # under 8 characters
        {"current_password": "OldPassword1", "new_password": "x" * 129},
        {"current_password": "OldPassword1", "new_password": "OldPassword1"},  # same as the current one
        {"current_password": "", "new_password": "NewPassword2"},
        {"new_password": "NewPassword2"},  # current_password missing
        {"current_password": "OldPassword1"},  # new_password missing
        {},
        {"current_password": "OldPassword1", "new_password": "NewPassword2", "email": "x@y.com"},  # extra field
    ):
        res = client.put("/users/me/password", json=body, headers=headers)
        assert res.status_code == 422, body

    assert _login(client, email, "OldPassword1").status_code == 200  # still the old one


def test_change_password_only_affects_the_caller(client):
    headers_a, email_a = _register(client, password="PasswordA111")
    _, email_b = _register(client, password="PasswordB222")

    client.put(
        "/users/me/password",
        json={"current_password": "PasswordA111", "new_password": "PasswordA999"},
        headers=headers_a,
    )

    assert _login(client, email_b, "PasswordB222").status_code == 200  # B is untouched


def test_change_password_requires_a_user_token(client):
    body = {"current_password": "OldPassword1", "new_password": "NewPassword2"}
    assert client.put("/users/me/password", json=body).status_code == 401
    assert client.put("/users/me/password", json=body, headers=admin_login_headers(client)).status_code == 401


def test_change_password_does_not_invalidate_the_existing_token(client):
    # known limit (JWT is stateless): a token issued before the change keeps working until it expires
    headers, _ = _register(client, password="OldPassword1")
    client.put(
        "/users/me/password",
        json={"current_password": "OldPassword1", "new_password": "NewPassword2"},
        headers=headers,
    )

    assert client.get("/users/me", headers=headers).status_code == 200
