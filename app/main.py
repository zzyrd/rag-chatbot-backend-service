"""main API entrypoint"""
import os
import uuid
from datetime import timedelta
from typing import Callable, Awaitable
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, UploadFile, HTTPException
from minio import Minio
from pinecone import Pinecone
from openai import OpenAI

from app.custom_models.upload import FileUploadResponse
from app.custom_models.ocr import OcrRequest, OcrResponse
from app.custom_models.extract import ExtractRequest, ExtractResponse
from app.utilities.upload import get_file_content, allowed_file, read_file
from app.utilities.ocr import store_embeddings
from app.utilities.extract import query, generate_response
from app.logger.custom_logger import log

load_dotenv()
app = FastAPI()
minio_client = Minio(endpoint=os.getenv('MINIO_ENDPOINT'),
                access_key=os.getenv('MINIO_ACCESS_KEY'),
                secret_key=os.getenv('MINIO_SECRET_KEY'),
                secure=False) # Since it's local, secure is set to False
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

@app.middleware("http")
async def request_middleware(request: Request, \
                             call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """middleware to add request_id to logger context field and response header"""
    request_id = str(uuid.uuid4())
    with log.contextualize(request_id=request_id):
        response =  await call_next(request)
        response.headers["X-Request-ID"] = request_id
    return response

@app.post("/upload")
async def file_upload(files: list[UploadFile]) -> list[FileUploadResponse] | dict:
    """
    Accepts one or more file uploads (limited to pdf, tiff, png, jpeg formats).
    """
    if not files:
        log.warning("No Uploaded File")
        raise HTTPException(status_code=400, detail="No Uploaded File")
    res = []
    try:
        for file in files:
            if not allowed_file(file):
                res.append(FileUploadResponse(filename=file.filename, succeeded=False, \
                                            message="unsupported file format"))
            else:
                bucket_name = os.getenv('MINIO_BUCKET_NAME')
                object_name = file.filename
                # Reset file cursor to beginning
                await file.seek(0)
                # Upload file stream to blob storage
                minio_client.put_object(bucket_name, object_name, \
                                        file.file, file.size, \
                                        file.content_type)
                # Generate a presigned URL for the uploaded file
                expires_timedelta = timedelta(days=int(os.getenv('MINIO_URL_EXPIRE_DAYS')))
                presigned_url = minio_client.presigned_get_object(bucket_name, \
                                                                object_name, \
                                                                expires=expires_timedelta)

                res.append(FileUploadResponse(filename=file.filename, \
                                            succeeded=True, \
                                            message="File uploaded", \
                                            file_url=presigned_url))

    except Exception as e:
        log.error(str(e))
        raise HTTPException(status_code=500, detail={"message": str(e)}) from e

    return res

@app.post("/ocr")
async def mock_ocr(file: OcrRequest) -> OcrResponse | dict:
    """
    Simulates running an OCR service on a file for a given a signed url.
    Process OCR results with OpenAI's embedding models, 
    then upload the embeddings to a vector database
    """
    try:
        mock_files = os.getenv('MOCK_OCR_FILES').split(',')
        data = None
        if file.filename in mock_files:
            json_file = file.filename.rsplit(".", 1)[0] + '.json'
            # performance bottleneck
            data = read_file(json_file)
        else:
            data = await get_file_content(file.file_url, file.filename.lower().split('.')[-1])
            # files that are not in mock_files should stop doing embeddings
            raise FileExistsError("Only two documents are supported: 建築基準法施行令.pdf, 東京都建築安全条例.pdf")

        if not data:
            raise ValueError("Data Process Error")

        res = await store_embeddings(openai_client, pc_client, data, file.filename)
        if not res:
            raise ValueError("Embeddings Error")

        return OcrResponse(message="ocr task finished", details=res)
    except Exception as e:
        log.error(str(e))
        raise HTTPException(status_code=500, detail={"message": str(e)}) from e

@app.post("/extract")
async def text_query(req_body: ExtractRequest) -> ExtractResponse | dict:
    """
    high level support for doing this and that.
    """
    query_text = req_body.query_text
    doc_id = req_body.file_id
    try:
        # query vector db
        prompt = query(pc_client, openai_client, query_text, doc_id)
        if not prompt:
            raise ValueError("Not Found Relvant Context")
        # answer question with given prompt
        answer = generate_response(openai_client, prompt)
        if not answer:
            raise ValueError("No Available Answer From LLM Model")
        return ExtractResponse(message="query finished", query_answer=answer)
    except Exception as e:
        log.error(str(e))
        raise HTTPException(status_code=500, detail={"message": str(e)}) from e
