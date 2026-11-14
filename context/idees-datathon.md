# Idées pour gagner le défi AlphaForge AI

Version 2, réécrite le 14 novembre 2026 à partir de `defi-datathon.md` (énoncé, grille, personas, livrables), `aide-memoire.md` (AWS) et `notes.md`. Elle remplace la version précédente, qui reposait sur des personas inexacts (Prudent, Équilibré, Audacieux) et sur des hypothèses non confirmées. L'énoncé officiel fait foi.

## Ce que le jury récompense

| Critère | Poids | Ce qui fait gagner des points | Où on le gagne dans notre plan |
|-|-|-|-|
| Solution | 20 % | Une décision formulée en une phrase, un prototype qui fonctionne de bout en bout | Idée centrale, section suivante |
| Agentique | 20 % | Chaque agent a une raison d'exister; on voit quel outil a été appelé et quelle vérification a influencé la réponse | Panneau de trace + agent vérificateur |
| Données | 20 % | Source datée, calcul refait, chiffre retrouvé sur un graphique légendé, vérification capable de détecter une erreur | Cas de test chiffrés + détection de donnée manquante |
| UX/UI | 10 % | Changer de profil et voir la contrainte qui change, sans explication orale | Sélecteur de persona et bandeau « ce qui a changé » |
| AWS | 15 % | Une fonctionnalité qui dépend d'AWS, avec ce que le service reçoit et renvoie | Amazon Bedrock visible dans l'interface |
| Pitch | 15 % | Public visé, décision qui lui pose problème, raison de réutiliser l'outil | Vidéo de 5 minutes et fiche d'une page |

Ce qui ne rapporte rien : la performance historique d'un portefeuille simulé, le nombre d'agents, les architectures spectaculaires impossibles à expliquer. Condition éliminatoire : au moins un service AWS doit contribuer au fonctionnement et se démontrer.

Principe directeur : un seul cas, très bien raconté et vérifiable, vaut mieux que cinq fonctionnalités survolées. Le même actif, la même date et les mêmes hypothèses doivent apparaître dans le prototype, la vidéo, la documentation et la fiche.

## Idée centrale : « Que change ce transfert pour moi ? »

**Décision en une phrase :** « Que change le transfert de 10 % de mon portefeuille diversifié vers un fonds technologique médiatisé, selon que je suis Amira, Mateo ou Robert ? » C'est le scénario que les organisateurs proposent eux-mêmes en exemple, donc le jury le comprendra tout de suite, et on peut le rendre plus fin qu'un simple exemple.

**Comment ça marche :**
1. L'utilisateur choisit un persona, un portefeuille (celui du compte, ou un portefeuille d'exemple) et un changement (ex. 10 % vers un FNB technologique).
2. Des outils Python calculent, avec du code reproductible : exposition sectorielle avant et après, concentration, rendement total, volatilité, baisse maximale depuis un sommet, sur une période et une devise explicites.
3. Un agent Strands appelé par FastAPI et propulsé par Amazon Bedrock reçoit ces valeurs avec leurs sources et dates, puis explique en langage simple ce que le changement signifie pour ce persona.
4. Un agent vérificateur relit l'explication et rejette tout chiffre qui ne vient pas d'un appel d'outil.
5. L'interface montre la réponse, un graphique avec légende, le panneau de trace (outils appelés, entrées, sorties) et l'étiquette fait, hypothèse ou scénario sur chaque chiffre.

**Pourquoi un seul agent plus un vérificateur :** chaque agent a un rôle clair (calculer et expliquer, puis contrôler). Cela répond directement à « pourquoi cet agent existe-t-il ? » sans complexité décorative.

### Adaptation aux trois personas (même faits, contraintes différentes)

À garder identiques : actif, date, données de marché. Seule la contrainte qui interprète les faits change. Les seuils ci-dessous sont des choix de l'équipe, à annoncer comme tels dans l'interface.

