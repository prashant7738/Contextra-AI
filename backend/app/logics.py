# in this file all the logics are here 

import re

import os
from dotenv import load_dotenv
load_dotenv()
from huggingface_hub import InferenceClient

import chromadb
import uuid
db_client = chromadb.PersistentClient(path='./my_vector_db')
collection = db_client.get_or_create_collection(name="knowledge-base")


chat_model = InferenceClient(
    model="meta-llama/Llama-3.1-8B-Instruct",
    api_key=os.environ["HF_TOKEN"]
)


client = InferenceClient(
    provider="hf-inference",
    api_key=os.environ["HF_TOKEN"],
)


# this is smart chunking so that sentence remain intant
def chunking(doc, chunk_size = 50):
    sentences = re.split(r'(?<=[.!?]) +', doc)

    chunks = []
    current = []
    word_count = 0

    for sentence in sentences:
        words = len(sentence.split())

        if words + word_count > chunk_size :
            chunks.append(" ".join(current))
            current = [sentence]
            word_count = words

        else:
            current.append(sentence)
            word_count += words

    if current:
        chunks.append(" ".join(current))

    return chunks



def embedding_data(data):
    return client.feature_extraction(
        data,
        model="BAAI/bge-base-en-v1.5",
    )


def vector_storring(chunks,embeddings):

    ids = [str(uuid.uuid4()) for _ in chunks]
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids= ids
    )