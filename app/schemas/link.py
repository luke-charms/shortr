from pydantic import BaseModel, HttpUrl, ConfigDict

class LinkCreate(BaseModel):
    url: HttpUrl
    
class LinkResponse(BaseModel):
    url: HttpUrl
    slug: str

    # Updated for Pydantic V2
    model_config = ConfigDict(from_attributes=True)