| Persona | Contrainte qui change l'interprétation | Ce que l'outil calcule et affiche |
|-|-|-|
| Amira, 26 ans, horizon 15 ans et plus | Risque élevé, mais diversification voulue | Poids de la technologie avant et après, concentration, et pourquoi la diversification reste utile malgré la tolérance au risque |
| Mateo, 41 ans, horizon 8 à 12 ans, ESG | Critères ESG explicites | Le critère ESG pertinent, la donnée qui permet de l'évaluer, et ce qui reste incertain quand elle manque |
| Robert, 59 ans, horizon 3 à 5 ans | Préservation du capital, attrait pour une occasion médiatisée | Baisse maximale historique comparée à son horizon, et pourquoi la couverture médiatique renseigne peu sur la préservation du capital |

Le bandeau « ce qui a changé » compare deux personas côte à côte et surligne la contrainte responsable de la différence. C'est ce qui rapporte les points UX et la minute de démonstration du changement de persona.

### Vérifications chiffrées prêtes pour la démonstration

Ce sont les cas de test des organisateurs, à automatiser en tests unitaires et à montrer dans la vidéo (critère Données) :

- Portefeuille à 20 % de technologie, fonds réduit à 20 % de technologie, nouveau fonds à 80 % : un transfert de 10 % donne **26 %** (20 % + 10 % × (80 % − 20 %)).
- Même cas à 5 % : **23 %**.
- Retirer un fichier de composition : l'application doit signaler la donnée manquante au lieu d'inventer.
- Changer de persona : les expositions calculées doivent rester identiques.

### Ce qui distingue notre solution

- **Détection d'erreur visible :** une vérification qui échoue en direct (donnée manquante, séries sur des périodes différentes) et que l'interface signale.
- **Coordonner :** avant toute comparaison, un contrôle vérifie que les séries couvrent la même période et la même devise.
- **Honnêteté sur l'incertitude :** quand l'information ne permet pas de trancher, la réponse dit ce qui manque. Le rapport demande explicitement d'éviter les justifications inventées après coup.
- **Trace réelle :** le panneau de trace est généré par les appels réellement effectués, pas reconstitué par le modèle.
- **Cadre responsable :** la réponse se présente comme une simulation. Guardrails bloque les formulations d'achat ou de vente et le texte affiche ce qui relève des faits, des hypothèses et du scénario.

## Idée secondaire (si le temps le permet) : « Le buzz rapporte-t-il ? »

Réutilise le tableau Discover (StocksFeed) pour Robert et Amira, qui s'intéressent aux occasions médiatisées. L'outil mesure le rendement ajusté à 1, 3 et 5 jours après un pic de mentions, comparé au secteur, à partir de la date de publication de l'article (pas la date de fin de période). L'agent dit combien d'événements ont été observés, la médiane et la dispersion, et conclut honnêtement quand l'effet est trop faible. **Risque :** l'historique de StocksFeed est peut-être court, à vérifier avant d'investir du temps. À abandonner sans regret si l'idée centrale n'est pas terminée.

## Données

| Besoin | Source | Point de vigilance |
|-|-|-|
| Prix, rendements, dividendes | yfinance (déjà dans le backend) | Prix ajusté (`adj_close`), alignement des dates, droits de redistribution |
| Composition et secteurs des FNB | yfinance (à vérifier : données de fonds) ou fiche de l'émetteur | Dater la composition, signaler la part non divulguée |
| ESG pour Mateo | Publications d'émetteurs, données disponibles sur les titres | Probablement incomplet : prévoir et montrer le cas de donnée manquante |
| Actualités | StocksFeed (déjà intégré) | Un titre de presse ne prouve ni causalité ni critère ESG |
| Taux, devises (option) | API Valet de la Banque du Canada | Délais de publication, devises |

Pour chaque donnée : pourquoi elle est pertinente, d'où elle vient, comment elle est transformée, ce qu'elle permet de conclure. Chaque chiffre affiché porte source, date, unité ou devise.

## Intégration AWS

Principe : peu de services, bien démontrés, avec leur rôle et leurs permissions expliqués. Région de l'événement : us-east-1.

