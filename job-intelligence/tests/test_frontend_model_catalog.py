from pathlib import Path


def test_openrouter_claude_45_model_ids_use_decimal_version():
    catalog = (Path(__file__).parents[1] / "frontend/lib/api.ts").read_text(encoding="utf-8")

    assert "anthropic/claude-sonnet-4.5" in catalog
    assert "anthropic/claude-opus-4.5" in catalog
    assert "anthropic/claude-sonnet-4-5" not in catalog
    assert "anthropic/claude-opus-4-5" not in catalog


def test_resume_lab_uses_deepseek_v41_flash_instead_of_v4_pro():
    frontend = Path(__file__).parents[1] / "frontend"
    catalog = (frontend / "lib/api.ts").read_text(encoding="utf-8")
    page = (frontend / "app/resume-lab/page.tsx").read_text(encoding="utf-8")

    assert "deepseek/deepseek-v4.1-flash" in catalog
    assert '"deepseek-v4.1-flash"' in page
    assert "deepseek-v4-pro-0813" not in catalog + page


def test_resume_lab_catalog_contains_only_paid_models_and_google_gemini():
    catalog = (Path(__file__).parents[1] / "frontend/lib/api.ts").read_text(encoding="utf-8")
    resume_lab_catalog = catalog.split("export function resumeLabModelChoices()", 1)[1].split(
        "export async function getSchedulerStatus", 1
    )[0]

    assert 'cost: "Free"' not in resume_lab_catalog
    assert 'provider: "gemini"' not in resume_lab_catalog
    assert 'provider: "openrouter", model: "google/gemini-3.1-pro-preview"' in resume_lab_catalog


def test_resume_lab_refinement_never_replaces_a_higher_scoring_resume():
    page = (
        Path(__file__).parents[1] / "frontend/app/resume-lab/page.tsx"
    ).read_text(encoding="utf-8")

    assert "refinedAts.score < currentAts.score" in page
    assert "Kept the higher-scoring resume" in page
