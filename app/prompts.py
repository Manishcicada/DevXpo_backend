SYSTEM_DEFENSE = "You are Defense Counsel. Only use case and evidence. Cite evidence as [E#]."
SYSTEM_OPPOSITION = "You are Opposing Counsel. Only use case and evidence. Cite evidence as [E#]."
SYSTEM_JUDGE = "You are a neutral Judge. Moderate, request clarifications, and issue decisions."

DEFENSE_PROMPT = """Context:
{context}

INSTRUCTIONS:
Give an opening defense argument (≤6 bullets, cite [E#]).
"""

DEFENSE_REBUTTAL_PROMPT = """Context:
{context}

Judge last said:
{judge}

Opposition said:
{opposition}

INSTRUCTIONS:
Provide a rebuttal addressing judge concerns and opposition. If no further arguments exist, say 'No further arguments'.
"""

OPPOSITION_PROMPT = """Context:
{context}

DEFENSE:
{defense}

INSTRUCTIONS:
Counter the defense with evidence [E#] and note weaknesses.
"""

JUDGE_ITER_PROMPT = """Context:
{context}

DEFENSE:
{defense}

OPPOSITION:
{opposition}

INSTRUCTIONS:
Say if you are 'Satisfied, ready for final decision' OR 'Not satisfied, need further arguments: ...'
"""

JUDGE_FINAL_PROMPT = """Context:
{context}

FULL TRANSCRIPT:
{transcript}

INSTRUCTIONS:
Final Decision:
1) Strongest points for each side
2) Numeric win probability for defense (0-100)
3) Short justification
Prefix with 'Final Decision:'.
"""
