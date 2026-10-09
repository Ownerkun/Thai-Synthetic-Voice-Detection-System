from tests.conftest import predict_and_get_detection_id, register_and_get_headers


def test_get_feedback_returns_404_before_any_feedback_is_submitted(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, headers)

    res = client.get(f"/history/{detection_id}/feedback", headers=headers)
    assert res.status_code == 404


def test_put_feedback_returns_404_if_nothing_to_edit_yet(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, headers)

    res = client.put(
        f"/history/{detection_id}/feedback",
        json={"user_agrees": False},
        headers=headers,
    )
    assert res.status_code == 404


def test_submit_then_read_then_edit_feedback(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, headers)

    created = client.post(
        f"/history/{detection_id}/feedback", json={"user_agrees": True}, headers=headers
    )
    assert created.status_code == 201, created.text
    assert created.json()["user_agrees"] is True
    assert created.json()["updated_at"] is None  # never edited yet

    read_back = client.get(f"/history/{detection_id}/feedback", headers=headers)
    assert read_back.status_code == 200
    assert read_back.json()["id"] == created.json()["id"]

    edited = client.put(
        f"/history/{detection_id}/feedback",
        json={"user_agrees": False},
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["id"] == created.json()["id"]  # same row edited, not a new one
    assert edited.json()["user_agrees"] is False
    assert edited.json()["updated_at"] is not None

    after = client.get(f"/history/{detection_id}/feedback", headers=headers)
    assert after.json()["user_agrees"] is False


def test_put_feedback_rejects_invalid_body(client):
    headers = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, headers)
    client.post(
        f"/history/{detection_id}/feedback", json={"user_agrees": True}, headers=headers
    )

    res = client.put(f"/history/{detection_id}/feedback", json={}, headers=headers)
    assert res.status_code == 422


def test_user_cannot_read_or_edit_someone_elses_feedback(client):
    owner = register_and_get_headers(client)
    other = register_and_get_headers(client)
    detection_id = predict_and_get_detection_id(client, owner)
    client.post(
        f"/history/{detection_id}/feedback", json={"user_agrees": True}, headers=owner
    )

    assert (
        client.get(f"/history/{detection_id}/feedback", headers=other).status_code
        == 404
    )
    assert (
        client.put(
            f"/history/{detection_id}/feedback",
            json={"user_agrees": False},
            headers=other,
        ).status_code
        == 404
    )

    assert (
        client.get(f"/history/{detection_id}/feedback", headers=owner).json()[
            "user_agrees"
        ]
        is True
    )


def test_feedback_edit_endpoints_require_login_return_401_not_422(client):
    some_id = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/history/{some_id}/feedback").status_code == 401
    assert (
        client.put(
            f"/history/{some_id}/feedback", json={"user_agrees": True}
        ).status_code
        == 401
    )
