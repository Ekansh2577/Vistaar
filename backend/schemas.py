from pydantic import BaseModel

class QuestionRequest(BaseModel):
    question: str

class WebSearchRequest(BaseModel):
    query: str
