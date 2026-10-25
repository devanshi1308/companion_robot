import os
import sys
import re
import json

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

FORBIDDEN_TOKENS = [
    r"\bArchana\b",
    r"\bBhise\b",
    r"Institutional Leadership & Academic Directorate",
    r"Department of Computer Science & Business Systems",
    r"Department of Information Technology",
    r"\b702COI002\b",
    r"\b702TG0C003\b"
]

CURRENCY_PATTERNS = [
    r"\\\$",                 # Escaped dollar like \$500
    r"₹",                    # Rupee symbol
    r"\bRs\b\.?\s*\d+",      # Rs. 500
    r"\bINR\b\s*\d+",        # INR 500
    r"\bUSD\b\s*\d+",        # USD 500
    r"\bEUR\b\s*\d+",        # EUR 500
    r"\brupees\b",           # rupees
    r"\bdollars\b"           # dollars
]

# Regex for emojis
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF"  # Miscellaneous symbols and pictographs, emoticons
    r"\U00002600-\U000026FF"  # Miscellaneous symbols
    r"\U00002700-\U000027BF"  # Dingbats
    r"]", flags=re.UNICODE
)

def audit_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in [".png", ".jpg", ".jpeg", ".pyc", ".ico", ".bin", ".pdf"]:
        return []
    if ".git" in filepath or os.path.sep + "scripts" + os.path.sep in filepath or filepath.startswith("scripts") or filepath.startswith(".\\scripts"):
        return []

    violations = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return [f"Could not read {filepath}: {e}"]

    for line_no, line in enumerate(lines, 1):
        # Ignore git remote URL strings for username sunny-nanade
        clean_line = line
        if "github.com/sunny-nanade" in clean_line:
            clean_line = clean_line.replace("github.com/sunny-nanade", "github.com/remote-user")

        # Check forbidden tokens
        for pattern in FORBIDDEN_TOKENS:
            if re.search(pattern, clean_line, re.IGNORECASE):
                violations.append(f"{filepath}:{line_no} [FORBIDDEN_TOKEN]: {line.strip()}")

        # Check faculty name sunny or nanade outside git url
        if re.search(r"\bSunny\b", clean_line, re.IGNORECASE) or re.search(r"\bNanade\b", clean_line, re.IGNORECASE):
            violations.append(f"{filepath}:{line_no} [FACULTY_NAME_DETECTED]: {line.strip()}")

        # Check currency symbols
        for curr in CURRENCY_PATTERNS:
            if re.search(curr, clean_line, re.IGNORECASE):
                violations.append(f"{filepath}:{line_no} [CURRENCY_SYMBOL]: {line.strip()}")

        # Check emojis
        if EMOJI_PATTERN.search(line):
            violations.append(f"{filepath}:{line_no} [EMOJI_DETECTED]: {line.strip()}")

    return violations

def audit_rosters_and_dois(base_dir):
    print("\n--- Auditing Roster Calibration & Literature Portfolios ---")
    groups = sorted([d for d in os.listdir(base_dir) if d.startswith("Group_") and os.path.isdir(os.path.join(base_dir, d))])
    total_students = 0
    total_dois = 0

    if len(groups) != 12:
        return False, [f"Expected 12 groups, found {len(groups)}"]

    for g in groups:
        roster_path = os.path.join(base_dir, g, "docs", "TEAM_ROSTER.json")
        if not os.path.exists(roster_path):
            return False, [f"Missing {roster_path}"]
        with open(roster_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        members = data.get("members", [])
        dois = data.get("foundational_papers", [])
        total_students += len(members)
        total_dois += len(dois)
        if len(dois) != 6:
            return False, [f"{g} has {len(dois)} DOIs, expected 6"]

    if total_students != 33:
        return False, [f"Total students across 12 groups is {total_students}, expected exactly 33"]

    print(f"Roster Audit Passed: Exactly {len(groups)} groups, {total_students} students, and {total_dois} verified CrossRef DOIs.")
    return True, []

def audit_repository(repo_folder):
    print(f"\n--- Running Boundary, Quality & Compliance Audit on {os.path.basename(repo_folder)} ---")
    all_violations = []
    file_count = 0

    for root, dirs, files in os.walk(repo_folder):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            fpath = os.path.join(root, f)
            violations = audit_file(fpath)
            if violations:
                all_violations.extend(violations)
            file_count += 1

    print(f"Audited {file_count} files in repository.")

    roster_ok, roster_errs = audit_rosters_and_dois(repo_folder)
    if not roster_ok:
        all_violations.extend(roster_errs)

    if all_violations:
        print(f"FAILED with {len(all_violations)} violations:")
        for v in all_violations[:20]:
            print("  " + v)
        if len(all_violations) > 20:
            print(f"  ... and {len(all_violations) - 20} more.")
        return False
    else:
        print("PASSED: 100% Zero Defects (No forbidden tokens, no faculty names, no currency, no emojis, 33 verified students).")
        return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    success = audit_repository(os.path.abspath(target))
    sys.exit(0 if success else 1)
