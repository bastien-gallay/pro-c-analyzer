# Pro*C Static Analyzer

[![CI](https://github.com/USERNAME/proc-analyzer/workflows/CI/badge.svg)](https://github.com/USERNAME/proc-analyzer/actions/workflows/ci.yml)
[![Code Quality](https://github.com/USERNAME/proc-analyzer/workflows/Code%20Quality/badge.svg)](https://github.com/USERNAME/proc-analyzer/actions/workflows/quality.yml)
[![codecov](https://codecov.io/gh/USERNAME/proc-analyzer/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/proc-analyzer)
[![PyPI version](https://badge.fury.io/py/proc-analyzer.svg)](https://badge.fury.io/py/proc-analyzer)

Analyseur statique complet pour code Pro*C (Oracle Embedded SQL), calculant :

- **Complexité cyclomatique** (McCabe) - nombre de chemins indépendants
- **Complexité cognitive** (SonarSource) - difficulté de compréhension
- **Métriques Halstead** - volume, difficulté, effort, bugs estimés
- **TODO/FIXME/HACK/XXX** - avec priorités et localisation
- **Curseurs SQL imbriqués** - anti-pattern de performance
- **Allocations mémoire dangereuses** - fuites, buffer overflow, fonctions dangereuses
- **Inventaire des modules** - basé sur les entêtes de fichiers

## Installation

```bash
pip install -r requirements.txt
```

Ou installation en mode développement :

```bash
pip install -e .
```

## Utilisation

### Analyse complète

```bash
# Fichier unique
proc-analyzer analyze fichier.pc

# Répertoire (récursif)
proc-analyzer analyze ./src --pattern "*.pc"

# Plusieurs patterns séparés par des points-virgules
proc-analyzer analyze ./src --pattern "*.pc;*.sc;*.inc"

# Pattern insensible à la casse (trouve *.pc, *.PC, *.Pc, etc.)
proc-analyzer analyze ./src --ipattern "*.PC;*.SC"

# Mode verbeux (Halstead, détails)
proc-analyzer analyze ./src -v
```

### Commandes spécialisées

```bash
# Liste des TODO/FIXME
proc-analyzer todos ./src

# Analyse de sécurité (mémoire + curseurs)
proc-analyzer security ./src

# Inventaire des modules
proc-analyzer inventory ./src
```

### Export

```bash
# JSON (compact)
proc-analyzer analyze ./src -f json -o rapport.json

# JSON (pretty, avec indentation)
proc-analyzer analyze ./src -f json-pretty -o rapport.json

# HTML (rapport interactif)
proc-analyzer analyze ./src -f html -o rapport.html

# Markdown (compatible GitHub/GitLab)
proc-analyzer analyze ./src -f markdown -o rapport.md

# CSV
proc-analyzer analyze ./src -f csv -o rapport.csv
```

### Options

```
--pattern, -p      Pattern(s) glob, séparés par des points-virgules (ex: "*.pc;*.sc;*.inc") (défaut: *.pc)
--ipattern, -i     Pattern(s) glob insensible à la casse, séparés par des points-virgules (ex: "*.PC;*.SC")
                   (prioritaire sur --pattern si les deux sont fournis)
--format, -f       Format: text, json, json-pretty, html, markdown, csv
                   (défaut: text)
--output, -o       Fichier de sortie (requis pour html/markdown)
--threshold-cyclo  Seuil cyclomatique (défaut: 10)
--threshold-cognitive  Seuil cognitif (défaut: 15)
--recursive/-R     Recherche récursive (défaut: oui)
--verbose, -v      Mode verbeux
--no-halstead      Désactiver Halstead
--no-todos         Désactiver TODO/FIXME
--no-cursors       Désactiver analyse curseurs
--no-memory        Désactiver analyse mémoire
```

### Formats de sortie

- **text** : Affichage formaté dans le terminal (avec Rich)
- **json** : JSON compact sans indentation
- **json-pretty** : JSON avec indentation pour lisibilité (inclut métadonnées)
- **html** : Rapport HTML interactif avec CSS et JavaScript intégrés
- **markdown** : Markdown compatible GitHub/GitLab avec tableaux
- **csv** : Export CSV pour analyse dans des tableurs

#### Détails des formats

##### JSON (json/json-pretty)

- Structure avec métadonnées (version, date de génération)
- `json` : format compact sans indentation
- `json-pretty` : format lisible avec indentation (recommandé)

##### HTML

- Rapport interactif autonome (CSS et JavaScript inclus)
- Tableaux triables
- Sections collapsibles
- Code couleur pour les niveaux de complexité
- Navigation facilitée

##### Markdown

- Format texte structuré compatible GitHub/GitLab
- Tableaux au format Markdown
- Badges et icônes pour les indicateurs
- Parfait pour intégration dans documentation

## Exemple de sortie

```
╭──────────────────────────────────────────────╮
│ Pro*C Static Analyzer v0.2                   │
│ Complexité · TODO/FIXME · Curseurs · Mémoire │
╰──────────────────────────────────────────────╯

📄 examples/sample.pc
  Module: sample.pc - Gestion des employés
  Lignes: 354 (non vides: 291)
  Fonctions: 10
  Blocs SQL: 26
  TODO/FIXME: 8 (3 haute priorité)
  Curseurs: 3 (1 issues, 1 imbriqués)
  Mémoire: 5 problèmes (0 critiques)

  Fonction              Lignes   Cyclo   Cogn   SQL   Halstead Vol   Bugs Est.
  connect_db (L37)          14       2      1     1            127        0.04
  find_employee (L57)       27       4      6     1            241        0.08
  update_salary (L90)       53      11     18     2            539        0.18
  ...

📝 TODO/FIXME
  HIGH (3)
    FIXME sample.pc:60 - Cette fonction ne gère pas les erreurs correctement
    XXX sample.pc:78 - buffer jamais libéré - fuite mémoire
    FIXME sample.pc:298 - Curseur imbriqué - très mauvais

🔄 Problèmes de curseurs SQL
  ERROR sample.pc:302
    Curseur: inner_cursor - ouvert dans boucle FETCH - risque de performance

🧠 Problèmes de gestion mémoire
  ERROR (1)
    ► sample.pc:61 malloc() sans vérification NULL
  WARNING (4)
    ► strcpy() sans vérification de taille
    ► malloc() sans free() correspondant

📊 RÉSUMÉ
  Fichiers analysés                    1
  Fonctions totales                   10
  Complexité cyclomatique moyenne   5.60
  TODO/FIXME                           8
  Problèmes curseurs                   1
  Problèmes mémoire                    5
```

## Architecture

```
proc_analyzer/
├── preprocessor.py   # Neutralise EXEC SQL → C parsable
├── parser.py         # AST via tree-sitter
├── cyclomatic.py     # McCabe: if, while, &&, ||, ?:
├── cognitive.py      # Sonar: pénalité d'imbrication
├── halstead.py       # Volume, difficulté, effort, bugs
├── comments.py       # TODO/FIXME + entêtes modules
├── cursors.py        # Détection curseurs imbriqués
├── memory.py         # malloc/free, strcpy, buffer overflow
├── analyzer.py       # Orchestration
└── cli.py            # Interface Rich + Click
```

## Métriques

### Complexité Cyclomatique (McCabe)

Compte les points de décision : `if`, `while`, `for`, `case`, `&&`, `||`, `?:`

Seuils recommandés :

- 1-5 : Simple
- 6-10 : Modéré
- 11-20 : Complexe
- 21+ : Très complexe, refactoring recommandé

### Complexité Cognitive (SonarSource)

Pénalise l'imbrication et les structures difficiles :

- +1 pour chaque structure de contrôle
- +1 supplémentaire par niveau d'imbrication
- +1 pour break/continue vers labels

### Métriques Halstead

- **Volume** (V) : taille du programme
- **Difficulté** (D) : effort de compréhension
- **Effort** (E) : travail mental requis
- **Bugs estimés** (B) : V / 3000

### Problèmes mémoire détectés

- `malloc`/`calloc` sans vérification NULL
- Allocation sans `free` correspondant
- `free` sans mise à NULL (dangling pointer)
- Fonctions dangereuses : `strcpy`, `sprintf`, `gets`...
- `sizeof` sur pointeur au lieu du type

### Curseurs SQL

- Curseurs déclarés mais non fermés
- Curseurs ouverts dans une boucle FETCH (imbrication)
- FETCH sans vérification SQLCODE

## API Python

```python
from proc_analyzer import ProCAnalyzer

analyzer = ProCAnalyzer(
    enable_halstead=True,
    enable_todos=True,
    enable_cursors=True,
    enable_memory=True,
)

# Analyser un fichier
metrics = analyzer.analyze_file('program.pc')
print(f"Fonctions: {metrics.function_count}")
print(f"TODOs: {metrics.todo_count}")

# Analyser un répertoire
report = analyzer.analyze_directory('./src')
print(report.to_json())

# Accéder aux problèmes
for filepath, issue in report.get_all_memory_issues():
    print(f"{filepath}: {issue['message']}")
```

## Limitations

- Ne gère pas les macros C complexes (préprocesseur)
- Les blocs EXEC SQL sont comptés mais non analysés sémantiquement
- L'analyse mémoire est heuristique (pas de flow analysis complet)
- Pas de support des extensions spécifiques à certains compilateurs

## Licence

MIT
