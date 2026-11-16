import spacy

class ContextQualityEvaluator:
    def __init__(self, model_name: str = "es_core_news_sm"):
        # Load Spanish spaCy model (matching your Laguna AI / Spanish text corpus)
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"Model '{model_name}' not found. Run: python -m spacy download {model_name}")
            raise

    def compute_fact_density(self, text: str) -> dict:
        doc = self.nlp(text)
        word_count = len([token for token in doc if not token.is_punct and not token.is_space])
        
        if word_count == 0:
            return {"entity_density": 0.0, "noun_chunk_density": 0.0, "score": 0.0}

        # 1. Count Named Entities (Facts, Organizations, Dates, Numbers)
        entity_count = len(doc.ents)
        
        # 2. Count Noun Chunks (Subject/Object anchors)
        noun_chunk_count = len(list(doc.noun_chunks))

        # Calculate normalized densities per 50 words
        entity_density = (entity_count / word_count) * 50
        noun_chunk_density = (noun_chunk_count / word_count) * 50

        # Composite factual richness score
        richness_score = (entity_density * 0.6) + (noun_chunk_density * 0.4)

        return {
            "word_count": word_count,
            "entity_count": entity_count,
            "noun_chunk_count": noun_chunk_count,
            "entity_density": round(entity_density, 2),
            "richness_score": round(richness_score, 2)
        }

# --- Example Usage in your Digestion Pipeline ---
if __name__ == "__main__":
    evaluator = ContextQualityEvaluator()
    
    sample_context =  "Laguna AI integra automatización, inteligencia artificial, analítica y diseño de procesos mediante un enfoque colaborativo que parte de la realidad operativa para desarrollar soluciones implementables por los equipos de trabajo." #"Laguna AI implementa soluciones utilizando frameworks basados en Python y modelos de lenguaje en servidores dedicados en Bogotá."
    metrics = evaluator.compute_fact_density(sample_context)
    print("Context Metrics:", metrics)