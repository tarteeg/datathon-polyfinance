# AlphaForge AI — Rapport d’équipe du Datathon PolyFinances 2026

**Le défi.** Concevoir un agent qui s’appuie sur des données financières publiques pour éclairer une décision d’investissement précise. La personne qui utilise le prototype doit pouvoir comprendre ce que l’agent a vérifié, pourquoi la conclusion varie selon le profil fictif choisi et sur quelles données elle repose. La Banque Nationale, AWS et PolyFinances laissent aux équipes le choix du cas d’usage, des actifs, des modèles et de l’essentiel de l’architecture. (Photos 5785, 5786 et 5795.)

**Condition d’admissibilité.** Au moins un service AWS doit contribuer au fonctionnement de la solution, et l’équipe doit pouvoir le démontrer. Sans intégration effective, le projet est inadmissible à l’évaluation finale. La qualité de cette intégration compte également pour **15 % de la note**. Les tutoriels de l’atelier demeurent facultatifs. (Photos 5790 et 5793, présentation à 09:58.)

**Remise.** L’atelier fixe la remise du dépôt GitHub et de l’application au **dimanche 15 novembre 2026 à 23 h 59**. La présentation demande quatre livrables à préparer pour la remise : **un prototype accompagné de son code, une vidéo d’environ cinq minutes, une documentation technique et une fiche synthèse d’une page**. Les documents fournis ne précisent ni échéance distincte ni lieu de dépôt particulier pour les trois derniers. [Horaire de l’atelier](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop)

## Horaire et sauvegarde du projet

| Date et heure en 2026 | Étape |
|---|---|
| Samedi 14 novembre, en matinée | Ouverture des comptes AWS des équipes. |
| Samedi 14 novembre, à midi | Début du Datathon. |
| Dimanche 15 novembre, à 16 h | Fin de l’événement sur place. |
| Dimanche 15 novembre, à 23 h 59 | Date limite de remise du dépôt GitHub et de l’application. |
| Lundi 16 novembre | Le guide de nettoyage annonce la suppression définitive des comptes et des données à **13 h 59**. Si l’on ajoute les 72 heures de durée à l’heure de début affichée dans le tableau de bord, on obtient **11 h 30**, à fuseau horaire égal. |

L’horaire de l’atelier ne précise pas le fuseau horaire. Pour éviter de dépendre de l’heure de fermeture du lundi, visez la remise du dimanche pour terminer les sauvegardes. Conservez hors du compte temporaire l’enregistrement de la démonstration, le code, les carnets de calcul, les données dont la conservation est permise, les instructions données aux modèles, les définitions des outils et la configuration AWS. Un fichier copié dans CloudShell se trouve toujours dans l’environnement de l’événement. [Notes sur l’horaire et le tableau de bord](POLYFINANCES-WORKSHOP.md) · [Guide de nettoyage et d’exportation](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/90-cleanup)

## Ce que le jury évalue

Comparer des actifs, analyser un scénario, expliquer un risque ou proposer une répartition fictive du portefeuille sont des cas d’usage possibles. L’équipe peut aussi concevoir une autre aide à la décision dont elle peut justifier les résultats. Un seul actif suffit si son analyse permet de répondre à la question. La performance historique d’un portefeuille simulé ne fait pas l’objet d’un critère distinct. Le jury évalue ce que la solution permet de comprendre, la qualité des données à l’appui et la démonstration qu’en fait l’équipe. (Photos 5785, 5786 et 5793.)

| Critère | Poids | Éléments évalués | Suggestion pour la démonstration |
|---|---:|---|---|
| Solution | 20 % | Pertinence, innovation, créativité et prototype fonctionnel | Formulez la décision en une phrase. Exécutez le cas et montrez ce que l’utilisateur peut désormais comprendre. |
| Agentique | 20 % | Architecture et explicabilité | Montrez quel outil l’agent a appelé, ce qu’il a obtenu et quelle vérification a influencé sa réponse. |
| Données | 20 % | Rigueur, validation et visualisation | Partez d’une source datée, refaites un calcul et retrouvez le chiffre sur un graphique légendé. Montrez une vérification capable de détecter une erreur. |
| UX/UI | 10 % | Intuitivité, ergonomie et clarté | Une personne qui découvre l’interface peut-elle changer de profil et repérer la contrainte qui a changé sans explication orale ? |
| AWS | 15 % | Qualité de l’intégration | Exécutez la fonctionnalité qui dépend d’AWS. Montrez ce que le service reçoit, ce qu’il renvoie et où il intervient. |
| Pitch | 15 % | Présentation, valeur d’affaires et marketing | Identifiez le public visé, la décision qui lui pose problème et la raison qu’il aurait de réutiliser l’outil. |

