from pydantic import BaseModel

class TextRequest(BaseModel):
    text: str

class LLMResponse(BaseModel):
    response: str
