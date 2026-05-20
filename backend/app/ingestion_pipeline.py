# File input --> text extractor --> chunking(recursive) --> embedding model --> vector database

from fastapi import FastAPI, UploadFile
import fitz
from .logics import chunking, embedding_data, vector_storring, collection, chat_model

from .serializer import QueryRequest

app = FastAPI()

@app.post('/file_input')
async def file_input(file: UploadFile):
    contents = await file.read()

    # with open('temp.pdf','wb') as f:
    #     f.write(contents)

    # doc = fitz.open('temp.pdf')

    doc = fitz.open(stream=contents, filetype="pdf")

    text = ""
    
    for page in doc:
        text += page.get_text()

    # return {
    #     "extracted_text" : text
    # }


# Now i got extracted text . so i need now to convert these text into vector embedding. nah first i need to do chunking.and this chunking is done by defining chunk size

    chunks = chunking(text, chunk_size=100)

# now we need to do vector embedding

    embedded_data = embedding_data(chunks)

# for storing 
    vector_storring(chunks,embedded_data)


    return {
        "chunks_count": len(chunks),
        "extracted_text":text,
        "chunked_text" : chunks,
        "embedded_data_type":len(embedded_data),
        "status": "embedded and stored"
    }





# RETREIVAL PIPELINE

@app.post('/chat')
def chat(query : QueryRequest):
    query_embedding = embedding_data(query.request)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    # join
    context = "\n".join(results['documents'][0])


    # Prompt the LLM
    prompt = f"""
    You are a helpful assistant. Use the following context to answer the question.
    If you don't know the answer, say you don't know.
    
    Context:
    {context}
    
    Question: {query.request}
    """


    response = chat_model.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.1
    )

    return response.choices[0].message.content