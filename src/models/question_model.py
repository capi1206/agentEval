from pydantic import BaseModel, Field
from typing import List, Optional

class EvaluationQuestion(BaseModel):
    question_id: str
    chunk_id: str = Field(..., description="ID of the source chunk this question is derived from.")
    question: str = Field(..., description="The factual question formulated for the chatbot.")
    context: str = Field(..., description="The key facts or summary snippet.")
    source_url: str = Field(..., description="The original webpage URL for verification.")