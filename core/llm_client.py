import os
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_a, **_k):
        return False
import sys
import subprocess
import json
import time
import requests
from typing import Dict, Any, List, Union
from rich.console import Console

class LLMManager:
    """Manages multi-provider LLM calls (Gemini Primary -> Groq Fallback)."""
    def __init__(self, config: Dict[str, Any], console: Console = None):
        self.config = config
        self.console = console or Console()
        load_dotenv()
        self.api_key = os.environ.get("GEMINI_API_KEY") or self.config.get("api_key", "")
        self.api_base_url = os.environ.get("GEMINI_API_BASE_URL") or self.config.get("api_base_url", "https://generativelanguage.googleapis.com/v1beta/models/")
        self.api_timeout = self.config.get("api_timeout", 60)
        
        # Groq Setup
        self.groq_key = os.environ.get("GROQ_API_KEY") or self.config.get("groq_api_key", "")
        self.groq_model = self.config.get("groq_model", "moonshotai/kimi-k2-instruct-0905")
        self.groq_client = None
        self.fallback_enabled = False
        
        if self.groq_key and "YOUR_GROQ" not in self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
                self.fallback_enabled = True
            except ImportError:
                self.console.print("[dim yellow]⚠️ 'groq' library not found. Running independent command to install...[/]")
                subprocess.Popen([sys.executable, "-m", "pip", "install", "-q", "groq"]).wait()
                try:
                    from groq import Groq
                    self.groq_client = Groq(api_key=self.groq_key)
                    self.fallback_enabled = True
                    self.console.print("[dim green]✅ Groq library installed & loaded.[/]")
                except:
                    self.console.print("[dim red]❌ Failed to load Groq. Fallback disabled.[/]")

    def _call_gemini(self, payload: Dict, model_id: str, status_message: str) -> Union[str, None]:
        """Attempt to call Gemini API. Raises exception on 429."""
        try:
            with self.console.status(status_message, spinner="dots"):
                response = requests.post(
                    f"{self.api_base_url}{model_id}:generateContent",
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=self.api_timeout
                )
            
            if response.status_code == 429:
                raise ResourceWarning("Gemini Rate Limit Exceeded")
            
            response.raise_for_status()
            
            response_json = response.json()
            if response_json and "candidates" in response_json and response_json["candidates"]:
                candidate = response_json["candidates"][0]
                text = candidate.get("content", {}).get("parts", [{}])[0].get("text")
                return text
            return None

        except ResourceWarning:
            raise # Propagate up to fallback handler
        except Exception as e:
            self.console.print(f"[bold red]Gemini Error:[/][dim] {e}[/dim]")
            return None

    def _call_groq(self, contents: List[Dict]) -> Union[str, None]:
        """Fallback to Groq API (Kimi k2)."""
        if not self.groq_client: return None
        
        # Convert Gemini 'contents' [{"role": "user", "parts": [{"text": "..."}]}] 
        # to Groq messages [{"role": "user", "content": "..."}]
        messages = []
        for turn in contents:
            role = turn["role"]
            if role == "model": role = "assistant"
            
            # Combine all parts into one text
            text_parts = []
            for p in turn.get("parts", []):
                if "text" in p: text_parts.append(p["text"])
            
            content = "\n".join(text_parts)
            messages.append({"role": role, "content": content})

        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=messages,
                model=self.groq_model,
                temperature=0.7,
                max_tokens=4096
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            self.console.print(f"[bold red]Groq Fallback Error:[/][dim] {e}[/dim]")
            return None

    def generate_content(self, contents: List[Dict], model_id: str, use_grounding: bool = False, current_theme_colors: Dict = None) -> tuple:
        """Try Gemini, fallback to Groq if rate limited."""
        payload: Dict = {"contents": contents}
        if self.config.get('max_output_tokens'):
            payload["generationConfig"] = {"maxOutputTokens": self.config['max_output_tokens']}
            
        if use_grounding:
            payload["tools"] = [{"googleSearch": {}}]

        primary = self.config.get('primary_provider', 'gemini')
        color = current_theme_colors.get('secondary', 'cyan') if current_theme_colors else 'cyan'
        
        # ─── GROQ PRIMARY ───
        if primary == "groq" and self.fallback_enabled:
            status = f"[{color}]Thinking (Groq)...[/]"
            with self.console.status(status, spinner="dots"):
                try:
                    text_groq = self._call_groq(contents)
                    if text_groq: return text_groq, "groq"
                except Exception as e:
                    self.console.print(f"[bold red]Groq Error:[/][dim] {e}[/dim]")
            
            # Fallback to Gemini
            self.console.print("[bold yellow]⚠️ Groq Failed! Switching to Gemini...[/]")
            try:
                text_gemini = self._call_gemini(payload, model_id, f"[{color}]Thinking (Gemini Fallback)...[/]")
                if text_gemini: return text_gemini, "gemini"
            except Exception as e:
                self.console.print(f"[bold red]Gemini Fallback Error:[/][dim] {e}[/dim]")
                return None, None

        # ─── GEMINI PRIMARY ───
        else:
            status = f"[{color}]Searching the web...[/]" if use_grounding else f"[{color}]Thinking (Gemini)...[/]"
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    text_gemini = self._call_gemini(payload, model_id, status)
                    if text_gemini: return text_gemini, "gemini"
                    break
                except ResourceWarning:
                    # 429 DETECTED -> FALLBACK
                    if self.fallback_enabled:
                        self.console.print("[bold yellow]⚠️ Gemini Rate Limit Hit! Switching to Groq...[/]")
                        text_groq = self._call_groq(contents)
                        if text_groq: return text_groq, "groq"
                        break
                    else:
                        if attempt < max_retries - 1:
                            self.console.print(f"[dim red]Fallback disabled. Waiting 10s (Retry {attempt+1}/{max_retries})...[/]")
                            time.sleep(10)
                        else:
                            self.console.print("[bold red]❌ API Rate limit exceeded and no fallback available.[/]")
                except Exception as e:
                    self.console.print(f"[bold red]Gemini Error:[/][dim] {e}[/dim]")
                    break

        return None, None

    def analyze_intent(self, user_input: str, available_tools: List[str] = None) -> Union[Dict, None]:
        """
        Uses Groq (Kimi K2) to classify intent as 'chat' or 'task'.
        When classified as 'task', also suggests the best matching tool from available_tools.
        
        Returns:
            dict: {"intent": "task"|"chat", "suggested_tool": "tool_name"|null}
            None: if Groq is unavailable (caller should use fallback heuristics)
        """
        if not self.groq_client:
            return None
            
        tools_context = ""
        if available_tools:
            tools_context = (
                "\n\nAVAILABLE TOOLS (only use these exact names):\n"
                + "\n".join([f"- {t}" for t in available_tools])
                + "\n\nIf intent is 'task', also suggest the best tool from the list above."
            )
        
        system_prompt = (
            "You are an intent classifier for an autonomous agent called SARA. "
            "Respond with ONLY a valid JSON object, no other text.\n"
            "- If the user wants you to DO something (play music, open file, create folder, "
            "write code, send message, control volume, etc.), respond: "
            '{\"intent\": \"task\", \"suggested_tool\": \"tool_name_or_null\"}\n'
            "- If the user wants to TALK or ASK questions (hi, how are you, what is X, "
            "explain Y, etc.), respond: "
            '{\"intent\": \"chat\", \"suggested_tool\": null}\n'
            + tools_context
        )
        
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                model=self.groq_model,
                temperature=0.1,
                max_tokens=60
            )
            raw = chat_completion.choices[0].message.content.strip()
            
            # Parse JSON response
            import json as _json
            try:
                result = _json.loads(raw)
                if result.get("intent") in ["task", "chat"]:
                    return result
            except _json.JSONDecodeError:
                # Fallback: check if raw is just "task" or "chat"
                if raw.lower() in ["task", "chat"]:
                    return {"intent": raw.lower(), "suggested_tool": None}
            
            return None
        except Exception:
            return None

