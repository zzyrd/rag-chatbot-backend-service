"""Upload endpoint model schema"""
from pydantic import BaseModel

class FileUploadResponse(BaseModel):
    """
    response object for uploaded file
    """
    filename: str
    succeeded: bool
    message: str | None = None
    file_url: str | None = None
