import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from src.services.chat_client import ChatClient
from src.services.llm_service import LLMService

load_dotenv()


class JudgeGrade(BaseModel):
    score: int = Field(..., ge=1, le=5, description="Puntuación entera del 1 al 5")
    reasoning: str = Field(..., description="Justificación breve de fundamentación y relevancia")


class EvaluationResult(BaseModel):
    question_id: str
    question: str
    context: str
    bot_reply: str
    score: int = Field(..., description="Integer score from 1 to 5")
    reasoning: str = Field(..., description="Justification for the grade")

class JEVEvaluationService:
    def __init__(
        self,
        chat_client: ChatClient,
        evaluation_data_path: str,
        llm_service: Optional[LLMService] = None,
    ):
        self.chat_client = chat_client
        self.evaluation_data_path = Path(evaluation_data_path)
        self.llm_service = llm_service or LLMService()

    def evaluate_response(self, question: str, answer: str, context: str) -> tuple[int, str]:
        """
        Delegates grading to LLMService (DeepSeek) on a 1-5 scale for groundedness and relevance.
        """
        prompt = f"""Eres un juez de evaluación de IA objetivo. Califica la respuesta del chatbot con respecto al contexto y la pregunta proporcionados.
Asigna una puntuación entera del 1 al 5 basada en qué tan bien fundamentada, precisa y relevante es la respuesta en relación con el contexto.

Criterios de evaluación:
- Fundamentación (Groundedness): ¿La respuesta se deriva estrictamente del contexto sin inventar información (alucinaciones)?
- Relevancia (Answer Relevance): ¿La respuesta aborda de manera precisa y directa la pregunta utilizando la información del contexto?

- 1: Completamente incorrecta, alucinada, irrelevante o desconectada del contexto.
- 3: Parcialmente correcta o pasa por alto detalles clave presentes en el contexto.
- 5: Totalmente precisa, completamente fundamentada en el contexto y responde de manera directa a la pregunta.

Pregunta: {question}
Respuesta: {answer}
Contexto: {context}

Devuelve tu evaluación exclusivamente en formato JSON válido con las claves "score" (entero 1-5) y "reasoning" (explicación breve en español).
"""

        try:
            print("Sending reply and context to DeepSeek judge for evaluation...")
            result_data = self.llm_service.generate_structured_evaluation(
                prompt=prompt,
                response_schema=JudgeGrade,
            )
            print("Evaluation received from DeepSeek. Parsing score...")

            validated = JudgeGrade.model_validate(result_data)
            return validated.score, validated.reasoning
        except Exception as e:
            print(f"Error during LLM evaluation scoring: {e}")
            return 1, f"Evaluation error: {str(e)}"

    def run_evaluation_pipeline(self, output_report_path: str = "data/reports/evaluation_results.json"):
        """
        Scans a directory (or reads a single file), loads all evaluation questions,
        queries the chatbot client, scores via LLMService, and saves aggregated reports.
        """
        if not self.evaluation_data_path.exists():
            raise FileNotFoundError(f"Evaluation dataset path not found at {self.evaluation_data_path}")

        items = []

        # Check if path is a directory; if so, scan recursively for json files
        if self.evaluation_data_path.is_dir():
            print(f"Scanning directory for evaluation files: {self.evaluation_data_path}")
            json_files = sorted(self.evaluation_data_path.rglob("*.json"))
            
            for file_path in json_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Handle different payload structures (list or dictionary wrappers)
                    file_items = []
                    if isinstance(data, list):
                        file_items = data
                    elif isinstance(data, dict):
                        file_items = data.get("evaluation_questions", data.get("evaluations", []))
                    
                    if file_items:
                        print(f"Loaded {len(file_items)} questions from {file_path.name}")
                        items.extend(file_items)
                except Exception as e:
                    print(f"Warning: Could not parse {file_path}: {e}")
        else:
            # Single file fallback
            with open(self.evaluation_data_path, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
            
            if isinstance(eval_data, list):
                items = eval_data
            elif isinstance(eval_data, dict):
                items = eval_data.get("evaluation_questions", eval_data.get("evaluations", []))

        if not items:
            print(f"No evaluation questions found at {self.evaluation_data_path}")
            return []

        results = []
        print(f"Starting evaluation run over total aggregated questions: {len(items)}")

        for idx, item in enumerate(items):
            question = item.get("question")
            context = item.get("expected_answer_context") or item.get("context") or item.get("summary", "No explicit context provided.")
            
            if not question:
                continue

            print(f"\n[{idx+1}/{len(items)}] Asking chatbot: '{question}'")

            # 1. Get live response from chatbot via Playwright client
            bot_reply = self.chat_client.send_message(question)
            print(f"Bot Reply: {bot_reply[:100]}...")

            # 2. Score via DeepSeek evaluation judge
            score, reasoning = self.evaluate_response(question, bot_reply, context)
            print(f"Score: {score}/5 | Reasoning: {reasoning}")

            record = EvaluationResult(
                question_id=item.get("question_id", f"q_{idx}"),
                question=question,
                context=context,
                bot_reply=bot_reply,
                score=score,
                reasoning=reasoning,
            )
            results.append(record.model_dump())

        # 3. Save aggregated report results
        os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
        with open(output_report_path, "w", encoding="utf-8") as f:
            json.dump(results, indent=2, ensure_ascii=False, fp=f)

        print(f"\nEvaluation pipeline completed successfully. Results saved to {output_report_path}")
        return results