# Verified Experience Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ask for truthful supporting bullets when important JD keywords are absent, save those notes permanently with the selected profile, and use them as source facts during generation.

**Architecture:** Add one nullable profile column and reuse the existing optimistic-concurrency profile-save endpoint. A small gap-analysis endpoint uses the backend's existing keyword planner, while the frontend opens a focused checkpoint dialog before calling generation. Generation combines the imported resume and verified notes into one validation baseline without emitting a notes section.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, SQLite, pytest, Next.js 15, React 19, TypeScript, Radix Dialog.

## Global Constraints

- Changes and deployment occur only in `/home/ubuntu/JobSpy` on the VM.
- Notes are plain text with a maximum length of 6,000 characters.
- Saving non-empty notes requires an explicit truthfulness confirmation in the UI.
- Missing notes never block generation; **Continue Without Adding** remains available.
- The model must not invent experience or output a separate verified-notes section.
- Existing profiles migrate to an empty notes value without user action.
- Use test-first development and commit each independently testable task.

---

### Task 1: Persist verified notes on Resume Lab profiles

**Files:**
- Create: `job-intelligence/alembic/versions/0004_verified_experience_notes.py`
- Modify: `job-intelligence/storage/models.py:315-330`
- Modify: `job-intelligence/storage/repository.py:84-115`
- Modify: `job-intelligence/api/schemas.py:134-160`
- Modify: `job-intelligence/api/main.py:690-714`
- Test: `job-intelligence/tests/test_resume_lab_profiles.py`

**Interfaces:**
- Produces: `ResumeLabProfile.verified_experience_notes: str | None`.
- Produces: optional `verified_experience_notes` on `ResumeLabResumeUpdate` and required string on `ResumeLabProfileOut`.
- Produces: `JobRepository.save_resume_lab_resume(..., verified_experience_notes: str | None = None)`; `None` preserves the saved value.

- [ ] **Step 1: Write failing persistence and API tests**

Add tests that save notes, verify `source_version` increments, verify the response returns the notes, and verify omitting the field preserves them:

```python
def test_verified_experience_notes_persist_without_being_cleared_when_omitted():
    session = make_session()
    repository = JobRepository(session)
    profile = repository.list_resume_lab_profiles()[1]
    saved = repository.save_resume_lab_resume(
        profile.id,
        resume_text="Java engineer with Spring Boot and APIs. " * 3,
        resume_filename="java.txt",
        expected_source_version=0,
        only_if_empty=False,
        verified_experience_notes="- Built Kafka consumers for order processing.",
    )
    assert saved.verified_experience_notes == "- Built Kafka consumers for order processing."
    assert saved.source_version == 1

    saved_again = repository.save_resume_lab_resume(
        profile.id,
        resume_text=saved.resume_text,
        resume_filename=saved.resume_filename,
        expected_source_version=1,
        only_if_empty=False,
    )
    assert saved_again.verified_experience_notes == saved.verified_experience_notes
    assert saved_again.source_version == 2
```

Extend `test_profile_api_saves_and_removes_only_resume` with a request containing notes and assertions for the returned value. Add a 6,001-character request assertion expecting HTTP 422.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
cd /home/ubuntu/JobSpy/job-intelligence
docker run --rm -v "$PWD:/app" -w /app job-intelligence-api sh -lc \
  "pip install -q pytest && pytest -q tests/test_resume_lab_profiles.py"
