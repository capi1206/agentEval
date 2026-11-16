import os
import json
from dotenv import load_dotenv
from typing import Type
from pydantic import BaseModel
from openai import OpenAI
# Load environment variables from the .env file in the project root
load_dotenv()

class LLMService:
    def __init__(self, model_name: str = "deepseek-chat"):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is missing.")
            
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model_name = model_name

    def summarize_chunk(self, chunk_text: str) -> str:
        prompt = (
            "Eres un editor técnico experto. Proporciona un resumen conciso "
            "que capture la información fáctica central; este resumen se utilizará para testear" 
             " la eficacia de sistema RAG, "
            "por lo que no debes omitir detalles y responde solo con el resumen:\n\n"
            f"{chunk_text}"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating summary from DeepSeek: {e}")
            return "Summary generation failed."

    def generate_evaluation_question(self, summary: str) -> dict:
        prompt = (
            "Eres un ingeniero experto en evaluación de RAG. Tu objetivo es probar la capacidad de un chatbot "
            "para recuperar y sintetizar información precisa.\n\n"
            f"Resumen del fragmento:\n{summary}\n\n"
            "Tarea:\n"
            "Debes formular una pregunta fáctica, específica y desafiante que PUEDA SER RESPONDIDA ÚNICAMENTE "
            "con el texto proporcionado sin tener que hacer una referencia al fragmento, " 
             "la pregunta no debe hacer referencia explícita a dicho fragmento. "
            "Devuelve la salida en formato JSON válido con la clave: 'question'."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            print(f"Error generating question from DeepSeek: {e}")
            return {
                "question": "Failed to generate evaluation question."
            }

    def generate_structured_evaluation(self, prompt: str, response_schema: Type[BaseModel]) -> dict:
        """
        Used by JEVEvaluationService to grade responses in JSON format.
        DeepSeek requires explicit JSON schema instructions in the prompt when using json_object mode.
        """
        schema_json = json.dumps(response_schema.model_json_schema(), ensure_ascii=False)
        system_instruction = (
            "Eres un evaluador estricto que responde ÚNICAMENTE con un objeto JSON válido "
            f"que cumple exactamente con este esquema JSON:\n{schema_json}"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            print(f"Error during DeepSeek evaluation scoring: {e}")
            raise

