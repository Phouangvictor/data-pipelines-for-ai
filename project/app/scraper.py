import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import time

BASE_URL = "https://books.toscrape.com/"

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. SITE INDISPONIBLE — get_page()
# ---------------------------------------------------------------------------

def get_page(url: str) -> BeautifulSoup | None:
    """
    Fetch a page and return a BeautifulSoup object.

    Erreurs gérées :
    - ConnectionError   : site indisponible / pas de réseau
    - Timeout           : le serveur ne répond pas
    - HTTPError         : page manquante (404), serveur en erreur (500…)
    - Toute autre erreur requests

    Retourne None sans bloquer le pipeline.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()         # lève HTTPError si 4xx / 5xx
        response.encoding = "utf-8"
        return BeautifulSoup(response.text, "html.parser")

    except requests.exceptions.ConnectionError:
        logger.error(f"[SITE INDISPONIBLE] Impossible de joindre : {url}")
    except requests.exceptions.Timeout:
        logger.error(f"[TIMEOUT] Le serveur ne répond pas : {url}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"[PAGE MANQUANTE] Erreur HTTP {e.response.status_code} : {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"[ERREUR RÉSEAU] {e} — URL : {url}")

    return None  # on retourne None → le pipeline continue


# ---------------------------------------------------------------------------
# 2. PAGE MANQUANTE — get_categories()
# ---------------------------------------------------------------------------

def get_categories(soup: BeautifulSoup) -> list[dict]:
    """
    Extrait toutes les catégories depuis la sidebar de la homepage.

    Erreurs gérées :
    - Balise nav absente (structure HTML inattendue)
    - Attribut href manquant sur un lien
    """
    categories = []

    try:
        nav = soup.find("ul", class_="nav-list")
        if not nav:
            logger.error("[PAGE MANQUANTE] Sidebar des catégories introuvable — structure HTML modifiée ?")
            return categories

        for link in nav.find_all("a"):
            try:
                name = link.get_text(strip=True)
                href = link["href"]              # KeyError si href absent
                if name.lower() == "books":
                    continue
                categories.append({"name": name, "url": BASE_URL + href})
            except KeyError:
                logger.warning(f"[DONNÉE MAL FORMÉE] Lien sans attribut href ignoré : {link}")

    except Exception as e:
        logger.error(f"[ERREUR INATTENDUE] Lors de l'extraction des catégories : {e}")

    logger.info(f"Found {len(categories)} categories.")
    return categories


# ---------------------------------------------------------------------------
# 3. DONNÉE MAL FORMÉE — _extract_book() + _get_book_details()
# ---------------------------------------------------------------------------

def _get_book_details(detail_url: str) -> dict:
    """
    Visite la page détail d'un livre et extrait UPC et Availability
    depuis le tableau produit.

    Retourne un dict avec les clés 'upc' et 'availability'.
    Si la page est inaccessible ou mal formée, retourne des valeurs None
    sans bloquer le pipeline.

    Exemple de tableau HTML ciblé :
        <tr><th>UPC</th><td>a897fe39b1053632</td></tr>
        <tr><th>Availability</th><td>In stock (22 available)</td></tr>
    """
    defaults = {"upc": None, "availability": None}

    soup = get_page(detail_url)
    if soup is None:
        return defaults

    try:
        # Le tableau produit indexé par libellé de ligne
        table = soup.find("table", class_="table-striped")
        if not table:
            logger.warning(f"[DONNÉE MAL FORMÉE] Tableau produit introuvable : {detail_url}")
            return defaults

        rows = {
            row.find("th").get_text(strip=True): row.find("td").get_text(strip=True)
            for row in table.find_all("tr")
        }

        upc = rows.get("UPC")
        availability = rows.get("Availability")

        if not upc:
            logger.warning(f"[DONNÉE MAL FORMÉE] UPC introuvable : {detail_url}")
        if not availability:
            logger.warning(f"[DONNÉE MAL FORMÉE] Availability introuvable : {detail_url}")

        return {"upc": upc, "availability": availability}

    except (AttributeError, TypeError) as e:
        logger.warning(f"[DONNÉE MAL FORMÉE] Erreur lecture tableau produit ({e}) : {detail_url}")
        return defaults


def _extract_book(article, category_name: str, listing_url: str) -> dict | None:
    """
    Extrait titre, prix, note, catégorie depuis l'article de la page listing,
    puis visite la page détail pour récupérer UPC et Availability.

    Erreurs gérées (champ par champ pour des messages clairs) :
    - Balise h3 / a absente       → titre introuvable
    - Balise price_color absente  → prix introuvable
    - Balise star-rating absente  → note introuvable
    - Note non reconnue dans RATING_MAP
    Un seul champ manquant suffit à ignorer le livre (retourne None).
    UPC / Availability : non bloquants — None si indisponibles.
    """
    # --- Titre + URL détail ---
    try:
        anchor = article.find("h3").find("a")
        title = anchor["title"]
        # href relatif ex: "../../catalogue/book-title_123/index.html"
        detail_url = urljoin(listing_url, anchor["href"])
    except (AttributeError, KeyError, TypeError):
        logger.warning("[DONNÉE MAL FORMÉE] Titre introuvable — livre ignoré.")
        return None

    # --- Prix ---
    try:
        price_text = article.find("p", class_="price_color").get_text(strip=True)
        if not price_text:
            raise ValueError("Prix vide")
    except (AttributeError, ValueError):
        logger.warning(f"[DONNÉE MAL FORMÉE] Prix introuvable pour '{title}' — livre ignoré.")
        return None

    # --- Note ---
    try:
        rating_class = article.find("p", class_="star-rating")["class"][1]
        rating = RATING_MAP.get(rating_class)
        if rating is None:
            raise ValueError(f"Note non reconnue : '{rating_class}'")
    except (AttributeError, KeyError, IndexError, ValueError) as e:
        logger.warning(f"[DONNÉE MAL FORMÉE] Note invalide pour '{title}' ({e}) — livre ignoré.")
        return None

    # --- UPC + Availability (page détail) ---
    details = _get_book_details(detail_url)
    time.sleep(0.3)  # délai poli entre chaque page détail

    return {
        "title": title,
        "price_gbp": price_text,
        "rating": rating,
        "category": category_name,
        "upc": details["upc"],
        "availability": details["availability"],
    }


# ---------------------------------------------------------------------------
# 4. PAGINATION — scrape_books_in_category()
# ---------------------------------------------------------------------------

def scrape_books_in_category(category_name: str, category_url: str) -> list[dict]:
    """
    Scrape tous les livres d'une catégorie, toutes pages confondues.

    Erreurs gérées :
    - Page inaccessible  → on arrête la pagination de cette catégorie
    - Aucun article      → on log un warning et on continue
    - Lien "suivant" mal formé → on arrête la pagination proprement
    """
    books = []
    current_url = category_url

    while current_url:
        soup = get_page(current_url)

        # Si la page est inaccessible, on ne bloque pas le pipeline
        if soup is None:
            logger.warning(f"[SITE INDISPONIBLE] Page ignorée, on passe à la catégorie suivante : {current_url}")
            break

        articles = soup.find_all("article", class_="product_pod")
        if not articles:
            logger.warning(f"[PAGE MANQUANTE] Aucun livre trouvé sur : {current_url}")

        for article in articles:
            book = _extract_book(article, category_name, current_url)
            if book:
                books.append(book)

        # Pagination
        try:
            next_btn = soup.find("li", class_="next")
            if next_btn:
                next_href = next_btn.find("a")["href"]
                base = current_url.rsplit("/", 1)[0]
                current_url = base + "/" + next_href
                time.sleep(0.5)
            else:
                current_url = None
        except (AttributeError, KeyError) as e:
            logger.warning(f"[DONNÉE MAL FORMÉE] Lien de pagination invalide ({e}) — arrêt de la pagination.")
            current_url = None

    logger.info(f"  [{category_name}] {len(books)} books scraped.")
    return books


# ---------------------------------------------------------------------------
# 5. ORCHESTRATION — scrape_all_books()
# ---------------------------------------------------------------------------

def scrape_all_books() -> list[dict]:
    """
    Point d'entrée principal : scrape tous les livres de toutes les catégories.

    Erreurs gérées :
    - Homepage inaccessible → RuntimeError (bloquant, rien à scraper)
    - Catégorie en erreur   → on log et on passe à la suivante (non bloquant)
    """
    logger.info("Starting extraction...")

    homepage = get_page(BASE_URL)
    if homepage is None:
        raise RuntimeError("[SITE INDISPONIBLE] Impossible d'atteindre la homepage — pipeline arrêté.")

    categories = get_categories(homepage)
    if not categories:
        raise RuntimeError("[PAGE MANQUANTE] Aucune catégorie trouvée — pipeline arrêté.")

    all_books = []
    errors = 0

    for cat in categories:
        try:
            books = scrape_books_in_category(cat["name"], cat["url"])
            all_books.extend(books)
        except Exception as e:
            errors += 1
            logger.error(f"[ERREUR INATTENDUE] Catégorie '{cat['name']}' ignorée : {e}")

    if errors:
        logger.warning(f"{errors} catégorie(s) ont échoué et ont été ignorées.")

    logger.info(f"Extraction complete. Total raw records: {len(all_books)}")
    return all_books
