# Roadmap de déploiement AWS : AlphaForge AI

Rédigée le 14 novembre 2026. Elle décrit les étapes du déploiement et le rôle de chaque service AWS. Remise du dépôt et de l'application : dimanche 15 novembre à 23 h 59. Le compte d'équipe est supprimé le lundi 16 novembre.

Légende : ✅ fait et vérifié · ⬜ à faire · ⚠️ à vérifier avant de s'y fier.

## 1. Vue d'ensemble

```mermaid
flowchart LR
    User["Navigateur"] -->|HTTPS| FE["ECS Express Mode : frontend Next.js"]
    FE -->|HTTP privé ou public| BE["ECS Express Mode : backend FastAPI"]
    FE -->|TLS, port 5432| DB[("Aurora PostgreSQL")]
    BE -->|yfinance| Yahoo["Yahoo Finance"]
    BE -->|HTTP| Feed["StocksFeed"]
    BE -.->|Phase 6| Bedrock["Amazon Bedrock (Nova, Guardrails)"]
    FE -.->|Secrets au démarrage| SM["Secrets Manager"]
    BE -.->|Secrets au démarrage| SM
    ECR["Amazon ECR : images"] --> FE
    ECR --> BE
    CB["AWS CodeBuild : construction"] --> ECR
    FE --> CW["CloudWatch Logs"]
    BE --> CW
```

| Service AWS | Rôle dans le projet | Phase |
|---|---|---|
| Amazon Aurora PostgreSQL | Comptes, sessions, portefeuilles (déjà en place) | 1 |
| Amazon ECR | Stocker les images Docker du frontend et du backend | 3 |
| AWS CodeBuild | Construire les images (Docker n'est pas installé dans l'environnement de travail) | 3 |
| AWS Secrets Manager | Mot de passe de la base, secret d'authentification, certificat | 4 |
| Amazon ECS Express Mode (Fargate) | Exécuter les deux conteneurs avec HTTPS et équilibreur de charge gérés | 5 |
| Amazon CloudWatch Logs | Journaux des deux services | 5 |
| Amazon Bedrock, Guardrails, Nova Web Grounding | Couche d'agent d'AlphaForge AI (critères AWS et Agentique du jury) | 6 |

### Pourquoi ECS Express Mode et pas Amplify ou App Runner
- Amplify Hosting ne prend en charge que Next.js jusqu'à la version 15 selon [sa documentation](https://docs.aws.amazon.com/amplify/latest/userguide/ssr-amplify-support.html). Le projet est en Next.js 16.
- AWS App Runner n'accepte plus de nouveaux clients depuis le 30 avril 2026, et AWS recommande ECS Express Mode ([avis AWS](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)).

## 2. Phases

### Phase 0 : vérifications préalables ✅ (sauf quotas)
- ✅ Les identifiants AWS sont disponibles dans l'environnement de travail (rôle de l'atelier, compte d'équipe).
- ✅ Le cluster Aurora `datathon` existe dans `us-east-1` (Aurora PostgreSQL 17.9, `available`, une instance Serverless v2).
- ✅ Le `DATABASE_HOST` configuré correspond à ce cluster.
- ✅ Le VPC par défaut contient 6 sous-réseaux publics, un par zone de disponibilité.
- ✅ Droits du rôle de l'atelier, simulés avec `iam:SimulatePrincipalPolicy` : autorisés pour ECR (création de dépôt, push), CodeBuild (projet, build), Secrets Manager (création), ECS (cluster, service, Express Mode), IAM (création de rôle, `PassRole`, attachement de politique), CloudWatch Logs, équilibreur de charge, règles du groupe de sécurité, et Bedrock (`Converse`, `InvokeModel`, `ApplyGuardrail`, `CreateGuardrail`, `InvokeTool`). Limite : la simulation ne prend pas en compte les politiques de contrôle de service (SCP) de l'organisation. Le premier appel réel de création le confirmera.
- ✅ État du compte (lectures réussies) : aucun cluster ECS, aucun projet CodeBuild, un dépôt ECR de démarrage CDK, trois secrets déjà présents (dont un nommé `polyfinance/bedroc…`, non lu). Aucun rôle d'exécution ECS n'existe : il faudra le créer.
- ✅ Bedrock, `us-east-1` : les modèles et profils d'inférence suivants sont listés : `us.amazon.nova-2-lite-v1:0` (modèle de Web Grounding), `us.amazon.nova-pro-v1:0`, `us.amazon.nova-premier-v1:0`, plusieurs profils Claude. Cette liste montre ce que le compte voit. L'accès réel au modèle reste à confirmer par un premier appel (phase 6).
- ⬜ Quotas : non vérifiés (Fargate, équilibreurs de charge).

