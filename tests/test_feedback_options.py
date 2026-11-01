"""GET /feedback/options - the questionnaire catalog the frontend renders its form from"""
from typing import Literal, get_args

from app.schemas.feedback import DETAIL_FIELDS, FeedbackDetailsOut, FeedbackRequest


def _literal_values(annotation) -> set[str]:
    """Collect the values of the Literal hidden inside X | None or list[X]"""
    if get_args(annotation) and getattr(annotation, "__origin__", None) is Literal:
        return set(get_args(annotation))
    found: set[str] = set()
    for arg in get_args(annotation):
        found |= _literal_values(arg)
    return found


def _questions(client) -> dict:
    res = client.get("/feedback/options")
    assert res.status_code == 200, res.text
    return {q["key"]: q for q in res.json()["questions"]}


def test_options_need_no_login_and_include_the_privacy_notice(client):
    body = client.get("/feedback/options").json()
    assert "ไม่เก็บไฟล์เสียง" in body["notice"]


def test_there_is_exactly_one_question_per_answer_field(client):
    questions = _questions(client)
    assert set(questions) == set(DETAIL_FIELDS)
    assert len(client.get("/feedback/options").json()["questions"]) == len(DETAIL_FIELDS)  # no duplicates


def test_option_values_match_what_the_api_accepts(client):
    for key, question in _questions(client).items():
        accepted = _literal_values(FeedbackDetailsOut.model_fields[key].annotation)
        if question["type"] == "text":
            assert not accepted and question["options"] is None, key
        else:
            offered = [o["value"] for o in question["options"]]
            assert len(set(offered)) == len(offered), key  # no duplicate options
            assert set(offered) == accepted, key
            assert all(o["label"] for o in question["options"]), key


def test_question_types_and_text_limits_match_the_request_schema(client):
    questions = _questions(client)
    assert questions["audio_issues"]["type"] == "multi"
    assert all(q["type"] == "single" for k, q in questions.items() if q["options"] and k != "audio_issues")
    for key, question in questions.items():
        if question["type"] == "text":
            max_length = next(m.max_length for m in FeedbackRequest.model_fields[key].metadata if hasattr(m, "max_length"))
            assert question["max_length"] == max_length, key
        else:
            assert question["max_length"] is None, key


def test_every_question_has_a_thai_label_and_conditions_point_at_real_fields(client):
    for key, question in _questions(client).items():
        assert any("฀" <= ch <= "๿" for ch in question["label"]), key
        for field, value in (question["show_if"] or {}).items():
            assert value in _literal_values(FeedbackDetailsOut.model_fields[field].annotation), key


def test_input_method_is_not_asked_of_the_user_but_everything_else_is(client):
    questions = _questions(client)
    assert questions["input_method"]["ask_user"] is False
    assert all(q["ask_user"] for k, q in questions.items() if k != "input_method")
    assert questions["playback_device"]["show_if"] == {"audio_source": "speaker_replay"}
