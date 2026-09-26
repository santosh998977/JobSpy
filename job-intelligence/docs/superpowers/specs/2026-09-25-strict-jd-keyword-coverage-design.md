# Strict JD Keyword Coverage

## Goal

Resume Lab must include every detected job-description keyword in the final resume. A run is not complete unless exact keyword coverage is 100%.

## Truth boundary

The user confirmed hands-on Java and .NET full-stack experience and confirmed the supplied JD technologies as known experience. Before each generation, Resume Lab will require the user to confirm that all detected JD keywords reflect real knowledge or experience. Confirmed terms may be placed in the summary and technical-skills section. Resume Lab must not invent employers, dates, metrics, project assignments, certifications, or education.

## Behavior

1. Extract the existing curated JD keyword list.
2. Require a per-generation confirmation that every detected keyword is truthful for the candidate.
3. Treat every detected term as required after confirmation and include it exactly in the generated resume.
4. Send missing terms through the existing repair pass.
5. Reject the result unless coverage reaches 100%; never return a partially compliant resume as `REVIEWED`.
6. Return the missing keyword names in the generation events so the UI explains the failure.

The current Tejasri Java request already supplies this confirmation; subsequent UI runs will use the same required confirmation control.

## Data flow

The existing profile resume plus verified notes remains the source of truth for factual history. A required request flag records the per-run keyword confirmation. The existing keyword planner supplies all detected terms to the writer, reviewer, repair step, and final acceptance gate. No new service or dependency is needed.

## Error handling

Provider failures continue through the existing fallback chain. If providers respond but any required keyword remains absent after repair, the run is stored as failed with the exact missing terms. The prior reviewed resume remains untouched.

## Tests

- A generated resume missing one required term is not marked reviewed.
- A repair that restores every term is accepted at 100%.
- The failure event lists missing terms.
- Generation without keyword confirmation is rejected.
- Existing employer/date/numeric-claim validation remains active.
