import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sync_showcases():
    print(f"--- Synchronizing LinkedIn Video Showcases in {os.path.basename(BASE_DIR)} ---")
    groups = sorted([d for d in os.listdir(BASE_DIR) if d.startswith("Group_") and os.path.isdir(os.path.join(BASE_DIR, d))])
    
    submitted_count = 0
    pending_count = 0
    group_status = {}

    for g in groups:
        group_folder = os.path.join(BASE_DIR, g)
        roster_path = os.path.join(group_folder, "docs", "TEAM_ROSTER.json")
        readme_path = os.path.join(group_folder, "README.md")
        
        if not os.path.exists(roster_path):
            continue
            
        with open(roster_path, "r", encoding="utf-8") as f:
            roster = json.load(f)
            
        showcase = roster.get("project_showcase", {})
        linkedin_url = showcase.get("linkedin_url", "PENDING_SUBMISSION")
        
        is_submitted = (linkedin_url and linkedin_url != "PENDING_SUBMISSION" and "linkedin.com" in linkedin_url)
        group_status[g] = linkedin_url if is_submitted else "PENDING_SUBMISSION"
        
        if is_submitted:
            submitted_count += 1
            print(f"[{g[:8]}] ACTIVE LINK: {linkedin_url}")
            # Update group README.md
            if os.path.exists(readme_path):
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Update image link and text link
                content = re.sub(
                    r"\[!\[Watch Video Demonstration on LinkedIn\]\([^\)]+\)\]\([^\)]+\)",
                    f"[![Watch Video Demonstration on LinkedIn](docs/figures/video_poster.png)]({linkedin_url})",
                    content
                )
                content = re.sub(
                    r"\* \*\*Video Demonstration:\*\* \[Watch 60-Second Walkthrough on LinkedIn\]\([^\)]+\)",
                    f"* **Video Demonstration:** [Watch 60-Second Walkthrough on LinkedIn]({linkedin_url})",
                    content
                )
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(content)
        else:
            pending_count += 1
            
    # Update COHORT_DASHBOARD.html
    dashboard_path = os.path.join(BASE_DIR, "COHORT_DASHBOARD.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r", encoding="utf-8") as f:
            dash_content = f.read()
            
        for g, url in group_status.items():
            pattern = re.compile(rf'(folder:\s*"{g}",[\s\S]*?linkedinUrl:\s*")[^"]*(")')
            if pattern.search(dash_content):
                dash_content = pattern.sub(rf'\g<1>{url}\g<2>', dash_content)
                
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dash_content)
            
    print(f"\nSync Complete: {submitted_count} submitted, {pending_count} pending.")

if __name__ == "__main__":
    sync_showcases()
