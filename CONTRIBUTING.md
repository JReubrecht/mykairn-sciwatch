# Guide de Contribution — myKairn SciWatch

Merci de contribuer à **myKairn SciWatch** ! Ce document décrit les conventions d'architecture, d'ajout de nouveaux profils d'audit ou connecteurs scientifiques, et de validation qualité.

## 1. Philosophie d'Architecture

- **Légèreté & Portabilité (VM Freebox)** : Le cœur d'exécution (`src/mykairn_sciwatch`) est conçu pour tourner avec une empreinte mémoire minimale (< 35 Mo RAM) sur une VM Ubuntu 24.04 (Freebox Delta) sans dépendre de bibliothèques C/C++ lourdes.
- **Modularité Multi-Sujets** : Aucune logique métier propre au trail running n'est codée en dur dans les connecteurs ou le stockage. Tout sujet d'audit est piloté par un profil déclaratif YAML dans `profiles/<slug>.yaml`.
- **Moteur Hybride Déterministe + IA** : Le classement 6D doit toujours produire un résultat complet et pertinent en mode 100% déterministe (`deterministic_ebm`), l'API LLM (`Gemini Flash`, `OpenAI`, `Anthropic`) intervenant comme couche d'enrichissement optionnelle.

## 2. Ajouter un Nouveau Sujet à Auditer

Vous pouvez ajouter un nouveau sujet de trois manières :

1. **Via la CLI** :
   ```bash
   sciwatch profile create \
     --name "Récupération, Sommeil et VFC en Sport d'Endurance" \
     --keywords "heart rate variability, sleep quality, endurance recovery, overreaching" \
     --domain "sports_science" \
     --start-year 2017
   ```
2. **Via le Dashboard Web** (`http://192.168.1.170:8095`) :
   Cliquez sur **« ➕ Nouveau Sujet à Auditer »**, saisissez vos mots-clés et cliquez sur **« Créer & Lancer l'Audit »**.
3. **Manuellement** :
   Dupliquez `profiles/generic_audit_template.yaml` dans `profiles/<votre_sujet>.yaml` et personnalisez les sections `queries`, `themes` et `target_scopes`.

## 3. Lancer la Suite de Tests

Avant toute Pull Request, exécutez la suite de tests unitaires et d'intégration :

```bash
make test
# ou directement :
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py" -v
```
