# Resume Layout and Content Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate truthful, humanized resumes with one dynamic Technical Skills table, prominent job titles, and a project description plus final Environment line for every role.

**Architecture:** Keep the existing plain-text resume contract. Improve the DOCX renderer at its shared parsing boundary, and tighten the existing writer/reviewer prompts rather than adding another post-processing layer.

**Tech Stack:** Python 3, python-docx, pytest, existing Resume Lab orchestration.

## Global Constraints

- The source resume is the sole source of candidate facts.
- Add JD keywords only when the source resume contains the exact term or an unambiguous equivalent.
- Do not add dependencies or introduce a new resume format.
- Preserve every employer, date, education entry, project line, and Environment line.
- Job titles use 12-point bold dark-blue text.

---

### Task 1: Render skills and role headings correctly

**Files:**
- Modify: `ai/resume_docx.py`
- Test: `tests/test_resume_rebuilder.py`

**Interfaces:**
- Consumes: the existing plain-text resume passed to `build_resume_docx(resume_text, candidate_name=None)`.
- Produces: `_extract_technical_skill_rows(resume_text) -> list[tuple[str, str]]` and `_add_technical_skills_table(doc, rows)`.

- [ ] **Step 1: Write failing DOCX tests**

Add tests that build a Java resume and assert:

```python
document = Document(io.BytesIO(build_resume_docx(java_resume)))
skill_tables = [t for t in document.tables if t.cell(0, 0).text == "Programming Languages"]
assert len(skill_tables) == 1
assert "Java" in skill_tables[0].cell(0, 1).text
assert ".NET 6/7/8" not in " ".join(c.text for t in document.tables for row in t.rows for c in row.cells)
assert sum(p.text == "TECHNICAL SKILLS" for p in document.paragraphs) == 1
assert not any(p.text.startswith("Programming Languages:") for p in document.paragraphs)
```

Add a two-line role-layout test and assert the role paragraph has style `Resume Job Title`, its first run is bold, and its effective size is 12 points.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `pytest tests/test_resume_rebuilder.py -k "technical_skills or split_role" -v`

Expected: FAIL because the renderer uses the hard-coded .NET table and does not recognize `Company, City, ST | Dates`.

- [ ] **Step 3: Implement dynamic skills extraction**

Remove `_TECHNICAL_SKILL_ROWS`. Add a small parser that reads lines between `TECHNICAL SKILLS` and the next section, splits `Category: values`, and returns only non-empty rows:

```python
def _extract_technical_skill_rows(resume_text: str) -> list[tuple[str, str]]:
    rows = []
    in_skills = False
    for raw in resume_only_text(resume_text).splitlines():
        line = raw.strip()
        heading = _normalized_heading(line)
        if heading == "technical skills":
            in_skills = True
            continue
        if in_skills and _is_section_heading(line):
            break
        if in_skills and ":" in line:
            label, value = (part.strip() for part in line.split(":", 1))
            if label and value:
                rows.append((label, value))
    return rows
```

Pass these rows to `_add_technical_skills_table`. Keep `_prepare_resume_lines` responsible for removing the original skills body so it cannot be rendered a second time.

- [ ] **Step 4: Support the two-line role layout and title styling**

Extend `_split_company_location_date` to accept `Company, City, ST | Dates`, separating the final two comma-delimited location parts from the company. Change `Resume Job Title` to 12 points and render the title run with `size=12`, `bold=True`, and `_NAVY`.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/test_resume_rebuilder.py -k "technical_skills or split_role" -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ai/resume_docx.py tests/test_resume_rebuilder.py
git commit -m "fix: render tailored resume sections once"
```

---

### Task 2: Require complete, humanized experience blocks

**Files:**
- Modify: `ai/resume_orchestrator.py`
- Modify: `ai/resume_rebuilder.py`
- Test: `tests/test_resume_orchestrator.py`
- Test: `tests/test_resume_rebuilder.py`

**Interfaces:**
- Consumes: existing `OrchestrationRequest` and `build_resume_prompt` inputs.
- Produces: unchanged plain-text resume format with `Project:` before bullets and `Environment:` after the final bullet of every role.

- [ ] **Step 1: Write failing prompt-contract tests**

Assert writer, reviewer, refinement, and legacy rebuild prompts contain all of these rules:

```python
assert "Project:" in prompt
assert "Environment:" in prompt
assert "final line of every role" in prompt
assert "supported JD keywords" in prompt
assert "unsupported" in prompt
assert "vary" in prompt.lower()
```

Update the page-target test to assert the prompt never permits Environment lines to be dropped.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_resume_orchestrator.py tests/test_resume_rebuilder.py -k "prompt or page_target or experience" -v`

Expected: FAIL because page-length guidance currently allows Environment lines to be dropped and the orchestrator does not require complete role blocks.

- [ ] **Step 3: Tighten the shared prompt instructions**

In `_length_instruction`, replace the Environment-removal permission with:

```python
"Keep one concise Project line and an Environment line as the final line of every role. "
"Meet the page target by tightening or merging bullets, never by removing those structural lines."
```

In writer, reviewer, refinement, and rebuild instructions require:

```text
For every role, include one concise Project: description grounded in the source resume,
varied achievement bullets that naturally cover supported JD keywords, and one Environment:
line after the final bullet. Add or expand bullets only when the source resume supports the claim.
Never add unsupported JD keywords as candidate experience.
```

Retain the existing anti-AI wording rules; do not add a second humanization engine.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_resume_orchestrator.py tests/test_resume_rebuilder.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai/resume_orchestrator.py ai/resume_rebuilder.py tests/test_resume_orchestrator.py tests/test_resume_rebuilder.py
git commit -m "feat: require complete tailored experience blocks"
```

---

### Task 3: Verify, publish, and deploy

**Files:**
- No product-code files added.
- Generate a disposable sample under the test temporary directory only.

**Interfaces:**
- Consumes: commits from Tasks 1 and 2.
- Produces: tested `main`, pushed remote, and updated VM service.

- [ ] **Step 1: Run the complete automated suite**

Run: `pytest -q`

Expected: all tests pass; only previously documented skips remain.

- [ ] **Step 2: Generate and inspect one representative DOCX**

Generate a Java sample through `build_resume_docx`, reopen it with `Document`, and assert one skills heading/table, 12-point bold job-title runs, one Project line per role, and an Environment line after each role's final bullet.

- [ ] **Step 3: Check repository and secret safety**

Run: `git status --short` and `git grep -I "sk-" $(git rev-list --all)`.

Expected: only intentional plan/document changes are present and no API key is found.

- [ ] **Step 4: Push and deploy**

Push `main`, update the VM checkout with a fast-forward pull, rebuild only the affected Resume Lab/API service, and leave the TradingAgents and OmniRoute services untouched.

- [ ] **Step 5: Smoke-test Resume Lab**

Confirm the health endpoint and Resume Lab page return HTTP 200. Generate one resume from the attached profile and verify the downloaded DOCX structure.

- [ ] **Step 6: Record completion**

Report the pushed commit hashes, tests run, service status, and any provider/API errors encountered during the live generation smoke test.
