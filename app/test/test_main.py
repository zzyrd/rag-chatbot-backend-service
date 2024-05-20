"""unit test cases for three endpoints"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_wrong_request():
    """
    Send HTTP get request, which is not allowed.
    """
    response = client.get("/upload")
    assert response.status_code == 405
    assert response.json() == {'detail': 'Method Not Allowed'}

def test_upload_wrong_files(mocker):
    """
    Send HTTP post request with not allowed file format.
    """
    files = [
        ("files", ("test_file1.txt", b"file content 1", "text/plain")),
        ("files", ("test_file2.txt", b"file content 2", "text/plain")),
    ]
    mocker.patch("app.main.minio_client.put_object", return_value=None)
    mocker.patch("app.main.minio_client.presigned_get_object", return_value=None)

    response = client.post("/upload", files=files)
    assert response.status_code == 200
    assert response.json() == [
    {
        "filename": "test_file1.txt",
        "succeeded": False,
        "message": "unsupported file format",
        "file_url": None
    },
    {
        "filename": "test_file2.txt",
        "succeeded": False,
        "message": "unsupported file format",
        "file_url": None
    }
    ]

def test_upload_empty_files(mocker):
    """
    Send HTTP post request with empty file.
    """
    files = []
    mocker.patch("app.main.minio_client.put_object", return_value=None)
    mocker.patch("app.main.minio_client.presigned_get_object", return_value=None)

    response = client.post("/upload", files=files)
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "input": None,
                "loc": [
                    "body",
                    "files",
                ],
                "msg": "Field required",
                "type": "missing"
            }
        ]
    }

def test_upload_valid_files(mocker):
    """
    Send HTTP post request with allowed files.
    """
    files = [
        ("files", ("test1.pdf", b"file content 1", "application/pdf")),
        ("files", ("test2.pdf", b"file content 2", "application/pdf")),
    ]
    mocker.patch("app.main.minio_client.put_object", return_value=None)
    mocker.patch("app.main.minio_client.presigned_get_object", return_value="www.example.com")

    response = client.post("/upload", files=files)
    assert response.status_code == 200
    assert response.json() == [
    {
        "filename": "test1.pdf",
        "succeeded": True,
        "message": "File uploaded",
        "file_url": "www.example.com"
    },
    {
        "filename": "test2.pdf",
        "succeeded": True,
        "message": "File uploaded",
        "file_url": "www.example.com"
    }
    ]

def test_ocr_wrong_request():
    """
    Send HTTP get request, which is not allowed.
    """
    response = client.get("/ocr")
    assert response.status_code == 405
    assert response.json() == {'detail': 'Method Not Allowed'}

def test_ocr_empty_body(mocker):
    """
    Send HTTP post request with empty body.
    """
    body = {}
    mocker.patch("app.main.open", return_value="this is the file content")
    mocker.patch("app.main.get_file_content", return_value="this is test file")
    mocker.patch("app.main.store_embeddings", return_value=None)

    response = client.post("/ocr", json=body)
    assert response.status_code == 422
    assert response.json() == {'detail': [
        {'type': 'missing', 'loc': ['body', 'filename'], 'msg': 'Field required', 'input': {}},
        {'type': 'missing', 'loc': ['body', 'file_url'], 'msg': 'Field required', 'input': {}}
        ]}

def test_ocr_invalid_body(mocker):
    """
    Send HTTP post request with not allowed file.
    """
    body = {
            "filename": "test.pdf",
            "file_url": "www.example.com"
            }
    mocker.patch("app.main.read_file", return_value="this is the file content")
    mocker.patch("app.main.get_file_content", return_value="this is test file")
    mocker.patch("app.main.store_embeddings", return_value=None)

    response = client.post("/ocr", json=body)
    assert response.status_code == 500
    assert response.json() == {'detail':
                               {'message':
                                'Only two documents are supported: 建築基準法施行令.pdf, 東京都建築安全条例.pdf'}
    }

def test_ocr_valid_body_read_error(mocker):
    """
    Send HTTP post request with allowed file, but occurs a read error
    """
    body = {
            "filename": "建築基準法施行令.pdf",
            "file_url": "www.example.com"
            }
    mocker.patch("app.main.read_file", return_value=None) # read error
    mocker.patch("app.main.get_file_content", return_value="this is test file")
    mocker.patch("app.main.store_embeddings", return_value=None)

    response = client.post("/ocr", json=body)
    assert response.status_code == 500
    assert response.json() == {'detail': {'message': 'Data Process Error'}}

def test_ocr_valid_body_embedding_error(mocker):
    """
    Send HTTP post request with allowed file, but occurs an embedding error
    """
    body = {
            "filename": "建築基準法施行令.pdf",
            "file_url": "www.example.com"
            }
    mocker.patch("app.main.read_file", return_value="this is the file content")
    mocker.patch("app.main.get_file_content", return_value="this is test file")
    mocker.patch("app.main.store_embeddings", return_value=None) # embedding error

    response = client.post("/ocr", json=body)
    assert response.status_code == 500
    assert response.json() == {'detail': {'message': 'Embeddings Error'}}

def test_ocr_valid_body_success(mocker):
    """
    Send HTTP post request with allowed file successfully
    """
    body = {
            "filename": "建築基準法施行令.pdf",
            "file_url": "www.example.com"
            }
    mocker.patch("app.main.read_file", return_value="this is the file content")
    mocker.patch("app.main.get_file_content", return_value="this is test file")
    mocker.patch("app.main.store_embeddings", return_value={
            "doc_name": "建築基準法施行令",
            "doc_id": "doc0",
            "chunk_size": 0,
            "number_of_chunks": 0
        })

    response = client.post("/ocr", json=body)
    assert response.status_code == 200
    assert response.json() == {'message': 'ocr task finished', 'details':
                               {'doc_name': '建築基準法施行令',
                                'doc_id': 'doc0',
                                'chunk_size': 0,
                                'number_of_chunks': 0
                                }
                               }

def test_extract_wrong_request():
    """
    Send HTTP get request, which is not allowed.
    """
    response = client.get("/extract")
    assert response.status_code == 405
    assert response.json() == {'detail': 'Method Not Allowed'}

def test_extract_empty_body(mocker):
    """
    Send HTTP post request with empty body.
    """
    body = {}
    mocker.patch("app.main.query", return_value="this is query")
    mocker.patch("app.main.generate_response", return_value="this is generate_response")

    response = client.post("/extract", json=body)
    assert response.status_code == 422
    assert response.json() == {'detail': [
        {'type': 'missing', 'loc': ['body', 'query_text'],
         'msg': 'Field required', 'input': {}
         },
         {'type': 'missing', 'loc': ['body', 'file_id'],
          'msg': 'Field required', 'input': {}
          }
          ]}

def test_extract_invalid_body(mocker):
    """
    Send HTTP post request with invalid body
    """
    body = {
        "query_text": 123,
        "file_id": 123
        }
    mocker.patch("app.main.query", return_value="this is query")
    mocker.patch("app.main.generate_response", return_value="this is generate_response")

    response = client.post("/extract", json=body)
    assert response.status_code == 422
    assert response.json() == {'detail': [
        {'type': 'string_type', 'loc': ['body', 'query_text'],
         'msg': 'Input should be a valid string', 'input': 123}, 
         {'type': 'string_type', 'loc': ['body', 'file_id'],
          'msg': 'Input should be a valid string', 'input': 123}
          ]}

def test_extract_valid_body_query_error(mocker):
    """
    Send HTTP post request with valid body, but occurs query error
    """
    body = {
        "query_text": "How are you?",
        "file_id": "doc0"
        }
    mocker.patch("app.main.query", return_value=None) # query error
    mocker.patch("app.main.generate_response", return_value="this is generate_response")

    response = client.post("/extract", json=body)
    assert response.status_code == 500
    assert response.json() == {'detail': {'message': 'Not Found Relvant Context'}}

def test_extract_valid_body_answer_error(mocker):
    """
    Send HTTP post request with valid body, but occurs LLM response error for answers
    """
    body = {
        "query_text": "How are you?",
        "file_id": "doc0"
        }
    mocker.patch("app.main.query", return_value="this is query text")
    mocker.patch("app.main.generate_response", return_value=None) # answer error

    response = client.post("/extract", json=body)
    assert response.status_code == 500
    assert response.json() == {'detail': {'message': 'No Available Answer From LLM Model'}}

def test_extract_valid_body_success(mocker):
    """
    Send HTTP post request with valid body successfully
    """
    body = {
        "query_text": "How are you?",
        "file_id": "doc0"
        }
    mocker.patch("app.main.query", return_value="this is query text")
    mocker.patch("app.main.generate_response", return_value="this is answer")

    response = client.post("/extract", json=body)
    assert response.status_code == 200
    assert response.json() == {'message': 'query finished', 'query_answer': 'this is answer'}
