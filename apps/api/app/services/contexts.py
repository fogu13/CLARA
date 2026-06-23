from __future__ import annotations

import csv
import io
import sqlite3
from pathlib import Path

from app.domain.models import (
    ContextCompletenessMetric,
    CustomerContextImportResult,
    CustomerContextCompletenessReport,
    CustomerContextRecord,
    CustomerContextValidationReport,
    SignalValidationIssue,
)


REQUIRED_CONTEXT_FIELDS = ["customer_id", "account_id"]

RECOMMENDED_CONTEXT_FIELDS = [
    "account_name",
    "parent_account_id",
    "parent_account_name",
    "segment",
    "lifecycle_stage",
    "plan_tier",
    "contact_role",
    "account_value",
    "renewal_date",
    "consent_status",
    "health_score",
    "owner",
    "product_owner",
    "region",
]

CONTEXT_CSV_FIELDS = [*REQUIRED_CONTEXT_FIELDS, *RECOMMENDED_CONTEXT_FIELDS]

COMPLETENESS_FIELDS: list[tuple[str, str, str, float]] = [
    ("account_name", "Account name", "routing", 0.7),
    ("lifecycle_stage", "Lifecycle stage", "scoring", 1.0),
    ("plan_tier", "Plan tier", "scoring", 0.7),
    ("contact_role", "Contact role", "routing", 1.0),
    ("account_value", "Account value", "scoring", 1.2),
    ("renewal_date", "Renewal date", "routing", 0.7),
    ("consent_status", "Consent status", "governance", 1.2),
    ("health_score", "Health score", "scoring", 1.0),
    ("owner", "Owner", "routing", 1.2),
    ("product_owner", "Product owner", "routing", 1.0),
    ("region", "Region", "routing", 0.6),
]

CORE_COMPLETE_FIELDS = {
    "account_name",
    "lifecycle_stage",
    "contact_role",
    "account_value",
    "consent_status",
    "health_score",
    "owner",
    "product_owner",
}


