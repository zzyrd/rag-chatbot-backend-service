
"""ocr utility functions"""
import os
import time
import math
from pinecone import Pinecone
from pinecone import Index
from pinecone import ServerlessSpec
from pinecone import PineconeException
from openai import OpenAI, OpenAIError
import tiktoken

async def store_embeddings(client: OpenAI, pc: Pinecone, data:str, file_name:str) -> dict | None:
    """
    generate data embeddings and store into vector db
    """
    try:
        index_name = os.getenv('PINECONE_INDEX_NAME')
        index_init(index_name, pc)
        index = pc.Index(index_name)
        chunk_size = 256
        tokens = token_chunks(data, chunk_size=chunk_size)
        # determine maxium batch size
        max_batch_size = math.ceil(int(os.getenv('OPENAI_EMBEDDING_MAX_INPUT')) / chunk_size) - 1
        # create embeddings and store
        doc_name = file_name.rsplit(".", 1)[0]
        doc_id = mock_doc_encode(doc_name)
        # performance bottleneck -> use asynchronous approach
        upload_embeddings(client, index, tokens, doc_id, batch_size=max_batch_size)
        return {
            "doc_name": doc_name,
            "doc_id": doc_id,
            "chunk_size": chunk_size,
            "number_of_chunks": len(tokens)
        }
    except (PineconeException, OpenAIError, ValueError) as e:
        # add logger
        print("Error:", e)

    return None

def index_init(index_name: str | None, pc: Pinecone) -> None:
    """create a index if index_name is not found"""
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1536,  # dimensionality of text-embed-3-small
            metric='cosine',
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        # wait for index to be initialized
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
        # add logger info for first time index creation

def token_chunks(data: str, chunk_size: int = 256) -> list[tuple[list[int],str]]:
    """A helper function to chunk data into tokens with given chunk_size"""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(data)
    res = []
    for i in range(0, len(tokens), chunk_size):
        token = tokens[i: min(i+chunk_size, len(tokens))]
        text = enc.decode(token)
        res.append((token, text))
    return res

def upload_embeddings(client:OpenAI, index: Index, \
                      tokens: list[tuple[list[int],str]], doc_id:str, batch_size: int = 1) -> None:
    """
    A helper function to create embeddings and upload to vector DB in batch.
    Caveat: batch_size might exceed maximum context length of the given model.
    todo: calculate the maximum batch_size based on given model and given data
    """
    if batch_size < 1 or not isinstance(batch_size, int):
        raise ValueError('batch_size should be an integer bigger than 0')

    model_name = os.getenv('OPENAI_EMBEDDING_MODEL')
    namespace = os.getenv('PINECONE_NAMESPACE')
    for i in range(0, len(tokens), batch_size):
        # get batch of chunks and IDs
        tokens_batch = [token for token, _ in tokens[i: min(i+batch_size, len(tokens))]]
        text_batch = [text for _, text in tokens[i: min(i+batch_size, len(tokens))]]
        ids_batch = [f"{doc_id}#chunk{n}" for n in range(i, min(i+batch_size, len(tokens)))]
        # create embeddings
        res = client.embeddings.create(input=tokens_batch, model=model_name)
        embeds = [record.embedding for record in res.data]
        # prep metadata and upsert batch
        meta = [{'text': text} for text in text_batch]
        to_upsert = zip(ids_batch, embeds, meta)
        # upsert to Pinecone
        index.upsert(vectors=list(to_upsert), namespace=namespace)

# mock encode for different documents
def mock_doc_encode(file: str) -> str:
    """
    Call a cache service or DB to get the integer value of given document.
    if not found, create a new record into the cache service or DB
    """
    hash_map = {"建築基準法施行令": "doc0", "東京都建築安全条例": "doc1"}
    if file in hash_map:
        return hash_map[file]

    # generate new record: {filename: newId}
    return ''
