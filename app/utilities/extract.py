"""extract utility functions"""
import os
from pinecone import Pinecone
from pinecone import PineconeException
from openai import OpenAI, OpenAIError
import tiktoken

def query(pc: Pinecone, client: OpenAI, query_text: str, file_id: str) -> list | None:
    """
    query vector database based on given query text
    """
    try:
        index_name = os.getenv('PINECONE_INDEX_NAME')
        namespace = os.getenv('PINECONE_NAMESPACE')
        model_name = os.getenv('OPENAI_EMBEDDING_MODEL')
        # encode query into tokens
        enc = tiktoken.get_encoding("cl100k_base")
        token = enc.encode(query_text)
        if len(token) > int(os.getenv('OPENAI_EMBEDDING_MAX_INPUT')):
            raise ValueError(f"Token size exceed the maximum value: \
                             {int(os.getenv('OPENAI_EMBEDDING_MAX_INPUT'))}")

        query_embed = client.embeddings.create(input=token, model=model_name).data[0].embedding
        index = pc.Index(index_name)
        res = index.query(namespace=namespace, vector=query_embed, \
                               top_k=15, include_metadata=True) # k = 15: get more relvant context
        # print(res)
        # find the match where start with the same file_id in the id field
        matches = [m['metadata']['text'] for m in res['matches'] if m['id'].startswith(file_id)]
        return create_prompt(matches, query_text)
    except (PineconeException, OpenAIError, ValueError) as e:
        # add logger
        print("Error:", e)
    return None

def create_prompt(matches: list, query_text: str) -> str:
    """
    query vector database based on given query text
    """
    max_token_count = int(os.getenv('OPENAI_GPT_MODEL_MAX_TOKEN'))
    enc = tiktoken.get_encoding("cl100k_base")
    prompt_start = "Answer the question based on the context below.\n\n"+ "Context:\n"
    prompt_end = f"\n\nQuestion: {query_text}\nAnswer:"
    cur_token_count = max_token_count - (len(enc.encode(prompt_start)) \
                                          + len(enc.encode(prompt_end)))
    context = ''
    for m in matches:
        cur_token_count -= len(enc.encode(m))
        if cur_token_count > 0:
            context += m + '\n'
        else:
            break
    return prompt_start + context + prompt_end


def generate_response(client: OpenAI, prompt: str) -> str | None:
    """
        call LLM model to generate answer by a given prompt
    """
    try:
        model_name = os.getenv('OPENAI_GPT_MODEL')
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", \
                "content": "You are a helpful assistant knowing both English and Japanese. \
                You will be given some domain specific knowledge in Japanese, please answer questions with \
                the contextual information in both Japanese and English"},
                {"role": "user", "content": prompt}
            ]
            )
        print(completion)
        return completion.choices[0].message.content
    except OpenAIError as e:
        # add logger
        print("Error:", e)
    return None
  