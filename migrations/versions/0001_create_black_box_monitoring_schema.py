"""create black box monitoring schema"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
    )
    op.create_table(
        "check_types",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_check_types")),
        sa.UniqueConstraint("code", name=op.f("uq_check_types_code")),
    )
    op.create_table(
        "status_levels",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_status_levels")),
        sa.UniqueConstraint("code", name=op.f("uq_status_levels_code")),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "failure_threshold", sa.SmallInteger(), server_default="3", nullable=False
        ),
        sa.Column(
            "recovery_threshold", sa.SmallInteger(), server_default="2", nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "failure_threshold > 0", name=op.f("ck_services_positive_failure_threshold")
        ),
        sa.CheckConstraint(
            "recovery_threshold > 0",
            name=op.f("ck_services_positive_recovery_threshold"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_services_category_id_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_services")),
        sa.UniqueConstraint("name", name=op.f("uq_services_name")),
    )
    op.create_table(
        "checks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("service_id", sa.BigInteger(), nullable=False),
        sa.Column("check_type_id", sa.SmallInteger(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("interval_sec", sa.Integer(), server_default="60", nullable=False),
        sa.Column("timeout_sec", sa.Double(), server_default="10", nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "timeout_sec > 0 AND timeout_sec < 'Infinity'::double precision",
            name=op.f("ck_checks_finite_positive_timeout"),
        ),
        sa.CheckConstraint(
            "interval_sec > 0", name=op.f("ck_checks_positive_interval")
        ),
        sa.ForeignKeyConstraint(
            ["check_type_id"],
            ["check_types.id"],
            name=op.f("fk_checks_check_type_id_check_types"),
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], name=op.f("fk_checks_service_id_services")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checks")),
    )
    op.create_table(
        "service_statuses",
        sa.Column("service_id", sa.BigInteger(), nullable=False),
        sa.Column("status_level_id", sa.SmallInteger(), nullable=False),
        sa.Column(
            "consecutive_failures", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "consecutive_successes", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name=op.f("ck_service_statuses_nonnegative_failures"),
        ),
        sa.CheckConstraint(
            "consecutive_successes >= 0",
            name=op.f("ck_service_statuses_nonnegative_successes"),
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name=op.f("fk_service_statuses_service_id_services"),
        ),
        sa.ForeignKeyConstraint(
            ["status_level_id"],
            ["status_levels.id"],
            name=op.f("fk_service_statuses_status_level_id_status_levels"),
        ),
        sa.PrimaryKeyConstraint("service_id", name=op.f("pk_service_statuses")),
    )
    op.create_table(
        "check_results",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("check_id", sa.BigInteger(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.SmallInteger(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tls_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "response_time_ms >= 0",
            name=op.f("ck_check_results_nonnegative_response_time"),
        ),
        sa.CheckConstraint(
            "status_code BETWEEN 100 AND 599", name=op.f("ck_check_results_http_status")
        ),
        sa.ForeignKeyConstraint(
            ["check_id"], ["checks.id"], name=op.f("fk_check_results_check_id_checks")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_check_results")),
    )
    op.create_index(
        "ix_check_results_check_id_checked_at",
        "check_results",
        ["check_id", sa.literal_column("checked_at DESC")],
        unique=False,
    )
    op.create_table(
        "http_check_settings",
        sa.Column("check_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "expected_status", sa.SmallInteger(), server_default="200", nullable=False
        ),
        sa.Column(
            "follow_redirects",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "slow_response_ms", sa.Integer(), server_default="2000", nullable=False
        ),
        sa.Column("content_pattern", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "expected_status BETWEEN 100 AND 599",
            name=op.f("ck_http_check_settings_http_status"),
        ),
        sa.CheckConstraint(
            "slow_response_ms > 0",
            name=op.f("ck_http_check_settings_positive_slow_response"),
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["checks.id"],
            name=op.f("fk_http_check_settings_check_id_checks"),
        ),
        sa.PrimaryKeyConstraint("check_id", name=op.f("pk_http_check_settings")),
    )
    op.create_table(
        "tls_check_settings",
        sa.Column("check_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "warn_before_days", sa.SmallInteger(), server_default="14", nullable=False
        ),
        sa.CheckConstraint(
            "warn_before_days > 0",
            name=op.f("ck_tls_check_settings_positive_warning_threshold"),
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["checks.id"],
            name=op.f("fk_tls_check_settings_check_id_checks"),
        ),
        sa.PrimaryKeyConstraint("check_id", name=op.f("pk_tls_check_settings")),
    )

    op.bulk_insert(
        sa.table(
            "check_types",
            sa.column("id", sa.SmallInteger()),
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
        ),
        [
            {"id": 1, "code": "http", "name": "HTTP"},
            {"id": 2, "code": "tls", "name": "TLS"},
            {"id": 3, "code": "tcp", "name": "TCP"},
        ],
    )
    op.bulk_insert(
        sa.table(
            "status_levels",
            sa.column("id", sa.SmallInteger()),
            sa.column("code", sa.String()),
            sa.column("label", sa.String()),
            sa.column("color", sa.String()),
            sa.column("severity", sa.SmallInteger()),
        ),
        [
            {
                "id": 1,
                "code": "UNKNOWN",
                "label": "Неизвестно",
                "color": "gray",
                "severity": 0,
            },
            {
                "id": 2,
                "code": "GREEN",
                "label": "Доступен",
                "color": "green",
                "severity": 1,
            },
            {
                "id": 3,
                "code": "YELLOW",
                "label": "Деградация",
                "color": "yellow",
                "severity": 2,
            },
            {
                "id": 4,
                "code": "RED",
                "label": "Недоступен",
                "color": "red",
                "severity": 3,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("tls_check_settings")
    op.drop_table("http_check_settings")
    op.drop_index("ix_check_results_check_id_checked_at", table_name="check_results")
    op.drop_table("check_results")
    op.drop_table("service_statuses")
    op.drop_table("checks")
    op.drop_table("services")
    op.drop_table("status_levels")
    op.drop_table("check_types")
    op.drop_table("categories")
