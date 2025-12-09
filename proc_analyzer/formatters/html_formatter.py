"""
Formatter HTML pour les rapports d'analyse.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..analyzer import AnalysisReport, FileMetrics


class HTMLFormatter:
    """
    Formatter pour générer des rapports HTML interactifs.

    Génère un fichier HTML autonome avec CSS intégré et JavaScript
    minimal pour l'interactivité (tri, filtres).
    """

    def __init__(self):
        """Initialise le formatter avec l'environnement Jinja2."""
        template_dir = Path(__file__).parent / "templates" / "html"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Charger les fichiers statiques
        static_dir = template_dir / "static"
        self.css_content = (static_dir / "styles.css").read_text(encoding="utf-8")
        self.js_content = (static_dir / "script.js").read_text(encoding="utf-8")

    def format(self, report: AnalysisReport) -> str:
        """
        Formate un rapport en HTML.

        Args:
            report: Rapport d'analyse à formater

        Returns:
            Chaîne HTML complète
        """
        template = self.env.get_template("base.html")

        # Préparer les données pour les templates
        todos_data = self._prepare_todos_data(report)
        memory_data = self._prepare_memory_issues_data(report)

        context = {
            "generated_at": datetime.now().strftime("%d/%m/%Y à %H:%M:%S"),
            "css_content": self.css_content,
            "js_content": self.js_content,
            "summary": self._prepare_summary_data(report),
            "files": self._prepare_files_data(report),
            "todos_data": todos_data,
            "cursor_issues": self._prepare_cursor_issues_data(report),
            "memory_issues": memory_data.get("memory_issues"),
            "memory_issues_by_severity": memory_data.get("memory_issues_by_severity", {}),
        }

        return template.render(**context)

    def save(self, report: AnalysisReport, output_path: str) -> None:
        """
        Sauvegarde un rapport HTML dans un fichier.

        Args:
            report: Rapport d'analyse à sauvegarder
            output_path: Chemin du fichier de sortie
        """
        output = Path(output_path)
        output.write_text(self.format(report), encoding="utf-8")

    def _prepare_summary_data(self, report: AnalysisReport) -> dict[str, Any]:
        """
        Prépare les données du résumé pour le template.

        Args:
            report: Rapport d'analyse

        Returns:
            Dictionnaire avec les données du résumé
        """
        return {
            "total_files": report.total_files,
            "total_functions": report.total_functions,
            "total_lines": report.total_lines,
            "total_lines_formatted": f"{report.total_lines:,}",
            "avg_cyclomatic": report.avg_cyclomatic,
            "avg_cognitive": report.avg_cognitive,
            "total_todos": report.total_todos,
            "total_cursor_issues": report.total_cursor_issues,
            "total_memory_issues": report.total_memory_issues,
        }

    def _prepare_files_data(self, report: AnalysisReport) -> list[dict[str, Any]]:
        """
        Prépare les données des fichiers pour le template.

        Args:
            report: Rapport d'analyse

        Returns:
            Liste de dictionnaires avec les données de chaque fichier
        """
        files_data = []
        for file_metrics in report.files:
            files_data.append(self._prepare_file_data(file_metrics))
        return files_data

    def _prepare_file_data(self, metrics: FileMetrics) -> dict[str, Any]:
        """
        Prépare les données d'un fichier pour le template.

        Args:
            metrics: Métriques du fichier

        Returns:
            Dictionnaire avec les données du fichier
        """
        file_name = Path(metrics.filepath).name

        # Préparer les fonctions
        functions_data = []
        for func in metrics.functions:
            functions_data.append(
                {
                    "name": func.name,
                    "start_line": func.start_line,
                    "line_count": func.line_count,
                    "cyclomatic_complexity": func.cyclomatic_complexity,
                    "cognitive_complexity": func.cognitive_complexity,
                    "sql_blocks_count": func.sql_blocks_count,
                    "cyclo_class": self._complexity_class(func.cyclomatic_complexity, 5, 10),
                    "cogn_class": self._complexity_class(func.cognitive_complexity, 8, 15),
                }
            )

        # Grouper les TODOs par priorité
        todos_by_priority = {"high": [], "medium": [], "low": []}
        if metrics.todos:
            for todo in metrics.todos:
                priority = todo.get("priority", "low")
                todos_by_priority[priority].append(
                    {
                        "tag": todo.get("tag", "TODO"),
                        "message": todo.get("message", ""),
                        "line_number": todo.get("line_number", 0),
                    }
                )

        # Préparer les problèmes de curseurs
        cursor_issues = []
        if metrics.cursor_analysis and metrics.cursor_analysis.get("issues"):
            for issue in metrics.cursor_analysis["issues"]:
                cursor_issues.append(
                    {
                        "severity": issue.get("severity", "info"),
                        "cursor_name": issue.get("cursor_name", "?"),
                        "message": issue.get("message", ""),
                        "line_number": issue.get("line_number", 0),
                    }
                )

        # Grouper les problèmes mémoire par sévérité
        memory_issues_by_severity = {"critical": [], "error": [], "warning": [], "info": []}
        memory_warnings_count = 0
        if metrics.memory_analysis and metrics.memory_analysis.get("issues"):
            for issue in metrics.memory_analysis["issues"]:
                severity = issue.get("severity", "info")
                memory_issues_by_severity[severity].append(
                    {
                        "message": issue.get("message", ""),
                        "line_number": issue.get("line_number", 0),
                        "recommendation": issue.get("recommendation", ""),
                    }
                )
                if severity == "warning":
                    memory_warnings_count += 1

        # Calculer les classes de complexité pour les moyennes du fichier
        avg_cyclo_int = int(metrics.avg_cyclomatic)
        avg_cogn_int = int(metrics.avg_cognitive)
        avg_cyclo_class = self._complexity_class(avg_cyclo_int, 5, 10)
        avg_cogn_class = self._complexity_class(avg_cogn_int, 8, 15)

        return {
            "filename": file_name,
            "has_todos": "true" if metrics.todos else "false",
            "has_cursor_issues": (
                "true"
                if (metrics.cursor_analysis and metrics.cursor_analysis.get("issues"))
                else "false"
            ),
            "has_memory_issues": (
                "true"
                if (metrics.memory_analysis and metrics.memory_analysis.get("issues"))
                else "false"
            ),
            "avg_cyclomatic": f"{metrics.avg_cyclomatic:.2f}",
            "avg_cognitive": f"{metrics.avg_cognitive:.2f}",
            "avg_cyclo_class": avg_cyclo_class,
            "avg_cogn_class": avg_cogn_class,
            "total_lines": metrics.total_lines,
            "non_empty_lines": metrics.non_empty_lines,
            "function_count": metrics.function_count,
            "total_sql_blocks": metrics.total_sql_blocks,
            "todos_count": len(metrics.todos) if metrics.todos else 0,
            "high_todos_count": (
                sum(1 for t in metrics.todos if t.get("priority") == "high") if metrics.todos else 0
            ),
            "cursor_issues_count": len(cursor_issues),
            "memory_warnings_count": memory_warnings_count,
            "functions": functions_data,
            "todos": metrics.todos if metrics.todos else [],
            "todos_by_priority": todos_by_priority,
            "cursor_issues": cursor_issues,
            "memory_issues": (
                metrics.memory_analysis.get("issues", []) if metrics.memory_analysis else []
            ),
            "memory_issues_by_severity": memory_issues_by_severity,
        }

    def _prepare_todos_data(self, report: AnalysisReport) -> dict[str, Any]:
        """
        Prépare les données TODOs pour le template.

        Args:
            report: Rapport d'analyse

        Returns:
            Dictionnaire avec les données TODOs
        """
        todos = report.get_all_todos()
        if not todos:
            return {"todos": None, "todos_by_priority": {"high": [], "medium": [], "low": []}}

        # Grouper par priorité
        todos_by_priority = {"high": [], "medium": [], "low": []}
        for filepath, todo in todos:
            priority = todo.get("priority", "low")
            todos_by_priority[priority].append(
                {
                    "filepath": filepath,
                    "filename": Path(filepath).name,
                    "tag": todo.get("tag", "TODO"),
                    "message": todo.get("message", ""),
                    "line_number": todo.get("line_number", 0),
                }
            )

        return {
            "todos": todos,
            "todos_by_priority": todos_by_priority,
        }

    def _prepare_cursor_issues_data(self, report: AnalysisReport) -> list[dict[str, Any]]:
        """
        Prépare les données des problèmes de curseurs pour le template.

        Args:
            report: Rapport d'analyse

        Returns:
            Liste de dictionnaires avec les problèmes de curseurs
        """
        issues = report.get_all_cursor_issues()
        if not issues:
            return []

        cursor_issues_data = []
        for filepath, issue in issues:
            cursor_issues_data.append(
                {
                    "filepath": filepath,
                    "filename": Path(filepath).name,
                    "severity": issue.get("severity", "info"),
                    "cursor_name": issue.get("cursor_name", "?"),
                    "message": issue.get("message", ""),
                    "line_number": issue.get("line_number", 0),
                }
            )

        return cursor_issues_data

    def _prepare_memory_issues_data(self, report: AnalysisReport) -> dict[str, Any]:
        """
        Prépare les données des problèmes mémoire pour le template.

        Args:
            report: Rapport d'analyse

        Returns:
            Dictionnaire avec les problèmes mémoire groupés par sévérité
        """
        issues = report.get_all_memory_issues()
        if not issues:
            return {
                "memory_issues": None,
                "memory_issues_by_severity": {
                    "critical": [],
                    "error": [],
                    "warning": [],
                    "info": [],
                },
            }

        # Grouper par sévérité
        memory_issues_by_severity = {"critical": [], "error": [], "warning": [], "info": []}
        for filepath, issue in issues:
            severity = issue.get("severity", "info")
            memory_issues_by_severity[severity].append(
                {
                    "filepath": filepath,
                    "filename": Path(filepath).name,
                    "message": issue.get("message", ""),
                    "line_number": issue.get("line_number", 0),
                    "recommendation": issue.get("recommendation", ""),
                }
            )

        return {
            "memory_issues": issues,
            "memory_issues_by_severity": memory_issues_by_severity,
        }

    def _complexity_class(self, value: int, low: int, medium: int) -> str:
        """
        Retourne la classe CSS selon la complexité.

        Args:
            value: Valeur de complexité
            low: Seuil bas
            medium: Seuil moyen

        Returns:
            Classe CSS correspondante
        """
        if value <= low:
            return "complexity-low"
        elif value <= medium:
            return "complexity-medium"
        else:
            return "complexity-high"
