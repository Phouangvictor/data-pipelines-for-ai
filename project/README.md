# Data Pipeline — Books to Scrape

**Cours : Data Pipelines for AI — MSc 2025-2026**
**Session 1/3 — Introduction ETL / ELT et premier pipeline**

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
  ┌─────────────────────────────────────────────┐
  │  EXTRACT  —  scraper.py                     │
  │  ├── get_page()               fetch HTTP    │
  │  ├── get_categories()         50 catégories │
  │  └── scrape_books_in_category() pagination  │
  └─────────────────────────────────────────────┘
         │  1000 enregistrements bruts
         ▼
  ┌─────────────────────────────────────────────┐
  │  TRANSFORM  —  transform.py                 │
  │  ├── clean_price()    "£51.77" → 51.77      │
  │  ├── dropna()         valeurs manquantes     │
  │  └── drop_duplicates() 1 doublon supprimé   │
  └─────────────────────────────────────────────┘
         │  999 enregistrements propres
         ▼
  ┌─────────────────────────────────────────────┐
  │  LOAD  —  main.py                           │
  │  └── data/books.csv                         │
  └─────────────────────────────────────────────┘
```

**Approche** : ETL simplifié — transformation avant stockage, adapté aux petits volumes.

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
| `price_gbp` | float | `54.23` | Prix en livres sterling |
| `rating` | int | `4` | Note de 1 à 5 étoiles |
| `category` | string | `"History"` | Catégorie du livre |

### Extrait du CSV

```
title,price_gbp,rating,category
It's Only the Himalayas,45.17,2,Travel
See America: A Celebration of Our National Parks & Treasured Sites,48.87,3,Travel
Vagabonding: An Uncommon Guide to the Art of Long-Term World Travel,36.94,2,Travel
An Abundance of Katherines,10.0,5,Young Adult
The Star-Touched Queen,46.02,5,Fantasy
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
| Durée d'exécution | ~61s |

---

## Qualité des données

### Nettoyage appliqué

| Problème | Traitement |
|---|---|
| Symbole `£` dans le prix | Supprimé, converti en `float` |
| Encodage défaillant (`â` parasites) | Réponse HTTP forcée en UTF-8 |
| Valeurs manquantes | `dropna()` sur les 4 champs critiques |
| Doublons | `drop_duplicates()` sur la paire `(title, category)` |

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

## Source des données

- **Site** : [books.toscrape.com](https://books.toscrape.com) — site de démonstration conçu pour le scraping
- **Données fictives** : prix et notes générés aléatoirement, aucune donnée personnelle
- **Conformité RGPD** : pas de données personnelles collectées, usage pédagogique