## Trois personas pour éprouver la solution

L’atelier présente de grandes catégories de risque. La présentation donne à chaque investisseur fictif un objectif, un horizon de placement et des préférences parfois en tension. Les durées ci-dessous correspondent à **l’horizon de placement**. Les organisateurs conseillent de montrer **au moins deux situations contrastées**. Tester les trois profils permet à l’équipe de vérifier que sa méthode d’analyse s’adapte à chacun. (Photo 5787, présentation de 00:21 à 03:44.)

| Persona | Situation présentée | Ce que la solution pourrait démontrer |
|---|---|---|
| **Amira, 26 ans** | Tolérance au risque élevée, horizon de **15 ans et plus**. Elle s’intéresse à la croissance, aux technologies émergentes et aux cryptoactifs, tout en tenant à la diversification. | Si un placement envisagé renforce une exposition déjà importante, chiffrez cette concentration et expliquez pourquoi la diversification reste pertinente pour elle. |
| **Mateo, 41 ans** | Risque modéré, horizon de **8 à 12 ans**. Il recherche un équilibre entre croissance et stabilité et accorde une importance explicite aux critères environnementaux, sociaux et de gouvernance (ESG). | Identifiez le critère ESG pertinent et la donnée qui permet de l’évaluer. S’il manque une information, précisez quelle partie de la comparaison demeure incertaine. |
| **Robert, 59 ans** | Risque faible à modéré, horizon de **3 à 5 ans**. Il privilégie la préservation du capital et la stabilité, mais s’intéresse parfois à une occasion très médiatisée. | Reconnaissez ce qui a retenu son attention, puis expliquez en termes simples en quoi le risque de perte pourrait entrer en conflit avec son horizon. |

**Pour rendre l’adaptation visible**, gardez le même actif, la même date et les mêmes données de marché lorsque vous changez de persona. Les faits historiques restent identiques. Faites ressortir la contrainte qui change leur interprétation. Le modèle doit pouvoir expliquer cette différence à partir des mêmes observations.

## Ce que signifient « agentique » et « auto-explicative »

La présentation autorise un agent unique, plusieurs agents ou des agents spécialisés. La conférencière évoque aussi la possibilité d’un agent qui confronte les conclusions des autres. L’équipe doit pouvoir expliquer pourquoi chaque agent existe, ce qu’il fait et comment son résultat aide l’utilisateur. (Photo 5788, présentation de 04:33 à 06:45.)

| Terme employé par les organisateurs | Comportement observable |
|---|---|
| **Mobiliser** | Sélectionner les données publiques, les outils, les modèles ou les résultats de recherche pertinents et y accéder. |
| **Coordonner** | Ordonner les tâches et les contrôles. Avant de comparer deux actifs, vérifier par exemple que les séries couvrent la même période. |
| **Adapter** | Déterminer quelles observations comptent à la lumière des objectifs, de l’horizon, des préférences et des contraintes du profil. |
| **Expliquer** | Relier la conclusion à ses sources, à ses hypothèses et aux facteurs déterminants. Préciser les incertitudes et les limites. |

Une mise en œuvre possible consiste à donner à un seul agent utilisant Amazon Bedrock deux types d’outils : l’un récupère des observations datées, l’autre effectue des calculs reproductibles. Le code peut calculer les rendements, les baisses depuis un sommet ou l’exposition sectorielle. Le modèle reçoit les valeurs obtenues et leurs sources pour les expliquer. Conservez une trace des appels réellement effectués et de leurs résultats, limitez le nombre de tentatives et prévoyez une condition d’arrêt. Ce relevé permet de vérifier l’explication en la comparant au déroulement réel de l’analyse. [Atelier sur les agents](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/35-agents)

## Choix des données et utilisation responsable

Le jeu de données de départ est facultatif. Vous pouvez le compléter ou le remplacer en documentant vos choix. Pour chaque donnée, répondez à quatre questions : **Pourquoi est-elle pertinente ? D’où vient-elle ? Comment a-t-elle été transformée ? Que permet-elle de conclure ?** Consignez la source, la date d’observation, la date de publication s’il y a lieu, la devise ou l’unité et les lacunes de couverture. (Photo 5789, présentation de 07:27 à 09:33.)

