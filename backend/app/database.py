"""
Loads the three source databases (genuine medicines, banned companies,
medicine details) once at startup and exposes them for lookup.
"""
import logging

import pandas as pd

from app import config

logger = logging.getLogger("medverify.database")

REQUIRED_COLUMNS = {
    "genuine": "Name of Medicine",
    "banned": "Name of the Company",
    "details": "Medicine Name",
}


class DatabaseLoadError(RuntimeError):
    """Raised when one of the source database files is missing or malformed."""


class MedicineDatabase:
    def __init__(self):
        self.genuine_df: "pd.DataFrame | None" = None
        self.banned_df: "pd.DataFrame | None" = None
        self.details_df: "pd.DataFrame | None" = None

        self.genuine_names_list: list[str] = []
        self.banned_company_list: list[str] = []
        self.details_names_list: list[str] = []

        self.loaded: bool = False

    def load(self):
        logger.info("Loading MedVerify databases...")

        try:
            self.genuine_df = pd.read_excel(config.GENUINE_MEDICINES_PATH)
            self.banned_df = pd.read_excel(config.BANNED_COMPANIES_PATH)
            self.details_df = pd.read_csv(config.MEDICINE_DETAILS_PATH, dtype=str, low_memory=False)
        except FileNotFoundError as e:
            raise DatabaseLoadError(
                f"A required MedVerify data file is missing: {e}. "
                "Verify/name lookups cannot run until it's present in backend/data/."
            ) from e
        except (ValueError, pd.errors.ParserError) as e:
            raise DatabaseLoadError(f"A MedVerify data file could not be parsed: {e}") from e

        for df, key, path in (
            (self.genuine_df, "genuine", config.GENUINE_MEDICINES_PATH),
            (self.banned_df, "banned", config.BANNED_COMPANIES_PATH),
            (self.details_df, "details", config.MEDICINE_DETAILS_PATH),
        ):
            col = REQUIRED_COLUMNS[key]
            if col not in df.columns:
                raise DatabaseLoadError(
                    f"Expected column '{col}' not found in {path}. "
                    f"Found columns: {list(df.columns)}"
                )

        self.genuine_names_list = (
            self.genuine_df["Name of Medicine"].dropna().astype(str).str.strip().str.lower().tolist()
        )
        self.banned_company_list = (
            self.banned_df["Name of the Company"].dropna().astype(str).str.strip().str.lower().tolist()
        )
        self.details_names_list = (
            self.details_df["Medicine Name"].dropna().astype(str).str.strip().str.lower().tolist()
        )

        self._warn_on_duplicates("genuine medicines", self.genuine_names_list)
        self._warn_on_duplicates("banned companies", self.banned_company_list)

        self.loaded = True
        logger.info(
            "Loaded: %d genuine medicines | %d banned companies | %d detail records",
            len(self.genuine_names_list),
            len(self.banned_company_list),
            len(self.details_names_list),
        )

    @staticmethod
    def _warn_on_duplicates(label: str, names: list[str]):
        seen = set()
        dupes = set()
        for n in names:
            if n in seen:
                dupes.add(n)
            seen.add(n)
        if dupes:
            logger.warning(
                "%d duplicate name(s) found in %s dataset (first match wins): %s",
                len(dupes), label, sorted(dupes)[:10],
            )

    def get_genuine_row(self, matched_name: str):
        row = self.genuine_df[
            self.genuine_df["Name of Medicine"].astype(str).str.strip().str.lower() == matched_name
        ]
        return row.iloc[0] if not row.empty else None

    def get_detail_row(self, matched_name: str):
        row = self.details_df[
            self.details_df["Medicine Name"].astype(str).str.strip().str.lower() == matched_name
        ]
        return row.iloc[0] if not row.empty else None


# Single shared instance, loaded once when the app starts
db = MedicineDatabase()
