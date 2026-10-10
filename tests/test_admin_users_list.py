import uuid

from tests.conftest import admin_login_headers, make_wav_bytes


def _create_user(
    client, tag: str, name: str, display_name: str | None = None
) -> tuple[str, dict]:
    """Register a user whose email contains `tag`, so a test can search for exactly its own users"""
    email = f"{tag}-{name}@example.com"
    body = {"email": email, "password": "Password1234"}
    if display_name is not None:
        body["display_name"] = display_name
    res = client.post("/auth/register", json=body)
    assert res.status_code == 201, res.text
    return email, {"Authorization": f"Bearer {res.json()['access_token']}"}


def _predict(client, headers: dict) -> None:
    res = client.post(
        "/predict",
        files={"files": ("clip.wav", make_wav_bytes(), "audio/wav")},
        headers=headers,
    )
    assert res.status_code == 200, res.text


def test_list_users_requires_admin_token(client):
    assert client.get("/admin/users").status_code == 401

    user_headers = _create_user(client, uuid.uuid4().hex[:8], "plain")[1]
    assert client.get("/admin/users", headers=user_headers).status_code == 401


def test_list_users_returns_the_expected_fields_and_never_the_password(client):
    admin = admin_login_headers(client)
    tag = uuid.uuid4().hex[:8]
    email, _ = _create_user(client, tag, "a", display_name="Somchai")

    body = client.get("/admin/users", params={"q": tag}, headers=admin).json()
    assert body["total"] == 1
    item = body["items"][0]
    assert set(item) == {
        "id",
        "email",
        "display_name",
        "created_at",
        "last_login_at",
        "is_active",
        "detection_count",
    }
    assert item["email"] == email
    assert item["display_name"] == "Somchai"
    assert item["is_active"] is True
    assert item["last_login_at"] is None  # registered but never logged in
    assert item["detection_count"] == 0


def test_list_users_counts_detections_per_user(client):
    admin = admin_login_headers(client)
    tag = uuid.uuid4().hex[:8]
    _, busy = _create_user(client, tag, "busy")
    _create_user(client, tag, "idle")

    _predict(client, busy)
    _predict(client, busy)
    client.post(  # a guest check must not be counted for anybody
        "/predict", files={"files": ("g.wav", make_wav_bytes(), "audio/wav")}
    )

    items = client.get("/admin/users", params={"q": tag}, headers=admin).json()["items"]
    counts = {item["email"]: item["detection_count"] for item in items}
    assert counts == {f"{tag}-busy@example.com": 2, f"{tag}-idle@example.com": 0}


def test_list_users_search_matches_email_or_display_name_ignoring_case(client):
    admin = admin_login_headers(client)
    tag = uuid.uuid4().hex[:8]
    _create_user(client, tag, "one", display_name=f"Napat {tag}")
    _create_user(client, tag, "two", display_name="Somying")

    def search(q: str) -> list[str]:
        res = client.get("/admin/users", params={"q": q}, headers=admin)
        return [item["email"] for item in res.json()["items"]]

    assert search(f"{tag}-ONE") == [f"{tag}-one@example.com"]  # by email, any case
    assert search(f"NAPAT {tag}") == [
        f"{tag}-one@example.com"
    ]  # by display_name, any case
    assert sorted(search(tag)) == [f"{tag}-one@example.com", f"{tag}-two@example.com"]
    assert search(f"nothing-matches-{tag}") == []


def test_list_users_search_treats_percent_and_underscore_literally(client):
    admin = admin_login_headers(client)
    tag = uuid.uuid4().hex[:8]
    _create_user(client, tag, "x")

    # "%" would match every row if it were used as an SQL wildcard
    res = client.get("/admin/users", params={"q": f"{tag}%"}, headers=admin)
    assert res.json()["total"] == 0


def test_list_users_filters_by_is_active(client):
    admin = admin_login_headers(client)
    tag = uuid.uuid4().hex[:8]
    _create_user(client, tag, "a")
    _create_user(client, tag, "b")

    all_users = client.get("/admin/users", params={"q": tag}, headers=admin).json()
    assert all_users["total"] == 2

    active = client.get(
        "/admin/users", params={"q": tag, "is_active": "true"}, headers=admin
    ).json()
    suspended = client.get(
        "/admin/users", params={"q": tag, "is_active": "false"}, headers=admin
    ).json()
    assert active["total"] == 2
    assert suspended["total"] == 0


def test_list_users_is_newest_first_and_paginates_with_a_stable_total(client):
    admin = admin_login_headers(client)
    tag = uuid.uuid4().hex[:8]
    for name in ("a", "b", "c"):
        _create_user(client, tag, name)

    full = client.get("/admin/users", params={"q": tag}, headers=admin).json()
    page1 = client.get(
        "/admin/users", params={"q": tag, "limit": 2, "offset": 0}, headers=admin
    ).json()
    page2 = client.get(
        "/admin/users", params={"q": tag, "limit": 2, "offset": 2}, headers=admin
    ).json()

    assert full["total"] == page1["total"] == page2["total"] == 3
    assert (page1["limit"], page1["offset"]) == (2, 0)
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 1
    # the two pages together are exactly the full list, in the same order, with no repeats
    assert [i["id"] for i in page1["items"] + page2["items"]] == [
        i["id"] for i in full["items"]
    ]


def test_list_users_rejects_bad_paging_values(client):
    admin = admin_login_headers(client)
    for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}):
        res = client.get("/admin/users", params=params, headers=admin)
        assert res.status_code == 422, params
