from ai import resume_keyword_plan
from ai.resume_keyword_plan import (
    build_keyword_plan,
    normalized_hash,
    replace_two_recent_titles,
)


THREE_ROLE_RESUME = """Santosh Mulakidi
Senior .NET Developer

PROFESSIONAL EXPERIENCE
Senior .NET Developer | Acme Corp | Dallas, TX
2024 - Present
- Built Python APIs with Azure.

Software Engineer | Beta LLC | Austin, TX
2021 - 2024
- Developed REST services.

Junior Developer | OldCo | Houston, TX
2018 - 2021
- Maintained internal applications.

EDUCATION
Master of Science
"""


def test_keyword_plan_requires_only_source_supported_jd_terms():
    plan = build_keyword_plan(
        "Senior engineer using Python, PyTorch, Azure, and REST APIs.",
        "AI Engineer requires Python, PyTorch, Azure, LangChain, and Kubernetes.",
        target_title="AI Engineer",
    )
    assert plan.supported == ["Python", "PyTorch", "Azure"]
    assert plan.unsupported == ["LangChain", "Kubernetes"]


def test_keyword_plan_ignores_urls_and_partial_technology_names():
    plan = build_keyword_plan(
        "JavaScript engineer. Portfolio: https://example.net/java",
        "JavaScript role. Apply at https://careers.example.net/jobs/java",
        target_title="Frontend Developer",
    )
    assert plan.supported == ["JavaScript"]
    assert plan.unsupported == []

    plan = build_keyword_plan(
        "Portfolio: https://example.net",
        "Build .NET services with Azure.",
    )
    assert ".NET" in plan.unsupported


def test_replace_two_recent_titles_preserves_older_role_and_employers():
    transformed, originals = replace_two_recent_titles(THREE_ROLE_RESUME, "AI Engineer")
    assert originals == ["Senior .NET Developer", "Software Engineer"]
    assert transformed.count("AI Engineer |") == 2
    assert "Acme Corp" in transformed and "2024 - Present" in transformed
    assert "Junior Developer | OldCo" in transformed


def test_replace_two_recent_titles_handles_split_role_layout_without_overwriting_employers():
    resume = """PROFESSIONAL EXPERIENCE
Senior Java Software Developer
Schneider Electric, Carrollton, TX | January 2025 - Present
- Built Spring Boot services.

Senior Java Developer
Oracle, Austin, TX | February 2023 - December 2024
- Built Java services.

Software Engineer
JPMorgan Chase, Columbus, OH | January 2020 - January 2023
- Maintained applications.

EDUCATION
Bachelor of Technology
"""

    transformed, originals = replace_two_recent_titles(resume, "Lead Software Engineer")

    assert originals == ["Senior Java Software Developer", "Senior Java Developer"]
    assert transformed.count("Lead Software Engineer") == 2
    assert "Schneider Electric, Carrollton, TX | January 2025 - Present" in transformed
    assert "Oracle, Austin, TX | February 2023 - December 2024" in transformed
    assert "Software Engineer\nJPMorgan Chase" in transformed


def test_placeholder_target_title_never_replaces_real_titles_or_employers():
    transformed, originals = replace_two_recent_titles(THREE_ROLE_RESUME, "Target Role")

    assert transformed == THREE_ROLE_RESUME.rstrip("\n")
    assert originals == []


def test_keyword_plan_covers_supported_healthcare_full_stack_jd_phrases():
    source = (
        "Cross-functional Java J2EE engineer using Spring Boot, React, TypeScript, and Python. "
        "Built data processing batch validation with SQL, NoSQL, search, indexing, Azure App Services, "
        "Docker, Kubernetes, GitHub Actions, test-driven development, GitHub Copilot, "
        "prompt engineering, and code review."
    )
    jd = (
        "Own cross-functional Java/J2EE Spring Boot and React TypeScript applications. "
        "Build Python data-processing pipelines with batch validation, SQL, NoSQL and search/indexing. "
        "Use Azure App Services, AKS, Cosmos DB, Docker, Kubernetes, GitHub Actions, "
        "test-driven development, GitHub Copilot, prompt engineering, and code review."
    )

    plan = build_keyword_plan(source, jd)

    assert {
        "Cross-functional", "J2EE", "React", "TypeScript", "Python",
        "Data processing", "Batch", "Validation", "NoSQL", "Search", "Indexing",
        "Azure App Services", "GitHub Actions", "Test-driven development",
        "GitHub Copilot", "Prompt engineering", "Code review",
    } <= set(plan.supported)
    assert {"AKS", "Cosmos DB"} <= set(plan.unsupported)


def test_confirmed_keyword_plan_requires_every_detected_jd_term():
    plan = build_keyword_plan(
        "Java engineer",
        "Java Python Airflow",
        require_all=True,
    )

    assert plan.supported == ["Java", "Python", "Airflow"]
    assert plan.unsupported == []


def test_keyword_coverage_repair_adds_every_missing_term_once():
    repaired = resume_keyword_plan.ensure_keyword_coverage(
        "SUMMARY\nJava engineer\n\nTECHNICAL SKILLS\nLanguages: Java\n\nPROFESSIONAL EXPERIENCE",
        ["Java", "Python", "Airflow"],
    )

    assert "Verified JD Keywords: Python, Airflow" in repaired
    assert repaired.lower().count("python") == 1
    assert resume_keyword_plan.ensure_keyword_coverage(
        repaired, ["Java", "Python", "Airflow"]
    ) == repaired


def test_hash_is_stable_for_line_endings_and_outer_space():
    assert normalized_hash(" a\r\nb ") == normalized_hash("a\nb")
