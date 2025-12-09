"""
Analyseur Pro*C principal
Orchestre le prétraitement, parsing et calcul des métriques
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .cognitive import CognitiveCalculator
from .comments import CommentAnalyzer, ModuleInventory
from .cursors import CursorAnalyzer
from .cyclomatic import CyclomaticCalculator
from .halstead import HalsteadCalculator
from .memory import MemoryAnalyzer
from .parser import FunctionInfo, ProCParser
from .preprocessor import ExecSqlBlock, ProCPreprocessor


@dataclass
class FunctionMetrics:
    """
    Métriques pour une fonction.

    Attributes:
        name: Nom de la fonction
        start_line: Numéro de ligne de début (1-indexed)
        end_line: Numéro de ligne de fin (1-indexed)
        line_count: Nombre de lignes de la fonction
        cyclomatic_complexity: Complexité cyclomatique (McCabe)
        cognitive_complexity: Complexité cognitive (SonarSource)
        sql_blocks_count: Nombre de blocs SQL dans la fonction
        parameters_count: Nombre de paramètres
        return_type: Type de retour de la fonction
        halstead: Métriques Halstead (optionnel)
    """

    name: str
    start_line: int
    end_line: int
    line_count: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    sql_blocks_count: int = 0
    parameters_count: int = 0
    return_type: str = "void"
    halstead: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.line_count,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "cognitive_complexity": self.cognitive_complexity,
            "sql_blocks_count": self.sql_blocks_count,
            "parameters_count": self.parameters_count,
            "return_type": self.return_type,
        }
        if self.halstead:
            result["halstead"] = self.halstead
        return result


@dataclass
class FileMetrics:
    """
    Métriques pour un fichier Pro*C.

    Attributes:
        filepath: Chemin du fichier analysé
        total_lines: Nombre total de lignes
        non_empty_lines: Nombre de lignes non vides
        functions: Liste des métriques des fonctions
        sql_statistics: Statistiques sur les blocs SQL trouvés
        parse_errors: Indique si des erreurs de parsing ont été détectées
        error_message: Message d'erreur si parse_errors est True
        module_info: Informations sur le module (titre, description, etc.)
        todos: Liste des TODO/FIXME trouvés dans le fichier
        cursor_analysis: Résultat de l'analyse des curseurs SQL
        memory_analysis: Résultat de l'analyse de sécurité mémoire
    """

    filepath: str
    total_lines: int
    non_empty_lines: int
    functions: list[FunctionMetrics] = field(default_factory=list)
    sql_statistics: dict[str, Any] = field(default_factory=dict)
    parse_errors: bool = False
    error_message: str = ""
    module_info: Optional[dict[str, Any]] = None
    todos: list[dict[str, Any]] = field(default_factory=list)
    cursor_analysis: Optional[dict[str, Any]] = None
    memory_analysis: Optional[dict[str, Any]] = None

    @property
    def function_count(self) -> int:
        return len(self.functions)

    @property
    def avg_cyclomatic(self) -> float:
        if not self.functions:
            return 0.0
        return sum(f.cyclomatic_complexity for f in self.functions) / len(self.functions)

    @property
    def avg_cognitive(self) -> float:
        if not self.functions:
            return 0.0
        return sum(f.cognitive_complexity for f in self.functions) / len(self.functions)

    @property
    def max_cyclomatic(self) -> int:
        if not self.functions:
            return 0
        return max(f.cyclomatic_complexity for f in self.functions)

    @property
    def max_cognitive(self) -> int:
        if not self.functions:
            return 0
        return max(f.cognitive_complexity for f in self.functions)

    @property
    def total_sql_blocks(self) -> int:
        return self.sql_statistics.get("total_blocks", 0)

    @property
    def todo_count(self) -> int:
        return len(self.todos)

    @property
    def cursor_issues_count(self) -> int:
        if self.cursor_analysis:
            return self.cursor_analysis.get("total_issues", 0)
        return 0

    @property
    def memory_issues_count(self) -> int:
        if self.memory_analysis:
            return self.memory_analysis.get("total_issues", 0)
        return 0

    def to_dict(self) -> dict:
        result = {
            "filepath": self.filepath,
            "total_lines": self.total_lines,
            "non_empty_lines": self.non_empty_lines,
            "function_count": self.function_count,
            "avg_cyclomatic": round(self.avg_cyclomatic, 2),
            "avg_cognitive": round(self.avg_cognitive, 2),
            "max_cyclomatic": self.max_cyclomatic,
            "max_cognitive": self.max_cognitive,
            "total_sql_blocks": self.total_sql_blocks,
            "sql_statistics": self.sql_statistics,
            "parse_errors": self.parse_errors,
            "functions": [f.to_dict() for f in self.functions],
        }

        if self.module_info:
            result["module_info"] = self.module_info
        if self.todos:
            result["todos"] = self.todos
            result["todo_count"] = len(self.todos)
        if self.cursor_analysis:
            result["cursor_analysis"] = self.cursor_analysis
        if self.memory_analysis:
            result["memory_analysis"] = self.memory_analysis

        return result


@dataclass
class AnalysisReport:
    """
    Rapport d'analyse complet pour un projet Pro*C.

    Attributes:
        files: Liste des métriques pour chaque fichier analysé
        module_inventory: Inventaire des modules du projet (si activé)
    """

    files: list[FileMetrics] = field(default_factory=list)
    module_inventory: Optional[dict[str, Any]] = None

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_functions(self) -> int:
        return sum(f.function_count for f in self.files)

    @property
    def total_lines(self) -> int:
        return sum(f.total_lines for f in self.files)

    @property
    def total_sql_blocks(self) -> int:
        return sum(f.total_sql_blocks for f in self.files)

    @property
    def total_todos(self) -> int:
        return sum(f.todo_count for f in self.files)

    @property
    def total_cursor_issues(self) -> int:
        return sum(f.cursor_issues_count for f in self.files)

    @property
    def total_memory_issues(self) -> int:
        return sum(f.memory_issues_count for f in self.files)

    @property
    def avg_cyclomatic(self) -> float:
        all_complexities = [f.cyclomatic_complexity for file in self.files for f in file.functions]
        if not all_complexities:
            return 0.0
        return sum(all_complexities) / len(all_complexities)

    @property
    def avg_cognitive(self) -> float:
        all_complexities = [f.cognitive_complexity for file in self.files for f in file.functions]
        if not all_complexities:
            return 0.0
        return sum(all_complexities) / len(all_complexities)

    def get_high_complexity_functions(
        self, cyclo_threshold: int = 10, cognitive_threshold: int = 15
    ) -> list[tuple]:
        """
        Retourne les fonctions dépassant les seuils de complexité.

        Args:
            cyclo_threshold: Seuil de complexité cyclomatique
            cognitive_threshold: Seuil de complexité cognitive

        Returns:
            Liste de tuples (filepath, FunctionMetrics) pour les fonctions à risque
        """
        results = []
        for file in self.files:
            for func in file.functions:
                if (
                    func.cyclomatic_complexity > cyclo_threshold
                    or func.cognitive_complexity > cognitive_threshold
                ):
                    results.append((file.filepath, func))
        return results

    def get_all_todos(self) -> list[tuple]:
        """
        Retourne tous les TODOs/FIXME avec leur fichier.

        Returns:
            Liste de tuples (filepath, todo_dict) pour tous les TODOs
        """
        results = []
        for file in self.files:
            for todo in file.todos:
                results.append((file.filepath, todo))
        return results

    def get_all_cursor_issues(self) -> list[tuple]:
        """
        Retourne tous les problèmes de curseurs SQL détectés.

        Returns:
            Liste de tuples (filepath, issue_dict) pour tous les problèmes
        """
        results = []
        for file in self.files:
            if file.cursor_analysis and "issues" in file.cursor_analysis:
                for issue in file.cursor_analysis["issues"]:
                    results.append((file.filepath, issue))
        return results

    def get_all_memory_issues(self) -> list[tuple]:
        """
        Retourne tous les problèmes de sécurité mémoire détectés.

        Returns:
            Liste de tuples (filepath, issue_dict) pour tous les problèmes
        """
        results = []
        for file in self.files:
            if file.memory_analysis and "issues" in file.memory_analysis:
                for issue in file.memory_analysis["issues"]:
                    results.append((file.filepath, issue))
        return results

    def to_dict(self) -> dict:
        result = {
            "summary": {
                "total_files": self.total_files,
                "total_functions": self.total_functions,
                "total_lines": self.total_lines,
                "total_sql_blocks": self.total_sql_blocks,
                "avg_cyclomatic": round(self.avg_cyclomatic, 2),
                "avg_cognitive": round(self.avg_cognitive, 2),
                "total_todos": self.total_todos,
                "total_cursor_issues": self.total_cursor_issues,
                "total_memory_issues": self.total_memory_issues,
            },
            "files": [f.to_dict() for f in self.files],
        }

        if self.module_inventory:
            result["module_inventory"] = self.module_inventory

        return result

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_csv_rows(self) -> Iterator[list[str]]:
        """
        Génère les lignes CSV pour export.

        Yields:
            Lignes CSV, la première étant l'en-tête
        """
        yield [
            "file",
            "function",
            "start_line",
            "end_line",
            "lines",
            "cyclomatic",
            "cognitive",
            "sql_blocks",
            "params",
            "return_type",
            "halstead_volume",
            "halstead_difficulty",
            "halstead_bugs",
        ]

        for file in self.files:
            for func in file.functions:
                halstead = func.halstead or {}
                yield [
                    file.filepath,
                    func.name,
                    str(func.start_line),
                    str(func.end_line),
                    str(func.line_count),
                    str(func.cyclomatic_complexity),
                    str(func.cognitive_complexity),
                    str(func.sql_blocks_count),
                    str(func.parameters_count),
                    func.return_type,
                    str(halstead.get("volume", "")),
                    str(halstead.get("difficulty", "")),
                    str(halstead.get("bugs_estimate", "")),
                ]


class ProCAnalyzer:
    """
    Analyseur statique pour code Pro*C.

    Orchestre le prétraitement, le parsing et le calcul des métriques
    (complexité cyclomatique, cognitive, Halstead, TODO/FIXME, curseurs, mémoire).

    Attributes:
        preprocessor: Préprocesseur pour neutraliser les blocs EXEC SQL
        parser: Parser C utilisant tree-sitter
        enable_halstead: Active le calcul des métriques Halstead
        enable_todos: Active la détection des TODO/FIXME
        enable_cursors: Active l'analyse des curseurs SQL
        enable_memory: Active l'analyse de sécurité mémoire
        module_inventory: Inventaire des modules du projet

    Example:
        >>> analyzer = ProCAnalyzer()
        >>> report = analyzer.analyze_file('program.pc')
        >>> # ou pour un répertoire avec plusieurs patterns
        >>> report = analyzer.analyze_directory(
        ...     './src',
        ...     patterns=['*.pc', '*.sc', '*.inc']
        ... )
    """

    def __init__(
        self,
        enable_halstead: bool = True,
        enable_todos: bool = True,
        enable_cursors: bool = True,
        enable_memory: bool = True,
    ) -> None:
        """
        Initialise l'analyseur Pro*C.

        Args:
            enable_halstead: Active le calcul des métriques Halstead
            enable_todos: Active la détection des TODO/FIXME
            enable_cursors: Active l'analyse des curseurs SQL
            enable_memory: Active l'analyse de sécurité mémoire
        """
        self.preprocessor = ProCPreprocessor()
        self.parser = ProCParser()
        self.enable_halstead = enable_halstead
        self.enable_todos = enable_todos
        self.enable_cursors = enable_cursors
        self.enable_memory = enable_memory
        self.module_inventory = ModuleInventory()

    def _create_function_metrics(
        self,
        func: FunctionInfo,
        sql_blocks: list[ExecSqlBlock],
        cyclo_calc: CyclomaticCalculator,
        cognitive_calc: CognitiveCalculator,
        halstead_calc: Optional[HalsteadCalculator],
    ) -> FunctionMetrics:
        """
        Crée les métriques pour une fonction.

        Args:
            func: Information sur la fonction
            sql_blocks: Liste des blocs SQL trouvés
            cyclo_calc: Calculateur de complexité cyclomatique
            cognitive_calc: Calculateur de complexité cognitive
            halstead_calc: Calculateur Halstead (optionnel)

        Returns:
            Métriques de la fonction
        """
        sql_blocks_in_function = sum(
            1 for block in sql_blocks if func.start_line <= block.line_number <= func.end_line
        )

        func_metrics = FunctionMetrics(
            name=func.name,
            start_line=func.start_line,
            end_line=func.end_line,
            line_count=func.line_count,
            cyclomatic_complexity=cyclo_calc.calculate(func),
            cognitive_complexity=cognitive_calc.calculate(func),
            sql_blocks_count=sql_blocks_in_function,
            parameters_count=len(func.parameters),
            return_type=func.return_type,
        )

        if halstead_calc:
            halstead_metrics = halstead_calc.calculate(func)
            func_metrics.halstead = halstead_metrics.to_dict()

        return func_metrics

    def analyze_source(self, source: str, filepath: str = "<string>") -> FileMetrics:
        """
        Analyse du code source Pro*C directement.

        Args:
            source: Code source Pro*C
            filepath: Nom de fichier pour le rapport

        Returns:
            Métriques du fichier
        """
        metrics = FileMetrics(
            filepath=filepath,
            total_lines=source.count("\n") + 1,
            non_empty_lines=sum(1 for line in source.split("\n") if line.strip()),
        )

        try:
            processed_source, sql_blocks = self.preprocessor.preprocess(source)
            metrics.sql_statistics = self.preprocessor.get_sql_statistics()

            self.parser.parse(processed_source)
            metrics.parse_errors = self.parser.has_errors

            cyclo_calc = CyclomaticCalculator(self.parser)
            cognitive_calc = CognitiveCalculator(self.parser)

            halstead_calc = None
            if self.enable_halstead:
                halstead_calc = HalsteadCalculator(self.parser)

            for func in self.parser.get_functions():
                func_metrics = self._create_function_metrics(
                    func, sql_blocks, cyclo_calc, cognitive_calc, halstead_calc
                )
                metrics.functions.append(func_metrics)

            self._analyze_additional_metrics(source, filepath, metrics)

        except (ValueError, TypeError, AttributeError, KeyError) as e:
            metrics.parse_errors = True
            metrics.error_message = f"Erreur d'analyse: {type(e).__name__}: {str(e)}"
        except Exception as e:
            metrics.parse_errors = True
            metrics.error_message = (
                f"Erreur inattendue lors de l'analyse: {type(e).__name__}: {str(e)}"
            )

        return metrics

    def _analyze_additional_metrics(self, source: str, filepath: str, metrics: FileMetrics) -> None:
        """
        Effectue les analyses supplémentaires (TODOs, curseurs, mémoire).

        Args:
            source: Code source Pro*C
            filepath: Chemin du fichier
            metrics: Métriques du fichier à enrichir
        """
        if self.enable_todos:
            comment_analyzer = CommentAnalyzer()
            todos, module_info = comment_analyzer.analyze(source, filepath)
            metrics.todos = [t.to_dict() for t in todos]
            metrics.module_info = module_info.to_dict()
            self.module_inventory.add_module(module_info)

        if self.enable_cursors:
            cursor_analyzer = CursorAnalyzer()
            cursor_result = cursor_analyzer.analyze(source)
            metrics.cursor_analysis = cursor_result.to_dict()

        if self.enable_memory:
            memory_analyzer = MemoryAnalyzer()
            memory_result = memory_analyzer.analyze(source)
            metrics.memory_analysis = memory_result.to_dict()

    def analyze_file(self, filepath: str) -> FileMetrics:
        """
        Analyse un fichier Pro*C.

        Args:
            filepath: Chemin vers le fichier .pc

        Returns:
            Métriques du fichier
        """
        path = Path(filepath)

        if not path.exists():
            return FileMetrics(
                filepath=str(path),
                total_lines=0,
                non_empty_lines=0,
                parse_errors=True,
                error_message=f"File not found: {filepath}",
            )

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError) as e:
            return FileMetrics(
                filepath=str(path),
                total_lines=0,
                non_empty_lines=0,
                parse_errors=True,
                error_message=f"Erreur de lecture du fichier: {type(e).__name__}: {str(e)}",
            )

        return self.analyze_source(source, str(path))

    def analyze_directory(
        self,
        directory: str,
        pattern: Optional[str] = None,
        patterns: Optional[list[str]] = None,
        recursive: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> AnalysisReport:
        """
        Analyse tous les fichiers Pro*C d'un répertoire.

        Args:
            directory: Chemin du répertoire
            pattern: Pattern glob pour les fichiers (défaut: *.pc) - déprécié, utiliser patterns
            patterns: Liste de patterns glob pour les fichiers (défaut: ["*.pc"])
            recursive: Recherche récursive (défaut: True)
            progress_callback: Callback optionnel appelé pour chaque fichier analysé.
                              Signature: callback(filepath: str, current: int, total: int)

        Returns:
            Rapport d'analyse complet
        """
        self.module_inventory = ModuleInventory()

        report = AnalysisReport()
        path = Path(directory)

        if not path.exists():
            return report

        if patterns is not None:
            patterns_list = patterns
        elif pattern is not None:
            patterns_list = [pattern]
        else:
            patterns_list = ["*.pc"]

        files_set: set[Path] = set()
        for pat in patterns_list:
            if recursive:
                files = path.rglob(pat)
            else:
                files = path.glob(pat)
            files_set.update(f for f in files if f.is_file())

        file_list = sorted(files_set)
        total_files = len(file_list)

        for index, filepath in enumerate(file_list, 1):
            if progress_callback:
                progress_callback(str(filepath), index, total_files)

            metrics = self.analyze_file(str(filepath))
            report.files.append(metrics)

        if self.enable_todos:
            report.module_inventory = self.module_inventory.to_dict()

        return report

    def analyze_files(self, filepaths: list[str]) -> AnalysisReport:
        """
        Analyse une liste de fichiers.

        Args:
            filepaths: Liste des chemins de fichiers

        Returns:
            Rapport d'analyse complet
        """
        self.module_inventory = ModuleInventory()

        report = AnalysisReport()

        for filepath in filepaths:
            metrics = self.analyze_file(filepath)
            report.files.append(metrics)

        if self.enable_todos:
            report.module_inventory = self.module_inventory.to_dict()

        return report
