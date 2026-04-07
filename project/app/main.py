import logging
import time
import os
from datetime import datetime
from scraper import scrape_all_books
from transform import clean_data

# --- Logging configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "books.csv")


def run_pipeline():
    logger.info("=" * 50)
    logger.info("PIPELINE START")
    logger.info("=" * 50)
    start = time.time()

    # --- EXTRACT ---
    try:
        raw_books = scrape_all_books()
    except RuntimeError as e:
        logger.critical(f"[PIPELINE ARRÊTÉ] Extraction impossible : {e}")
        return

    if not raw_books:
        logger.critical("[PIPELINE ARRÊTÉ] Aucune donnée extraite — rien à sauvegarder.")
        return

    # --- TRANSFORM ---
    try:
        df = clean_data(raw_books)
    except Exception as e:
        logger.critical(f"[PIPELINE ARRÊTÉ] Erreur pendant la transformation : {e}")
        return

    # --- LOAD ---
    try:
        logger.info("Saving data to CSV...")
        df["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
        logger.info(f"  Saved {len(df)} books to {OUTPUT_PATH}")
    except OSError as e:
        logger.critical(f"[PIPELINE ARRÊTÉ] Impossible d'écrire le CSV : {e}")
        return

    elapsed = time.time() - start
    logger.info("=" * 50)
    logger.info(f"PIPELINE COMPLETE in {elapsed:.1f}s")
    logger.info(f"  Total books: {len(df)}")
    logger.info(f"  Categories:  {df['category'].nunique()}")
    logger.info(f"  Price range: £{df['price_gbp'].min():.2f} – £{df['price_gbp'].max():.2f}")
    logger.info(f"  Avg rating:  {df['rating'].mean():.2f} / 5")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_pipeline()