def read_context_csv_rows(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    headers = reader.fieldnames or []
    rows = [{key: value or "" for key, value in row.items() if key is not None} for row in reader]
    return headers, rows


def parse_optional(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def parse_number(value: str | None, default: float | None = None) -> float | None:
    parsed = parse_optional(value)
    if parsed is None:
        return default

    return float(parsed)


def context_field_is_populated(record: CustomerContextRecord, field: str) -> bool:
    value = getattr(record, field)
    if field == "account_value":
        return bool(value and value > 0)
    if field == "health_score":
        return value is not None
    if field == "consent_status":
        return bool(value and value.strip().lower() not in {"", "unknown", "missing"})
    if isinstance(value, str):
        return bool(value.strip())

    return value is not None


def context_completeness_report(
    records: list[CustomerContextRecord],
) -> CustomerContextCompletenessReport:
    total_records = len(records)
    total_accounts = len({record.account_id for record in records})
    metrics: list[ContextCompletenessMetric] = []
    weighted_score = 0.0
    total_weight = 0.0
    warnings: list[SignalValidationIssue] = []

    for field, label, importance, weight in COMPLETENESS_FIELDS:
        populated_records = sum(
            1 for record in records if context_field_is_populated(record, field)
        )
        coverage = round(populated_records / total_records, 3) if total_records else 0.0
        metrics.append(
            ContextCompletenessMetric(
                field=field,
                label=label,
                populated_records=populated_records,
                total_records=total_records,
                coverage=coverage,
                importance=importance,
            )
        )
        weighted_score += coverage * weight
        total_weight += weight

    readiness_score = round(weighted_score / total_weight, 3) if total_weight else 0.0

    complete_records = sum(
        1
        for record in records
        if all(context_field_is_populated(record, field) for field in CORE_COMPLETE_FIELDS)
    )

    metric_by_field = {metric.field: metric for metric in metrics}
    warning_thresholds = {
        "account_value": 0.8,
        "consent_status": 0.9,
        "health_score": 0.75,
        "owner": 0.9,
        "contact_role": 0.7,
        "lifecycle_stage": 0.8,
    }

    if total_records == 0:
        warnings.append(
            SignalValidationIssue(
                severity="warning",
                message="No customer context records are loaded.",
            )
        )

    for field, threshold in warning_thresholds.items():
        metric = metric_by_field[field]
        if metric.coverage < threshold:
            warnings.append(
                SignalValidationIssue(
                    severity="warning",
                    field=field,
                    message=(
                        f"{metric.label} coverage is {round(metric.coverage * 100)}%; "
                        f"target is {round(threshold * 100)}%."
                    ),
                )
            )

    if readiness_score >= 0.85 and not warnings:
        readiness_level = "ready"
    elif readiness_score >= 0.65:
        readiness_level = "usable"
    else:
        readiness_level = "needs_attention"

    return CustomerContextCompletenessReport(
        total_records=total_records,
        total_accounts=total_accounts,
        complete_records=complete_records,
        readiness_score=readiness_score,
        readiness_level=readiness_level,
        metrics=metrics,
        warnings=warnings,
    )


def validate_context_csv(
    csv_text: str,
    *,
    existing_customer_ids: set[str] | None = None,
) -> CustomerContextValidationReport:
    headers, rows = read_context_csv_rows(csv_text)
    existing_customer_ids = existing_customer_ids or set()
    errors: list[SignalValidationIssue] = []
    warnings: list[SignalValidationIssue] = []
    rows_with_errors: set[int] = set()
    seen_customer_ids: dict[str, int] = {}

    if not headers:
        errors.append(
            SignalValidationIssue(
                severity="error",
                message="CSV must include a header row.",
            )
        )

    for field in REQUIRED_CONTEXT_FIELDS:
        if field not in headers:
            errors.append(
                SignalValidationIssue(
                    severity="error",
                    field=field,
                    message=f"Missing required column: {field}.",
                )
            )

    for field in RECOMMENDED_CONTEXT_FIELDS:
        if field not in headers:
            warnings.append(
                SignalValidationIssue(
                    severity="warning",
                    field=field,
                    message=f"Missing recommended column: {field}.",
                )
            )

    for row_index, row in enumerate(rows, start=2):
        row_has_error = False
        customer_id = row.get("customer_id", "").strip()

        for field in REQUIRED_CONTEXT_FIELDS:
            if not row.get(field, "").strip():
                errors.append(
                    SignalValidationIssue(
                        severity="error",
                        row_number=row_index,
                        field=field,
                        message=f"Row {row_index} is missing {field}.",
                    )
                )
                row_has_error = True

        if customer_id:
            first_seen_row = seen_customer_ids.get(customer_id)
            if first_seen_row is not None:
                errors.append(
                    SignalValidationIssue(
                        severity="error",
                        row_number=row_index,
                        field="customer_id",
                        message=(
                            f"Duplicate customer_id {customer_id} also appears on row {first_seen_row}."
                        ),
                    )
                )
                row_has_error = True
            else:
                seen_customer_ids[customer_id] = row_index

            if customer_id in existing_customer_ids:
                warnings.append(
                    SignalValidationIssue(
                        severity="warning",
                        row_number=row_index,
                        field="customer_id",
                        message=f"Customer context {customer_id} already exists and will be updated.",
                    )
                )

        for field in ["account_value", "health_score"]:
            raw_value = row.get(field, "").strip()
            if not raw_value:
                continue

            try:
                parsed_value = float(raw_value)
            except ValueError:
                errors.append(
                    SignalValidationIssue(
                        severity="error",
                        row_number=row_index,
                        field=field,
                        message=f"Row {row_index} has a non-numeric {field}.",
                    )
                )
                row_has_error = True
                continue

            if field == "account_value" and parsed_value < 0:
                errors.append(
                    SignalValidationIssue(
                        severity="error",
                        row_number=row_index,
                        field=field,
                        message=f"Row {row_index} has a negative account_value.",
                    )
                )
                row_has_error = True
            if field == "health_score" and not 0 <= parsed_value <= 1:
                errors.append(
                    SignalValidationIssue(
                        severity="error",
                        row_number=row_index,
                        field=field,
                        message=f"Row {row_index} health_score must be between 0 and 1.",
                    )
                )
                row_has_error = True

        if row_has_error:
            rows_with_errors.add(row_index)

    return CustomerContextValidationReport(
        valid=not errors,
        total_rows=len(rows),
        importable_rows=max(0, len(rows) - len(rows_with_errors)),
        errors=errors,
        warnings=warnings,
    )


def parse_context_csv(csv_text: str) -> list[CustomerContextRecord]:
    _, rows = read_context_csv_rows(csv_text)
    records: list[CustomerContextRecord] = []

    for row in rows:
        records.append(
            CustomerContextRecord(
                customer_id=row.get("customer_id", "").strip(),
                account_id=row.get("account_id", "").strip(),
                account_name=parse_optional(row.get("account_name")),
                parent_account_id=parse_optional(row.get("parent_account_id")),
                parent_account_name=parse_optional(row.get("parent_account_name")),
                segment=parse_optional(row.get("segment")),
                lifecycle_stage=parse_optional(row.get("lifecycle_stage")),
                plan_tier=parse_optional(row.get("plan_tier")),
                contact_role=parse_optional(row.get("contact_role")),
                account_value=parse_number(row.get("account_value"), 0.0) or 0.0,
                renewal_date=parse_optional(row.get("renewal_date")),
                consent_status=parse_optional(row.get("consent_status")) or "unknown",
                health_score=parse_number(row.get("health_score")),
                owner=parse_optional(row.get("owner")),
                region=parse_optional(row.get("region")),
            )
        )

    return records


class CustomerContextStore:
    def __init__(self) -> None:
        self._records: dict[str, CustomerContextRecord] = {}

    def list_context(self) -> list[CustomerContextRecord]:
        return sorted(
            self._records.values(),
            key=lambda record: (record.account_id, record.customer_id),
        )

    def import_context(
        self,
        records: list[CustomerContextRecord],
    ) -> CustomerContextImportResult:
        imported = 0
        updated = 0

        for record in records:
            if record.customer_id in self._records:
                updated += 1
            else:
                imported += 1
            self._records[record.customer_id] = record

        return CustomerContextImportResult(
            imported=imported,
            updated=updated,
            total_context_records=len(self._records),
        )

    def existing_customer_ids(self) -> set[str]:
        return set(self._records.keys())


class SQLiteCustomerContextStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_context (
                customer_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                account_name TEXT,
                parent_account_id TEXT,
                parent_account_name TEXT,
                segment TEXT,
                lifecycle_stage TEXT,
                plan_tier TEXT,
                contact_role TEXT,
                account_value REAL NOT NULL,
                renewal_date TEXT,
                consent_status TEXT NOT NULL,
                health_score REAL,
                owner TEXT,
                product_owner TEXT,
                region TEXT
            )
            """
        )
        self._ensure_columns(
            {
                "parent_account_id": "TEXT",
                "parent_account_name": "TEXT",
                "contact_role": "TEXT",
                "product_owner": "TEXT",
            }
        )
        self._connection.commit()

    def _ensure_columns(self, columns: dict[str, str]) -> None:
        existing_columns = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(customer_context)")
        }

        for column_name, column_type in columns.items():
            if column_name in existing_columns:
                continue
            self._connection.execute(
                f"ALTER TABLE customer_context ADD COLUMN {column_name} {column_type}"
            )

    def list_context(self) -> list[CustomerContextRecord]:
        rows = self._connection.execute(
            "SELECT * FROM customer_context ORDER BY account_id, customer_id"
        ).fetchall()
        return [self._context_from_row(row) for row in rows]

    def import_context(
        self,
        records: list[CustomerContextRecord],
    ) -> CustomerContextImportResult:
        imported = 0
        updated = 0

        for record in records:
            exists = self._connection.execute(
                "SELECT 1 FROM customer_context WHERE customer_id = ?",
                (record.customer_id,),
            ).fetchone()
            if exists is None:
                imported += 1
            else:
                updated += 1

            self._connection.execute(
                """
                INSERT INTO customer_context (
                    customer_id,
                    account_id,
                    account_name,
                    parent_account_id,
                    parent_account_name,
                    segment,
                    lifecycle_stage,
                    plan_tier,
                    contact_role,
                    account_value,
                    renewal_date,
                    consent_status,
                    health_score,
                    owner,
                    product_owner,
                    region
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    account_id = excluded.account_id,
                    account_name = excluded.account_name,
                    parent_account_id = excluded.parent_account_id,
                    parent_account_name = excluded.parent_account_name,
                    segment = excluded.segment,
                    lifecycle_stage = excluded.lifecycle_stage,
                    plan_tier = excluded.plan_tier,
                    contact_role = excluded.contact_role,
                    account_value = excluded.account_value,
                    renewal_date = excluded.renewal_date,
                    consent_status = excluded.consent_status,
                    health_score = excluded.health_score,
                    owner = excluded.owner,
                    product_owner = excluded.product_owner,
                    region = excluded.region
                """,
                (
                    record.customer_id,
                    record.account_id,
                    record.account_name,
                    record.parent_account_id,
                    record.parent_account_name,
                    record.segment,
                    record.lifecycle_stage,
                    record.plan_tier,
                    record.contact_role,
                    record.account_value,
                    record.renewal_date,
                    record.consent_status,
                    record.health_score,
                    record.owner,
                    record.product_owner,
                    record.region,
                ),
            )

        self._connection.commit()
        total = self._connection.execute("SELECT COUNT(*) FROM customer_context").fetchone()[0]
        return CustomerContextImportResult(
            imported=imported,
            updated=updated,
            total_context_records=total,
        )

    def existing_customer_ids(self) -> set[str]:
        rows = self._connection.execute("SELECT customer_id FROM customer_context").fetchall()
        return {row["customer_id"] for row in rows}

    @staticmethod
    def _context_from_row(row: sqlite3.Row) -> CustomerContextRecord:
        return CustomerContextRecord(
            customer_id=row["customer_id"],
            account_id=row["account_id"],
            account_name=row["account_name"],
            parent_account_id=row["parent_account_id"],
            parent_account_name=row["parent_account_name"],
            segment=row["segment"],
            lifecycle_stage=row["lifecycle_stage"],
            plan_tier=row["plan_tier"],
            contact_role=row["contact_role"],
            account_value=float(row["account_value"]),
            renewal_date=row["renewal_date"],
            consent_status=row["consent_status"],
            health_score=None if row["health_score"] is None else float(row["health_score"]),
            owner=row["owner"],
            product_owner=row["product_owner"],
            region=row["region"],
        )
