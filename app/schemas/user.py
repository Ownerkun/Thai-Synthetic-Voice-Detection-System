from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # ฟิลด์แปลก (เช่น email, is_active, password_hash) -> 422

    display_name: str | None = Field(default=None, min_length=1, max_length=100)  # ส่ง null = ล้างชื่อ

    @model_validator(mode="after")
    def check_fields(self) -> "UserUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Send at least one field to update: display_name")
        return self

class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)  # กฎเดียวกับตอนสมัคร (RegisterRequest)

    @model_validator(mode="after")
    def check_different(self) -> "ChangePasswordRequest":
        if self.new_password == self.current_password:
            raise ValueError("New password must be different from the current password")
        return self