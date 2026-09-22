# Verified Experience Notes Before Resume Generation

## Problem

Resume Lab currently starts generation immediately. When a job description contains important
keywords absent from the selected profile, the user has no structured opportunity to supply
truthful supporting experience first. The generator must not invent that experience.

## Goal

Before generation, show important missing job-description keywords and allow the user to save
truthful supporting bullets permanently with the selected profile. The saved notes become part of
the source-of-truth context for all future generations from that profile.

## Non-goals

- Do not automatically claim experience for a missing keyword.
- Do not require notes when the user has none.
- Do not insert a visible "notes" section into the generated resume.
- Do not redesign the existing ATS scoring or profile system.

## User experience

When the user clicks **Generate Resume**, Resume Lab compares the job description with the base
resume and previously saved verified notes.

If important keywords are missing, a modal displays up to ten of them and provides one multiline
field for factual bullets. The modal has three actions:

- **Save & Generate**: requires a confirmation that the notes are truthful, saves them permanently,
  then generates with the updated profile version.
- **Continue Without Adding**: generates from the existing profile without changing it.
- **Cancel**: returns to Resume Lab without generating.

The profile panel also displays and permits editing of the saved notes. If no important keywords are
missing, generation starts without opening the modal.

## Data model and API

Add a nullable `verified_experience_notes` text column to `resume_lab_profiles` through an Alembic
migration. Expose it as an empty string in Resume Lab profile responses.

Extend the existing profile-save request with an optional `verified_experience_notes` field. When
the field is omitted, existing notes remain unchanged. When it changes, the repository increments
`source_version`, preserving the endpoint's optimistic-concurrency check.

The original resume checksum remains a checksum of the imported resume. Generation derives a
separate source hash from the resume checksum plus verified notes so cache entries and cover-letter
validation cannot reuse output created before the notes changed.

Input rules:

- Plain text only.
- Maximum 6,000 characters.
- Empty text clears the saved notes after confirmation.

## Generation flow

The backend combines the profile's resume text and verified notes into the truth baseline passed to
the orchestrator and factual validator. The prompt labels the notes as user-verified facts and asks
the model to integrate only relevant facts into appropriate summary, skills, or experience bullets.
It explicitly forbids outputting a separate notes section.

Missing-keyword analysis runs against the base resume plus saved notes. User-entered bullets are not
treated as permission to add unrelated keywords; normal supported-keyword planning and factual
validation still apply.

## Errors and concurrency

If another tab changes the profile before notes are saved, the existing source-version conflict is
shown and generation does not start. Failed saves keep the modal contents so the user can retry.
Generation failures do not remove successfully saved notes.

## Testing

Backend tests verify:

- notes persist and increment the profile version;
- omitted notes do not clear existing notes;
- source and cache hashes change when notes change;
- prompts include verified notes but forbid a notes section;
- numeric-claim validation accepts only claims present in the resume or verified notes.

Frontend tests or focused component checks verify:

- missing keywords open the checkpoint before generation;
- Save & Generate persists notes and uses the returned profile version;
- Continue Without Adding starts generation unchanged;
- truthful confirmation is required only when saving notes;
- no-gap generation remains one click.

## Deployment

Run the migration before restarting the API. Existing profiles receive empty notes and continue to
work without user action. Rebuild the frontend and API, then verify profile saving, generation, cache
invalidation, and the live health endpoints.
