from pydantic import BaseModel


class ScrapeRequest(BaseModel):
    url: str | None = None
    urls: list[str] | None = None
    parallel: int = 1


class ScrapeResult(BaseModel):
    url: str
    markdown: str | None = None
    status: str
    error: str | None = None


class ScrapeResponse(BaseModel):
    results: list[ScrapeResult]
