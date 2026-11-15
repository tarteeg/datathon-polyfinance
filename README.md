# Datathon PolyFinances 2026 : AlphaForge AI

Projet d'équipe pour le Datathon PolyFinances 2026, proposé avec la Banque Nationale et propulsé par AWS. Le défi AlphaForge AI demande de concevoir un outil qui utilise l'IA générative, les agents et des données financières publiques pour éclairer une décision d'investissement, selon trois personas fictifs : Prudent, Équilibré et Audacieux.

> Le tableau de bord Next.js, l’API FastAPI, le chat financier et les alertes RiskRipple sont en place. BreakPoint AI est accessible depuis la barre latérale du tableau de bord.

## Pile technique

- Frontend : Next.js 16, React 19, TypeScript, Tailwind CSS 4 et shadcn/ui, basé sur Studio Admin. Recharts pour les graphiques et OpenUI pour afficher les réponses du chat.
- Authentification : Better Auth.
- Base de données : Amazon Aurora PostgreSQL (comptes, sessions, portefeuilles, historique du chat).
- Backend : FastAPI et Uvicorn (Python 3.12).
- IA : Amazon Bedrock (Converse et ConverseStream, base de connaissances pour RiskRipple) et Strands Agents pour les agents RiskRipple.
- Calcul : pandas, NumPy, SciPy et NetworkX.
- Données : Yahoo Finance (yfinance), StocksFeed et l'API Valet de la Banque du Canada.

Le compte AWS d'équipe est activé le 14 novembre 2026 et supprimé le 16 novembre en fin de journée. Le code doit être sur GitHub avant l'expiration.

## Guide d'installation

### Prérequis

- Git
- Python 3.12
- Node.js et npm (version compatible avec Next.js 16)
- Une base PostgreSQL existante (Amazon Aurora PostgreSQL) et son certificat CA RDS, pour les comptes, sessions, portefeuilles et conversations
- Un compte AWS avec accès à Amazon Bedrock, pour le chat financier (identifiants AWS ou clé API Bedrock)
- OpenSSL, pour générer les clés secrètes

### 1. Cloner le dépôt

```sh
git clone <url-du-depot>
cd datathon-polyfinance
```

### 2. Générer les clés partagées

Deux valeurs doivent être créées une seule fois :

```sh
openssl rand -hex 32      # CHAT_API_KEY, identique dans les deux applications
openssl rand -base64 32   # BETTER_AUTH_SECRET, tableau de bord seulement
```

### 3. Installer le serveur FastAPI

Depuis `backend-server/` :

```sh
cd backend-server
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Renseignez `.env` :

| Variable | Rôle |
| --- | --- |
| `STOCKSFEED_BASE_URL` | Adresse de l'API StocksFeed (valeur par défaut fournie) |
| `AWS_REGION`, `BEDROCK_MODEL_ID` | Région et modèle Bedrock utilisés par le chat |
| `AWS_BEARER_TOKEN_BEDROCK` | Optionnel : clé API Bedrock à la place des identifiants AWS |
| `CHAT_API_KEY` | Clé partagée avec le tableau de bord |
| `DATABASE_*` | Mêmes valeurs de connexion que le tableau de bord, requises par les analyses RiskRipple |

Démarrez le serveur :

```sh
python main.py
```

Vérifiez-le avec la [documentation Swagger](http://localhost:8000/docs) ou `curl 'http://localhost:8000/stock/AAPL/history?period=1mo'`.

### 4. Installer le tableau de bord

Dans un second terminal, depuis `frontend-dashboard/` :

```sh
cd frontend-dashboard
npm install
cp .env.example .env.local
```

Renseignez `.env.local` :

| Variable | Rôle |
| --- | --- |
| `BETTER_AUTH_URL` | `http://localhost:3000` en local |
| `BETTER_AUTH_SECRET` | Secret généré à l'étape 2 |
| `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_CA_CERT` | Connexion à la base PostgreSQL existante |
| `BACKEND_API_URL` | Adresse du serveur FastAPI, `http://127.0.0.1:8000` |
| `CHAT_API_KEY` | Même valeur que dans `backend-server/.env` |

Sur une base vide, créez les tables, puis démarrez :

```sh
npm run auth:migrate
npm run portfolio:migrate
npm run chat:migrate
npm run dev
```

Ouvrez [le tableau de bord local](http://localhost:3000), créez un compte ou connectez-vous.

Gardez les identifiants dans `.env` et `.env.local`, qui ne doivent pas être versionnés. Pour plus de détails, consultez le [guide du serveur](backend-server/README.md) et le [guide du tableau de bord](frontend-dashboard/README.md).

### Dépannage

- Le chat renvoie une erreur d'authentification : vérifiez que `CHAT_API_KEY` est identique dans les deux fichiers d'environnement, puis redémarrez les deux serveurs.
- Erreur Bedrock : vérifiez `AWS_REGION`, `BEDROCK_MODEL_ID` et les permissions `bedrock:InvokeModel` et `bedrock:InvokeModelWithResponseStream`.
- Erreur de connexion à la base : vérifiez le point d'accès en écriture Aurora (sans protocole ni port), le nom de la base et `DATABASE_CA_CERT`.
- Les cours ou les actualités n'apparaissent pas : le serveur a besoin d'un accès HTTPS sortant vers Yahoo Finance et StocksFeed.

## Fonctionnalités

Le tableau de bord, basé sur [Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard), permet de suivre un portefeuille simulé, de consulter les cours et les actualités d’un titre, de repérer les actions du S&P 500 les plus citées dans les articles des dernières 24 heures et de poser des questions au chat financier. Le chat s'appuie sur Amazon Bedrock, des outils de calcul (exposition sectorielle, concentration, historique de risque, conversion de devises) et une vérification des chiffres de chaque réponse. BreakPoint AI détermine à partir de quelle baisse d’un FNB une limite de perte est atteinte et compare le scénario au recul historique d’un portefeuille SPY/TLT en 2022. Une page RiskRipple analyse l'exposition du portefeuille aux alertes d'actualité et de réglementation. Les paramètres sont accessibles en cliquant sur votre nom dans la barre latérale.

L’API récupère les cours auprès de Yahoo Finance avec yfinance et les actualités auprès de [StocksFeed](https://stocksfeed.benollomo.com/). Amazon Aurora PostgreSQL conserve les comptes, les sessions et les positions du portefeuille. Consultez le [guide d’architecture](ARCHITECTURE.md) pour suivre les échanges entre les services.

## Équipe et licence

Membres de l'équipe :

- Sami Mostfa
- Pacifique Uwamukiza
- Benjamin Ollomo
- Mohamed Oubagha

