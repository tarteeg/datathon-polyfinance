# L'IA chez AWS : votre aide-mémoire

Polyfinances, Datathon 2026. Le défi, votre compte AWS d'équipe, deux chemins pour analyser et comment continuer.

Le Datathon PolyFinances, défi proposé avec la Banque Nationale et propulsé par AWS, est l'occasion de travailler en équipe sur un vrai problème financier et d'apprendre comment l'intelligence artificielle, et en particulier l'**IA générative et les agents**, peut éclairer une décision d'investissement.

Public cible : les participants de tous les programmes. Il est utile d'avoir une ou deux personnes qui programment dans l'équipe, mais un assistant IA peut écrire le code avec vous.

## 1. Le défi en bref

Le défi **AlphaForge AI** demande de concevoir une solution originale qui utilise l'IA et des **données financières publiques** pour appuyer l'analyse ou la décision d'investissement, selon trois personas d'investisseurs fictifs : Prudent, Équilibré et Audacieux. Vous choisissez librement les actifs.

L'énoncé officiel fait foi, et les organisateurs peuvent le préciser ou le modifier sur place. Ce qui suit vient de l'énoncé et reste un repère :

- **Simulation uniquement** : aucune transaction réelle, et l'outil ne se présente pas comme un conseil financier personnalisé.
- **Démarche avant performance** : le jury valorise une démarche crédible, utile et bien démontrée, pas le meilleur rendement passé ni le nombre d'agents.
- **Traçabilité** : citez la source, la date et la devise de chaque donnée, et distinguez les faits, les hypothèses et les scénarios.

## 2. Ce qui fait un projet solide

Le choix des technologies est la partie facile. D'un point de vue technique, voici ce qui distingue un projet qui convainc :

- **Partez d'une décision précise.** Un investisseur prudent qui se demande si un FNB obligataire réduit vraiment son risque. Une investisseuse audacieuse qui compare deux actions technologiques. L'IA générative convainc quand elle éclaire une décision réelle.
- **Calculez avec du code, expliquez avec le modèle.** Rendements, volatilité et corrélations se calculent avec pandas. Le modèle explique et met en contexte, à partir de ces chiffres.
- **Prenez la confiance au sérieux.** Une solution qui cite ses sources, montre son raisonnement et dit quand elle ne sait pas se démarque. Dites-le dans votre présentation.
- **Montrez deux personas.** Comparer ce que votre outil répond à deux profils différents illustre son adaptabilité en une minute de démo.

## 3. Votre compte AWS d'équipe

Un seul compte AWS par équipe, activé le samedi 14 novembre au matin. Tous les services AWS sont inclus.

1. Le code d'accès vous sera envoyé par courriel avant le Datathon. Partagez-le dans votre équipe.
2. Allez à catalog.workshops.aws/join
3. Entrez le code d'accès, puis connectez-vous avec votre courriel.
4. Dans le menu de gauche : Open AWS console.

Règles du jeu : compte valide jusqu'au lundi 16 novembre, en fin de journée (heure exacte précisée avec le code), puis supprimé avec toutes ses données. Avant l'expiration : code sur GitHub, données et notes sur vos portables.

## 4. Deux chemins pour analyser des données

| Chemin | Pour qui | Pour commencer |
|---|---|---|
| Kiro | Vous décrivez l'analyse, Kiro écrit et exécute le code Python. Bon départ si le code vous intimide. | kiro.dev. Pendant le Datathon : environnements Kiro avec crédits fournis. D'ici là : compte AWS Builder ID gratuit, et crédits supplémentaires avec les formations Skill Builder. |
| Notebooks Amazon SageMaker AI | Vous aimez travailler dans Jupyter, cellule par cellule, avec pandas, NumPy ou scikit-learn. | Ouvrir JupyterLab dans SageMaker AI Studio (guide JupyterLab). |
| Dans les deux cas | Pour expliquer, résumer ou raisonner sur du texte, appelez un modèle Bedrock, directement ou avec Strands. | aws.amazon.com/fr/bedrock |

Un bon réflexe, peu importe l'outil : en agentique, un outil peut être une calculatrice. Le code calcule, le modèle explique, et chaque chiffre devrait citer sa source. Vérifiez toujours que les chiffres ont du sens.

## 5. Pièges classiques des données financières

- **Prix brut ou ajusté** : un fractionnement d'actions (split) coupe le prix brut sans que personne perde d'argent. Utilisez le prix ajusté (adj_close) pour comparer le passé au présent.
- **Date de fin ou date de publication** : les résultats d'un trimestre sont publiés des semaines après sa fin. Utiliser une information avant sa publication fausse une simulation.
- **Rendement sans risque** : un rendement seul ne dit rien. Regardez aussi la volatilité et la baisse maximale (ou le ratio de Sharpe).
- **Rendement passé** : ne garantit pas le rendement futur.

## 6. L'IA en finance : exemples publics

