from typing import List
from .models import Chunk

def chunk_document(text: str, window: int = 1200, overlap: int = 200) -> List[Chunk]:
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(len(text), start + window)
        slice_ = text[start:end]
        last_dot = slice_.rfind(".")
        if last_dot > window*0.5:
            end = start + last_dot + 1
        chunks.append(Chunk(id=idx, page=0, start=start, end=end, text=text[start:end]))
        idx += 1
        start = max(end - overlap, end)
    return chunks
