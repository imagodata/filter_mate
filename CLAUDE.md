# Filter Mate - Agent Instructions

## Scope
Plugin QGIS de filtrage avancé. Tu es l'agent dédié à ce projet.

## Conventions
- Python 3.10+, PyQGIS API
- Tests dans /tests/
- Point d'entrée: filter_mate.py
- Style: PEP 8, docstrings Google

## Permissions
- Lire/modifier tout le code du projet
- Lancer les tests
- Ne PAS modifier les fichiers de config QGIS système

## Mémoire
Maintiens .claude/memory.md avec les décisions importantes et les patterns récurrents.

## Serena MCP - Auto-activation
At the start of each session, activate the project with activate_project using name "filter_mate".
This gives you LSP-powered code intelligence on /project.
