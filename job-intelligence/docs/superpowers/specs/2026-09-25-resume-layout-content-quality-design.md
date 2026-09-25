# Resume Layout and Content Quality Design

## Goal

Make Resume Lab produce one truthful Technical Skills section, prominent job titles, richer JD-aligned experience bullets, and a project description plus final Environment line for every role.

## Current problems

- The DOCX path can render skills twice: once as a table and again as normal paragraphs.
- A two-line role layout such as `Job Title` followed by `Company, Location | Dates` is not recognized as a role header, so the title receives body-text styling.
- Project descriptions are optional and `Project Overview:` content is discarded by the renderer.
- Page-length instructions explicitly allow Environment lines to be removed.
- JD alignment requests keywords, but does not clearly require additional bullets when supported source evidence is available.

## Approved design

### Technical Skills

Parse the generated Technical Skills lines and use those values to build exactly one skills table. Do not use a hard-coded candidate-specific skills catalog, and do not retain duplicate skills paragraphs outside the table.

### Experience formatting

Recognize both supported input layouts:

1. `Role | Company | Location` followed by a date line.
2. `Role` followed by `Company, Location | Dates`.

Render the role title at 12 points, bold, and dark blue. Keep company, location, and dates visually secondary.

### Content rules

Require every role to contain:

- one concise `Project:` description grounded in the source resume;
- enough varied achievement bullets to incorporate supported JD keywords naturally;
- one `Environment:` line after the final bullet.

The source resume remains the sole source of truth. Unsupported JD keywords must not become candidate claims and remain keyword gaps.

### Humanized writing

Retain the existing anti-repetition rules and strengthen the instruction to vary sentence length, openings, and technical context. Avoid generic AI phrases and do not invent metrics, technologies, projects, or responsibilities.

## Verification

Add focused tests that inspect the generated DOCX structure and prompting rules:

- one Technical Skills heading and one dynamic skills table;
- no hard-coded skills from another profile;
- 12-point bold title formatting for both role layouts;
- project descriptions required and preserved;
- Environment required as the last line of each role;
- supported JD keywords may expand bullets while unsupported keywords remain excluded.

Run the focused resume tests, then the complete test suite. Generate one sample DOCX and inspect its paragraphs and tables before deployment.
