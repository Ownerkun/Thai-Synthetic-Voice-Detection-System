from pydantic import BaseModel

NOTICE = (
    "การตอบแบบสอบถามนี้ไม่บังคับ ระบบไม่เก็บไฟล์เสียงของคุณ "
    "เก็บเฉพาะคำตอบเหล่านี้เพื่อนำไปปรับปรุงความแม่นยำของการตรวจสอบ"
)


class OptionOut(BaseModel):
    value: str
    label: str


class QuestionOut(BaseModel):
    key: str  # ชื่อฟิลด์ใน request ของ POST/PUT /history/{id}/feedback
    type: str  # "single" เลือกข้อเดียว · "multi" เลือกได้หลายข้อ · "text" พิมพ์เอง
    label: str
    help: str | None = None
    options: list[OptionOut] | None = None  # เฉพาะ single / multi
    max_length: int | None = None  # เฉพาะ text
    ask_user: bool = True  # False = frontend รู้เองอยู่แล้ว ส่งให้อัตโนมัติ ไม่ต้องถามผู้ใช้
    show_if: dict[str, str] | None = None  # ถามเมื่อฟิลด์อื่นมีค่านี้เท่านั้น เช่น {"audio_source": "speaker_replay"}


class FeedbackOptionsOut(BaseModel):
    notice: str  # ข้อความแจ้งความเป็นส่วนตัวที่ควรแสดงเหนือฟอร์ม
    questions: list[QuestionOut]


def _single(key: str, label: str, options: list[tuple[str, str]], **extra) -> QuestionOut:
    return QuestionOut(key=key, type="single", label=label, options=[OptionOut(value=v, label=t) for v, t in options], **extra)


QUESTIONS: list[QuestionOut] = [
    _single(
        "audio_source",
        "เสียงนี้ได้มาอย่างไร",
        [
            ("direct_voice", "พูดหรืออัดใส่ไมโครโฟนโดยตรง"),
            ("speaker_replay", "เปิดเสียงจากอีกเครื่องผ่านลำโพง แล้วอัดอีกที"),
            ("phone_call", "อัดจากสายโทรศัพท์"),
            ("chat_voice_message", "ข้อความเสียงจากแอปแชต (เช่น LINE)"),
            ("shared_media", "คลิปหรือไฟล์ที่ได้รับส่งต่อ/ดาวน์โหลดมา"),
            ("other", "อื่นๆ"),
        ],
    ),
    _single(
        "input_method",
        "ส่งเสียงเข้าระบบอย่างไร",
        [("recorded_in_app", "อัดเสียงในเว็บนี้"), ("uploaded_file", "อัปโหลดไฟล์")],
        ask_user=False,
    ),
    _single(
        "environment",
        "อัดเสียงที่ไหน",
        [
            ("quiet_room", "ห้องเงียบ"),
            ("noisy_indoor", "ในอาคารที่มีเสียงรบกวน"),
            ("outdoors", "กลางแจ้ง"),
            ("in_vehicle", "ในรถหรือยานพาหนะ"),
            ("crowded_public", "ที่สาธารณะที่คนพลุกพล่าน"),
        ],
    ),
    _single(
        "mic_distance",
        "ไมโครโฟนอยู่ห่างผู้พูดแค่ไหน",
        [
            ("close", "ชิดปาก (ไม่เกิน 5 ซม.)"),
            ("normal", "ระยะปกติ (6 ซม. - 20 ซม.)"),
            ("far", "ไกล (มากกว่า 20 ซม.)"),
        ],
    ),
    QuestionOut(
        key="audio_issues",
        type="multi",
        label="เสียงมีปัญหาอะไรบ้าง",
        help="เลือกได้หลายข้อ · ถ้าไม่มีปัญหาให้ส่ง [] (รายการว่าง) ซึ่งต่างจากการไม่ตอบข้อนี้",
        options=[
            OptionOut(value="background_noise", label="มีเสียงรบกวนรอบข้าง"),
            OptionOut(value="echo", label="มีเสียงก้อง/สะท้อน"),
            OptionOut(value="uneven_volume", label="เสียงดังเบาไม่สม่ำเสมอ"),
            OptionOut(value="too_quiet", label="เสียงเบามาก"),
            OptionOut(value="distorted", label="เสียงแตก"),
            OptionOut(value="choppy", label="เสียงขาดๆ หายๆ"),
            OptionOut(value="music_or_tv", label="มีเสียงเพลงหรือทีวีแทรก"),
            OptionOut(value="multiple_speakers", label="มีคนพูดหลายคน"),
        ],
    ),
    QuestionOut(key="recording_device", type="text", label="รุ่นอุปกรณ์ที่ใช้อัดเสียง (ถ้ารู้)", help="เช่น Galaxy A54, iPhone 18", max_length=100),
    QuestionOut(
        key="playback_device",
        type="text",
        label="รุ่นอุปกรณ์/ลำโพงที่ใช้เปิดเสียง (ถ้ารู้)",
        max_length=100,
        show_if={"audio_source": "speaker_replay"},
    ),
    _single(
        "truth_basis",
        "คุณรู้ได้อย่างไรว่าเสียงนี้จริงหรือสังเคราะห์",
        [
            ("self_recorded", "ฉันอัดเสียงจริงนี้ด้วยตัวเอง"),
            ("self_generated", "ฉันสร้างเสียงนี้ด้วยเครื่องมือ AI เอง"),
            ("know_the_speaker", "ฉันรู้จักผู้พูด/รู้ที่มาของเสียงแน่ชัด"),
            ("not_sure", "ไม่แน่ใจ"),
        ],
    ),
    _single(
        "speaker_accent",
        "สำเนียงของผู้พูด",
        [("central", "ภาคกลาง"), ("northern", "ภาคเหนือ"), ("northeastern", "ภาคอีสาน"), ("southern", "ภาคใต้"), ("other", "อื่นๆ")],
    ),
    _single(
        "speaker_age_group",
        "ช่วงอายุของผู้พูด",
        [("under_20", "ต่ำกว่า 20 ปี"), ("20_39", "20 - 39 ปี"), ("40_59", "40 - 59 ปี"), ("60_plus", "60 ปีขึ้นไป")],
    ),
    QuestionOut(key="comment", type="text", label="ข้อมูลเพิ่มเติม", help="อย่าพิมพ์ชื่อ เบอร์โทร หรือข้อมูลส่วนตัวของใคร", max_length=300),
]
