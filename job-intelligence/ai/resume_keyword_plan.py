from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


TECH_TERMS = (
    "C#", ".NET", "ASP.NET Core", "Java", "Python", "PyTorch", "TensorFlow",
    "Spring Boot", "Hibernate", "Kafka", "Maven", "Gradle", "JUnit", "Mockito",
    "Azure", "AWS", "GCP", "SQL", "SQL Server", "PostgreSQL", "MongoDB",
    "Oracle", "Jenkins",
    "React", "Angular", "TypeScript", "JavaScript", "REST API", "REST APIs",
    "Microservices", "Docker", "Kubernetes", "LangChain", "LLM", "RAG",
    "Machine Learning", "Artificial Intelligence", "NLP", "CI/CD", "Git",
    "J2EE", "Cross-functional", "Technical anchor", "Technical ownership",
    "Design direction", "Release readiness", "Backlog refinement", "Technical estimation",
    "Mentoring", "Data processing", "Data transformation", "Batch", "Validation",
    "Workflow orchestration", "Scheduled batch processing", "Distributed data processing",
    "NoSQL", "Document databases", "Search", "Indexing", "Azure App Services", "App Services", "AKS",
    "Cosmos DB", "Azure DevOps", "GitHub Actions", "Test-driven development", "TDD",
    "AI-accelerated SDLC", "AI-assisted development", "AI coding assistants", "GitHub Copilot", "VS Code",
    "IntelliJ", "Prompt engineering", "Code review", "Test generation", "Refactoring",
    "Downstream clients", "Airflow",
)

ALIASES = {
    "dotnet": ".net",
    "c sharp": "c#",
    "restful api": "rest api",
    "rest apis": "rest api",
}


@dataclass(frozen=True)
class KeywordPlan:
    supported: list[str]
    unsupported: list[str]
    placements: dict[str, str]


def _normalize_term(value: str) -> str:
    normalized = re.sub(r"\s+", " ", re.sub(r"[-–—]+", " ", value.strip().lower()))
    return ALIASES.get(normalized, normalized)


def _searchable_text(value: str) -> str:
    scrubbed = re.sub(r"https?://\S+|www\.\S+|\b\S+@\S+\b", " ", value.lower())
    return re.sub(r"[-–—]+", " ", scrubbed)


def _term_match(text: str, term: str) -> re.Match[str] | None:
    return re.search(rf"(?<!\w){re.escape(_normalize_term(term))}(?!\w)", text)


def normalized_hash(*parts: str) -> str:
    normalized = "\x1f".join(re.sub(r"\s+", " ", part).strip() for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extract_target_title(explicit_title: str | None, job_description: str) -> str:
    if explicit_title and explicit_title.strip():
        return explicit_title.strip()
    for line in job_description.splitlines():
        value = line.strip().strip("#*:- ")
        if value and len(value) <= 100 and re.search(r"\b(engineer|developer|architect|analyst|manager)\b", value, re.I):
            return value
    return "Target Role"


def build_keyword_plan(
    source_resume: str, job_description: str, *, target_title: str | None = None
) -> KeywordPlan:
    source = _searchable_text(source_resume)
    jd = _searchable_text(job_description)
    title = _normalize_term(target_title or "")
    found: list[tuple[int, str]] = []
    for term in TECH_TERMS:
        match = _term_match(jd, term)
        if match:
            found.append((match.start(), term))
    found.sort()
    supported = [term for _, term in found if _term_match(source, term)]
    unsupported = [
        term for _, term in found
        if not _term_match(source, term) and _normalize_term(term) != title
    ]
    placements = {
        term: "skills" if len(term.split()) <= 2 else "recent_roles"
        for term in supported
    }
    return KeywordPlan(supported=supported, unsupported=unsupported, placements=placements)


def replace_two_recent_titles(resume_text: str, target_title: str) -> tuple[str, list[str]]:
    if _normalize_term(target_title) in {"", "target role"}:
        return resume_text.rstrip("\n"), []

    lines = resume_text.splitlines()
    in_experience = False
    originals: list[str] = []
    section_re = re.compile(r"^(education|technical skills|skills|certifications?|projects?)\s*:?$", re.I)
    role_re = re.compile(
        r"\b(developer|engineer|architect|lead|manager|analyst|consultant)\b", re.I
    )
    for index, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^(professional |work )?experience\s*:?$", stripped, re.I):
            in_experience = True
            continue
        if in_experience and section_re.match(stripped):
            break
        if not in_experience or len(originals) >= 2 or stripped.startswith(("-", "•", "*")):
            continue
        prefix = line[: len(line) - len(line.lstrip())]
        if "|" in stripped:
            title, remainder = stripped.split("|", 1)
            if role_re.search(title) and remainder.strip():
                originals.append(title.strip())
                lines[index] = f"{prefix}{target_title.strip()} |{remainder}"
        elif len(stripped.split()) <= 12 and role_re.search(stripped):
            originals.append(stripped)
            lines[index] = f"{prefix}{target_title.strip()}"
    return "\n".join(lines), originals
