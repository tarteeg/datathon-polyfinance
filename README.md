# Datathon PolyFinances 2026 : AlphaForge AI

Projet d'équipe pour le Datathon PolyFinances 2026, proposé avec la Banque Nationale et propulsé par AWS. Le défi AlphaForge AI demande de concevoir un outil qui utilise l'IA générative, les agents et des données financières publiques pour éclairer une décision d'investissement, selon trois personas fictifs : Prudent, Équilibré et Audacieux.

> État : le projet n'est pas commencé. Ce README sera complété au fil du développement.

## Contraintes du défi

- Simulation uniquement : aucune transaction réelle, et l'outil ne se présente pas comme un conseil financier personnalisé.
- Démarche avant performance : le jury valorise une démarche crédible et bien démontrée, pas le meilleur rendement passé.
- Traçabilité : chaque donnée cite sa source, sa date et sa devise, et on distingue faits, hypothèses et scénarios.

L'énoncé officiel fait foi et peut être précisé par les organisateurs sur place.

## Approche prévue

Le code calcule, le modèle explique. Rendements, volatilité et corrélations sont calculés avec pandas, puis un modèle de langage les met en contexte à partir de ces chiffres. On utilise les prix ajustés (`adj_close`) et on évite le biais d'anticipation (dates de publication plutôt que dates de fin de trimestre). La décision précise à éclairer et la comparaison de deux personas restent à définir.

## Pile technique envisagée

- Amazon Bedrock pour appeler les modèles (région de Montréal disponible)
- Strands Agents (Python) pour l'agent et ses outils de calcul
- Amazon SageMaker AI (JupyterLab) ou Kiro pour l'analyse
- pandas, NumPy, scikit-learn

Le compte AWS d'équipe est activé le 14 novembre 2026 et supprimé le 16 novembre en fin de journée. Le code doit être sur GitHub avant l'expiration.

## Démarrage

À venir. Prérequis prévus : Python 3.10 ou plus, `pip install strands-agents`, et une clé API Bedrock dans la variable d'environnement `AWS_BEARER_TOKEN_BEDROCK`.

## Équipe et licence

Membres de l'équipe :

- Sami Mostfa
- Pacifique Uwamukiza
- Benjamin Ollomo
- Mohamed Oubagha

