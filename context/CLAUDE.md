# CLAUDE.md : guide du dépôt

Projet de template pour le Datathon PolyFinances 2026 (défi AlphaForge AI, Banque Nationale, AWS, PolyFinances). Il contient un tableau de bord Next.js, une API FastAPI et une base Aurora PostgreSQL sur AWS.

## À lire en premier

`context/defi-datathon.md` est le fichier le plus important du projet. Il présente le défi, l'admissibilité (au moins un service AWS démontrable), la remise (dimanche 15 novembre 2026 à 23 h 59), la grille d'évaluation (Solution 20 %, Agentique 20 %, Données 20 %, UX/UI 10 %, AWS 15 %, Pitch 15 %), les trois personas (Amira, Mateo, Robert), les sources de données suggérées, l'exemple de démonstration chiffrée et les quatre livrables (prototype, vidéo d'environ 5 minutes, documentation, fiche d'une page). Toute décision de conception doit être confrontée à ce document.

Règles du défi à respecter dans le code et l'interface : simulation uniquement (aucune transaction réelle, aucun conseil personnalisé), chaque donnée avec source, date et devise, distinction entre faits, hypothèses et scénario, explicabilité vérifiable (garder la trace des appels d'outils réellement effectués).

## Fichiers de contexte dans `context/`

| Fichier | Rôle |
|-|-|
| `defi-datathon.md` | Rapport de référence du défi (voir ci-dessus). Le plus important. |
| `presentation-atelier-finance.md` | Extraction texte des 16 diapos de l'atelier finance de la présentatrice BNCD : objectifs, familles d'actifs, rendement, horizon, risque, diversification, profil investisseur, données, explicabilité, exemple XSP, ressources. |
| `aide-memoire.md` | Aide-mémoire AWS du workshop (défi, compte d'équipe, deux chemins d'analyse, suite). |
| `idees-datathon.md` | Plan pour gagner le défi : grille de jugement, idée centrale « Que change ce transfert pour moi ? » avec les personas Amira, Mateo et Robert, services AWS, plan heure par heure et script de la vidéo. |
| `CLAUDE.md` | Ce fichier. |

## Fichiers versionnés

### Racine

