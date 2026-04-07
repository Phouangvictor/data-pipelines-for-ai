# Data Pipeline — Books to Scrape

---

## Objectif du projet

Construire un pipeline de données complet de type **ETL** qui :

1. **Extrait** les données de livres depuis le site [books.toscrape.com](https://books.toscrape.com)
2. **Transforme** et nettoie les données (prix, encodage, doublons, valeurs manquantes)
3. **Charge** les données propres dans un fichier CSV exploitable

**Problématique** : identifier les livres les mieux notés et comparer les prix par catégorie.

---

## Architecture du pipeline

```
Site web (books.toscrape.com)
         │
         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  EXTRACT  —  scraper.py                                 │
  │                                                         │
  │  get_page()          → fetch HTTP avec gestion erreurs  │
  │  get_categories()    → 50 catégories depuis la sidebar  │
  │  scrape_books_in_category()  → pagination automatique   │
  │  _get_book_details() → page détail (UPC + availability) │
  │  _extract_book()     → parsing champ par champ          │
  └─────────────────────────────────────────────────────────┘
         │  1000 enregistrements bruts (7 champs)
         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  TRANSFORM  —  transform.py                             │
  │                                                         │
  │  clean_price()        "£51.77"              → 51.77     │
  │  clean_availability() "In stock (22 avail)" → 22        │
  │  dropna()             valeurs manquantes supprimées      │
  │  drop_duplicates()    1 doublon supprimé                 │
  │  cast types           float / int / Int64 / str         │
  └─────────────────────────────────────────────────────────┘
         │  999 enregistrements propres
         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  LOAD  —  main.py                                       │
  │                                                         │
  │  Ajout colonne scraped_at (horodatage)                  │
  │  Export → data/books.csv (UTF-8, sans index)            │
  └─────────────────────────────────────────────────────────┘
```

**Approche** : ETL simplifié — transformation avant stockage, adapté aux petits volumes.

Chaque étape est **indépendante et résiliente** : une erreur sur un livre ou une catégorie ne bloque pas le reste du pipeline. Seule l'inaccessibilité totale du site déclenche un arrêt complet.

---

## Structure du projet

```
project/
├── app/
│   ├── scraper.py      # EXTRACT  — requests + BeautifulSoup
│   ├── transform.py    # TRANSFORM — pandas
│   └── main.py         # Orchestration, logs, gestion des erreurs
├── data/
│   └── books.csv       # Sortie finale : 999 livres, 4 colonnes
└── README.md
```

---

## Technologies utilisées

| Outil | Version | Rôle |
|---|---|---|
| `Python` | 3.12 | Langage principal |
| `requests` | — | Téléchargement des pages HTML |
| `BeautifulSoup4` | — | Parsing HTML et extraction des données |
| `pandas` | — | Nettoyage, déduplication, export CSV |
| `logging` | stdlib | Monitoring de l'exécution |

---

## Installation des dépendances

```bash
pip install requests beautifulsoup4 pandas
```

---

## Lancer le pipeline

```bash
cd project/app
python3 main.py
```

Le fichier `data/books.csv` est généré automatiquement à la fin de l'exécution.

**Durée estimée** : ~60 secondes (1000 livres, 50 catégories, délai poli de 0.5s/page).

---

## Description des données collectées

| Colonne | Type | Exemple | Description |
|---|---|---|---|
| `title` | string | `"Sapiens: A Brief History..."` | Titre complet du livre |
| `category` | string | `"History"` | Catégorie du livre (50 valeurs possibles) |
| `price_gbp` | float | `54.23` | Prix en livres sterling, nettoyé depuis `"£54.23"` |
| `rating` | int | `4` | Note de 1 à 5 étoiles (One → Five converti en int) |
| `availability` | int | `22` | Nombre d'exemplaires en stock, extrait depuis `"In stock (22 available)"` |
| `upc` | string | `"a22124811bfa8350"` | Code produit universel unique, issu de la page détail du livre |
| `scraped_at` | datetime | `"2026-03-31 17:00:33"` | Horodatage d'exécution du pipeline (ajouté à la phase LOAD) |

> `availability` et `upc` nécessitent une visite de la page détail de chaque livre (requête supplémentaire). Un délai de 0.3s est appliqué entre chaque appel pour ne pas surcharger le serveur.

### Extrait du CSV

```
title,category,price_gbp,rating,availability,upc,scraped_at
It's Only the Himalayas,Travel,45.17,2,19,a22124811bfa8350,2026-03-31 17:00:33
Full Moon over Noah's Ark,Travel,49.43,4,15,ce60436f52c5ee68,2026-03-31 17:00:33
See America: A Celebration of Our National Parks & Treasured Sites,Travel,48.87,3,14,f9705c362f070608,2026-03-31 17:00:33
An Abundance of Katherines,Young Adult,10.0,5,3,ce6396d1e2fa5e30,2026-03-31 17:00:33
The Star-Touched Queen,Fantasy,46.02,5,7,c57e715f0e2aebf4,2026-03-31 17:00:33
...
```

---

## Résultats d'exécution

| Métrique | Valeur |
|---|---|
| Enregistrements bruts extraits | 1000 |
| Livres après nettoyage | 999 |
| Catégories couvertes | 50 |
| Doublons supprimés | 1 |
| Valeurs manquantes | 0 |
| Fourchette de prix | £10.00 – £59.99 |
| Note moyenne | 2.92 / 5 |
| Requêtes HTTP totales | ~1050 (50 pages listing + ~1000 pages détail) |
| Durée d'exécution | ~61s |

---

## Qualité des données

### Nettoyage appliqué

| Problème | Traitement |
|---|---|
| Symbole `£` et `Â` dans le prix | Supprimés, convertis en `float` via `clean_price()` |
| Encodage défaillant (`â` parasites) | Réponse HTTP forcée en UTF-8 (`response.encoding = "utf-8"`) |
| Availability en texte brut | Parsé en `int` via regex : `"In stock (22 available)"` → `22` |
| Valeurs manquantes sur champs critiques | `dropna()` sur `title`, `price_gbp`, `rating`, `category` |
| Doublons | `drop_duplicates()` sur la paire `(title, category)`, première occurrence conservée |
| Types hétérogènes | Cast explicite : `price_gbp` → `float`, `rating` → `int`, `availability` → `Int64` |

### Doublon détecté et supprimé

Lors de l'exécution, **1 doublon** a été détecté sur le site lui-même :

| # | Titre | Prix | Note | Catégorie |
|---|---|---|---|---|
| occurrence 1 *(conservée)* | The Star-Touched Queen | £46.02 | 5 | Fantasy |
| occurrence 2 *(supprimée)* | The Star-Touched Queen | £32.30 | 5 | Fantasy |

> **Cause probable** : bug du site — le livre apparaît deux fois dans la pagination de la catégorie Fantasy, avec des prix différents. La première occurrence est conservée.

### Politesse serveur

Délai de **0.5s** entre chaque requête de pagination pour ne pas surcharger le serveur (bonne pratique web scraping, cf. cours slide 8).

---

## Gestion des erreurs

Chaque étape du pipeline gère ses erreurs indépendamment pour **ne pas bloquer le pipeline entier**.

| Cas d'erreur | Erreur Python | Comportement | Message log |
|---|---|---|---|
| Site indisponible / pas de réseau | `ConnectionError` | Continue, livre/catégorie ignoré | `[SITE INDISPONIBLE]` |
| Serveur ne répond pas | `Timeout` | Continue | `[TIMEOUT]` |
| Page manquante (404, 500…) | `HTTPError` | Continue avec code HTTP affiché | `[PAGE MANQUANTE]` |
| Titre absent dans le HTML | `AttributeError` | Livre ignoré | `[DONNÉE MAL FORMÉE]` |
| Prix absent ou vide | `AttributeError / ValueError` | Livre ignoré | `[DONNÉE MAL FORMÉE]` |
| Note non reconnue | `ValueError` | Livre ignoré avec valeur reçue | `[DONNÉE MAL FORMÉE]` |
| Lien de pagination cassé | `KeyError` | Arrêt propre de la pagination | `[DONNÉE MAL FORMÉE]` |
| Homepage inaccessible | `RuntimeError` | **Arrêt total** — rien à scraper | `[PIPELINE ARRÊTÉ]` |
| Écriture CSV impossible | `OSError` | **Arrêt total** — message clair | `[PIPELINE ARRÊTÉ]` |

**Principe** : une erreur sur un livre ou une catégorie ne bloque pas le reste. Seule l'inaccessibilité totale du site arrête le pipeline.

---

## Exemple de logs

```
2026-03-31 14:25:09 [INFO]  ==================================================
2026-03-31 14:25:09 [INFO]  PIPELINE START
2026-03-31 14:25:09 [INFO]  ==================================================
2026-03-31 14:25:09 [INFO]  Starting extraction...
2026-03-31 14:25:10 [INFO]  Found 50 categories.
2026-03-31 14:25:10 [INFO]    [Travel] 11 books scraped.
2026-03-31 14:25:12 [INFO]    [Mystery] 32 books scraped.
...
2026-03-31 14:26:10 [INFO]  Extraction complete. Total raw records: 1000
2026-03-31 14:26:10 [INFO]  Starting transformation...
2026-03-31 14:26:10 [INFO]    Raw records: 1000
2026-03-31 14:26:10 [WARNING]  Dropped 1 duplicate rows.
2026-03-31 14:26:10 [INFO]    Clean records: 999 (removed 1 total)
2026-03-31 14:26:10 [INFO]  Saving data to CSV...
2026-03-31 14:26:10 [INFO]    Saved 999 books to data/books.csv
2026-03-31 14:26:10 [INFO]  ==================================================
2026-03-31 14:26:10 [INFO]  PIPELINE COMPLETE in 61.0s
2026-03-31 14:26:10 [INFO]    Total books  : 999
2026-03-31 14:26:10 [INFO]    Categories   : 50
2026-03-31 14:26:10 [INFO]    Price range  : £10.00 – £59.99
2026-03-31 14:26:10 [INFO]    Avg rating   : 2.92 / 5
2026-03-31 14:26:10 [INFO]  ==================================================
```

---

## Choix techniques

| Décision | Justification |
|---|---|
| Deux niveaux de scraping (listing + détail) | Les champs `upc` et `availability` ne sont disponibles que sur la page détail de chaque livre |
| `Int64` (nullable) pour `availability` | Permet de conserver les `None` quand la page détail est inaccessible, sans casser le cast |
| Délai 0.3s par page détail + 0.5s par page listing | Politesse serveur — évite le bannissement IP et respecte les bonnes pratiques de scraping |
| `dropna()` uniquement sur les 4 champs critiques | `upc` et `availability` sont non bloquants : un livre peut être conservé même si sa page détail est inaccessible |
| `scraped_at` ajouté en phase LOAD (pas EXTRACT) | L'horodatage reflète le moment de l'écriture effective du CSV, pas de chaque requête individuelle |

---

## Source des données

- **Site** : [books.toscrape.com](https://books.toscrape.com) — site de démonstration conçu pour le scraping
- **Données fictives** : prix et notes générés aléatoirement, aucune donnée personnelle
- **Conformité RGPD** : pas de données personnelles collectées, usage pédagogique
