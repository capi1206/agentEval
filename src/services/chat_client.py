import time
from playwright.sync_api import sync_playwright, Page, FrameLocator


class ChatClient:
    """
    Browser-based client using Playwright to interact with a chatbot
    embedded inside an HTML <iframe>.
    """

    def __init__(
        self,
        page_url: str,
        iframe_selector: str = "iframe",
        launcher_selector: str | None = None,
        input_selector: str = "textarea, input[type='text']",
        bot_message_selector: str = ".bot-message",
        popup_close_selector: str | None =None,
        headless: bool = False,
        response_timeout_ms: int = 20000,
    ):
        self.page_url = page_url
        self.iframe_selector = iframe_selector
        self.launcher_selector = launcher_selector
        self.input_selector = input_selector
        self.popup_close_selector = popup_close_selector
        self.bot_message_selector = bot_message_selector
        self.headless = headless
        self.response_timeout_ms = response_timeout_ms

        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = None
        self._frame: FrameLocator | None = None

        self._start_session()

    def _dismiss_popups(self, popup_close_selector: str | None = None):
        """Closes any modal, cookie banner, or promo popup blocking the page."""
        try:
            if popup_close_selector:
                close_btn = self._page.locator(popup_close_selector).first
                if close_btn.is_visible(timeout=3000):
                    close_btn.click()
                    return
            # Fallback: pressing Escape closes most standard HTML/JS modals
            self._page.keyboard.press("Escape")
        except Exception:
            pass  # No popup appeared, continue normally
    
    def _start_session(self):
        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)

        self._context = self._browser.new_context()
        self._page = self._context.new_page()
        self._page.goto(self.page_url, wait_until="domcontentloaded")

        # # 1. Dismiss the popup ("Cerrar")
        # try:
        #     close_btn = self._page.get_by_role("button", name="Cerrar")
        #     close_btn.wait_for(state="visible", timeout=5000)
        #     close_btn.click()
        #     print("Dismissed popup.")
        # except Exception:
        #     print("No popup appeared, continuing...")

        # 2. Click the chat launcher button to open the widget
        try:
            print("Opening chat widget via launcher...")
            launcher = self._page.get_by_role("button", name="💬")
            launcher.wait_for(state="visible", timeout=10000)
            launcher.click()
            time.sleep(1) # Brief pause for animation/iframe mounting
        except Exception as e:
            print(f"Warning: Could not click chat launcher: {e}")

        # 3. Now attach to the iframe and wait for the input box
        try:
            self._page.wait_for_selector(self.iframe_selector, state="visible", timeout=8000)
            self._frame = self._page.frame_locator(self.iframe_selector).first
            self._frame.locator(self.input_selector).first.wait_for(state="visible", timeout=5000)
            print("Chat successfully bound inside iframe.")
        except Exception:
            print("No iframe found or input not in iframe. Falling back to main page context...")
            self._frame = self._page  # Fallback to main page locator if not an iframe
            self._frame.locator(self.input_selector).first.wait_for(state="visible", timeout=10000)
            print("Chat successfully bound to main page DOM.")

    def send_message(self, question: str) -> str:
        """
        Types the question, submits it, and waits for a new response string 
        longer than 5 characters to appear.
        """
        try:
            # 1. Identify all current message elements/texts on the page to use as a baseline
            messages_locator = self._page.locator("div.chat-message, div.message, .lw-bot-response, p")
            
            existing_texts = set()
            for i in range(messages_locator.count()):
                try:
                    txt = messages_locator.nth(i).inner_text().strip()
                    if txt:
                        existing_texts.add(txt)
                except Exception:
                    pass

            # 2. Fill input and submit via Enter
            chat_input = self._page.locator(self.input_selector).first
            chat_input.wait_for(state="visible", timeout=10000)
            chat_input.fill(question)
            chat_input.press("Enter")

            print("Question sent. Waiting for new bot response...")

            deadline = time.time() + (self.response_timeout_ms / 1000.0)
            previous_text = ""
            stable_checks = 0

            # 3. Poll until a NEW message appears that isn't the user's question, 
            # isn't an old greeting/timestamp, and is longer than 5 characters.
            while time.time() < deadline:
                count = messages_locator.count()
                if count > 0:
                    for i in range(count - 1, max(-1, count - 4), -1):
                        try:
                            candidate = messages_locator.nth(i)
                            current_text = candidate.inner_text().strip()
                            
                            if (
                                current_text 
                                and current_text != question 
                                and not current_text.startswith("0:") 
                                and len(current_text) > 5
                                and current_text not in existing_texts
                            ):
                                if current_text == previous_text:
                                    stable_checks += 1
                                    if stable_checks >= 2:  # Reduced to 2 checks (~1s) for faster return
                                        print(f"Captured stable response: {current_text[:60]}...")
                                        return current_text
                                else:
                                    stable_checks = 0
                                    previous_text = current_text
                                break
                        except Exception:
                            pass

                time.sleep(0.5)

            return "CHATBOT_TIMEOUT_ERROR: Response timed out while streaming."

        except Exception as e:
            print(f"Error interacting with chatbot: {e}")
            return f"CHATBOT_INTERACTION_ERROR: {str(e)}"

    def reset_session(self):
        """
        Clears browser cookies/storage and reloads the page so each evaluation
        question starts with a clean conversation history.
        """
        if self._context:
            self._context.close()
        self._start_session()

    def close(self):
        """Cleanly shuts down the browser when the evaluation run finishes."""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()


if __name__ == "__main__":
    # Run with headless=False first so you can visually watch Playwright click & type
    client = ChatClient(
        page_url="https://www.easychatbot.app/test/a169f2422bcd5ba504de5d7d66e8fa65",
        iframe_selector="iframe",             # Replace with specific iframe selector if multiple exist
        launcher_selector=None,               # e.g., "#chat-launcher-btn" if closed by default
        input_selector="textarea",            # Replace with actual input selector inside iframe
        bot_message_selector=".chat-body p, .message-content, .chatbot-message", # Replace with actual bot bubble class/attribute
        popup_close_selector="button:has-text('Cerrar'), button[aria-label*='Cerrar' i]",
        headless=False,
    )
    try:
        reply = client.send_message("Hola, ¿qué servicios ofrecen?")
        print(f"Bot Reply:\n{reply}")
    finally:
        client.close()