| Fichier | Rôle |
|-|-|
| `README.md` | Présentation du template et démarrage local. |
| `.gitignore` | Exclusions Git (Python, `.env`, `.venv`, fichiers d'éditeur). |

### `backend-server/` : API FastAPI (Python 3.12)

Fournit au tableau de bord les prix et les articles. Lancement : `python main.py` dans le dossier (Swagger sur `http://localhost:8000/docs`).

| Fichier | Rôle |
|-|-|
| `README.md` | Routes, périodes et intervalles de bougies, structure, lancement. |
| `requirements.txt` | Dépendances Python. |
| `.env.example` | Modèle de `.env` (`STOCKSFEED_BASE_URL`). |
| `main.py` | Point d'entrée : démarre uvicorn sur `app.main:app` avec rechargement. |
| `app/main.py` | Crée l'application FastAPI et enregistre les routeurs. |
| `app/modules/stocks/routes.py` | Route `GET /stock/{ticker}/history` (dernier prix et bougies). |
| `app/modules/stocks/schemas.py` | Types de requête et de réponse des routes de prix. |
| `app/modules/stocksfeed/routes.py` | Routes d'articles (`/articles`, `/article/{slug}`) et `/stocks/most-mentioned` (tableau Discover). |
| `app/integrations/yahoo/service.py` | Appel à Yahoo Finance via yfinance, conversion en cotation et bougies. |
| `app/integrations/stocksfeed/service.py` | Requêtes HTTP vers l'API StocksFeed (actualités). Remplaçable par un autre collecteur en gardant les mêmes routes. |
| `__init__.py` (plusieurs) | Marqueurs de paquets Python. |

Pour ajouter une fonctionnalité : créer un module sous `app/modules/` et enregistrer son routeur dans `app/main.py`. C'est ici que viendront les calculs analytiques et l'appel à l'agent (Bedrock).

### `frontend-dashboard/` : application Next.js 16 (fork de Studio Admin)

React 19, TypeScript, Tailwind v4, shadcn/ui, Better Auth, npm. Lancement : `npm install` puis `npm run dev` (port 3000). Lire `AGENTS.md` et le guide Next.js de `node_modules/next/dist/docs/` avant de coder.

Fichiers de configuration et documentation :

| Fichier | Rôle |
|-|-|
| `README.md`, `CONTRIBUTING.md`, `LICENSE` | Documentation et licence du template Studio Admin d'origine. |
| `AGENTS.md` | Consignes pour agents : stack, règle de ne pas modifier `src/components/ui/` ni `src/components/calendar/`, usage du skill shadcn. |
| `.env.example` | Modèle de `.env.local` : `BETTER_AUTH_URL`, `BETTER_AUTH_SECRET`, accès Aurora (`DATABASE_*`, `DATABASE_CA_CERT`), `BACKEND_API_URL`. |
| `docs/authentication.md` | Fonctionnement et mise en place de l'authentification (Better Auth sur Aurora). |
| `docs/superpowers/plans/2026-11-04-auth.md` | Plan d'implémentation de l'authentification. |
| `package.json`, `package-lock.json` | Dépendances et scripts (`dev`, `build`, `check`, `auth:migrate`, `portfolio:migrate`, `generate:presets`). |
| `biome.json` | Lint et formatage (Biome). |
| `components.json` | Configuration shadcn/ui. |
| `next.config.mjs`, `postcss.config.mjs`, `tsconfig.json`, `tsconfig.scripts.json` | Configuration Next.js, PostCSS et TypeScript (le second tsconfig sert aux scripts). |
| `vercel.json` | Redirections Vercel héritées du template, non nécessaires au projet. |
| `media/` | Captures et visuels du template (`dashboard.png`, `default/`). |

Code source dans `src/` :

| Dossier ou fichier | Rôle |
|-|-|
| `app/layout.tsx`, `globals.css`, `not-found.tsx`, `icon.tsx`, `apple-icon.tsx`, `opengraph-image.*`, `twitter-image.alt.txt`, `robots.txt`, `sitemap.ts` | Mise en page racine, styles globaux, icônes et métadonnées SEO. |
| `app/api/auth/[...all]/route.ts` | Point d'accès Better Auth (`/api/auth/*`). |
| `app/api/stocks/[ticker]/change/route.ts` | Route interne pour la variation d'un titre. |
| `app/(main)/auth/` | Pages de connexion et d'inscription (`v1/login`, `v1/register`) et leurs formulaires. |
| `app/(main)/dashboard/home/` | Page d'accueil utile du projet : portefeuille, tableau Discover (actions les plus citées), filtres d'actualités, onglets par secteur, édition des parts. |
| `app/(main)/dashboard/stock/[ticker]/` | Page d'un titre : graphique de prix, panneau de prix, actualités, articles, titres liés. |
| `app/(main)/dashboard/_components/` | Éléments communs : en-tête (paramètres, thème, recherche, mot de passe) et barre latérale (navigation, ajout d'un titre, prix du portefeuille, utilisateur), sélecteur de titres. |
| `app/(main)/dashboard/layout.tsx`, `page.tsx`, `[...not-found]/`, `coming-soon/` | Gabarit du tableau de bord, redirection et pages d'attente. |
| `app/(main)/unauthorized/` | Page d'accès refusé. |
| `app/(main)/dashboard/` autres sous-dossiers (`default`, `ecommerce`, `finance`, `crm`, `analytics`, `academy`, `kanban`, `tasks`, `users`, `roles`, `products`, `invoice`, `logistics`, `file-manager`, `infrastructure`, `patient-monitoring`, `profile`, `calendar`, `chat`, `mail`), `app/(main)/chat/`, `app/(main)/mail/` | Pages de démonstration héritées du template Studio Admin avec données fictives. Non utilisées par le projet, à ignorer ou retirer. |
| `components/ui/` | Composants shadcn/ui. Ne pas modifier. |
| `components/calendar/` | Composants de calendrier. Ne pas modifier. |
| `components/` autres (`app-logo.tsx`, `date-range-picker.tsx`, `simple-icon.tsx`) | Composants partagés. |
| `config/app-config.ts` | Nom et métadonnées de l'application. |
| `data/sp500.ts`, `data/users.ts` | Liste des titres du S&P 500 et données utilisateurs d'exemple. |
| `hooks/` | Hooks React (détection mobile, grand écran, coloration de code). |
| `lib/auth.ts`, `auth-client.ts`, `session.ts` | Configuration Better Auth côté serveur et client, lecture de la session (`requireSession`). |
| `lib/db.ts` | Pool PostgreSQL (`authPool`) vers Aurora, avec vérification TLS. |
| `lib/preferences/`, `stores/preferences/` | Préférences d'interface (thème, mise en page) et leur store. |
| `lib/` autres (`utils.ts`, `cookie.client.ts`, `local-storage.client.ts`, `fonts/`, `highlighter.tsx`, `data-table-features.ts`, `app-icon.tsx`) | Utilitaires généraux. |
| `navigation/sidebar/sidebar-items.ts` | Définition des entrées de la barre latérale. |
| `proxy.ts` | Protège `/dashboard/*`, `/chat/*` et `/mail/*` en vérifiant la session réelle. |
| `server/portfolio.ts`, `add-portfolio-stock.ts`, `server-actions.ts`, `stock-history.ts` | Code serveur : lecture et ajout des positions (table `portfolio_holdings`), actions serveur, appel au backend FastAPI pour l'historique des prix. |
| `scripts/create-portfolio-table.ts` | Crée la table `portfolio_holdings` (`npm run portfolio:migrate`). |
| `scripts/generate-theme-presets.ts`, `theme-boot.tsx` | Génération des thèmes et initialisation du thème au chargement. |
| `styles/` | Préréglages de thèmes (`presets/`) et icônes de drapeaux. |

## Flux de données

Navigateur, puis Next.js (rendu serveur et actions serveur), puis FastAPI (`BACKEND_API_URL`), puis Yahoo Finance (prix) et StocksFeed (articles). Comptes, sessions et positions du portefeuille sont dans Aurora PostgreSQL, accessibles uniquement depuis Next.js.

## État par rapport au défi

Aurora est le seul service AWS en place. Il manque la couche d'agent (Amazon Bedrock), les calculs analytiques reproductibles (volatilité, baisse maximale, corrélation, exposition sectorielle), la gestion des trois personas et l'explicabilité traçable. Voir `idees-datathon.md` pour les pistes.
