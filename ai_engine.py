import ollama
import time
import re
from prompts import build_section_prompt

# optional grammar checking library; install via pip if not already present
try:
    import language_tool_python
    _LANG_TOOL = language_tool_python.LanguageTool('en-US')
except ImportError:
    _LANG_TOOL = None
    # grammar checks will be skipped if library is unavailable

_CACHE = {}
_MAX_CACHE_SIZE = 100  # Limit cache memory usage

def _normalize(text: str) -> str:
    # Remove bullets
    text = re.sub(r"[-•*]+", "", text)
    # Remove repeated newlines
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def _is_high_quality(text: str) -> bool:
    """Quick heuristic to decide if generated text meets quality expectations.

    - Word count within reasonable academic paragraph limits
    - No obvious bullet-like language or connective phrases that signal poor structure
    """
    wc = len(text.split())
    # Relaxed word count bounds to match prompt guidelines (50-150 words)
    if wc < 50 or wc > 150:
        return False
    # reject text that still looks like it contains lists or instructions
    if any(bad in text.lower() for bad in ["bullet", "point:", "following are", "in this project", "in this study"]):
        return False

    # flag placeholders or weak, generic wording
    if any(bad in text.lower() for bad in ["lorem", "etc.", "and so on", "moreover", "as an example"]):
        return False

    # Basic contract: must be concise and professional
    if not text.endswith('.'):
        return False

    return True


def generate_section(
    project_title,
    heading,
    model="phi3:mini",
    temperature=0.25,
    max_retries=3,
    previous_summary=None
):
    cache_key = f"{project_title}_{heading}_{model}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    # Limit cache size to prevent memory bloat
    if len(_CACHE) > _MAX_CACHE_SIZE:
        _CACHE.clear()

    prompt = build_section_prompt(
        project_title,
        heading,
        previous_context=previous_summary
    )

    last_text = None
    for attempt in range(1, max_retries + 1):
        try:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_predict": 140}
            )

            text = _normalize(response.get("message", {}).get("content", ""))
            if not text:
                print(f"[ai_engine] attempt {attempt}: received empty response from model {model}.")
                continue

            last_text = text

            if _is_high_quality(text):
                _CACHE[cache_key] = text
                return text

            # Log quality issue and retry only once for a faster overall experience
            print(f"[ai_engine] attempt {attempt}: low-quality text for {heading} (wc={len(text.split())}).")
            if attempt < max_retries:
                continue

        except Exception as exc:
            print(f"[ai_engine] attempt {attempt}: ollama.chat failed: {exc}")
            # keep previous successful content to fallback to it while avoiding further retries
            if last_text:
                break
            continue

    # final fallback: return last generation (if any) or clear error text
    if last_text:
        print(f"[ai_engine] final fallback used for {heading}. Returning last model output.")
        _CACHE[cache_key] = last_text
        return last_text

    fallback = (
        f"[Failed to generate content for section: {heading}. "
        "Please retry, verify Ollama is running, and ensure the model is available.]"
    )
    print(f"[ai_engine] fallback: {fallback}")
    _CACHE[cache_key] = fallback
    return fallback