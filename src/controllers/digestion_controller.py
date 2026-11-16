import os
import json
import re
import uuid
from typing import List, Dict
from src.services.llm_service import LLMService
from src.services.context_quality_evaluator import ContextQualityEvaluator
from src.models.chunk_model import ChunkSummary
from src.models.question_model import EvaluationQuestion

class DigestionController:
    def __init__(self, min_word_count: int = 35):
        self.min_word_count= min_word_count
        self.processed_dir = "data/processed"
        self.eval_output_dir = os.path.join(self.processed_dir, "evaluations")
        
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.eval_output_dir, exist_ok=True)
        
        self.llm_service = LLMService()
        self.context_evaluator = ContextQualityEvaluator()

    def _clean_and_filter_chunks(self, raw_text: str) -> List[str]:
        lines = raw_text.split("\n")
        seen_chunks = set()
        relevant_chunks = []

        for line in lines:
            cleaned_line = line.strip()
            words = cleaned_line.split()
            if len(words) < self.min_word_count:
                continue

            normalized = re.sub(r'[^\w\s]', '', cleaned_line).lower()
            if normalized in seen_chunks:
                continue

            metrics = self.context_evaluator.compute_fact_density(normalized)
            
            # Filter criteria for high-value RAG evaluation
            if metrics["entity_density"] >= 1.0 and metrics["word_count"] >= 30:
                # Keep this chunk and generate a rigorous evaluation question
                print(f"Accepted chunk (Richness Score: {metrics['richness_score']})")
            else:
                print(f"Skipping fluff chunk (Low entity/fact density)")

            seen_chunks.add(normalized)
            relevant_chunks.append(cleaned_line)

        return relevant_chunks

    def process_raw_page_file(self, file_path: str) -> Dict:
        with open(file_path, "r", encoding="utf-8") as f:
            page_data = json.load(f)

        url = page_data.get("url")
        raw_content = page_data.get("content", "")

        filtered_chunks = self._clean_and_filter_chunks(raw_content)
        print(f"[{url}] Retained {len(filtered_chunks)} relevant chunks out of raw text.")

        processed_chunks_list = []
        evaluation_questions_list = []

        for i, chunk_text in enumerate(filtered_chunks):
            print(f"Processing chunk {i + 1} of {len(filtered_chunks)}...")
            
            # 1. Summarize chunk
            summary_text = self.llm_service.summarize_chunk(chunk_text)
            chunk_id = str(uuid.uuid4())
            
            # Map data to Chunk Model
            chunk_record = ChunkSummary(
                chunk_id=chunk_id,
                original_text=chunk_text,
                summary=summary_text,
                source_url=url
            )
            processed_chunks_list.append(chunk_record.model_dump())

            # 2. Generate evaluation question from chunk & summary
            q_data = self.llm_service.generate_evaluation_question(summary_text)
            
            eval_question = EvaluationQuestion(
                question_id=str(uuid.uuid4()),
                chunk_id=chunk_id,
                question=q_data.get("question", "Fallback question"),
                context=summary_text,
                source_url=url
            )
            evaluation_questions_list.append(eval_question.model_dump())

            # Test run break: stop after first chunk to manage API quotas / rate limits


        # 3. Compile and save digested chunks artifact
        digested_payload = {
            "source_url": url,
            "total_chunks": len(processed_chunks_list),
            "chunks": processed_chunks_list
        }
        base_name = os.path.basename(file_path)
        output_path = os.path.join(self.processed_dir, f"digested_{base_name}")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(digested_payload, f, ensure_ascii=False, indent=2)
        print(f"Saved processed digestion artifact to: {output_path}")

        # 4. Compile and save evaluation questions artifact
        eval_payload = {
            "source_url": url,
            "evaluation_questions": evaluation_questions_list
        }
        eval_output_path = os.path.join(self.eval_output_dir, f"eval_questions_{base_name}")
        with open(eval_output_path, "w", encoding="utf-8") as f:
            json.dump(eval_payload, f, ensure_ascii=False, indent=2)
        print(f"Saved evaluation dataset to: {eval_output_path}")

        return digested_payload

if __name__ == "__main__":
    raw_dir = "data/raw"
    controller = DigestionController(min_word_count=20)

    count = 0
    if os.path.exists(raw_dir):
        files = sorted(os.listdir(raw_dir))
        for filename in files:
            if filename.endswith(".json"):
                path = os.path.join(raw_dir, filename)
                controller.process_raw_page_file(path)
                # count +=1 # Process only the first file for testing
                # if True:
                #     break