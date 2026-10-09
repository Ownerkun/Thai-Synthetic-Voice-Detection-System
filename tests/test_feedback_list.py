from tests.conftest import predict_and_get_detection_id, register_and_get_headers


def test_feedback_list_is_empty_for_a_new_user(client):
    headers = register_and_get_headers(client)
    res = client.get("/feedback", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


def test_feedback_list_shows_my_feedback_with_detection_context_and_edits(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(
        client, headers, filename="call_from_bank.wav"
    )
    client.post(
        f"/history/{detection_id}/feedback", json={"user_agrees": True}, headers=headers
    )

    items = client.get("/feedback", headers=headers).json()
    assert len(items) == 1
    item = items[0]
    assert item["detection_id"] == detection_id
    assert item["original_filename"] == "call_from_bank.wav"
    assert item["verdict"] in ("real", "spoof")
    assert item["user_agrees"] is True
    assert item["updated_at"] is None

    client.put(
        f"/history/{detection_id}/feedback",
        json={"user_agrees": False},
        headers=headers,
    )

    items = client.get("/feedback", headers=headers).json()
    assert len(items) == 1  # editing must not create a second row
    assert items[0]["user_agrees"] is False
    assert items[0]["updated_at"] is not None


def test_feedback_list_is_newest_first_and_supports_limit_offset(client):
    headers = register_and_get_headers(client)
    first = predict_and_get_detection_id(client, headers, filename="first.wav")
    second = predict_and_get_detection_id(client, headers, filename="second.wav")
    client.post(
        f"/history/{first}/feedback", json={"user_agrees": True}, headers=headers
    )
    client.post(
        f"/history/{second}/feedback", json={"user_agrees": False}, headers=headers
    )

    names = [
        i["original_filename"] for i in client.get("/feedback", headers=headers).json()
    ]
    assert set(names) == {"first.wav", "second.wav"}

    page1 = client.get("/feedback?limit=1", headers=headers).json()
    page2 = client.get("/feedback?limit=1&offset=1", headers=headers).json()
    assert len(page1) == 1 and len(page2) == 1
    assert page1[0]["id"] != page2[0]["id"]


def test_feedback_list_only_contains_my_own_feedback(client):
    mine = register_and_get_headers(client)
    someone_else = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, someone_else)
    client.post(
        f"/history/{detection_id}/feedback",
        json={"user_agrees": True},
        headers=someone_else,
    )

    assert client.get("/feedback", headers=mine).json() == []


def test_feedback_list_requires_login_return_401_not_422(client):
    assert client.get("/feedback").status_code == 401
