from pydantic import BaseModel, Field, model_validator


class LoaderResponse(BaseModel):
    rows_downloaded: int
    files: list[str]


class ErrorResponse(BaseModel):
    detail: str
    type: str


class DateRangeParams(BaseModel):
    first_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date YYYY-MM-DD")
    last_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date YYYY-MM-DD")

    @model_validator(mode="after")
    def check_range(self) -> "DateRangeParams":
        if self.first_date > self.last_date:
            raise ValueError("first_date must be <= last_date")
        return self
