from pydantic import BaseModel, Field
from typing import List, Optional

class ChunkSummary(BaseModel):
    chunk_id: str
    original_text: str = Field(..., description="The filtered substantive text chunk.")
    summary: str = Field(..., description="LLM-generated summary of this specific chunk.")
    topic: Optional[str] = Field(None, description="Classified core topic of the chunk.")
    source_url: str