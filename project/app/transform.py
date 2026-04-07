import pandas as pd
import re
import logging

logger = logging.getLogger(__name__)


def clean_price(price_str: str) -> float | None:
    """Convert '£51.77' to 51.77. Returns None if parsing fails."""
    try:
        return float(price_str.replace("£", "").replace("Â", "").strip())
    except (ValueError, AttributeError):
        return None


def clean_availability(availability_str: str | None) -> int | None:
    """
    Extrait le nombre de livres en stock depuis la chaîne brute.

    Exemples :
        "In stock (22 available)"  → 22
        "In stock"                 → 0  (stock présent mais quantité inconnue)
        "Out of stock"             → 0
        None                       → None
    """
    if availability_str is None:
        return None
    match = re.search(r"\((\d+) available\)", availability_str)
    if match:
        return int(match.group(1))
    if "in stock" in availability_str.lower():
        return 0   # en stock mais quantité non précisée
    return 0       # out of stock ou valeur inconnue


def clean_data(raw_books: list[dict]) -> pd.DataFrame:
    """
    Transform raw scraped records into a clean DataFrame:
    - Parse and validate price
    - Parse availability → stock count (int)
    - Remove rows with missing critical fields
    - Remove duplicates (same title + category)
    - Reset index
    """
    logger.info("Starting transformation...")
    df = pd.DataFrame(raw_books)
    initial_count = len(df)
    logger.info(f"  Raw records: {initial_count}")

    # --- 1. Parse price ---
    df["price_gbp"] = df["price_gbp"].apply(clean_price)

    # --- 2. Parse availability ---
    df["availability"] = df["availability"].apply(clean_availability)

    # --- 3. Drop rows with missing critical values ---
    before_drop = len(df)
    df.dropna(subset=["title", "price_gbp", "rating", "category"], inplace=True)
    dropped_nulls = before_drop - len(df)
    if dropped_nulls > 0:
        logger.warning(f"  Dropped {dropped_nulls} rows with missing values.")

    # --- 4. Remove duplicates (same title in the same category) ---
    before_dedup = len(df)
    df.drop_duplicates(subset=["title", "category"], keep="first", inplace=True)
    dropped_dupes = before_dedup - len(df)
    if dropped_dupes > 0:
        logger.warning(f"  Dropped {dropped_dupes} duplicate rows.")

    # --- 5. Clean up types ---
    df["price_gbp"] = df["price_gbp"].astype(float)
    df["rating"] = df["rating"].astype(int)
    df["availability"] = df["availability"].astype("Int64")  # Int64 supporte les NaN
    df["title"] = df["title"].str.strip()
    df["category"] = df["category"].str.strip()
    df["upc"] = df["upc"].str.strip()

    # --- 6. Réordonner les colonnes ---
    df = df[["title", "category", "price_gbp", "rating", "availability", "upc"]]

    # --- 7. Reset index ---
    df.reset_index(drop=True, inplace=True)

    logger.info(f"  Clean records: {len(df)} (removed {initial_count - len(df)} total)")
    return df
