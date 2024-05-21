"""Extract endpoint model schema"""
from pydantic import BaseModel

class ExtractRequest(BaseModel):
    """
    request body for extract endpoint
    """
    query_text: str
    file_id: str

class ExtractResponse(BaseModel):
    """
    response object for extract endpoint
    """
    message: str
    query_answer: str
