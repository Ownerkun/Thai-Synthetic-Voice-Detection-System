import uuid

from tests.conftest import admin_login_headers, make_wav_bytes


def _create_user(
    client, display_name: str | None = "Original"
) -> tuple[str, dict, str]:
    """Register a user. Returns (email, user headers, user id). the id is looked up through the admin list"""
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    body = {"email": email, "password": "Password1234"}
    if display_name is not None:
        body["display_name"] = display_name
    res = client.post("/auth/register", json=body)
    assert res.status_code == 201, res.text
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    found = client.get(
        "/admin/users", params={"q": email}, headers=admin_login_headers(client)
    ).json()
    return email, headers, found["items"][0]["id"]


def test_patch_user_requires_admin_token(client):
    _email, user_headers, user_id = _create_user(client)
    body = {"display_name": "Hacked"}

    assert client.patch(f"/admin/users/{user_id}", json=body).status_code == 401
    assert (
        client.patch(
            f"/admin/users/{user_id}", json=body, headers=user_headers
        ).status_code
        == 401
    )


def test_patch_display_name_changes_only_that_field(client):
    admin = admin_login_headers(client)
    _email, _headers, user_id = _create_user(client)

    res = client.patch(
        f"/admin/users/{user_id}", json={"display_name": "New Name"}, headers=admin
    )
    assert res.status_code == 200
    body = res.json()
    assert body["display_name"] == "New Name"
    assert body["is_active"] is True  # not sent, not touched
    assert body["id"] == user_id


def test_patch_null_display_name_clears_it(client):
    admin = admin_login_headers(client)
    _email, _headers, user_id = _create_user(client, display_name="To be cleared")

    res = client.patch(
        f"/admin/users/{user_id}", json={"display_name": None}, headers=admin
    )
    assert res.status_code == 200
    assert res.json()["display_name"] is None


def test_patch_is_active_only_leaves_display_name_alone(client):
    admin = admin_login_headers(client)
    _email, _headers, user_id = _create_user(client, display_name="Keep me")

    res = client.patch(
        f"/admin/users/{user_id}", json={"is_active": False}, headers=admin
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False
    assert res.json()["display_name"] == "Keep me"


def test_suspended_user_is_rejected_immediately_and_can_be_reactivated(client):
    admin = admin_login_headers(client)
    _email, user_headers, user_id = _create_user(client)
    assert client.get("/history", headers=user_headers).status_code == 200

    client.patch(f"/admin/users/{user_id}", json={"is_active": False}, headers=admin)
    assert (
        client.get("/history", headers=user_headers).status_code == 401
    )  # same token, no waiting for expiry

    client.patch(f"/admin/users/{user_id}", json={"is_active": True}, headers=admin)
    assert client.get("/history", headers=user_headers).status_code == 200


def test_suspended_user_shows_up_in_the_is_active_filter(client):
    admin = admin_login_headers(client)
    email, _headers, user_id = _create_user(client)
    client.patch(f"/admin/users/{user_id}", json={"is_active": False}, headers=admin)

    res = client.get(
        "/admin/users", params={"q": email, "is_active": "false"}, headers=admin
    )
    assert [item["email"] for item in res.json()["items"]] == [email]


def test_patch_response_includes_the_detection_count(client):
    admin = admin_login_headers(client)
    _email, user_headers, user_id = _create_user(client)
    client.post(
        "/predict",
        files={"files": ("clip.wav", make_wav_bytes(), "audio/wav")},
        headers=user_headers,
    )

    res = client.patch(
        f"/admin/users/{user_id}", json={"display_name": "X"}, headers=admin
    )
    assert res.json()["detection_count"] == 1


def test_patch_rejects_an_empty_body(client):
    admin = admin_login_headers(client)
    _email, _headers, user_id = _create_user(client)

    res = client.patch(f"/admin/users/{user_id}", json={}, headers=admin)
    assert res.status_code == 422


def test_patch_rejects_unknown_fields(client):
    admin = admin_login_headers(client)
    _email, _headers, user_id = _create_user(client)

    for body in (
        {"email": "other@example.com"},
        {"password_hash": "x"},
        {"display_name": "ok", "is_admin": True},
    ):
        res = client.patch(f"/admin/users/{user_id}", json=body, headers=admin)
        assert res.status_code == 422, body


def test_patch_rejects_bad_values(client):
    admin = admin_login_headers(client)
    _email, _headers, user_id = _create_user(client)

    for body in (
        {"display_name": ""},
        {"display_name": "x" * 101},
        {"is_active": None},
        {"is_active": "maybe"},
    ):
        res = client.patch(f"/admin/users/{user_id}", json=body, headers=admin)
        assert res.status_code == 422, body


def test_patch_unknown_user_is_404(client):
    admin = admin_login_headers(client)
    res = client.patch(
        f"/admin/users/{uuid.uuid4()}", json={"is_active": False}, headers=admin
    )
    assert res.status_code == 404
    assert res.json() == {"detail": "User not found"}


def test_patch_malformed_user_id_is_422(client):
    admin = admin_login_headers(client)
    res = client.patch(
        "/admin/users/not-a-uuid", json={"is_active": False}, headers=admin
    )
    assert res.status_code == 422
