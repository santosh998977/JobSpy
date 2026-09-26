# Strict JD Keyword Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require user confirmation and guarantee that every detected JD keyword appears exactly in each completed Resume Lab generation.

**Architecture:** Extend the existing keyword planner with a confirmed-all mode, then reuse the existing writer/reviewer/repair flow. A deterministic final skills-line repair guarantees exact coverage; the existing score becomes a 100% acceptance gate. The frontend adds one native checkbox and passes the confirmation to the API.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, pytest, Next.js/TypeScript, native HTML checkbox, Docker Compose.

## Global Constraints

- Preserve employer, date, metric, project, certification, and education truth checks.
- Add no dependency or database migration.
- Do not return `REVIEWED` below 100% required-keyword coverage.
- Do not modify OmniRoute or TradingAgents services.

---

### Task 1: Strict backend keyword coverage

**Files:**
- Modify: `ai/resume_keyword_plan.py`
- Modify: `ai/resume_orchestrator.py`
- Modify: `api/schemas.py`
- Modify: `api/main.py`
- Test: `tests/test_resume_keyword_plan.py`
- Test: `tests/test_resume_orchestrator.py`
- Test: `tests/test_resume_lab_api.py`

**Interfaces:**
- Consumes: `build_keyword_plan(source_resume: str, job_description: str, *, target_title: str | None = None, require_all: bool = False)`
- Produces: `ensure_keyword_coverage(resume_text: str, required: list[str]) -> str`
- Produces: required request field `confirm_all_jd_keywords: Literal[True]`

- [ ] **Step 1: Write failing planner and repair tests**

```python
def test_confirmed_keyword_plan_requires_every_detected_jd_term():
    plan = build_keyword_plan("Java engineer", "Java Python Airflow", require_all=True)
    assert plan.supported == ["Java", "Python", "Airflow"]
    assert plan.unsupported == []

def test_keyword_coverage_repair_adds_every_missing_term_once():
    repaired = ensure_keyword_coverage(
        "SUMMARY\nJava engineer\n\nTECHNICAL SKILLS\nLanguages: Java\n\nPROFESSIONAL EXPERIENCE",
        ["Java", "Python", "Airflow"],
    )
    assert "Verified JD Keywords: Python, Airflow" in repaired
    assert repaired.lower().count("python") == 1
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest -q tests/test_resume_keyword_plan.py tests/test_resume_orchestrator.py`

Expected: FAIL because `require_all` and `ensure_keyword_coverage` do not exist.

- [ ] **Step 3: Add confirmed planning and deterministic coverage repair**

```python
terms = [term for _, term in found]
if require_all:
    return KeywordPlan(
        supported=terms,
        unsupported=[],
        placements={term: "skills" for term in terms},
    )

def ensure_keyword_coverage(resume_text: str, required: list[str]) -> str:
    missing = [term for term in required if term.lower() not in resume_text.lower()]
    if not missing:
        return resume_text
    line = "Verified JD Keywords: " + ", ".join(missing)
    marker = "\nPROFESSIONAL EXPERIENCE"
    return resume_text.replace(marker, f"\n{line}\n{marker}", 1)
```

- [ ] **Step 4: Write failing request and final-gate tests**

```python
def test_generate_request_requires_keyword_confirmation():
    with pytest.raises(ValidationError):
        ResumeLabGenerateRequest(
            profile_id=1,
            source_version=1,
            mode="HYBRID",
            job_description="Java and Python full-stack engineering position." * 2,
            idempotency_key="1234567890abcdef",
            confirm_all_jd_keywords=False,
        )

def test_confirmed_generation_returns_exact_100_percent_coverage():
    strict_request = replace(request(), confirm_all_jd_keywords=True)
    result = orchestrate_resume(strict_request, settings(), completion=FakeCompletion())
    assert result.status == "REVIEWED"
    assert result.ats_score == 100
    assert all(term.lower() in result.resume_text.lower() for term in ("Python", "LangChain", "Kubernetes"))
```

- [ ] **Step 5: Run tests and verify RED**

