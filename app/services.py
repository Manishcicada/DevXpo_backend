import os
import re
import requests
from pathlib import Path
from pdfminer.high_level import extract_text as pdf_extract_text
from PIL import Image
import pytesseract
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from . import prompts  # <-- make sure you have your prompts.py with system/user prompts

# Load API key
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("Set OPENROUTER_API_KEY env var in .env file or environment")

BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mistral-small-3.2-24b-instruct:free"  
# Recommended alternatives: mixtral-8x7b, meta-llama-3-8b, google-gemma-7b, qwen2-7b


# -------------------------------
# Utility: Extract text from files
# -------------------------------
def extract_text_from_file(path: Path) -> str:
    suf = path.suffix.lower()
    try:
        if suf == ".pdf":
            return pdf_extract_text(str(path))
        elif suf in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            img = Image.open(path)
            return pytesseract.image_to_string(img)
        elif suf == ".txt":
            return path.read_text(encoding="utf-8")
        else:
            return ""
    except Exception:
        return ""


# -------------------------------
# Utility: Call OpenRouter API
# -------------------------------
def _call_chat(messages, max_tokens=800) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# -------------------------------
# Build context from frontend JSON
# -------------------------------
def build_context(payload: dict) -> str:
    case_info = payload.get("caseInfo", {})
    user_claim = payload.get("userClaim", {})
    evidence = payload.get("evidence", {})
    opposition = payload.get("opposition", {})
    settings = payload.get("simulationSettings", {})

    case_block = (
        f"CASE TITLE: {case_info.get('title','')}\n"
        f"TYPE: {case_info.get('caseType','')}\n"
        f"INCIDENT DATE: {case_info.get('incidentDate','')}\n"
        f"LOCATION: {case_info.get('location','')}\n\n"
        f"USER CLAIM:\nMain Claim: {user_claim.get('mainClaim','')}\n"
        f"Objective: {user_claim.get('objective','')}\n"
        f"Supporting Statement: {user_claim.get('supportingStatement','')}\n\n"
        f"OPPOSITION:\nAnticipated Arguments: {opposition.get('anticipatedArguments','')}\n"
        f"Probable Weaknesses: {opposition.get('probableWeaknesses','')}\n\n"
        f"SETTINGS:\nTrial Depth: {settings.get('trialDepth','')}\n"
        f"Tone: {settings.get('tone','')}\n"
        f"Verdict Output: {settings.get('verdictOutput','')}\n"
    )

    # Evidence handling
    ev_files = evidence.get("files", [])
    ev_texts = []
    for i, file in enumerate(ev_files, start=1):
        file_path = Path(file)
        extracted = extract_text_from_file(file_path) if file_path.exists() else ""
        excerpt = extracted[:1500]
        ev_texts.append(f"[E{i}] {file_path.name}\n{excerpt}")

    return case_block + "\n\nEVIDENCES:\n" + ("\n\n".join(ev_texts) if ev_texts else "No evidence provided.")


# -------------------------------
# Courtroom Simulation
# -------------------------------
def run_simulation(payload: dict, get_user_input=None) -> Tuple[List[Dict], Dict]:
    context = build_context(payload)
    transcript = []
    defense_out, opposition_out, judge_out = "", "", ""

    # Map trial depth → number of rounds
    depth_map = {"quick": 2, "standard": 4, "full": 6}
    max_rounds = depth_map.get(payload.get("simulationSettings", {}).get("trialDepth"), 4)

    for round_idx in range(max_rounds):
        # Defense
        if round_idx == 0:
            d_prompt = prompts.DEFENSE_PROMPT.format(context=context)
        else:
            d_prompt = prompts.DEFENSE_REBUTTAL_PROMPT.format(
                context=context,
                judge=judge_out,
                opposition=opposition_out
            )
        defense_out = _call_chat(
            [{"role": "system", "content": prompts.SYSTEM_DEFENSE},
             {"role": "user", "content": d_prompt}], max_tokens=500
        )
        transcript.append({"agent": "defense", "content": defense_out})

        # Check if defense requests testimony
        needs_testimony = any(
            kw in defense_out.lower() for kw in ["testimony", "statement", "please provide", "can the user", "user input"]
        )

        # Opposition
        o_prompt = prompts.OPPOSITION_PROMPT.format(context=context, defense=defense_out)
        opposition_out = _call_chat(
            [{"role": "system", "content": prompts.SYSTEM_OPPOSITION},
             {"role": "user", "content": o_prompt}], max_tokens=500
        )
        transcript.append({"agent": "opposition", "content": opposition_out})

        if any(kw in opposition_out.lower() for kw in ["testimony", "statement", "please provide", "can the user", "user input"]):
            needs_testimony = True

        # Ask user if needed
        if needs_testimony and get_user_input:
            user_testimony = get_user_input(f"Round {round_idx+1}: Provide testimony/evidence: ")
            if user_testimony:
                transcript.append({"agent": "user", "content": user_testimony})
                context += f"\n\nUSER INPUT (Round {round_idx+1}): {user_testimony}"

        # Judge
        j_prompt = prompts.JUDGE_ITER_PROMPT.format(
            context=context,
            defense=defense_out,
            opposition=opposition_out
        )
        judge_out = _call_chat(
            [{"role": "system", "content": prompts.SYSTEM_JUDGE},
             {"role": "user", "content": j_prompt}], max_tokens=400
        )
        transcript.append({"agent": "judge", "content": judge_out})

        if "satisfied" in judge_out.lower() or "final decision" in judge_out.lower():
            break

    # Final Decision
    j_final_prompt = prompts.JUDGE_FINAL_PROMPT.format(
        context=context,
        transcript="\n\n".join([f"{t['agent'].upper()}: {t['content']}" for t in transcript])
    )
    judge_final_out = _call_chat(
        [{"role": "system", "content": prompts.SYSTEM_JUDGE},
         {"role": "user", "content": j_final_prompt}], max_tokens=400
    )

    # Extract win probability
    win_prob = 50.0
    m = re.search(r"(\d{1,3})\s*%|\b(\d{1,3})\s*percent", judge_final_out, re.IGNORECASE)
    if m:
        num = m.group(1) or m.group(2)
        win_prob = min(max(float(num), 0.0), 100.0)

    return transcript, {
        "win_probability": win_prob,
        "justification": judge_final_out,
        "raw": judge_final_out
    }
