"""upload utility functions"""
import os
import json
import httpx
import fitz  # PyMuPDF
from fastapi import UploadFile
from app.logger.custom_logger import log

def allowed_file(file: UploadFile) -> bool:
    """
    validate if file provided is allowed entension.
    """
    try:
        extensions = os.getenv('ALLOWED_EXTENSIONS').split(',')
        return file.filename.lower().rsplit(".", 1)[1] in extensions
    except (KeyError,TypeError,ValueError) as e:
        raise e

async def get_file_content(url: str, file_type: str) -> str | None:
    """
    use httpx to asynchrously get file from given url
    Handle different file format accordingly (pdf,tiff,png,jpeg)
    """
    try:
        async with httpx.AsyncClient() as httpx_client:
            response = await httpx_client.get(url)
            if response.status_code == 200:
                if file_type == 'pdf':
                    return process_pdf(response.content)
                if file_type == 'tiff':
                    return None
                if file_type == 'png':
                    return None
                if file_type == 'jpeg':
                    return None
            else:
                raise ValueError(f"Failed to retrieve the file. \
                                 Status code: {response.status_code}")
    except (httpx.RequestError, OSError, ValueError) as e:
        log.error(e)
    return None

def process_pdf(file: bytes) -> str | None:
    """
    extract data out of pdf file
    """
    try:
        pdf_document = fitz.open(stream=file, filetype="pdf")
        extracted_text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            text = page.get_text()
            extracted_text += text + "\n"
        return extracted_text
    except OSError as e:
        raise e

def read_file(file_name: str) -> str:
    """Read local ocr folder and get target file content"""
    try:
        data = None
        with open(f"ocr/{file_name}", "r", encoding='UTF-8') as f:
            json_object = json.load(f)
            data = json_object['analyzeResult']['content']
        return data
    except OSError as e:
        raise e