| Service | Rôle | Priorité |
|-|-|-|
| Amazon Bedrock | Génère l'explication à partir des valeurs calculées, des contraintes du persona et des références. À montrer en démo : ce que le service reçoit, ce qu'il renvoie, et ce qui change quand on modifie une hypothèse. | Obligatoire |
| Strands Agents | Cadre d'agent dont les outils appellent nos fonctions de calcul et nos routes FastAPI. Nouvelle route `/agent`. | Noyau |
| Guardrails | Bloque les recommandations d'achat ou de vente, répond à « aucun conseil personnalisé ». | Noyau si le temps le permet |
| Aurora PostgreSQL | Déjà en place. Peut stocker scénarios, traces d'appels et personas. | Existant |
| S3 privé | Versions datées des fichiers de composition de fonds (pratique pour le cas de donnée manquante). | Optionnel |
| AgentCore Code Interpreter, Observability, Knowledge Bases, Memory | Utiles mais risquent de coûter trop de temps. À ne tenter qu'après la démo de bout en bout. | Bonus |

Les fonctions de calcul restent en Python local, appelées comme outils par l'agent. L'important est que Bedrock intervienne réellement dans le résultat affiché et que l'équipe puisse le prouver en direct.

## Plan réaliste

Début du Datathon le samedi 14 novembre à midi, remise le dimanche 15 novembre à 23 h 59, fin de l'événement sur place à 16 h. Les comptes AWS sont supprimés le lundi 16 novembre : sauvegarder code, vidéo et notes avant.

**Samedi après-midi**
1. Faire marcher un premier appel Bedrock depuis le backend et un agent Strands avec un seul outil (exposition sectorielle).
2. Écrire les fonctions de calcul avec les tests 26 % et 23 %.
3. Vérifier la disponibilité des compositions de FNB dans yfinance.

**Samedi soir**
4. Route `/agent` : explication par persona, trace des appels, étiquettes fait / hypothèse / scénario.
5. Retirer ou masquer les pages de démonstration héritées du template (pour l'UX).

**Dimanche matin**
6. Interface : sélecteur de persona, graphique légendé, panneau de trace, bandeau « ce qui a changé ».
7. Agent vérificateur et cas de donnée manquante.
8. Figer le scénario de démonstration (actif, date, hypothèses).

**Dimanche après-midi**
9. Enregistrer la vidéo pendant que le compte AWS fonctionne.
10. Rédiger la documentation (architecture, agents, sources, validations, limites) et la fiche d'une page avec le même cas.
11. Faire tester le dépôt par un coéquipier depuis une copie neuve, vérifier les liens, sauvegarder hors d'AWS.

## Livrables et script de la vidéo (environ 5 minutes)

- 30 s : l'utilisateur et sa décision.
- 90 s : premier cas (Amira), de la question à l'explication avec trace.
- 60 s : changement de persona (Robert ou Mateo), la contrainte qui change.
- 60 s : sources, calculs, appel Bedrock visible.
- 60 s : une hypothèse modifiée (10 % à 5 %), la limite de l'analyse, ce que l'utilisateur en retire.

Documentation et fiche : reprendre le même actif, la même date, les mêmes chiffres. Dans la documentation, remonter d'une affirmation affichée jusqu'au calcul et à sa source, et noter une validation effectuée et une limite observée.

## Pièges à éviter

- Faire des conseils d'achat ou de vente : simulation uniquement.
- Laisser le modèle inventer un chiffre : tout nombre vient d'un outil.
- Comparer des séries de périodes ou de devises différentes sans le dire.
- Utiliser le prix brut au lieu du prix ajusté, ou la date de fin de période au lieu de la date de publication.
- Annoncer un service AWS qu'on ne peut pas démontrer.
- Multiplier les fonctionnalités : couper dès que la démonstration de bout en bout est menacée.

## Références

- AWS, recherche d'investissement avec Strands sur AgentCore: https://aws.amazon.com/blogs/industries/automate-investment-research-using-strands-agents-on-bedrock-agentcore/
- AWS, Heurist Finance sur AgentCore: https://aws.amazon.com/blogs/machine-learning/how-heurist-finance-built-an-ai-native-investment-workbench-on-amazon-bedrock-agentcore/
- FinRobot: https://arxiv.org/html/2405.14767v1
- TradingAgents: https://huggingface.co/papers/2412.20138.md
- Atelier AWS sur les agents: https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents
