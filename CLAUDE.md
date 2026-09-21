# Companion Robot (MDRIIA Group 02): project memory

Read this first, then `prompt.md` (full phased plan). Keep this file updated whenever a decision changes.
Last updated: 2026-09-21.

## Project
MuJoCo simulation of a wheeled companion robot (1.10 m camera mast, pan-tilt) that patrols a living room, detects an unwitnessed elderly fall from pose-landmark kinematics, approaches to a 0.80-1.20 m standoff, does a simulated voice check-in, then emits a simulated emergency-dispatch alert. Measured: sensitivity, specificity, precision, F1, fall-to-alert latency, over N >= 50 (target 100) seeded trials vs a static-sensor baseline, plus a dimensionless economics model.

Authorized title (never alter): "How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?"

Team: Kamakshi Bahuguna (E007, vision/kinematics, branch `feat/e007-vision-pose-kinematics`); Devanshi Sachin Kambli (B029, MuJoCo/navigation/economics, branch `feat/b029-mujoco-physics-navigation`). The user is Devanshi.

## Layout
- `Group_02_Kamakshi_Devanshi/`: teacher-provided package and the graded deliverable. Currently untracked.
- `scenes/living_room.xml`, `scripts/open_scene.py`: Devanshi's earlier scene work; planned to move into the group folder as `models/domestic_environment.xml`.
- `docs/problem_statement_and_literature.md`: earlier problem-statement/literature notes.
- `prompt.md`: master plan, phases 0-8. Merged/reviewed via PR #1 (branch `docs/project-plan-prompt`).
- `sceneenv/`: broken venv (gitignored). Use a fresh Python 3.12 `.venv` instead.

## Decisions made (and why)
1. **Scope is one scenario only:** fall -> detect -> approach -> check-in -> simulated alert. Medication reminders, remote video, companion app are future work only. Why: 3-4 week build, reviewer feedback.
2. **Scaffold results are synthetic and must not be submitted as data.** `src/fall_detection_kinematics.py` uses hardcoded features and `sin()` latencies; no MuJoCo or MediaPipe. Replace with real seeded simulation output. Why: rubric needs N >= 50 real runs; fabricated evidence is an integrity risk.
3. **Landmark strategy (proposed, needs faculty confirmation):** MuJoCo ground-truth joints + noise/dropout/occlusion as a 33-landmark surrogate (primary); MediaPipe validated on real fall video (supporting); MediaPipe on rendered frames only as a stretch. Why: BlazePose rarely detects blocky sim avatars.
4. **Latency is measured, not summed from constants.** Packet transit and EMS gateway stay as labelled model parameters.
5. **Fix survival-decay inconsistency:** lambda = 0.0031 /s is about 17% drop per minute, not 10%. Use about 0.00176 /s or reword; cite the AHA 7-10% per minute rather than a hard 6-minute claim.
6. **Economics must be parameterised and dimensionless**, inputs verified against Kubitza et al. 2022 (78.5 min, 18.4 days are unverified), tied to measured specificity.
7. **Structure:** move own work into the group folder; only that folder may be edited for the course. Git-ignore tool-generated files (`.cursor/`, `.gemini/`, `.qoder/`, `.codebuddy/`, `.kiro/`, `AGENTS.md`, `GEMINI.md`, `QODER.md`, `CODEBUDDY.md`, `.cursorrules`, `.windsurfrules`, `opencode.jsonc`) so they do not reach the course PR.
8. **Branch names follow the roster** (`feat/...`), not the guide's `feature/...`.

## Hard rules (teacher's audit script and rubric)
- Edit only inside `Group_02_Kamakshi_Devanshi/`; never root course files or other groups.
- Zero currency: no symbols, or words like rupees/dollars/INR/USD + number. Dimensionless ratios only.
- No emojis, faculty names or forbidden tokens in group-folder files.
- Citations need real, resolving DOIs (fabricated = zero for Milestone 4).
- Conventional commits; PRs only, no direct push to `main`; each person's work traceable to their own commits.
- Paper: 4 pages IEEEtran, 3 figures, 2 tables, 5 citations. Video: 60-90 s on LinkedIn, URL in `docs/TEAM_ROSTER.json`.
- Run `scripts/audit_course_boundaries_and_rules.py` before every PR.

## Working preferences
- Plan first, then implement; report only numbers produced by re-runnable scripts.
- Use code-review-graph before scanning files. Its index covers git-tracked files only, so rebuild (`code-review-graph build`) after committing the group folder.
- Environment: system Python is 3.13 without mujoco; make a 3.12 venv.

## Side effects already made in this environment
`code-review-graph install` wrote hooks/config to `~/.codex`, `~/.cursor`, `~/.config/opencode`, a git pre-commit hook in this repo, and many root config files. Remove them if unwanted.

## Open questions (waiting on the user)
Repo layout (move all into group folder?); simple capsule human vs MuJoCo stock humanoid; is surrogate landmarks acceptable to faculty; work split of shared items; current academic week and earlier deadlines; extra requirements the user will add.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**This project has a knowledge graph. Start with the code-review-graph
MCP tools to narrow scope, then read the source.** The graph is cheaper than scanning files and
gives you structural context (callers, dependents, test coverage) that file search cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes_tool` or `query_graph_tool` instead of Grep
- **Understanding impact**: `get_impact_radius_tool` instead of manually tracing imports
- **Code review**: `detect_changes_tool` + `get_review_context_tool` instead of reading entire files
- **Finding relationships**: `query_graph_tool` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview_tool` + `list_communities_tool`

### Verify in the source

- Narrow scope with the graph, then read the source. Do not change code from graph output alone.
- For any non-trivial change, read the implementation and the relevant tests before concluding.
- Verify the exact source when touching behavior, database logic, migrations, retries, fallbacks,
  recovery, or compatibility code.
- When the graph and the source disagree, the source wins. The graph may be stale or may not
  model that relationship.
- An empty graph result can mean "not indexed" or "not statically visible", not "does not exist".

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes_tool` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context_tool` | Need source snippets for review — token-efficient |
| `get_impact_radius_tool` | Understanding blast radius of a change |
| `get_affected_flows_tool` | Finding which execution paths are impacted |
| `query_graph_tool` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes_tool` | Finding functions/classes by name or keyword |
| `get_architecture_overview_tool` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes_tool` for code review.
3. Use `get_affected_flows_tool` to understand impact.
4. Use `query_graph_tool` pattern="tests_for" to check coverage.
<!-- /code-review-graph MCP tools -->
