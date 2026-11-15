"""Validate CSV values and keep counts for each rejection reason."""

from decimal import Decimal

import pandas as pd


ID_PATTERN = r"[0-9a-f]{32}"
STATE_PATTERN = r"[A-Z]{2}"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"
MONEY_PATTERN = r"[0-9]{1,10}(\.[0-9]{1,2})?"
ORDER_STATUSES = {
    "approved", "canceled", "created", "delivered", "invoiced",
    "processing", "shipped", "unavailable",
}


class RowChecks:
    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.invalid = pd.Series(False, index=frame.index)
        self.reasons: dict[str, int] = {}

    def reject(self, reason: str, mask: pd.Series) -> None:
        self.invalid |= mask
        count = int(mask.sum())
        if count:
            self.reasons[reason] = count

    def require_pattern(self, column: str, pattern: str) -> None:
        self.reject(f"invalid_or_missing_{column}", ~self.frame[column].str.fullmatch(pattern))

    def require_unique(self, *columns: str) -> None:
        self.reject(f"duplicate_{'+'.join(columns)}", self.frame.duplicated(list(columns), keep=False))

    def require_reference(self, column: str, parent_keys: pd.Series) -> None:
        self.reject(f"missing_or_rejected_reference_{column}", ~self.invalid & ~self.frame[column].isin(parent_keys))

    def parse_timestamp(self, column: str, *, optional: bool = False) -> None:
        values = self.frame[column]
        parsed = pd.to_datetime(
            values.where(values.str.fullmatch(TIMESTAMP_PATTERN)),
            format=TIMESTAMP_FORMAT,
            errors="coerce",
        )
        invalid = parsed.isna() & (values.ne("") if optional else True)
        self.reject(f"invalid_or_missing_{column}", invalid)
        self.frame[column] = parsed

    def parse_money(self, column: str) -> None:
        values = self.frame[column]
        valid = values.str.fullmatch(MONEY_PATTERN)
        self.reject(f"invalid_or_missing_{column}", ~valid)
        self.frame[column] = values.where(valid, "0").map(Decimal)

    def parse_item_number(self) -> None:
        values = self.frame["order_item_id"]
        parsed = pd.to_numeric(values.where(values.str.fullmatch(r"[0-9]{1,10}")), errors="coerce")
        valid = parsed.between(1, 2_147_483_647).fillna(False)
        self.reject("invalid_or_missing_order_item_id", ~valid)
        self.frame["order_item_id"] = parsed.where(valid, 0).astype("int64")

    def accepted(self) -> pd.DataFrame:
        return self.frame.loc[~self.invalid]

    def report(self, loaded: int) -> dict:
        rejected = int(self.invalid.sum())
        return {
            "rows_checked": len(self.frame),
            "rows_rejected": rejected,
            "rows_valid_but_no_longer_referenced": len(self.frame) - rejected - loaded,
            "rejection_reasons": self.reasons,
        }