**Critère de sortie :** une liste des services utilisables, ou la liste des blocages à lever avec un mentor AWS. Atteint, sous réserve des SCP.

### Phase 1 : base de données ✅
- ✅ Les tables `user`, `account`, `session`, `verification`, `rateLimit` et `portfolio_holdings` existent. La table `chat_turns` existe aussi, d'origine inconnue.
- ✅ Les migrations Better Auth et portefeuille ont été appliquées.
- ✅ La connexion TLS avec le bundle de certificats `us-east-1` (3 certificats) fonctionne et la vérification du certificat reste active.
- ⬜ Décider si le groupe de sécurité du cluster reste ouvert au port 5432 depuis `0.0.0.0/0` (état actuel). Pour un datathon c'est acceptable. Après la démonstration, restreindre l'accès aux services ECS.

### Phase 2 : conteneurisation ✅ (fichiers écrits, testés sans Docker)
- ✅ `backend-server/Dockerfile` : Python 3.12 slim, utilisateur non privilégié, `uvicorn app.main:app --host 0.0.0.0 --port 8000`. `STOCKSFEED_BASE_URL` a une valeur par défaut (l'adresse publique de l'exemple), que le service peut remplacer. Le `main.py` de développement (rechargement, `127.0.0.1`) n'est pas utilisé.
- ✅ `frontend-dashboard/Dockerfile` : trois étapes (dépendances, build, exécution) sur Node 24 slim. `HUSKY=0` évite le script `prepare`. Le serveur démarre avec `next start` sur `0.0.0.0:3000`, utilisateur `node`.
- ✅ Le build exige les variables de la base, car `src/lib/db.ts` les vérifie dès l'import du module. Le Dockerfile passe donc des valeurs factices (`build-placeholder`) à la seule commande `npm run build`. Elles ne sont pas stockées dans l'image ni utilisées à l'exécution.
- ✅ `.dockerignore` des deux applications : exclusion de `.env*` (sauf `.env.example`), de `node_modules`, `.venv`, `.next` et `.git`.
- ✅ `BACKEND_API_URL` et `BETTER_AUTH_URL` ne sont pas figées : elles viennent de l'environnement au démarrage.
- ✅ Vérifié en local, sans Docker : `npm run build` réussit avec les valeurs factices, aucune ne se retrouve dans `.next`, `next start` sert la page de connexion avec son CSS (HTTP 200), `/api/auth/get-session` répond `null` avec la base, et la redirection vers la connexion fonctionne. Le backend lancé avec la commande du conteneur répond sur `/docs`, `/stock/MSFT/history` et `/articles`.
- ⚠️ **Les images n'ont pas été construites** : Docker n'est pas installé dans l'environnement de travail. Le premier vrai test sera la construction dans CodeBuild (phase 3). Les étapes `COPY` et `npm prune --omit=dev` du Dockerfile frontend ne sont pas encore éprouvées.
- ⬜ Vérification de santé des services ECS : le backend n'a pas de route `/health`, utiliser `/docs`. Le frontend peut utiliser `/auth/v1/login`.

**Critère de sortie :** les deux images se construisent sans erreur et sans secret dans les couches. À confirmer en phase 3.

### Phase 3 : construction et registre ✅
Réalisé le 14 novembre 2026. Le code part dans un bucket S3 privé (archive `git archive` de la branche `deploiement`), et non depuis GitHub : CodeBuild n'a donc besoin d'aucun jeton GitHub.
- ✅ Dépôts ECR `polyfinance/backend` et `polyfinance/frontend` (analyse à chaque push activée).
- ✅ Bucket S3 `polyfinance-build-src-<compte>-us-east-1` : accès public bloqué, versionnement activé.
- ✅ Rôle IAM `polyfinance-codebuild-role` : journaux, push sur ces deux dépôts ECR, lecture du bucket.
- ✅ Projet CodeBuild `polyfinance-build` (image `aws/codebuild/standard:7.0`, mode privilégié pour Docker, calcul moyen), recette `deploy/buildspec.yml`. Les images de base viennent du miroir public d'AWS (`public.ecr.aws/docker/library`).
- ✅ Premier build réussi (construction 115 s, envoi 40 s). Images dans ECR, étiquette `24360fd` (hash du commit) : backend 118 Mo, frontend 480 Mo.
- ✅ Les Dockerfiles ont donc été éprouvés dans un vrai environnement Docker.

Pour reconstruire après une modification : produire l'archive (`git archive --format=zip -o source-<hash>.zip HEAD`), la déposer dans `s3://<bucket>/source/`, mettre à jour l'emplacement de la source et la variable `IMAGE_TAG` du projet, puis lancer un build. Un jeton GitHub ou CodeConnections éviterait ces gestes manuels, au prix d'un secret supplémentaire.

