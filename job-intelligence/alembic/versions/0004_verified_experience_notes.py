"""add verified experience notes to Resume Lab profiles

Revision ID: 0004_verified_experience_notes
Revises: 0003_resume_lab_profiles_and_runs
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_verified_experience_notes"
down_revision = "0003_resume_lab_profiles_and_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_lab_profiles",
        sa.Column("verified_experience_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_lab_profiles", "verified_experience_notes")