```

Expected: failures because the model, schema, and repository do not accept `verified_experience_notes`.

- [ ] **Step 3: Add the migration, model, schema, and repository behavior**

Create revision `0004_verified_experience_notes` with `down_revision = "0003_resume_lab_profiles_and_runs"`:

```python
def upgrade() -> None:
    op.add_column(
        "resume_lab_profiles",
        sa.Column("verified_experience_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_lab_profiles", "verified_experience_notes")
```

Add the mapped column and schema fields:

```python
verified_experience_notes: Mapped[str | None] = mapped_column(Text)
```

```python
class ResumeLabResumeUpdate(BaseModel):
    resume_text: str = Field(min_length=50)
    resume_filename: str | None = Field(default=None, max_length=255)
    expected_source_version: int = Field(ge=0)
    only_if_empty: bool = False
    verified_experience_notes: str | None = Field(default=None, max_length=6000)
```

In the repository, normalize and assign notes only when the argument is not `None`; pass the payload field from the existing API endpoint.

- [ ] **Step 4: Run the profile tests and verify GREEN**

Run the Step 2 command. Expected: all profile tests pass.

- [ ] **Step 5: Commit**

```bash
git add job-intelligence/alembic/versions/0004_verified_experience_notes.py \
  job-intelligence/storage/models.py job-intelligence/storage/repository.py \
  job-intelligence/api/schemas.py job-intelligence/api/main.py \
  job-intelligence/tests/test_resume_lab_profiles.py
git commit -m "feat(resume-lab): persist verified experience notes"
```

### Task 2: Use verified notes as generation truth and invalidate stale cache

**Files:**
- Modify: `job-intelligence/api/main.py:738-824,867-920`
- Modify: `job-intelligence/ai/resume_orchestrator.py:175-220`
- Test: `job-intelligence/tests/test_resume_lab_api.py`
- Test: `job-intelligence/tests/test_resume_orchestrator.py`

**Interfaces:**
- Produces: `_resume_lab_source(profile: ResumeLabProfile) -> tuple[str, str]`, returning combined source facts and their hash.
- Consumes: `verified_experience_notes` created in Task 1.

- [ ] **Step 1: Write failing generation and prompt tests**

Add a generation test that saves notes, captures `OrchestrationRequest`, and proves both the note and a notes-derived source hash are used:

```python
def test_generation_uses_verified_notes_and_changes_source_hash(monkeypatch):
    # Build the standard in-memory session and save a Java resume plus Kafka notes.
    # Stub orchestrate_resume and POST /resume-lab/generate.
    assert "USER-VERIFIED EXPERIENCE NOTES" in calls[0].source_resume
    assert "Built Kafka consumers" in calls[0].source_resume
    run = repository.get_resume_lab_run(response.json()["run_id"])
    assert run.source_hash != profile.resume_sha256
```

Add an orchestrator-message test:

```python
def test_writer_integrates_notes_without_outputting_notes_section():
    messages = _messages(request_with_verified_notes)
    prompt = messages[-1]["content"]
    assert "user-verified" in prompt.lower()
    assert "do not output a separate" in prompt.lower()
```

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
pytest -q tests/test_resume_lab_api.py tests/test_resume_orchestrator.py
```

Expected: the captured source omits notes and cache/source hashes remain resume-only.

- [ ] **Step 3: Implement the combined truth baseline**

Add this helper near `_resume_lab_run_response`:

```python
def _resume_lab_source(profile: ResumeLabProfile) -> tuple[str, str]:
    resume = (profile.resume_text or "").strip()
    notes = (profile.verified_experience_notes or "").strip()
    if not notes:
        return resume, profile.resume_sha256 or normalized_hash(resume)
    source = (
        f"{resume}\n\nUSER-VERIFIED EXPERIENCE NOTES (source facts only):\n{notes}"
    )
    return source, normalized_hash(profile.resume_sha256 or "", notes)
```

Use `source_text, source_hash = _resume_lab_source(profile)` in generate and refine. Pass `source_text` to `OrchestrationRequest`/`RefineRequest`, use `source_hash` in `input_hash`, `ResumeLabRun.source_hash`, and any cache-key inputs.

Add this instruction to writer and refinement prompts:

```python
"Integrate relevant user-verified notes into appropriate resume sections. "
"Do not output a separate verified-notes or supplemental-notes section. "
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command. Expected: all focused API and orchestrator tests pass.

- [ ] **Step 5: Commit**

```bash
git add job-intelligence/api/main.py job-intelligence/ai/resume_orchestrator.py \
  job-intelligence/tests/test_resume_lab_api.py job-intelligence/tests/test_resume_orchestrator.py
git commit -m "feat(resume-lab): use verified notes as source facts"
```

### Task 3: Add server-side missing-keyword analysis

**Files:**
- Modify: `job-intelligence/api/schemas.py`
- Modify: `job-intelligence/api/main.py`
- Test: `job-intelligence/tests/test_resume_lab_api.py`

**Interfaces:**
- Produces: `POST /resume-lab/gaps` accepting `profile_id`, `source_version`, `job_description`, and optional `target_title`.
- Produces: `{ "missing_keywords": list[str] }`, capped at ten terms.
- Consumes: `_resume_lab_source` from Task 2 and `build_keyword_plan` from `ai.resume_keyword_plan`.

- [ ] **Step 1: Write failing endpoint tests**

```python
def test_gap_endpoint_excludes_keywords_supported_by_verified_notes():
    response = client.post("/resume-lab/gaps", json={
        "profile_id": profile.id,
        "source_version": profile.source_version,
        "job_description": "Java role requiring Spring Boot, Kafka, Kubernetes, and Oracle.",
        "target_title": "Senior Java Developer",
    })
    assert response.status_code == 200
    assert "Kafka" not in response.json()["missing_keywords"]
    assert len(response.json()["missing_keywords"]) <= 10
```

Also assert stale profile versions return HTTP 409.

- [ ] **Step 2: Run the endpoint tests and verify RED**

```bash
pytest -q tests/test_resume_lab_api.py -k gap
```

Expected: HTTP 404 because `/resume-lab/gaps` does not exist.

- [ ] **Step 3: Add schemas and endpoint**

```python
class ResumeLabGapRequest(BaseModel):
    profile_id: int
    source_version: int = Field(ge=0)
    job_description: str = Field(min_length=50)
    target_title: str | None = Field(default=None, max_length=500)


class ResumeLabGapResponse(BaseModel):
    missing_keywords: list[str]
```

The endpoint loads the profile, checks `source_version`, calls `_resume_lab_source`, then returns `build_keyword_plan(source, job_description, target_title=title).unsupported[:10]`.

- [ ] **Step 4: Run the gap and full backend core tests**

```bash
pytest -q tests/test_resume_lab_api.py -k gap
pytest -q --ignore=tests/career_alerts --ignore=tests/live
```

Expected: gap tests pass and the core suite has zero failures.

- [ ] **Step 5: Commit**

```bash
git add job-intelligence/api/schemas.py job-intelligence/api/main.py \
  job-intelligence/tests/test_resume_lab_api.py
git commit -m "feat(resume-lab): report missing JD keywords"
```

### Task 4: Add the pre-generation checkpoint UI

**Files:**
- Create: `job-intelligence/frontend/components/resume-lab/experience-checkpoint.tsx`
- Modify: `job-intelligence/frontend/types/job.ts:205-214`
- Modify: `job-intelligence/frontend/lib/api.ts:161-200`
- Modify: `job-intelligence/frontend/app/resume-lab/page.tsx:500-850,1100-1200`

**Interfaces:**
- Consumes: `POST /resume-lab/gaps` from Task 3.
- Consumes: optional `verified_experience_notes` in `saveResumeLabResume` from Task 1.
- Produces: `ExperienceCheckpoint` props `open`, `keywords`, `notes`, `saving`, `onNotesChange`, `onSaveAndGenerate`, `onContinue`, `onCancel`.

- [ ] **Step 1: Add TypeScript types and API functions, then verify the build fails at the missing component import**

```typescript
export type ResumeLabProfile = {
  id: number;
  name: string;
  resume_text: string | null;
  resume_filename: string | null;
  resume_sha256: string | null;
  verified_experience_notes: string;
  source_version: number;
  updated_at: string;
};

export function getResumeLabGaps(payload: {
  profile_id: number;
  source_version: number;
  job_description: string;
  target_title?: string | null;
}) {
  return request<{ missing_keywords: string[] }>("/resume-lab/gaps", {
    method: "POST", body: JSON.stringify(payload),
  });
}
```

Run `npm run typecheck`. Expected: failure until the checkpoint component and page handlers exist.

- [ ] **Step 2: Build the focused checkpoint component**

Use the existing Radix `Dialog`, `Textarea`, and `Button`; use a native checkbox. Render keyword chips, the 6,000-character textarea, truthfulness confirmation, and the three approved actions. Disable **Save & Generate** when notes are blank, over length, unconfirmed, or saving.

- [ ] **Step 3: Gate generation and preserve the returned profile version**

Split the current handler into:

```typescript
async function startGeneration(profile: ResumeLabProfile) {
  // Existing generation body, using profile.id and profile.source_version.
}

async function rebuildTailoredResume() {
  // Existing input checks.
  const gap = await getResumeLabGaps({
    profile_id: activeProfile.id,
    source_version: activeProfile.source_version,
    job_description: jobDescription,
    target_title: jobTitle || null,
  });
  if (gap.missing_keywords.length) {
    setMissingKeywords(gap.missing_keywords);
    setExperienceNotes(activeProfile.verified_experience_notes);
    setCheckpointOpen(true);
    return;
  }
  await startGeneration(activeProfile);
}
```

For **Save & Generate**, call `saveResumeLabResume` with the current resume fields and notes, replace that profile in state, close the dialog, then pass the returned profile directly to `startGeneration(saved)` so React state timing cannot send a stale version. **Continue Without Adding** closes the dialog and calls `startGeneration(activeProfile)`.

Add an editable Verified Experience Notes textarea in the profile card using the same save behavior but without triggering generation.

- [ ] **Step 4: Run frontend verification**

```bash
cd /home/ubuntu/JobSpy/job-intelligence/frontend
npm run typecheck
npm run build
```

Expected: both commands exit 0 and `/resume-lab` is included in the build output.

- [ ] **Step 5: Commit**

```bash
git add job-intelligence/frontend/components/resume-lab/experience-checkpoint.tsx \
  job-intelligence/frontend/types/job.ts job-intelligence/frontend/lib/api.ts \
  job-intelligence/frontend/app/resume-lab/page.tsx
git commit -m "feat(resume-lab): confirm missing keyword experience"
```

### Task 5: Migrate, deploy, and verify the live workflow

**Files:**
- No new source files.

**Interfaces:**
- Consumes all Tasks 1-4.
- Produces a migrated, deployed VM stack.

- [ ] **Step 1: Run final checks before deployment**

```bash
cd /home/ubuntu/JobSpy
git diff --check
git status --short
cd job-intelligence
docker run --rm -v "$PWD:/app" -w /app job-intelligence-api sh -lc \
  "pip install -q pytest && pytest -q --ignore=tests/career_alerts --ignore=tests/live"
cd frontend && npm run typecheck && npm run build
```

Expected: clean diff check, only intended committed changes, zero core-test failures, and successful frontend checks.

- [ ] **Step 2: Back up and migrate the database**

```bash
cd /home/ubuntu/JobSpy/job-intelligence
docker compose exec api python -c "from pathlib import Path; from storage.backups import backup_sqlite_database; from storage.config import get_settings; print(backup_sqlite_database(get_settings().database_url, backup_dir=Path('/data/backups')))"
docker compose run --rm api alembic upgrade head
```

Expected: a new backup under `/data/backups` and Alembic at revision `0004_verified_experience_notes`.

- [ ] **Step 3: Rebuild and restart affected services**

```bash
docker compose up -d --build api frontend
docker compose restart nginx
```

Expected: `api`, `frontend`, and `nginx` report `Up`.

- [ ] **Step 4: Verify the live feature**

Use a Java profile and a JD containing one absent keyword. Verify the checkpoint appears, saving a truthful bullet increments `source_version`, the subsequent generation request uses that new version, and **Continue Without Adding** starts generation without changing the profile. Confirm:

```bash
curl -fsS http://localhost/api/health
curl -fsS -o /dev/null http://localhost/resume-lab
docker compose logs --since=10m --tail=100 api frontend nginx
git status --short
```

Expected: both URLs return successfully, no new application errors appear, and the worktree is clean.
