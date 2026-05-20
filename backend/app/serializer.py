from pydantic import BaseModel

class QueryRequest(BaseModel):
    request : str