| Besoin d’analyse | Sources possibles citées dans l’atelier | Point à vérifier |
|---|---|---|
| Cours, volumes, rendements, dividendes et fractionnements d’actions | Yahoo Finance via yfinance | Précisez si les cours sont ajustés, alignez les dates d’observation et vérifiez les droits de redistribution. |
| Revenus, bénéfices, dette, trésorerie et événements d’entreprise | SEC EDGAR, SEDAR+, rapports destinés aux investisseurs | Pour reconstituer une décision passée, utilisez la date à laquelle le document est devenu public. |
| Concentration, chevauchement sectoriel et frais | Composition et fiches des fonds négociés en bourse (FNB), publiées par les émetteurs | Datez la composition du fonds et repérez la part non divulguée avant de chiffrer le chevauchement. |
| Taux, inflation, emploi et devises | API Valet de la Banque du Canada, FRED, Statistique Canada | Tenez compte des devises, des délais de publication et des calendriers de jours ouvrables. |
| Actualités, ESG, secteurs et cryptoactifs | Articles publics datés, publications des émetteurs et séries publiques pertinentes | Définissez ce que mesure le signal. Un titre de presse ne suffit pas pour établir une causalité ou le respect d’un critère ESG. |
| Contraintes de l’investisseur | Personas fictifs fournis et paramètres de scénario clairement identifiés | Précisez quelles préférences viennent des organisateurs et quels seuils l’équipe a choisis pour la démonstration. |

Le cadre autorise **la simulation uniquement**. Il exclut les transactions réelles, les connexions à un compte de courtage, les conseils financiers personnalisés, les renseignements personnels et les données bancaires confidentielles. Dans l’interface, indiquez au moment d’afficher le résultat ce qui relève des faits observés, des hypothèses et du scénario fictif. Signalez toute incertitude importante. Si l’information disponible ne permet pas de trancher, précisez ce qui manque. La présentation demande des explications concises, vérifiables et fidèles aux actions observables. Elle met expressément en garde contre les justifications inventées après coup. (Photo 5794, présentation de 17:49 à 19:40.) [Guide des données financières](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/50-datasets) · [Règles d’utilisation responsable](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/fr-FR/workshop/20-setup/10-responsible-use)

## Exemple de démonstration chiffrée

**Proposition pour l’équipe.** « Que change le transfert de 10 % d’un portefeuille diversifié vers un fonds technologique qui fait la manchette ? » L’agent a une tâche précise et l’utilisateur peut en observer les conséquences. Le transfert de 10 % est une hypothèse de simulation. L’équipe reste libre de choisir une autre question ou un autre actif.

1. **Formuler.** Définissez le changement envisagé, le placement dont le poids serait réduit, la date d’observation et la devise du portefeuille. Précisez ce que l’utilisateur devrait apprendre.
2. **Concevoir.** À partir de la composition datée des fonds, calculez l’exposition commune au secteur technologique. Supposons que le portefeuille soit initialement investi à 20 % en technologie. Le fonds dont on réduit le poids détient 20 % de titres technologiques et le nouveau fonds en détient 80 %. En transférant 10 % du portefeuille de l’un à l’autre, l’exposition totale passe à **26 %**, soit 20 % + 10 % × (80 % − 20 %). Ces chiffres fictifs fournissent aussi un cas de test.
3. **Contextualiser.** Pour Amira, montrez ce que le transfert change dans l’exposition aux titres de croissance et dans la concentration. Pour Robert, expliquez pourquoi la couverture médiatique renseigne peu sur la préservation du capital à trois ou cinq ans. Pour Mateo, montrez quelle information ESG l’émetteur publie et ce qu’elle couvre. Dans chaque cas, identifiez la contrainte qui influe sur l’interprétation.
4. **Éprouver.** Ramenez le transfert à 5 %. Avec les mêmes hypothèses, l’exposition attendue est de **23 %**. Retirez ensuite un fichier de composition et vérifiez que l’application signale la donnée manquante. Changez enfin de persona et vérifiez que les expositions calculées restent identiques.
5. **Expliquer.** Affichez l’exposition avant et après le transfert, les dates des sources et l’hypothèse d’une composition constante des fonds. Précisez que le poids d’un secteur, à lui seul, ne permet pas de prévoir les pertes futures. Donnez accès aux éléments qui soutiennent la réponse.

Ces étapes reprennent la méthode proposée par les organisateurs. Le scénario et les vérifications chiffrées sont des suggestions pour l’équipe. (Photo 5791.)

## Démontrer le rôle d’AWS dans un prototype réalisé en une fin de semaine

Utilisez la région de l’événement, **us-east-1**. Dans l’exemple ci-dessus, l’application pourrait transmettre à **Amazon Bedrock** les expositions calculées, les contraintes du persona et les références des sources, puis afficher l’explication produite. Pendant la démonstration, modifiez une hypothèse et montrez le nouveau résultat de l’outil ainsi que la réponse produite avec Bedrock. Un schéma simple peut situer cet appel dans l’architecture. La conférencière invite les équipes à consulter les mentors AWS pour toute question d’accès ou de choix de service. (Photo 5790, présentation de 09:58 à 11:12.)