**Critère de sortie :** atteint. Les deux images sont dans ECR avec leur étiquette.

### Phase 4 : secrets ✅
Réalisé le 14 novembre 2026.
- ✅ Un seul secret JSON, `polyfinance/app`, dans Secrets Manager (`us-east-1`), avec six clés : `DATABASE_HOST`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_CA_CERT` et `BETTER_AUTH_SECRET`. Une tâche ECS peut référencer une clé précise du JSON.
- ✅ `BETTER_AUTH_SECRET` est un nouveau secret aléatoire de 32 octets, différent de celui du développement local.
- ✅ Les valeurs sont passées de `.env.local` à AWS par un script local, sans affichage. Elles n'apparaissent ni dans Git, ni dans un Dockerfile, ni dans les journaux.
- ✅ Vérifié : le secret contient les six clés, et une connexion TLS à Aurora réussit avec les valeurs qu'il contient. Le certificat (4 575 caractères) reste très en dessous de la limite de 128 Ko par variable d'environnement.
- ✅ Rôle d'exécution `polyfinance-ecs-execution-role` (approbation : `ecs-tasks.amazonaws.com`, limitée à ce compte). Politiques : `AmazonECSTaskExecutionRolePolicy` (lecture des images, écriture des journaux) et une politique en ligne qui autorise `secretsmanager:GetSecretValue` sur `polyfinance/app` uniquement. Simulation : lecture autorisée sur ce secret, refusée sur les autres.
- ⬜ Les variables non secrètes (`DATABASE_PORT`, `BACKEND_API_URL`, `BETTER_AUTH_URL`, `STOCKSFEED_BASE_URL`) iront comme variables d'environnement ordinaires en phase 5.
- ⬜ Rôle de tâche du backend pour Bedrock : à créer en phase 6.

**Critère de sortie :** atteint. Le secret est lisible par le rôle d'exécution, et par lui seul.

### Phase 5 : services ECS Express Mode 🟡 (déployés, validation de bout en bout en attente)
Réalisé le 14 novembre 2026, avec les images d'étiquette `24360fd`.
- ✅ Rôle d'infrastructure `polyfinance-ecs-infrastructure-role` (approbation : `ecs.amazonaws.com`, politique gérée `AmazonECSInfrastructureRoleforExpressGatewayServices`). Cluster ECS `polyfinance`. Groupes de journaux `/ecs/polyfinance-backend` et `/ecs/polyfinance-frontend` (conservation 7 jours).
- ✅ Service `polyfinance-backend` : port 8000, 0,5 vCPU et 1 Go, une tâche, vérification de santé `/docs`. URL publique : https://po-e59a191cd93e413aa245ac0c45f4c3e9.ecs.us-east-1.on.aws. Rollout terminé (`COMPLETED`).
- ✅ Service `polyfinance-frontend` : port 3000, 1 vCPU et 2 Go, une tâche, vérification de santé `/auth/v1/login`. URL publique : https://po-8688b8a9273e447c9c115ab93278e7fe.ecs.us-east-1.on.aws. Variables : `DATABASE_PORT`, `BACKEND_API_URL`, `BETTER_AUTH_URL`. Secrets lus dans `polyfinance/app` : les six clés de la phase 4.
- ✅ `BETTER_AUTH_URL` réglée sur l'URL exacte du frontend après sa création (mise à jour du service). Elle avait d'abord une valeur provisoire, car l'URL n'existe qu'après la création.
- ✅ Vérifié par requêtes : le backend répond (HTTP 200) sur `/docs`, `/stock/AAPL/history` et `/articles`. Le frontend répond (HTTP 200) sur `/auth/v1/login` et `/api/auth/get-session`. Les journaux du frontend montrent un démarrage de Next.js sans erreur.
- ⚠️ **Non vérifié** : inscription, connexion et pages après connexion (cours, actualités, portefeuille). Cela inclut l'appel du frontend vers le backend et l'écriture d'un portefeuille dans Aurora depuis ECS. À tester dans un navigateur.
- ⚠️ Au dernier contrôle, le déploiement du frontend restait `IN_PROGRESS` : l'ancienne révision (celle de la valeur provisoire de `BETTER_AUTH_URL`) n'était pas encore retirée. Le site répond, mais à reconfirmer.
- ⚠️ Le premier essai de création du backend a échoué sur un droit du rôle d'infrastructure (`logs:DescribeLogGroups`), probablement un délai de propagation IAM : le second essai, quelques secondes plus tard, a réussi. À garder en tête si on recrée un service.
- ⚠️ Le groupe de sécurité d'Aurora reste ouvert au port 5432 depuis `0.0.0.0/0` (état de départ). Décision de le restreindre encore à prendre.
- ⚠️ Coût : les deux services (Fargate et équilibreur de charge) facturent à l'heure tant qu'ils tournent. À arrêter après la remise.

**Critère de sortie :** pas encore atteint. Il faut qu'un utilisateur s'inscrive, se connecte et ajoute un titre à son portefeuille sur l'URL publique du frontend.

### Phase 6 : couche d'agent AlphaForge AI ⬜
C'est elle qui rapporte les points sur les critères AWS (15 %) et Agentique (20 %). Détails dans `context/idees-datathon.md` et `context/VEILLE-TECHNOLOGIQUE.md`.
- ⬜ Premier appel `converse` à Amazon Bedrock depuis le backend, en `us-east-1`. ⚠️ Vérifier l'accès au modèle choisi dans le compte.
- ⬜ Route `/agent` avec un agent Strands, ses outils de calcul reproductibles et une trace des appels réels.
- ⬜ Vérification des chiffres en code : tout nombre de l'explication doit venir d'un outil.
- ⬜ Contextual grounding check de Bedrock Guardrails (`ApplyGuardrail`).
- ⬜ Encadré d'actualité avec Nova Web Grounding (régions américaines seulement, citations obligatoires).
- ⬜ Droits IAM du rôle de tâche du backend : `bedrock:InvokeModel` (ou Converse), `bedrock:ApplyGuardrail`, `bedrock:InvokeTool` pour Web Grounding.

**Critère de sortie :** le scénario de démonstration fonctionne de bout en bout sur l'URL publique, avec la trace et l'appel Bedrock visibles.

### Phase 7 : remise et sauvegarde ⬜
- ⬜ Enregistrer la vidéo d'environ cinq minutes pendant que le compte fonctionne.
- ⬜ Mettre à jour `ARCHITECTURE.md` et les README (obligation du fichier `AGENTS.md` quand le fonctionnement change).
- ⬜ Rédiger la documentation technique et la fiche d'une page avec le même cas que le prototype.
- ⬜ Pousser le code sur GitHub avant dimanche 23 h 59. Garder `.env.local` hors de Git.
- ⬜ Sauvegarder hors d'AWS : code, vidéo, secrets (gestionnaire de mots de passe), configuration des services.

## 3. Ordre et temps estimé

| Ordre | Phase | Durée indicative | Dépend de |
|---|---|---|---|
| 1 | 0 : vérifications | 15 min | Rien |
| 2 | 2 : Dockerfiles | 30 min | Rien |
| 3 | 3 : ECR et CodeBuild | 45 min | 0, 2 |
| 4 | 4 : secrets | 20 min | 0 |
| 5 | 5 : services ECS | 45 min | 3, 4 |
| 6 | 6 : agent Bedrock | plusieurs heures | 0, idéalement 5 |
| 7 | 7 : remise | 2 à 3 heures | Tout |

Ces durées sont des estimations, pas des mesures. Si le déploiement bloque, la phase 6 passe avant : l'agent et Bedrock comptent pour la note, l'hébergement non. L'application peut aussi être démontrée en local pendant la vidéo.

## 4. Risques

| Risque | Parade |
|---|---|
| Droits IAM insuffisants (ECS Express, CodeBuild, rôles) | Phase 0 en lecture d'abord, demander un mentor AWS |
| Construction des images impossible sans Docker | CodeBuild, ou construction sur une autre machine |
| `BETTER_AUTH_URL` différent de l'URL publique | Mise à jour et redéploiement après la création du service |
| Frontend inaccessible derrière le proxy de l'IDE | Utiliser l'URL publique d'ECS, pas le lien `/proxy/3000` |
| Base ouverte à tout Internet | Restreindre aux services ECS après la démonstration |
| Secret dans Git ou dans une image | `.dockerignore`, `.gitignore` (`.env*`), Secrets Manager |
| Compte supprimé lundi | Sauvegarder code, vidéo et secrets dimanche |
| Coût imprévu (Fargate, équilibreur, Bedrock, Web Grounding) | Une seule tâche par service, arrêter les services après la remise |

## 5. Décisions à prendre

1. Déployer l'application avant la couche d'agent, ou l'inverse (voir section 3).
2. Garder ou restreindre l'ouverture du port 5432 sur le groupe de sécurité d'Aurora.
3. Backend public (plus simple) ou privé (plus propre, demande plus de configuration réseau).
4. Branche Git pour les Dockerfiles et les scripts de déploiement.
