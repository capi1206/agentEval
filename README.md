# Chatbot RAG Evaluator: Architecture & Specification

## 1. Project Objective
The goal of this project is to build an automated evaluation framework for a Retrieval-Augmented Generation (RAG) chatbot that answers questions based on a specific target website. The system will programmatically scrape the website, digest content into structured topics, generate test questions, simulate user-chatbot interactions, and grade the chatbot's responses using an LLM-as-a-judge model.

---

## 2. Pipeline Workflow & Component Mapping (MVC Pattern)

### Phase 1: Ingestion & Scraping (`src/services/scraper_service.py`)
* **Objective:** Extract raw content from the target website heuristically.
* **Details to build:** 
  * Implement web requests or headless browser automation to crawl target URLs.
  * Clean HTML, strip navigation bars/footers, and extract meaningful textual content.
  * Save raw outputs into `data/raw/`.

### Phase 2: Digestion & Topic Extraction (`src/controllers/digestion_controller.py` & `src/models/chunk_model.py`)
* **Objective:** Break page text into semantic chunks and classify them into core topics.
* **Details to build:**
  * Chunking logic (by heading, token length, or paragraph).
  * Use an LLM via `src/services/llm_service.py` to "digest" chunks and map them into categorized topics.
  * Output processed data into `data/processed/`.

### Phase 3: Test Question Generation (`src/controllers/digestion_controller.py` & `src/models/question_model.py`)
* **Objective:** Automatically formulate diverse test questions based on extracted topics and chunks.
* **Details to build:**
  * Prompt templates to generate factual, multi-step, or edge-case questions from topic chunks.
  * Save generated questions to be consumed by the simulator.

### Phase 4: Interaction & Simulation (`src/controllers/evaluation_controller.py` & `src/services/chat_client.py`)
* **Objective:** Simulate structured conversations by sending generated questions to the target chatbot.
* **Details to build:**
  * API connector or wrapper (`chat_client.py`) to query your RAG chatbot.
  * Capture user queries, chatbot responses, and retrieved source documents (context).

### Phase 5: Jev-Powered Evaluation (`src/controllers/evaluation_controller.py` & `src/services/jev_service.py` & `src/models/evaluation_model.py`)
* **Objective:** Grade the chatbot's response against the original source context using an JEV model.
* **Details to build:**
  * Define bounded evaluation metrics using Jev primitives: Choice (e.g., assessing support categories like supported, contradicted, or insufficient), Score (ordered scale for completeness or relevance), and Noul / Boolean (estimating probabilities for binary checks like faithfulness).
  * `jev_service.py` formats the runtime state (query, chatbot answer, cited evidence/context) and queries the Jev API to return typed decisions and probability distributions instantly without open-ended text generation.
  * Export structured evaluation metrics and reports into `data/reports/`.

---

## 3. Development Roadmap & Checklist

- [ ] **Milestone 1: Setup & Scraper**
  - [ ] Initialize project structure and `requirements.txt`.
  - [ ] Build and test `scraper_service.py` on a sample page.
- [ ] **Milestone 2: Digestion & Question Generation**
  - [ ] Implement text chunking and topic grouping schemas (`chunk_model.py`).
  - [ ] Write question generation logic using an LLM client.
- [ ] **Milestone 3: Simulation & Chat Integration**
  - [ ] Configure `chat_client.py` to communicate with the target chatbot.
  - [ ] Automate query batching.
- [ ] **Milestone 4: LLM Judge & Reporting**
  - [ ] Implement `jev_service.py` wrapper for structured evaluation schemas (evaluation_model.py).
  - [ ] Set up rubric templates using Jev Choice, Score, and Noul parameters.   
  - [ ] Generate performance summary reports and probability audit logs.
- [ ] **Milestone 5: Testing Suite**
  - [ ] Write unit tests under `tests/` for scraper, digestion, and judge scoring using `pytest`.