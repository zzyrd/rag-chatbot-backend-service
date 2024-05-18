"""Ocr endpoint model schema"""
from pydantic import BaseModel

class OcrRequest(BaseModel):
    """
    request body for ocr endpoint
    """
    filename: str
    file_url: str

class OcrResponse(BaseModel):
    """
    response object for ocr endpoint
    """
    message: str
    details: dict
