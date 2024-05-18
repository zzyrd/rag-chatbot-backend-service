"""main API entrypoint"""
import os
import json
from datetime import timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, HTTPException
from minio import Minio
from pinecone import Pinecone
from openai import OpenAI

from custom_models.upload import FileUploadResponse
from custom_models.ocr import OcrRequest, OcrResponse
from custom_models.extract import ExtractRequest, ExtractResponse
from utilities.upload import get_file_content, allowed_file
from utilities.ocr import store_embeddings
from utilities.extract import query, generate_response

load_dotenv()
app = FastAPI()
minio_client = Minio(endpoint=os.getenv('MINIO_ENDPOINT'),
                access_key=os.getenv('MINIO_ACCESS_KEY'),
                secret_key=os.getenv('MINIO_SECRET_KEY'),
                secure=False) # Since it's local, secure is set to False
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pc_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

@app.post("/upload")
async def file_upload(files: list[UploadFile]) -> list[FileUploadResponse] | dict:
    """
    Accepts one or more file uploads (limited to pdf, tiff, png, jpeg formats).
    """
    if not files:
        # add logger
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
                await file.seek(0)  # Reset file cursor to beginning
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
        # add logger
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
            with open(f"ocr/{json_file}", "r", encoding='UTF-8') as f:
                json_object = json.load(f)
                data = json_object['analyzeResult']['content']
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
        # add logger
        raise HTTPException(status_code=500, detail={"message": str(e)}) from e

@app.post("/extract")
async def text_query(req_body: ExtractRequest) -> ExtractResponse | dict:
    """
    high level support for doing this and that.
    """
    query_text = req_body.query_text
    doc_id = req_body.file_id # need some global variables for doc_id
    try:
        # query vector db
        prompt = query(pc_client, openai_client, query_text, doc_id)
        if not prompt:
            raise ValueError("Not Found Relvant Context")
        # answer question with given prompt
        print(prompt)
        answer = generate_response(openai_client, prompt)
        if not answer:
            raise ValueError("No Available Answer From LLM Model")
        return ExtractResponse(message="query finished", query_answer=answer)
    except Exception as e:
        # add logger
        raise HTTPException(status_code=500, detail={"message": str(e)}) from e

