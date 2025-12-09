# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pro*C Static Analyzer - A static analysis tool for Pro*C code (Oracle Embedded SQL in C). It calculates complexity metrics, detects code issues, and identifies anti-patterns.

## Commands

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run the CLI
uv run proc-analyzer analyze examples/sample.pc
uv run proc-analyzer analyze ./src --pattern "*.pc" -v

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_cyclomatic.py

# Run a specific test
uv run pytest tests/test_cyclomatic.py::test_cyclomatic_simple_function -v

# Run tests with coverage
uv run pytest --cov=proc_analyzer

# Mutation testing with mutmut
uv run mutmut run
uv run mutmut results
uv run mutmut show <id>
uv run mutmut apply <id>
uv run mutmut run --paths-to-mutate proc_analyzer/analyzer.py
```

## Architecture

The analyzer follows a pipeline architecture:

1. **Preprocessor** (`preprocessor.py`): Neutralizes `EXEC SQL` blocks to produce valid C code for tree-sitter parsing. Tracks SQL block positions for later analysis.

2. **Parser** (`parser.py`): Generates AST via tree-sitter-c. Extracts function definitions with metadata (name, parameters, line numbers).

3. **Metric Calculators** (independent modules):
   - `cyclomatic.py`: McCabe complexity (decision points: if/while/for/case/&&/||/?:)
   - `cognitive.py`: SonarSource cognitive complexity (nesting penalties)
   - `halstead.py`: Volume, difficulty, effort, estimated bugs

4. **Issue Detectors** (independent modules):
   - `comments.py`: TODO/FIXME/HACK/XXX extraction with priority levels, module header parsing
   - `cursors.py`: SQL cursor analysis (nested cursors, unclosed cursors, missing SQLCODE checks)
   - `memory.py`: Dangerous patterns (malloc without NULL check, strcpy, missing free, dangling pointers)

5. **Orchestrator** (`analyzer.py`): Coordinates all modules. `ProCAnalyzer` is the main API class. Produces `FileMetrics` and `AnalysisReport` dataclasses.

6. **CLI** (`cli.py`): Rich + Click interface. Commands: `analyze`, `todos`, `security`, `inventory`, `preprocess`.

## Key Data Flow

```
Pro*C source → ProCPreprocessor → clean C + SQL blocks list
                                        ↓
                                   ProCParser (tree-sitter)
                                        ↓
                           ┌────────────┴────────────┐
                           ↓            ↓            ↓
                    CyclomaticCalc  CognitiveCalc  HalsteadCalc
                           └────────────┬────────────┘
                                        ↓
                              FunctionMetrics → FileMetrics → AnalysisReport
```

## Testing

**⚠️ RÈGLE OBLIGATOIRE :** Toute nouvelle fonctionnalité DOIT être accompagnée de tests unitaires. Voir `CODING_STANDARDS.md` section "Tests" pour les détails.

Tests use pytest fixtures defined in `tests/conftest.py`. Key fixtures:

- `simple_c_source`, `simple_proc_source`: Basic code samples
- `complex_function_source`: Code with nested control flow for complexity testing
- `cursor_source`, `memory_issues_source`, `todo_comments_source`: Specialized samples
- `parser`, `parser_complex`: Pre-initialized parser instances

### Mutation Testing

The project uses **mutmut** to evaluate test quality by introducing mutations in the code and checking if tests detect them.

**Commands:**

- `uv run mutmut run`: Run all mutation tests
- `uv run mutmut results`: Show summary of mutation test results
- `uv run mutmut show <id>`: Show details of a specific surviving mutation
- `uv run mutmut apply <id>`: Apply a mutation to the code for debugging
- `uv run mutmut run --paths-to-mutate proc_analyzer/analyzer.py`: Run mutations on a specific module

**Configuration:** Mutation testing is configured in `pyproject.toml` under `[tool.mutmut]`. It mutates code in `proc_analyzer/` and runs tests from `tests/`.

**CI/CD:** Mutation testing runs automatically in GitHub Actions on the `quality.yml` workflow for main/master branches and pull requests. Results are uploaded as artifacts and the job has a 30-minute timeout.

## Standards de Code

**TOUJOURS suivre `CODING_STANDARDS.md`** pour :

- Architecture et organisation du code
- Principes CUPID (Composable, Unix philosophy, Predictable, Idiomatic, Domain-based)
- Clean Code (noms significatifs, fonctions courtes, etc.)
- Typage (annotations complètes)
- Tests obligatoires (section Tests)
- Documentation (docstrings style Google)
