# FastAPI Application Documentation

## Table of Contents
- [FastAPI Application Documentation](#fastapi-application-documentation)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Prerequisites](#prerequisites)
  - [MinIO](#minio)
    - [How to deploy MinIO](#how-to-deploy-minio)
  - [Prepare `.env` file](#prepare-env-file)
  - [Running the Application](#running-the-application)
    - [Run Dcoker container](#run-dcoker-container)
    - [Run FastAPI locally](#run-fastapi-locally)
  - [API Endpoints](#api-endpoints)
  - [How to send request](#how-to-send-request)
    - [Request and Response Objects](#request-and-response-objects)
  - [Future Improvements](#future-improvements)
  - [Consideration for Production](#consideration-for-production)
    - [Security](#security)
    - [Scalability and Availability](#scalability-and-availability)

## Introduction
This FastAPI application is designed to manage and serve three different enpoints to faciliate an LLM driven application.
- `/upload`: Upload supported files (pdf, tiff, png, jpeg) to object store and return signed URLs
- `/ocr`: Do an OCR scanning on given file url and process OCR results with OpenAI embeddings, finally store document embeddings into vector database
- `/extract`: By given query text and file id, do embedding similarity search, and generate answer by using OpenAI chat completion API

## Prerequisites
- OpenAI Account and API Keys (LLM setup)
  - [OpenAI API register](https://openai.com/index/openai-api/)
  - [Generate API Keys](https://platform.openai.com/api-keys)
  - Keep your API Keys locally used in `.env` file
  - Caveat: calling OpenAI API may occur fees.
- Pinecone Account and API Keys (Vector DB setup)
  - [Pinecone official website](https://www.pinecone.io/)
  - [Pinecone setup](https://docs.pinecone.io/guides/get-started/quickstart)
  - Keep your API Keys locally, used in `.env` file
  - Choose free starter plan for study and experiment purpose
- MinIO setup (Object Store)
  - [MinIO official website](https://min.io/)
  - Set up minIO local object store for study and experiment purpose
  - For Details see the next section
  - Keep `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` locally, used in `.env` file
- Docker
  - Install Docker application
  - Run MinIO as a container application
  - Run Fast application as a container application (Optional)

## MinIO
MinIO is a high-performance, distributed object storage server that is designed for large-scale private cloud infrastructure. Is is software-defined and can run on any cloud or on-premises infrastructure, including public, private, or edge. MinIO is Amazon S3-compatible and is built for large-scale AI/ML, data lake, and database workloads.

MinIO is best suited for storing unstructured data such as Photos, Videos, Log files, Backups, VMs, and Container images.

### How to deploy MinIO
There are many different ways to implement MinIO object store. In this project, MinIO is deployed in the docker comtainer

1. Open your Terminal:
   ```
   mkdir -p ~/minio/data  # create local directory to keep data
   ```
2. Create docker network:
   ```
   docker network create --driver bridge my-network  # create a network named my-network
   ```

   Other network commands:
   ```
   docker network ls   # list network
   ```
   ```
   docker network rm my-network # remove network
   ```
3. Run MinIO container:
   ```
   docker run --network my-network -itd \
    -p 9000:9000 \
    -p 9001:9001 \
    --name minio \
    -v ~/minio/data:/data \
    -e "MINIO_ROOT_USER=minioadmin" \
    -e "MINIO_ROOT_PASSWORD=minioadmin" \
    quay.io/minio/minio server /data --console-address ":9001"
   ```
   Commands explanation:

   `--network my-network`: This specifies the network that the container should connect to. In this case, it's connecting to a network named "my-network".

   `-itd`: These flags are used for interactive mode (`-i`), keeping STDIN open (`-t`), and detaching from the container (`-d`). It means the container will run in the background, but you can still interact with it if needed.

   `-p 9000:9000 -p 9001:9001`: These options map ports from the host machine to the container. Port `9000` of the host is mapped to port `9000` of the container, and port `9001` of the host is mapped to port `9001` of the container. MinIO typically uses port `9000` for HTTP access and port `9001` for the console.

   `--name minio`: This option specifies the name of the container as "minio".

   `-v ~/minio/data:/data`: This option mounts a volume from the host machine to the container. It maps the `~/minio/data` directory on the host to the `/data` directory inside the container. This allows the MinIO server to store data persistently on the host machine

   `-e "MINIO_ROOT_USER=minioadmin" -e "MINIO_ROOT_PASSWORD=minioadmin"`: These options set environment variables inside the container. Here, it sets the `MINIO_ROOT_USER` to "minioadmin" and `MINIO_ROOT_PASSWORD` to "minioadmin", which are the default credentials for the MinIO root user.

   `quay.io/minio/minio`: This is the Docker image to be used for running the container. In this case, it pulls the MinIO image from the Quay.io registry.

   `server /data --console-address ":9001"`: This part specifies the command to be executed inside the container. It starts the MinIO server with `/data` as the data directory and specifies `--console-address ":9001"` to enable the MinIO console on port 9001. MinIO typically uses port 9000 for HTTP access and port 9001 for the console

4. Open web browser at `localhost:9001`
5. Enter `minioadmin` for both `Username` and `Password`
6. Select `Buckets` -> `Create Bucket` -> save `Bucket Name` locally, which used in `.env` file
7. Select `Access Keys` -> `Create access key` -> save `Access Key` and `Secret Key` locally, which used in `.env` file

## Prepare `.env` file
| Environment Vairable | Value|
|-----------------|-----------------|
| OPENAI_API_KEY | `<Your openai api key>` |
| OPENAI_EMBEDDING_MODEL | text-embedding-3-small |
| OPENAI_EMBEDDING_MAX_INPUT | 8191 |
| OPENAI_GPT_MODEL | gpt-4o |
| OPENAI_GPT_MODEL_MAX_TOKEN | 128000 |
| PINECONE_API_KEY | `<Your pinecone api key>` |
| PINECONE_INDEX_NAME | semantic-search-openai |
| PINECONE_NAMESPACE | construction_ns |
| MINIO_ENDPOINT | localhost:9000 (local) <br> minio:9000 (container)|
| MINIO_BUCKET_NAME | `<Your bucket name>` |
| MINIO_ACCESS_KEY | `<Your minio access key>` |
| MINIO_SECRET_KEY | `<Your minio secret key>` |
| MINIO_URL_EXPIRE_DAYS | 1 |
| MOCK_OCR_FILES | 建築基準法施行令.pdf,東京都建築安全条例.pdf |
| ALLOWED_EXTENSIONS | pdf,tiff,png,jpeg |


## Running the Application

### Run Dcoker container
```
docker run --network my-network --name fast-app -d -p 8000:8000 --env-file .env ghcr.io/zzyrd/tektome-fast-app:latest
```
Commands explanation:

`--network my-network`: This option specifies that the container should connect to an existing Docker network named "my-network". This allows the container to communicate with other containers on the same network.

`--name fast-app`: This option names the container "fast-app". Naming containers can make them easier to manage and refer to.

`-d`: This flag runs the container in detached mode, meaning it runs in the background and does not block the terminal.

`-p 8000:8000`: This option maps port `8000` on the host machine to port `8000` in the container. This makes the application accessible via port `8000` on the host.

`--env-file .env`: This option specifies an environment file (.env) that contains environment variables to be passed into the container. This is a convenient way to configure the container without hardcoding environment variables in the Docker command or Dockerfile.

<span style="color: red;">Caveat</span>: make sure your environment variable `MINIO_ENDPOINT` is using container name, not `localhost`. such as `MINIO_ENDPOINT=minio:9000`

`ghcr.io/zzyrd/tektome-fast-app:latest`: This specifies the Docker image to use for the container. It is pulled from the GitHub Container Registry (`ghcr.io`), from the repository `zzyrd/tektome-fast-app`, and uses the `latest` tag of the image.


The application will be accessible at `http://127.0.0.1:8000`.



### Run FastAPI locally

1. Clone the repository:
   
   Differen ways:
   -  ```sh
        git clone https://github.com/zzyrd/tektome-backend-service.git
        ```
    - ```sh
        git clone git@github.com:zzyrd/tektome-backend-service.git
        ```
    - Navigate to `https://github.com/zzyrd/tektome-backend-service` -> Click `Code` -> `Download ZIP`
  
    `CD` to the local repository:
    ```sh
    cd tektome-backend-service
    ```
    
2. Create and activate a virtual environment:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```
3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```
4. Move your `.env` file to the root directory

5. Start the FastAPI application:
   - Production
        ```sh
        fastapi run app/main.py
        ```
   - Dev
        ```sh
        fastapi dev app/main.py
        ```
6. The application will be accessible at `http://127.0.0.1:8000`.

## API Endpoints
- `POST /upload` - upload supported files to object store
- `POST /ocr` - ocr scan and create doc embeddings in vector db
- `POST /extract` - answer to user's query
- `GET /docs` - API docs Swagger UI
- `GET /redoc` - API doc second style

## How to send request

1. `curl` command
2. API Dev software such as `Postman` or `Insomnia`
3. Use Swagger UI doc `Try it out` at `http://127.0.0.1:8000/docs`

For simplicity, this project is using swagger UI to send requests to the API endpoints


### Request and Response Objects

**POST /upload**

- **Request:**
  - Swagger UI:
    ```
    Request body contains a list of files with Header: Content-Type: multipart/form-data'
    ```
  - `curl` command:
    ```
    curl -X 'POST' \
    'http://127.0.0.1:8000/upload' \
    -H 'accept: application/json' \
    -H 'Content-Type: multipart/form-data' \
    -F 'files=@東京都建築安全条例.pdf;type=application/pdf' \
    -F 'files=@建築基準法施行令.pdf;type=application/pdf'
    ```
- **Response:**
  - Success 200 OK
    - Response body
        ```json
        [
            {
                "filename": "東京都建築安全条例.pdf",
                "succeeded": true,
                "message": "File uploaded",
                "file_url": "www.example.com"
            },
            {
                "filename": "建築基準法施行令.pdf",
                "succeeded": true,
                "message": "File uploaded",
                "file_url": "www.example2.com"
            }
        ]
        ```
    - Response headers:
        ```
        content-length: 963 
        content-type: application/json 
        date: Wed,22 May 2024 02:23:01 GMT 
        server: uvicorn 
        x-request-id: 93cc7906-a92f-4627-8561-96a62158f738 
        ```
**POST /ocr**

- **Request:**
  - Swagger UI:
    
    Request body:
    ```json
    {
    "filename": "東京都建築安全条例.pdf",
    "file_url": "www.example.com"
    }
    ```
  - `curl` command:
    ```
    curl -X 'POST' \
    'http://127.0.0.1:8000/ocr' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
    "filename": "東京都建築安全条例.pdf",
    "file_url": "www.example.com"
    }'
    ```
- **Response:**
  - Success 200 OK
    - Response body
        ```json
        {
        "message": "ocr task finished",
        "details": {
            "doc_name": "東京都建築安全条例",
            "doc_id": "doc1",
            "chunk_size": 256,
            "number_of_chunks": 225
            }
        }
        ```
    - Response headers:
        ```
        content-length: 140 
        content-type: application/json 
        date: Wed,22 May 2024 02:31:09 GMT 
        server: uvicorn 
        x-request-id: b801e60a-fb62-492b-9b7d-959ecc0c34ca
        ```
**POST /extract**

- **Request:**
  - Swagger UI:
    
    Request body:
    ```json
    {
    "query_text": "学校の建物を建設するためのガイドは何ですか",
    "file_id": "doc1"
    }
    ```
  - `curl` command:
    ```
    curl -X 'POST' \
    'http://127.0.0.1:8000/extract' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
    "query_text": "学校の建物を建設するためのガイドは何ですか",
    "file_id": "doc1"
    }'
    ```
- **Response:**
  - Success 200 OK
    - Response body
        ```json
        {
        "message": "query finished",
        "query_answer": "学校の建物を建設するためのガイドは次の通りです：\n\n1. **非常用の照明装置**:\n   - 教室や地上に通ずる廊下、階段その他の通路に非常用の照明装置を設けることが必要です（採光上有効に直接外気に開放されている通路を除く）。\n\n2. **適用除外条件**:\n   - 建物の避難階や避難階の直上階にある場合、または当該部分の床面積の合計が500平方メートル以下の場合は、この規定は適用されません。\n\n3. **居室間の遮音**:\n   - 特殊建築物の居室相互間や居室とその他の部分との間仕切り壁は、遮音上有効な構造とする必要があります。\n\n4. **四階以上の教室の禁止**:\n   - 小学校や特別支援学校及びこれに類する専修学校や各種学校の用途に供する特殊建築物の四階以上には、教室や児童用の部屋を設けることが禁止されています。\n\n5. **排煙設備**:\n   - 窓やその他の開口部を有しない教室や廊下には、排煙設備を設ける必要があります。\n\n6. **内装制限**:\n   - 特別支援学校、専修学校、各種学校の用途に供する特殊建築物の居室の壁と天井は、難燃材料で仕上げる必要があります。また、主要な通路の壁や天井についても同様に難燃材料を使用する必要があります。\n\n---\n\nThe guidelines for constructing a school building are as follows:\n\n1. **Emergency Lighting System**:\n   - Emergency lighting systems must be installed in classrooms, corridors, stairs, and other passages leading to the ground, except for passages that are directly open to the outside air.\n\n2. **Exemption Conditions**:\n   - These regulations do not apply if the relevant part of the building is on the escape floor or the floor directly above it, or if the total floor area of the relevant part is 500 square meters or less.\n\n3. **Soundproofing Between Rooms**:\n   - Partition walls between rooms of special buildings for school use should be constructed to be effective for soundproofing.\n\n4. **Prohibition of Classrooms on the Fourth Floor or Above**:\n   - For primary schools, special support schools, and similar vocational and miscellaneous schools, classrooms and rooms for children cannot be established on the fourth floor or above of special buildings.\n\n5. **Smoke Ventilation Equipment**:\n   - Classrooms and corridors that do not have windows or other openings must be equipped with smoke ventilation equipment.\n\n6. **Interior Restrictions**:\n   - The walls and ceilings of rooms in special buildings serving special support schools, vocational schools, or miscellaneous schools must be finished with non-combustible materials. Additionally, the walls and ceilings of main corridors should also use non-combustible materials."
        }
        ```
    - Response headers:
        ```
        content-length: 2952 
        content-type: application/json 
        date: Wed,22 May 2024 02:40:23 GMT 
        server: uvicorn 
        x-request-id: 57c50b40-1584-492a-b8d5-2d1a1abc77a0 
        ```


## Future Improvements
- Implement user authentication and authorization such as `JWT token` and add Authorization middleware to check `Bearer TOKEN` on each request.
- Add `/health` endpoint to periodically check if API service is available.
- Extend logger module to have options to store logs in `.log` files or stream to third party storage for log aggregation and analytics such as `AWS cloutwatch` and `Elasticsearch`
- Improve API performance: Add `asych await` approach on `/ocr` and `/extract` endpoints to avoid waiting time for concurrent requests.
  - use `asyncio` to create asynchronously request to client such as `minio`, `pinecone`, and `openai`
  - use `multi-thread` to handle I/O tasks such as API calls to third party applications
  - Horizontal scaling by adding more instances running the backend services
- Add more unit tests to different modules within the application, and add coverage report.
- Move the `test` modules out of `app` directory to reduce the image size.

## Consideration for Production

### Security
The current API only supports HTTP request, which will send plaintext throughout the network. That is not secure. Nowadays almost all the web services are using `HTTPS` protocol to send requests by encrypting the message, and `Certificate` is required for the domain name.

In order to support `HTTPS`, the common way is to provide a external component, a `TLS Termination Proxy`, to handle `TLS handshake`, `Certificate Verification`, `Session keys Exchange`, and `Establish secure connection`. Hence, user will only send `HTTPS` request to the server location, The `TLS Termination Proxy` will decrypt the message, and send `HTTP` request to the FastAPI application. After processing the request, FastAPI sends back `HTTP` response to `TLS Termination Proxy`. Lastly, `TLS Termination Proxy` encrypt the response as `HTTPS` response back to user.

Options of technologies for TLS Termination Proxy:
- Traefix (certificate renewals supported)
- Caddy (certificate renewals supported)
- Nginx
- HAProxy

Options for free Certificate Authority:
- Let's Encrypt
- Cloud Services Provider CAs

### Scalability and Availability

There are many ways to make a system scalable and available with different engineering efforts. The main idea is the same.
1. Generally speaking, the system should be able to automatically restart/replace failed or crashed services to maintain high available without human intervention. In some cases, the system can automatically increase number of worker nodes to hanlde the `spike` requests.
2. System should be able to distribute and load balacing concurrent requests to several nodes, which are running the backend services, to hanlde the huge amount of requests without blocking the whole system.(Horizontal scaling)
3. For the sake of easiness to scale the system, make the application as `stateless` as possible.

Here is a brief summary of ways to deploy such a system in production environment.

1. Do everything manually. For example, we can launch serval `EC2` instances to run the `TLS Termination Proxy`, `backend services`, `Restart monitoring services`, `Database services`, etc. This is not a recommended way because it involves many operational overheads and engineering efforts. It's better to reuse the existing tools and services that are built by other talented people instead of reinventing the wheel again in the production.
2. Use container-based approach and container orchestration tools such as `Kubernetes` to manage the container applications. Then we deploy our applications to managed Kubernetes cluster in production. Examples of managed Kubernetes service are [Amazon EKS](https://aws.amazon.com/eks/) and [Azure Kubernetes Service](https://azure.microsoft.com/en-us/products/kubernetes-service). The container management tools will handle all the auto-scaling, auto-retart, failover, and networking between different containers, which is super convenient and powerful. Another advantage of using container is that the application can run on any operation system or platform without worrying about app dependencies and executables. (de facto approach) 
3. Use `Platform as a Service` (PaaS) cloud solution to host the application and abstract everythin else away from your side. For instance, [Heroku](https://www.heroku.com/platform) is one of cloud solution to host the application easily and manage auto-scaling, node replication, security by the platform. (easiest approach) 

In conclusion, there are many factors to affect the decision making on which approach to use such as service cost, engineering efforts, limited time to deliver, data privacy and security, and etc. It is always better to have deep and comprehensive discussion between engineering teams and stakeholders to decide the best approach at the end.