| Exemple | Ce que c'est | Lien |
|---|---|---|
| Robinhood | Un agent qui aide les analystes à enquêter sur les crimes financiers, sur Amazon Bedrock. | étude de cas |
| Nasdaq | L'IA générative d'AWS pour la surveillance des marchés, la lutte contre le blanchiment et la fraude. | histoires de clients |
| Bridgewater Associates | Un « associé d'investissement artificiel » bâti avec Amazon Bedrock (entretien vidéo). | vidéo AWS |
| Assistant de recherche en investissement | Architecture de référence AWS : agents Bedrock, Knowledge Bases, outils de portefeuille et de sentiment. | blogue AWS |

## 7. Avant le Datathon : le nouveau Free Tier d'AWS

1. Inscrivez-vous avec Google, GitHub ou Apple. Pour la plupart des nouveaux utilisateurs, aucune carte de crédit pour commencer.
2. Recevez 100 $ US de crédits gratuits et bâtissez tout de suite dans votre premier projet.
3. Collez le prompt de configuration dans un agent de code pour tout brancher.
4. Sur un forfait payant, fixez une limite de dépenses (dès 20 $ US/mois). Une fois atteinte, le projet est mis en pause.

Commencer : aws.amazon.com/fr/free. En savoir plus : le blogue AWS.

## 8. Les services présentés

| Service | Ce que c'est | Lien |
|---|---|---|
| Amazon Bedrock | Plusieurs modèles de pointe (Nova, Claude, Llama, Mistral) via une seule API. Disponible dans la région de Montréal. | aws.amazon.com/fr/bedrock |
| Knowledge Bases | Ancrer les réponses dans vos propres documents. | page du service |
| Guardrails | Sujets interdits, masquage de renseignements personnels, vérification de l'ancrage dans les sources. | page du service |
| Bedrock AgentCore | Exécution, mémoire, passerelle, identité et observabilité pour faire rouler des agents à grande échelle. | page du service |
| AgentCore Code Interpreter | L'agent écrit et exécute du code dans un environnement isolé pour calculer et analyser des données. | documentation |
| Strands Agents | SDK open source (Python ou TypeScript). Un agent fonctionnel en quelques lignes. | strandsagents.com |
| Kiro | IDE agentique d'AWS, piloté par les spécifications. | kiro.dev |

Plonger directement dans les agents : guide de démarrage AgentCore CLI.

## 9. Un agent Strands qui analyse des données

Python 3.10 ou plus, `pip install strands-agents`, et une clé API Bedrock dans `AWS_BEARER_TOKEN_BEDROCK`. Guide : quickstart Strands (Python).

```python
import csv, math, statistics
from strands import Agent, tool

@tool
def volatilite(fichier: str, symbole: str) -> float:
    """Volatilité annualisée (en %) d'un actif, à partir
    de la colonne adj_close d'un fichier de prix."""
    prix = [float(r["adj_close"]) for r in csv.DictReader(open(fichier))
            if r["symbol"] == symbole]
    rend = [b / a - 1 for a, b in zip(prix, prix[1:])]
    return round(statistics.stdev(rend) * math.sqrt(252) * 100, 2)

agent = Agent(tools=[volatilite])
agent("Quelle est la volatilité de TECH.TO dans prices_daily.csv ?")
```

La fonction est la calculatrice de l'agent. La docstring est ce que le modèle lit pour choisir ses outils. Utilisez le prix ajusté (adj_close) plutôt que le prix brut.

## 10. À regarder plus tard

- **[Chaîne]** AWS Developers sur YouTube, votre point de départ : https://www.youtube.com/@awsdevelopers
- **[Strands]** Comment fonctionnent réellement les agents IA (11:06), chapitre 1 du cours gratuit « Building AI Agent Harnesses with Strands Agents ». Piste audio française disponible : https://www.youtube.com/watch?v=ZpXWGjISMs8&list=PLDzwjhH-4yhU&index=1
- **[Kiro]** Kiro en 60 secondes (1:14) : https://www.youtube.com/watch?v=BIuakTF6NMs
- **[Kiro]** Présentation de Kiro, un IDE agentique (2:46) : https://www.youtube.com/watch?v=lYuxyp8lp_U

## 11. Continuer à apprendre, gratuitement

| Ressource | Ce que vous obtenez | Lien |
|---|---|---|
| AWS Student Rewards | Étudiants vérifiés (18 ans et plus) : 12 mois de Skill Builder Premium (900+ cours, labos pratiques), des crédits AWS et un bon d'examen de certification. Sur AWS Builder Center. | builder.aws.com/learn/students |
| AWS Skill Builder | Plus de 1 000 ressources gratuites, plans d'apprentissage sur l'IA générative et les agents, SimuLearn. | skillbuilder.aws |
| Parcours IA générative | Cours sur l'IA générative et Amazon Bedrock (Knowledge Bases, agents, Guardrails). | page du parcours |
| AI Practitioner | Un excellent premier objectif de certification AWS pour votre CV. | page de la certification |

*Transparence IA : Amazon Quick a été utilisé pour accélérer la recherche et la préparation de cette présentation.*

Présenté par Vincent Rioux, architecte de solutions senior, AWS Canada. Questions bienvenues en français ou en anglais.
