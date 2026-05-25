import re


def chunk_document(pages_data: list[dict], chunk_size: int = 50) -> list[dict]:
    """
    Takes list of pages with metadata and returns chunks preserving page info.
    
    pages_data = [
        {"page": 1, "text": "...", "filename": "doc.pdf"},
        {"page": 2, "text": "...", "filename": "doc.pdf"},
    ]
    """
    chunks = []
    
    for page_info in pages_data:
        text = page_info["text"]
        page_num = page_info["page"]
        filename = page_info["filename"]
        
        sentences = re.split(r"(?<=[.!?]) +", text)
        current = []
        word_count = 0
        
        for sentence in sentences:
            words = len(sentence.split())
            if words + word_count > chunk_size:
                if current:
                    chunks.append({
                        "text": " ".join(current),
                        "page": page_num,
                        "filename": filename
                    })
                current = [sentence]
                word_count = words
            else:
                current.append(sentence)
                word_count += words
        
        if current:
            chunks.append({
                "text": " ".join(current),
                "page": page_num,
                "filename": filename
            })
    
    return chunks