Run: `pytest -q tests/test_resume_orchestrator.py tests/test_resume_lab_api.py`

Expected: FAIL because confirmation is not represented or enforced.

- [ ] **Step 6: Pass confirmation through API and enforce final coverage**

```python
class ResumeLabGenerateRequest(BaseModel):
    confirm_all_jd_keywords: Literal[True]

@dataclass(frozen=True)
class OrchestrationRequest:
    confirm_all_jd_keywords: bool = False

# In generate_resume_lab_resume:
confirm_all_jd_keywords=payload.confirm_all_jd_keywords

# In orchestrate_resume after model repair passes:
if request.confirm_all_jd_keywords:
    best_text = ensure_keyword_coverage(best_text, plan.supported)
    best_score = _supported_coverage(best_text, plan.supported)
```

- [ ] **Step 7: Run backend regression tests**

Run: `pytest -q tests/test_resume_keyword_plan.py tests/test_resume_orchestrator.py tests/test_resume_lab_api.py tests/test_resume_rebuilder.py`

Expected: all tests PASS.

- [ ] **Step 8: Commit backend behavior**

```bash
git add ai/resume_keyword_plan.py ai/resume_orchestrator.py api/schemas.py api/main.py tests
git commit -m "feat: require complete JD keyword coverage"
```

### Task 2: Resume Lab confirmation control

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/resume-lab/page.tsx`

**Interfaces:**
- Consumes: `confirm_all_jd_keywords: true`
- Produces: a required native checkbox that gates `Generate Resume`

- [ ] **Step 1: Add request typing**

```typescript
confirm_all_jd_keywords: true;
```

- [ ] **Step 2: Add confirmation state and reset it when the JD changes**

```typescript
const [confirmAllKeywords, setConfirmAllKeywords] = useState(false);
```

- [ ] **Step 3: Add the native accessible checkbox**

```tsx
<label className="flex items-start gap-2 text-sm">
  <input
    type="checkbox"
    checked={confirmAllKeywords}
    onChange={(event) => setConfirmAllKeywords(event.target.checked)}
  />
  <span>I confirm every detected JD keyword reflects my real knowledge or experience.</span>
</label>
```

- [ ] **Step 4: Gate and send generation**

```typescript
if (!confirmAllKeywords) {
  toast.error("Confirm the JD keywords before generating");
  return;
}

confirm_all_jd_keywords: true,
```

- [ ] **Step 5: Run frontend checks**

Run: `npm run lint && npm run build`

Expected: both commands PASS.

- [ ] **Step 6: Commit frontend control**

```bash
git add frontend/lib/api.ts frontend/app/resume-lab/page.tsx
git commit -m "feat: confirm all resume JD keywords"
```

### Task 3: Push, deploy, and verify

**Files:** none.

**Interfaces:** Deploys `main` to `/home/ubuntu/JobSpy` and validates Resume Lab only.

- [ ] **Step 1: Push main**

Run: `git push origin main`

Expected: remote `main` advances to both feature commits.

- [ ] **Step 2: Fast-forward and rebuild Resume Lab services**

Run: `git pull --ff-only origin main && docker compose build api frontend && docker compose up -d api frontend scheduler nginx`

Expected: all four containers report `running` with zero restarts.

- [ ] **Step 3: Live API generation test**

POST `/api/resume-lab/generate?force_refresh=true` with `confirm_all_jd_keywords: true` and the supplied JD.

Expected: `status=REVIEWED`, `ats_score=100`, and every detected term appears in `resume_text`.

- [ ] **Step 4: Export and inspect DOCX**

POST `/api/resume/export-docx` with the reviewed text.

Expected: one technical-skills heading; every experience title uses `Resume Job Title`, bold, 12 pt; no `Target Role`; all required JD terms appear in extracted text.

- [ ] **Step 5: Verify repository and service state**

Run: `git status --short --branch`, `/api/health`, and `docker compose ps`.

Expected: local and VM `main` clean and aligned; health is `ok`; all services running.
