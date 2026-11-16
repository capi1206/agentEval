import os
import glob
from src.services.chat_client import ChatClient
from src.services.jev_service import JEVEvaluationService

if __name__ == "__main__":
    # 1. Locate the latest generated evaluation questions file dynamically
    eval_dir = "data/processed/evaluations"
    # eval_files = sorted(glob.glob(os.path.join(eval_dir, "eval_questions_*.json"))) #digested_page_14_1794253779
    
    # if not eval_files:
    #     raise FileNotFoundError(f"No evaluation questions files found in {eval_dir}. Run the DigestionController first!")
    


    # 2. Initialize the Playwright Chat Client
    client = ChatClient(
        page_url="https://www.easychatbot.app/test/a169f2422bcd5ba504de5d7d66e8fa65",
        iframe_selector="iframe",
        launcher_selector="button:has-text('💬')",
        input_selector="textarea, input[type='text'], [contenteditable='true']",
        bot_message_selector=".message, .chat-message",
        headless=False,
    )
    try:      
        # 3. Initialize the Evaluation Service pointing to the discovered file
        jev = JEVEvaluationService(
            chat_client=client,
            evaluation_data_path=eval_dir
        )

        # 4. Execute the pipeline
        jev.run_evaluation_pipeline(output_report_path="data/reports/final_evaluation_report.json")

    finally:
        # Clean up browser session
        if client._browser:
            client._browser.close()
        if client._playwright:
            client._playwright.stop()