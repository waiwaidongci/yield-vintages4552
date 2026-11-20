from pydantic import BaseModel, Field


class Login(BaseModel):
    email: str
    password: str


class LineInput(BaseModel):
    data: dict


class BatchInput(BaseModel):
    data: dict


class OutcomeInput(BaseModel):
    data: dict


class AuditInput(BaseModel):
    audit_date: str = Field(min_length=10, max_length=10)
