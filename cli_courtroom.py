import sys
from pathlib import Path
from app import services, models

# Case metadata
TITLE = "BSNL vs M/S S D Constructions"
DESCRIPTION = "A dispute regarding the installation of telecom equipment on a building."
CASE_TYPE = "Civil"

# Hardcoded evidence paths
DEFENSE_FILE = Path("uploads/Chief_General_Manager_Bharat_Sanchar_vs_M_S_S_D_Constructions_on_15_November_2022.PDF")
OPPOSITION_FILE = Path("uploads/Chief_General_Manager_Bharat_Sanchar_vs_M_S_S_D_Constructions_on_15_November_2022.PDF")


def get_evidence_paths():
    files = []
    if DEFENSE_FILE.exists():
        files.append(str(DEFENSE_FILE))
    else:
        print(f"Evidence file {DEFENSE_FILE} does not exist.")

    if OPPOSITION_FILE.exists():
        files.append(str(OPPOSITION_FILE))
    else:
        print(f"Evidence file {OPPOSITION_FILE} does not exist.")
    return files


def get_user_input(prompt_text):
    return input(prompt_text)


def main():
    print("=== Courtroom Simulation CLI ===\n")

    # Ask rounds style (trial depth)
    trial_depth = input("Choose trial depth (quick/standard/full) [default: standard]: ").strip().lower()
    if trial_depth not in ["quick", "standard", "full"]:
        trial_depth = "standard"

    # Collect evidence
    evidence_files = get_evidence_paths()

    # Build payload for services.run_simulation
    payload = {
        "caseInfo": {
            "title": TITLE,
            "caseType": CASE_TYPE,
            "incidentDate": "Unknown",
            "location": "Unknown"
        },
        "userClaim": {
            "mainClaim": DESCRIPTION,
            "objective": "Win the case",
            "supportingStatement": "The defense has strong evidence supporting its position."
        },
        "evidence": {
            "files": evidence_files
        },
        "opposition": {
            "anticipatedArguments": "The opposition will argue contractual breaches.",
            "probableWeaknesses": "Insufficient proof of contract details."
        },
        "simulationSettings": {
            "trialDepth": trial_depth,
            "tone": "formal",
            "verdictOutput": "summary"
        }
    }

    print("\nStarting simulation...\n")

    transcript, result = services.run_simulation(
        payload,
        get_user_input=get_user_input
    )

    print("\n=== Simulation Transcript ===")
    for entry in transcript:
        print(f"[{entry['agent'].upper()}] {entry['content']}\n")

    print("=== Judge's Final Decision ===")
    print(result["justification"])
    print(f"Win Probability: {result['win_probability']}%\n")


if __name__ == "__main__":
    main()
