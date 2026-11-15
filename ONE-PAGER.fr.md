# PolyFinances AlphaForge : RiskRipple

**Une alerte réglementaire ou un scénario d'investissement, expliqué avec preuves, pour chaque profil d'investisseur.**

*Brouillon d'une page. Simulation seulement : aucune transaction réelle, aucun conseil financier. Les crochets sont à remplir avec le cas filmé dans la vidéo.*

## Le problème

Quand une sanction, une réglementation, un tarif douanier ou un choc macro fait la une, l'investisseur veut savoir lesquels de ses titres sont exposés. L'effet dépasse rarement l'entreprise nommée : il passe par les fournisseurs, les matériaux et les clients. Les assistants IA répondent vite, mais ils énoncent parfois des chiffres qu'aucune source ne confirme, et ils ne disent pas ce qu'ils ont vérifié.

## Notre approche

**Le code calcule, le modèle explique, un contrôle vérifie.**

- **Veille.** RiskRipple surveille les sources publiques (sanctions OFAC et Affaires mondiales Canada, réglementation, séries FRED, dépôts SEC, nouvelles) et compare chaque document à chaque portefeuille enregistré.
- **Enquête multi-agents.** Quatre agents aux rôles distincts (veilleur réglementaire, enquêteur réglementaire, cartographe d'exposition, enquêteur d'ondulation) suivent le chemin événement → entreprise → portefeuille. L'exposition est un **poids du portefeuille**, pas une perte en dollars inventée.
- **Adaptation.** Amira, Mateo et Robert reçoivent les mêmes faits. Seule la lecture change selon leur risque, leur horizon et leurs préférences.
- **Vérification.** Après chaque réponse, un contrôle sans modèle cherche chaque chiffre dans les résultats des outils. Un second passage repère les causes non prouvées, le ton de conseil et les trous de données. Le verdict s'affiche dans la chronologie.

## AWS au cœur de la solution

| Service | Rôle |
|---|---|
| Amazon Bedrock (Converse, appel d'outils) | Chat, recommandations d'alertes, contrôle des affirmations |
| Strands Agents sur Bedrock | Enquête multi-agents |
| Bedrock Knowledge Base | Passages de preuve dans les rapports déposés, recherche hybride |
| Bedrock Guardrails | Refus des conseils personnalisés et des transactions, blocage des identités, filtre des attaques |
| Aurora PostgreSQL | Comptes, portefeuilles, historique, alertes |
| ECS Express Mode, ECR, CodeBuild, Secrets Manager, CloudWatch | Déploiement à chaque push sur `main` |

## Résultat sur un cas

**Cas : [décrire le cas filmé, par exemple le transfert de 10 % de [FONDS A] vers [FONDS B], ou la sanction X].**
L'exposition technologique passe de **[20 %]** à **[26 %]**, calculée par `simulate_transfer`, avec les taux de la Banque du Canada du **[date]**. Pour Amira, une concentration plus forte reste acceptable sur quinze ans. Pour Robert, la baisse maximale historique de **[Y %]** entre en conflit avec son horizon de trois à cinq ans. Les chiffres sont identiques, la lecture change. Verdict de vérification : **[validé, N chiffres contrôlés]**.

*Insérer ici une capture de la réponse avec la chronologie des outils.*

## Valeur pour l'utilisateur

- **Savoir quoi regarder.** Chaque chiffre a une source, une date et un calcul reproductible.
- **Gagner du temps.** Un balayage automatique remplace la lecture manuelle des documents réglementaires, avec un cache et un rafraîchissement en arrière-plan.
- **Moins de fausses alertes.** Une alerte n'est confirmée qu'avec une preuve d'exposition chiffrée.
- **Une lecture adaptée.** Même base factuelle, interprétation selon le profil.

## Originalité

Un contrôle des chiffres à deux étages visible dans l'interface, une enquête par chaînes de fournisseurs plutôt qu'une simple recherche de mots-clés, et une conformité intégrée dès le départ (simulation seulement, garde-fou versionné dans le dépôt).

## Limites et suite

Les fonds sont supposés à composition constante, l'historique ne prédit pas l'avenir, et la vérification est un avertissement. Prochaines étapes : plus de questions de test en français et en anglais, plus de sources de sanctions, le volet ESG pour Mateo, un agent débat et des contrôles exécutés à chaque déploiement.

*Équipe : Sami Mostfa, Pacifique Uwamukiza, Benjamin Ollomo, Mohamed Oubagha. Dépôt : [URL GitHub]. Application : [URL publique].*