Un compartiment S3 privé peut servir à partager des versions datées des données. Lambda peut exposer une fonction que l’application appelle. Une base de connaissances Bedrock peut être utile si une conclusion dépend d’un passage à retrouver dans un rapport. SageMaker et JupyterLab permettent aussi l’analyse exploratoire. Pour chaque service retenu, expliquez son rôle et ses permissions d’accès. Gardez les identifiants hors de Git et vérifiez les droits de redistribution des données que vous partagez. Le répertoire contient les liens vers les 35 pages de l’atelier, dont les guides sur le premier appel Bedrock, Strands, les garde-fous, les données et l’exportation. [Répertoire de l’atelier](POLYFINANCES-WORKSHOP.md)

## Les quatre livrables

| Livrable | Attentes des organisateurs | Vérification proposée |
|---|---|---|
| **1. Prototype et code** | Un cas d’utilisation complet et démontrable, dont le résultat est expliqué en termes accessibles. Un dépôt et un README décrivant les dépendances, les données, la configuration et les étapes de reproduction. | Un coéquipier repart d’une copie neuve du dépôt, suit le README, exécute l’exemple et retrouve les données qui justifient le résultat. |
| **2. Vidéo** | **Environ cinq minutes**, à titre indicatif. Montrer le problème, le rôle des agents, les données, le résultat et son explication de bout en bout. | Après un seul visionnement, une personne peut-elle nommer la décision, situer l’intervention d’AWS et expliquer pourquoi le deuxième cas mène à une interprétation différente ? |
| **3. Documentation** | Architecture, agents, méthodes, sources, hypothèses, explicabilité, validations, limites et pistes d’amélioration. | Remontez d’une affirmation affichée jusqu’au calcul et à sa source. Consignez le résultat d’une validation effectuée et une limite observée. |
| **4. Fiche synthèse** | Une page présentant le problème, la démarche, son originalité, les données, l’explicabilité et la valeur pour l’utilisateur. | Reprenez le cas du prototype. Intégrez un résultat ou une illustration que le lecteur peut comprendre sans ouvrir l’application. |

La photo 5792 confirme la durée indicative de la vidéo, difficile à distinguer à 15:24 dans l’enregistrement. Racontez le même cas dans les quatre livrables. Reprenez le même actif, la même date d’observation, les mêmes hypothèses et le même résultat afin que le jury puisse comparer le discours de l’équipe au comportement du prototype.

**Découpage suggéré pour cinq minutes.** Consacrez 30 secondes à l’utilisateur et à sa décision, 90 secondes au premier cas, une minute au changement de persona, puis une minute aux sources, aux calculs et à l’appel AWS. Dans la dernière minute, montrez l’effet d’une hypothèse modifiée, une limite de l’analyse et ce que l’utilisateur en retire. Enregistrez le fonctionnement réel du prototype pendant que le compte temporaire est actif.

## Vérifications avant la remise

- [ ] Le prototype mène à terme une analyse d’investissement simulée et présente les éléments qui étayent sa conclusion.
- [ ] AWS intervient dans une étape que l’équipe peut démontrer et dont elle peut justifier le choix.
- [ ] La démonstration présente des situations contrastées et identifie la contrainte qui change l’interprétation.
- [ ] Chaque chiffre est daté, sourcé et accompagné de son unité ou de sa devise. Les calculs sont reproductibles et les valeurs hypothétiques sont signalées.
- [ ] L’équipe a testé un changement d’hypothèse et un cas de donnée manquante. Elle peut décrire les résultats observés.
- [ ] Le jury peut accéder au dépôt, à l’application, à la vidéo, à la documentation et à la fiche synthèse. Un coéquipier a vérifié les liens.
- [ ] Le code, la configuration, les instructions données aux modèles et les données autorisées sont sauvegardés hors d’AWS. Pour les données à diffusion restreinte, la documentation explique comment les obtenir lorsque c’est permis.

## Sources

Ce rapport s’appuie sur les 11 photos de diapositives fournies, la présentation orale en français et l’atelier AWS consulté. Les numéros renvoient aux noms des fichiers photo. Les photos 5785 et 5786 présentent la raison d’être et l’énoncé du défi. Les suivantes couvrent les personas (5787), les agents (5788), les données (5789), l’admissibilité liée à AWS (5790), la méthode proposée (5791), les livrables (5792), la grille d’évaluation (5793), le cadre responsable (5794) et les conseils de clôture (5795). Les diapositives confirment les caractéristiques exactes des personas, les pondérations et la durée indicative de la vidéo lorsque la transcription automatique est ambiguë. L’énoncé complet et les précisions ultérieures des organisateurs sur place font foi. [Transcription française horodatée](TRANSCRIPTION-2026-11-14.md) · [Notes de l’atelier AWS et liens vers les sources](POLYFINANCES-WORKSHOP.md)
