from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime

class LinkCreate(BaseModel):
    url: HttpUrl
    expires_at: datetime | None = None
    
class LinkResponse(BaseModel):
    id: int
    url: HttpUrl
    slug: str
    click_count: int
    expires_at: datetime | None

    model_config = ConfigDict(from_attributes=True)