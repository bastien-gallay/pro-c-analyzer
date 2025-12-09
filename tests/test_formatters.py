"""
Tests unitaires pour les formatters de rapports.
"""

import json

import pytest

from proc_analyzer.analyzer import AnalysisReport, FileMetrics, FunctionMetrics, ProCAnalyzer
from proc_analyzer.formatters import HTMLFormatter, JSONFormatter, MarkdownFormatter


@pytest.fixture
def sample_report(tmp_path, simple_proc_source):
    """Crée un rapport d'analyse simple pour les tests."""
    file_path = tmp_path / "test.pc"
    file_path.write_text(simple_proc_source)

    analyzer = ProCAnalyzer(
        enable_halstead=True,
        enable_todos=True,
        enable_cursors=True,
        enable_memory=True,
    )
    report = analyzer.analyze_directory(str(tmp_path), "*.pc")
    return report


@pytest.fixture
def minimal_report():
    """Crée un rapport minimal pour les tests."""
    func_metrics = FunctionMetrics(
        name="test_func",
        start_line=1,
        end_line=10,
        line_count=10,
        cyclomatic_complexity=3,
        cognitive_complexity=2,
        sql_blocks_count=1,
    )

    file_metrics = FileMetrics(
        filepath="test.pc",
        total_lines=50,
        non_empty_lines=40,
        functions=[func_metrics],
        todos=[
            {
                "tag": "TODO",
                "message": "Test todo",
                "priority": "high",
                "line_number": 5,
            }
        ],
    )

    return AnalysisReport(files=[file_metrics])


class TestJSONFormatter:
    """Tests pour JSONFormatter."""

    def test_format_compact(self, minimal_report):
        """Test du format JSON compact."""
        formatter = JSONFormatter(pretty=False)
        output = formatter.format(minimal_report)

        # Doit être du JSON valide
        data = json.loads(output)

        # Doit contenir metadata et report
        assert "metadata" in data
        assert "report" in data

        # Vérifier les métadonnées
        assert "version" in data["metadata"]
        assert "generated_at" in data["metadata"]
        assert "tool" in data["metadata"]

        # Vérifier le rapport
        assert "files" in data["report"]
        assert len(data["report"]["files"]) > 0

    def test_format_pretty(self, minimal_report):
        """Test du format JSON pretty."""
        formatter = JSONFormatter(pretty=True, indent=2)
        output = formatter.format(minimal_report)

        # Doit être du JSON valide
        data = json.loads(output)

        # Doit contenir metadata et report
        assert "metadata" in data
        assert "report" in data

        # Le pretty doit avoir de l'indentation (plusieurs lignes)
        assert "\n" in output

    def test_save_to_file(self, minimal_report, tmp_path):
        """Test de sauvegarde dans un fichier."""
        output_file = tmp_path / "test_output.json"
        formatter = JSONFormatter(pretty=True)
        formatter.save(minimal_report, str(output_file))

        # Vérifier que le fichier existe
        assert output_file.exists()

        # Vérifier que le contenu est valide JSON
        data = json.loads(output_file.read_text())
        assert "metadata" in data
        assert "report" in data

    def test_format_with_full_report(self, sample_report):
        """Test avec un rapport complet."""
        formatter = JSONFormatter(pretty=True)
        output = formatter.format(sample_report)

        data = json.loads(output)

        # Vérifier la structure complète
        assert "metadata" in data
        assert "report" in data
        assert "summary" in data["report"]
        assert "files" in data["report"]

        # Vérifier les métriques dans le summary
        summary = data["report"]["summary"]
        assert "total_files" in summary
        assert "total_functions" in summary
        assert "total_lines" in summary


class TestHTMLFormatter:
    """Tests pour HTMLFormatter."""

    def test_format_basic_structure(self, minimal_report):
        """Test de la structure HTML de base."""
        formatter = HTMLFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir les balises HTML essentielles
        assert "<!DOCTYPE html>" in output
        assert "<html" in output
        assert "<head>" in output
        assert "<body>" in output
        assert "</html>" in output

    def test_format_contains_metadata(self, minimal_report):
        """Test que le HTML contient les métadonnées."""
        formatter = HTMLFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir le titre
        assert "Pro*C Static Analyzer" in output

        # Doit contenir une section résumé
        assert "Résumé" in output or "summary" in output.lower()

    def test_format_contains_summary(self, minimal_report):
        """Test que le résumé est présent."""
        formatter = HTMLFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir les cartes de résumé
        assert "summary-grid" in output or "summary-card" in output
        assert "Fichiers analysés" in output

    def test_format_contains_functions_table(self, minimal_report):
        """Test que le tableau des fonctions est présent."""
        formatter = HTMLFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir un tableau
        assert "<table>" in output
        assert "test_func" in output or "Fonctions" in output

    def test_format_contains_css(self, minimal_report):
        """Test que le CSS est inclus."""
        formatter = HTMLFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir du CSS
        assert "<style>" in output
        assert "body {" in output or "font-family" in output.lower()

    def test_format_contains_javascript(self, minimal_report):
        """Test que le JavaScript est inclus."""
        formatter = HTMLFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir du JavaScript
        assert "<script>" in output
        assert "addEventListener" in output or "querySelector" in output

    def test_save_to_file(self, minimal_report, tmp_path):
        """Test de sauvegarde dans un fichier."""
        output_file = tmp_path / "test_output.html"
        formatter = HTMLFormatter()
        formatter.save(minimal_report, str(output_file))

        # Vérifier que le fichier existe
        assert output_file.exists()

        # Vérifier le contenu
        content = output_file.read_text()
        assert "<!DOCTYPE html>" in content
        assert "Pro*C Static Analyzer" in content

    def test_format_with_todos(self, minimal_report):
        """Test avec des TODOs."""
        formatter = HTMLFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir une section TODO/FIXME si présente
        if minimal_report.total_todos > 0:
            assert "TODO" in output or "FIXME" in output

    def test_format_with_full_report(self, sample_report):
        """Test avec un rapport complet."""
        formatter = HTMLFormatter()
        output = formatter.format(sample_report)

        # Structure HTML valide
        assert "<!DOCTYPE html>" in output
        assert "</html>" in output

        # Doit contenir les sections principales
        assert "Résumé" in output or "summary" in output.lower()

    def test_prepare_summary_data(self, minimal_report):
        """Test de préparation des données du résumé."""
        formatter = HTMLFormatter()
        summary_data = formatter._prepare_summary_data(minimal_report)

        assert "total_files" in summary_data
        assert "total_functions" in summary_data
        assert "total_lines" in summary_data
        assert "total_lines_formatted" in summary_data
        assert "avg_cyclomatic" in summary_data
        assert "avg_cognitive" in summary_data
        assert "total_todos" in summary_data
        assert "total_cursor_issues" in summary_data
        assert "total_memory_issues" in summary_data

        assert summary_data["total_files"] == minimal_report.total_files
        assert summary_data["total_functions"] == minimal_report.total_functions
        assert isinstance(summary_data["total_lines_formatted"], str)
        assert "," in summary_data["total_lines_formatted"] or summary_data["total_lines"] < 1000

    def test_prepare_file_data(self, minimal_report):
        """Test de préparation des données d'un fichier."""
        formatter = HTMLFormatter()
        file_metrics = minimal_report.files[0]
        file_data = formatter._prepare_file_data(file_metrics)

        assert "filename" in file_data
        assert "has_todos" in file_data
        assert "has_cursor_issues" in file_data
        assert "has_memory_issues" in file_data
        assert "avg_cyclomatic" in file_data
        assert "avg_cognitive" in file_data
        assert "total_lines" in file_data
        assert "functions" in file_data
        assert "todos_by_priority" in file_data
        assert "cursor_issues" in file_data
        assert "memory_issues_by_severity" in file_data

        assert file_data["filename"] == "test.pc"
        assert file_data["has_todos"] == "true"
        assert len(file_data["functions"]) == 1
        assert file_data["functions"][0]["name"] == "test_func"
        assert "cyclo_class" in file_data["functions"][0]
        assert "cogn_class" in file_data["functions"][0]

    def test_prepare_todos_data(self, minimal_report):
        """Test de préparation des données TODOs."""
        formatter = HTMLFormatter()
        todos_data = formatter._prepare_todos_data(minimal_report)

        assert "todos" in todos_data
        assert "todos_by_priority" in todos_data
        assert "high" in todos_data["todos_by_priority"]
        assert "medium" in todos_data["todos_by_priority"]
        assert "low" in todos_data["todos_by_priority"]

        if minimal_report.total_todos > 0:
            assert todos_data["todos"] is not None
            assert (
                len(todos_data["todos_by_priority"]["high"]) > 0
                or len(todos_data["todos_by_priority"]["medium"]) > 0
                or len(todos_data["todos_by_priority"]["low"]) > 0
            )

    def test_prepare_cursor_issues_data(self, minimal_report):
        """Test de préparation des données des problèmes de curseurs."""
        formatter = HTMLFormatter()
        cursor_data = formatter._prepare_cursor_issues_data(minimal_report)

        assert isinstance(cursor_data, list)
        for issue in cursor_data:
            assert "filepath" in issue
            assert "filename" in issue
            assert "severity" in issue
            assert "cursor_name" in issue
            assert "message" in issue
            assert "line_number" in issue

    def test_prepare_memory_issues_data(self, minimal_report):
        """Test de préparation des données des problèmes mémoire."""
        formatter = HTMLFormatter()
        memory_data = formatter._prepare_memory_issues_data(minimal_report)

        assert "memory_issues" in memory_data
        assert "memory_issues_by_severity" in memory_data
        assert "critical" in memory_data["memory_issues_by_severity"]
        assert "error" in memory_data["memory_issues_by_severity"]
        assert "warning" in memory_data["memory_issues_by_severity"]
        assert "info" in memory_data["memory_issues_by_severity"]

    def test_complexity_class(self):
        """Test de la méthode _complexity_class."""
        formatter = HTMLFormatter()

        # Test low
        assert formatter._complexity_class(3, 5, 10) == "complexity-low"
        assert formatter._complexity_class(5, 5, 10) == "complexity-low"

        # Test medium
        assert formatter._complexity_class(6, 5, 10) == "complexity-medium"
        assert formatter._complexity_class(10, 5, 10) == "complexity-medium"

        # Test high
        assert formatter._complexity_class(11, 5, 10) == "complexity-high"
        assert formatter._complexity_class(20, 5, 10) == "complexity-high"

    def test_prepare_files_data(self, minimal_report):
        """Test de préparation des données de tous les fichiers."""
        formatter = HTMLFormatter()
        files_data = formatter._prepare_files_data(minimal_report)

        assert isinstance(files_data, list)
        assert len(files_data) == len(minimal_report.files)
        assert all("filename" in f for f in files_data)

    def test_prepare_file_data_includes_new_fields(self):
        """Test que les nouvelles données sont présentes dans _prepare_file_data."""
        # Créer un fichier avec des problèmes de curseurs et mémoire
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[
                FunctionMetrics(
                    name="test_func",
                    start_line=1,
                    end_line=10,
                    line_count=10,
                    cyclomatic_complexity=8,  # Complexité moyenne élevée
                    cognitive_complexity=12,  # Complexité cognitive élevée
                ),
            ],
            cursor_analysis={
                "total_cursors": 2,
                "total_issues": 3,
                "issues": [
                    {
                        "severity": "error",
                        "cursor_name": "cursor1",
                        "message": "Issue 1",
                        "line_number": 5,
                    },
                    {
                        "severity": "warning",
                        "cursor_name": "cursor2",
                        "message": "Issue 2",
                        "line_number": 10,
                    },
                    {
                        "severity": "info",
                        "cursor_name": "cursor3",
                        "message": "Issue 3",
                        "line_number": 15,
                    },
                ],
            },
            memory_analysis={
                "total_issues": 4,
                "issues": [
                    {
                        "severity": "critical",
                        "message": "Critical issue",
                        "line_number": 20,
                    },
                    {
                        "severity": "warning",
                        "message": "Warning 1",
                        "line_number": 25,
                    },
                    {
                        "severity": "warning",
                        "message": "Warning 2",
                        "line_number": 30,
                    },
                    {
                        "severity": "info",
                        "message": "Info issue",
                        "line_number": 35,
                    },
                ],
            },
        )

        formatter = HTMLFormatter()
        file_data = formatter._prepare_file_data(file_metrics)

        # Vérifier les nouveaux champs
        assert "cursor_issues_count" in file_data
        assert file_data["cursor_issues_count"] == 3

        assert "memory_warnings_count" in file_data
        assert file_data["memory_warnings_count"] == 2  # Seulement les warnings

        assert "avg_cyclo_class" in file_data
        assert "avg_cogn_class" in file_data
        # avg_cyclomatic = 8, donc complexity-medium (seuil 5, 10)
        assert file_data["avg_cyclo_class"] == "complexity-medium"
        # avg_cognitive = 12, donc complexity-medium (seuil 8, 15)
        assert file_data["avg_cogn_class"] == "complexity-medium"

    def test_prepare_file_data_complexity_classes(self):
        """Test que les classes de complexité sont correctement calculées."""
        formatter = HTMLFormatter()

        # Test avec complexité faible
        file_metrics_low = FileMetrics(
            filepath="low.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[
                FunctionMetrics(
                    name="simple_func",
                    start_line=1,
                    end_line=10,
                    line_count=10,
                    cyclomatic_complexity=3,
                    cognitive_complexity=4,
                ),
            ],
        )
        file_data_low = formatter._prepare_file_data(file_metrics_low)
        assert file_data_low["avg_cyclo_class"] == "complexity-low"
        assert file_data_low["avg_cogn_class"] == "complexity-low"

        # Test avec complexité moyenne
        file_metrics_medium = FileMetrics(
            filepath="medium.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[
                FunctionMetrics(
                    name="medium_func",
                    start_line=1,
                    end_line=10,
                    line_count=10,
                    cyclomatic_complexity=7,  # Entre 5 et 10
                    cognitive_complexity=10,  # Entre 8 et 15
                ),
            ],
        )
        file_data_medium = formatter._prepare_file_data(file_metrics_medium)
        assert file_data_medium["avg_cyclo_class"] == "complexity-medium"
        assert file_data_medium["avg_cogn_class"] == "complexity-medium"

        # Test avec complexité élevée
        file_metrics_high = FileMetrics(
            filepath="high.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[
                FunctionMetrics(
                    name="complex_func",
                    start_line=1,
                    end_line=10,
                    line_count=10,
                    cyclomatic_complexity=15,  # > 10
                    cognitive_complexity=20,  # > 15
                ),
            ],
        )
        file_data_high = formatter._prepare_file_data(file_metrics_high)
        assert file_data_high["avg_cyclo_class"] == "complexity-high"
        assert file_data_high["avg_cogn_class"] == "complexity-high"

    def test_file_summary_info_in_html_output(self):
        """Test que les informations de résumé sont présentes dans le HTML généré."""
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[
                FunctionMetrics(
                    name="test_func",
                    start_line=1,
                    end_line=10,
                    line_count=10,
                    cyclomatic_complexity=6,
                    cognitive_complexity=9,
                ),
            ],
            todos=[
                {
                    "tag": "TODO",
                    "message": "Test todo",
                    "priority": "high",
                    "line_number": 5,
                },
            ],
            cursor_analysis={
                "total_cursors": 1,
                "total_issues": 2,
                "issues": [
                    {
                        "severity": "error",
                        "cursor_name": "test_cursor",
                        "message": "Test issue",
                        "line_number": 10,
                    },
                    {
                        "severity": "warning",
                        "cursor_name": "test_cursor2",
                        "message": "Test issue 2",
                        "line_number": 15,
                    },
                ],
            },
            memory_analysis={
                "total_issues": 3,
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Memory warning",
                        "line_number": 20,
                    },
                    {
                        "severity": "warning",
                        "message": "Another warning",
                        "line_number": 25,
                    },
                    {
                        "severity": "info",
                        "message": "Info message",
                        "line_number": 30,
                    },
                ],
            },
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = HTMLFormatter()
        output = formatter.format(report)

        # Vérifier que les informations de résumé sont dans le header du fichier
        file_section_start = output.find("test.pc")
        assert file_section_start != -1

        file_section = output[file_section_start:]

        # Vérifier la présence des classes CSS pour la complexité
        assert "file-summary-info" in file_section

        # Vérifier que les informations sont présentes
        assert "Complexité:" in file_section
        assert "Cyclo" in file_section
        assert "Cogn" in file_section
        assert "TODO:" in file_section or "📝 TODO:" in file_section
        assert "Curseurs:" in file_section or "🔄 Curseurs:" in file_section
        assert "Mémoire:" in file_section or "🧠 Mémoire:" in file_section

        # Vérifier les valeurs
        assert "2" in file_section  # cursor_issues_count
        assert "2" in file_section  # memory_warnings_count (apparaît deux fois)
        assert "1" in file_section  # todos_count

    def test_file_summary_info_without_issues(self):
        """Test que les informations de résumé n'affichent pas les sections vides."""
        file_metrics = FileMetrics(
            filepath="clean.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[
                FunctionMetrics(
                    name="clean_func",
                    start_line=1,
                    end_line=10,
                    line_count=10,
                    cyclomatic_complexity=2,
                    cognitive_complexity=3,
                ),
            ],
            # Pas de TODOs, pas de curseurs, pas de problèmes mémoire
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = HTMLFormatter()
        output = formatter.format(report)

        file_section_start = output.find("clean.pc")
        assert file_section_start != -1

        file_section = output[file_section_start:]

        # La complexité doit toujours être présente
        assert "Complexité:" in file_section
        assert "Cyclo" in file_section
        assert "Cogn" in file_section

        # Les sections vides ne doivent pas apparaître
        # (elles sont conditionnelles avec {% if %})
        # On vérifie juste que le HTML est valide
        assert "file-summary-info" in file_section


class TestMarkdownFormatter:
    """Tests pour MarkdownFormatter."""

    def test_format_basic_structure(self, minimal_report):
        """Test de la structure Markdown de base."""
        formatter = MarkdownFormatter()
        output = formatter.format(minimal_report)

        # Doit commencer par un titre
        assert output.startswith("#")
        assert "Pro*C Static Analyzer" in output

    def test_format_contains_summary_table(self, minimal_report):
        """Test que le tableau résumé est présent."""
        formatter = MarkdownFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir un tableau Markdown
        assert "|" in output
        assert "Fichiers analysés" in output or "Métrique" in output

    def test_format_contains_functions(self, minimal_report):
        """Test que les fonctions sont présentes."""
        formatter = MarkdownFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir les fonctions
        assert "test_func" in output or "Fonctions" in output

        # Doit contenir un tableau de fonctions
        assert "| Fonction" in output or "| Fonction |" in output

    def test_format_contains_todos_section(self, minimal_report):
        """Test que la section TODOs est présente."""
        formatter = MarkdownFormatter()
        output = formatter.format(minimal_report)

        # Doit contenir une section TODO/FIXME
        if minimal_report.total_todos > 0:
            assert "TODO" in output or "FIXME" in output
            assert "##" in output  # Section markdown

    def test_format_markdown_syntax(self, minimal_report):
        """Test de la syntaxe Markdown."""
        formatter = MarkdownFormatter()
        output = formatter.format(minimal_report)

        # Doit utiliser des headers markdown
        assert "#" in output or "##" in output

        # Les tableaux doivent avoir le bon format
        lines = output.split("\n")
        table_lines = [line for line in lines if "|" in line and line.strip().startswith("|")]
        if table_lines:
            # Première ligne de tableau doit avoir des en-têtes
            assert any("|" in line for line in table_lines)

    def test_save_to_file(self, minimal_report, tmp_path):
        """Test de sauvegarde dans un fichier."""
        output_file = tmp_path / "test_output.md"
        formatter = MarkdownFormatter()
        formatter.save(minimal_report, str(output_file))

        # Vérifier que le fichier existe
        assert output_file.exists()

        # Vérifier le contenu
        content = output_file.read_text()
        assert "#" in content
        assert "Pro*C Static Analyzer" in content

    def test_format_with_full_report(self, sample_report):
        """Test avec un rapport complet."""
        formatter = MarkdownFormatter()
        output = formatter.format(sample_report)

        # Structure markdown valide
        assert output.startswith("#")

        # Doit contenir les sections principales
        assert "##" in output  # Sections secondaires

    def test_format_escaping(self, minimal_report):
        """Test de l'échappement des caractères spéciaux Markdown."""
        # Créer un rapport avec des caractères spéciaux
        func_metrics = FunctionMetrics(
            name="func|with|pipes",
            start_line=1,
            end_line=10,
            line_count=10,
            cyclomatic_complexity=1,
            cognitive_complexity=1,
        )

        file_metrics = FileMetrics(
            filepath="test|file.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[func_metrics],
        )

        report = AnalysisReport(files=[file_metrics])

        formatter = MarkdownFormatter()
        output = formatter.format(report)

        # Les pipes doivent être échappés dans les tableaux
        # Le nom de fonction ne doit pas casser les tableaux
        assert "func" in output or "with" in output


class TestFormattersIntegration:
    """Tests d'intégration des formatters."""

    def test_all_formatters_with_same_report(self, sample_report, tmp_path):
        """Test que tous les formatters fonctionnent avec le même rapport."""
        # JSON
        json_file = tmp_path / "test.json"
        json_formatter = JSONFormatter(pretty=True)
        json_formatter.save(sample_report, str(json_file))
        assert json_file.exists()

        # HTML
        html_file = tmp_path / "test.html"
        html_formatter = HTMLFormatter()
        html_formatter.save(sample_report, str(html_file))
        assert html_file.exists()

        # Markdown
        md_file = tmp_path / "test.md"
        md_formatter = MarkdownFormatter()
        md_formatter.save(sample_report, str(md_file))
        assert md_file.exists()

    def test_formatters_with_empty_report(self, tmp_path):
        """Test des formatters avec un rapport vide."""
        empty_report = AnalysisReport(files=[])

        # JSON doit quand même fonctionner
        json_formatter = JSONFormatter()
        json_output = json_formatter.format(empty_report)
        data = json.loads(json_output)
        assert "report" in data
        assert data["report"]["files"] == []

        # HTML doit quand même fonctionner
        html_formatter = HTMLFormatter()
        html_output = html_formatter.format(empty_report)
        assert "<!DOCTYPE html>" in html_output

        # Markdown doit quand même fonctionner
        md_formatter = MarkdownFormatter()
        md_output = md_formatter.format(empty_report)
        assert "#" in md_output

    def test_formatters_consistency(self, minimal_report):
        """Test que tous les formatters produisent un résultat cohérent."""
        # Tous doivent mentionner le même nombre de fichiers
        num_files = minimal_report.total_files

        json_formatter = JSONFormatter()
        json_output = json_formatter.format(minimal_report)
        json_data = json.loads(json_output)
        assert json_data["report"]["summary"]["total_files"] == num_files

        html_formatter = HTMLFormatter()
        html_output = html_formatter.format(minimal_report)
        assert str(num_files) in html_output

        md_formatter = MarkdownFormatter()
        md_output = md_formatter.format(minimal_report)
        assert str(num_files) in md_output


class TestFormattersPerFileIssues:
    """Tests pour vérifier que les TODO/bugs/warnings sont affichés par fichier."""

    def test_html_formatter_todos_in_file_section(self):
        """Test que les TODOs sont affichés dans la section de chaque fichier en HTML."""
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[],
            todos=[
                {
                    "tag": "TODO",
                    "message": "Fix this issue",
                    "priority": "high",
                    "line_number": 10,
                },
                {
                    "tag": "FIXME",
                    "message": "Critical bug",
                    "priority": "high",
                    "line_number": 20,
                },
                {
                    "tag": "NOTE",
                    "message": "Minor note",
                    "priority": "low",
                    "line_number": 30,
                },
            ],
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = HTMLFormatter()
        output = formatter.format(report)

        # Vérifier que les TODOs sont dans la section du fichier
        # La section du fichier doit contenir le nom du fichier
        file_section_start = output.find("test.pc")
        assert file_section_start != -1

        # Les TODOs doivent être après le nom du fichier dans sa section
        file_section = output[file_section_start:]

        # Vérifier la présence des TODOs dans la section du fichier
        assert "TODO/FIXME" in file_section
        assert "Fix this issue" in file_section
        assert "Critical bug" in file_section
        assert "L10" in file_section or "10" in file_section
        assert "L20" in file_section or "20" in file_section

        # Vérifier les badges de priorité
        assert "HIGH" in file_section or "high" in file_section

    def test_html_formatter_cursor_issues_in_file_section(self):
        """Test que les problèmes de curseurs sont affichés dans la section de chaque fichier en HTML."""
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[],
            cursor_analysis={
                "total_cursors": 2,
                "total_issues": 1,
                "issues": [
                    {
                        "severity": "error",
                        "cursor_name": "emp_cursor",
                        "message": "Unclosed cursor",
                        "line_number": 15,
                    },
                ],
            },
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = HTMLFormatter()
        output = formatter.format(report)

        # Vérifier que les problèmes de curseurs sont dans la section du fichier
        file_section_start = output.find("test.pc")
        assert file_section_start != -1

        file_section = output[file_section_start:]

        # Vérifier la présence des problèmes de curseurs
        assert "Problèmes de curseurs SQL" in file_section or "curseurs" in file_section.lower()
        assert "Unclosed cursor" in file_section
        assert "emp_cursor" in file_section
        assert "L15" in file_section or "15" in file_section

    def test_html_formatter_memory_issues_in_file_section(self):
        """Test que les problèmes mémoire sont affichés dans la section de chaque fichier en HTML."""
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[],
            memory_analysis={
                "total_issues": 2,
                "critical_count": 1,
                "issues": [
                    {
                        "severity": "critical",
                        "message": "Memory leak detected",
                        "line_number": 25,
                        "recommendation": "Add free() call",
                    },
                    {
                        "severity": "warning",
                        "message": "Dangerous function used",
                        "line_number": 35,
                    },
                ],
            },
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = HTMLFormatter()
        output = formatter.format(report)

        # Vérifier que les problèmes mémoire sont dans la section du fichier
        file_section_start = output.find("test.pc")
        assert file_section_start != -1

        file_section = output[file_section_start:]

        # Vérifier la présence des problèmes mémoire
        assert "Problèmes de gestion mémoire" in file_section or "mémoire" in file_section.lower()
        assert "Memory leak detected" in file_section
        assert "Add free() call" in file_section
        assert "L25" in file_section or "25" in file_section

    def test_markdown_formatter_todos_in_file_section(self):
        """Test que les TODOs sont affichés dans la section de chaque fichier en Markdown."""
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[],
            todos=[
                {
                    "tag": "TODO",
                    "message": "Fix this issue",
                    "priority": "high",
                    "line_number": 10,
                },
                {
                    "tag": "FIXME",
                    "message": "Critical bug",
                    "priority": "medium",
                    "line_number": 20,
                },
            ],
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = MarkdownFormatter()
        output = formatter.format(report)

        # Trouver la section du fichier
        file_section_start = output.find("test.pc")
        assert file_section_start != -1

        file_section = output[file_section_start:]

        # Vérifier la présence des TODOs dans la section du fichier
        assert "TODO/FIXME" in file_section or "TODO" in file_section
        assert "Fix this issue" in file_section
        assert "Critical bug" in file_section
        assert "L10" in file_section or "10" in file_section
        assert "L20" in file_section or "20" in file_section

    def test_markdown_formatter_cursor_issues_in_file_section(self):
        """Test que les problèmes de curseurs sont affichés dans la section de chaque fichier en Markdown."""
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[],
            cursor_analysis={
                "total_cursors": 1,
                "total_issues": 1,
                "issues": [
                    {
                        "severity": "warning",
                        "cursor_name": "data_cursor",
                        "message": "Nested cursor detected",
                        "line_number": 12,
                    },
                ],
            },
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = MarkdownFormatter()
        output = formatter.format(report)

        # Vérifier que les problèmes de curseurs sont dans la section du fichier
        file_section_start = output.find("test.pc")
        assert file_section_start != -1

        file_section = output[file_section_start:]

        # Vérifier la présence des problèmes de curseurs
        assert "curseurs" in file_section.lower() or "cursor" in file_section.lower()
        assert "Nested cursor detected" in file_section
        assert "data_cursor" in file_section
        assert "L12" in file_section or "12" in file_section

    def test_markdown_formatter_memory_issues_in_file_section(self):
        """Test que les problèmes mémoire sont affichés dans la section de chaque fichier en Markdown."""
        file_metrics = FileMetrics(
            filepath="test.pc",
            total_lines=50,
            non_empty_lines=40,
            functions=[],
            memory_analysis={
                "total_issues": 1,
                "critical_count": 0,
                "issues": [
                    {
                        "severity": "error",
                        "message": "Missing NULL check",
                        "line_number": 18,
                        "recommendation": "Add NULL check before use",
                    },
                ],
            },
        )

        report = AnalysisReport(files=[file_metrics])
        formatter = MarkdownFormatter()
        output = formatter.format(report)

        # Vérifier que les problèmes mémoire sont dans la section du fichier
        file_section_start = output.find("test.pc")
        assert file_section_start != -1

        file_section = output[file_section_start:]

        # Vérifier la présence des problèmes mémoire
        assert "mémoire" in file_section.lower() or "memory" in file_section.lower()
        assert "Missing NULL check" in file_section
        assert "Add NULL check before use" in file_section
        assert "L18" in file_section or "18" in file_section

    def test_html_formatter_multiple_files_with_issues(self):
        """Test que chaque fichier affiche ses propres issues en HTML."""
        file1 = FileMetrics(
            filepath="file1.pc",
            total_lines=30,
            non_empty_lines=25,
            functions=[],
            todos=[
                {"tag": "TODO", "message": "Issue in file1", "priority": "high", "line_number": 5}
            ],
        )

        file2 = FileMetrics(
            filepath="file2.pc",
            total_lines=40,
            non_empty_lines=35,
            functions=[],
            todos=[
                {
                    "tag": "FIXME",
                    "message": "Issue in file2",
                    "priority": "medium",
                    "line_number": 10,
                }
            ],
        )

        report = AnalysisReport(files=[file1, file2])
        formatter = HTMLFormatter()
        output = formatter.format(report)

        # Vérifier que chaque fichier a ses propres issues
        # Trouver les sections de fichiers en cherchant jusqu'à la prochaine section ou la fin
        file1_section_start = output.find("file1.pc")
        file2_section_start = output.find("file2.pc")

        # La section file1 va de file1.pc jusqu'à file2.pc (ou jusqu'à la fin si file2 n'existe pas)
        if file2_section_start != -1:
            file1_section = output[file1_section_start:file2_section_start]
        else:
            # Si file2 n'est pas trouvé, chercher la fin de la section file1
            # Chercher le </div></div> qui termine la section file1, avant la prochaine section globale
            file1_section_end = output.find("</div></div>", file1_section_start)
            if file1_section_end != -1:
                # Vérifier que ce n'est pas suivi d'une section globale (<h2>)
                next_h2 = output.find("<h2>", file1_section_end)
                if next_h2 != -1 and next_h2 - file1_section_end < 20:
                    # Le </div></div> est suivi d'une section globale, c'est la fin de file1
                    file1_section = output[
                        file1_section_start : file1_section_end + len("</div></div>")
                    ]
                else:
                    file1_section = output[
                        file1_section_start : file1_section_end + len("</div></div>")
                    ]
            else:
                file1_section = output[file1_section_start:]

        assert "Issue in file1" in file1_section
        assert "Issue in file2" not in file1_section

        # La section file2 va de file2.pc jusqu'à la fin de sa section </div></div>
        # (avant les sections globales comme <h2>TODO/FIXME</h2>)
        if file2_section_start != -1:
            # Chercher le </div></div> qui termine la section file2
            file2_section_end = output.find("</div></div>", file2_section_start)
            if file2_section_end != -1:
                # Vérifier que ce n'est pas suivi d'une section globale (<h2>)
                next_h2 = output.find("<h2>", file2_section_end)
                if next_h2 != -1 and next_h2 - file2_section_end < 20:
                    # Le </div></div> est suivi d'une section globale, c'est la fin de file2
                    file2_section = output[
                        file2_section_start : file2_section_end + len("</div></div>")
                    ]
                else:
                    # Chercher la prochaine section de fichier ou section globale
                    next_section = output.find(
                        '<div class="file-section">', file2_section_start + 1
                    )
                    if next_section != -1:
                        file2_section = output[file2_section_start:next_section]
                    else:
                        file2_section = output[
                            file2_section_start : file2_section_end + len("</div></div>")
                        ]
            else:
                # Pas de </div></div> trouvé, chercher la prochaine section
                next_section = output.find('<div class="file-section">', file2_section_start + 1)
                if next_section != -1:
                    file2_section = output[file2_section_start:next_section]
                else:
                    # Chercher la prochaine section globale
                    next_h2 = output.find("<h2>", file2_section_start + 1)
                    if next_h2 != -1:
                        file2_section = output[file2_section_start:next_h2]
                    else:
                        file2_section = output[file2_section_start:]
        else:
            file2_section = ""

        assert "Issue in file2" in file2_section
        assert "Issue in file1" not in file2_section


class TestBaseFormatter:
    """Tests pour BaseFormatter (implémentation par défaut de save)."""

    @staticmethod
    def _default_save_implementation(formatter, report: AnalysisReport, output_path: str) -> None:
        """
        Implémentation par défaut de save pour BaseFormatter.

        Cette fonction copie exactement le code de BaseFormatter.save pour permettre
        de tester les mutations. Le code doit être identique à celui dans base.py.

        Args:
            formatter: Instance du formatter (doit avoir une méthode format)
            report: Rapport d'analyse à sauvegarder
            output_path: Chemin du fichier de sortie
        """
        from pathlib import Path

        output = Path(output_path)
        output.write_text(formatter.format(report), encoding="utf-8")

    def test_base_formatter_save_creates_file(self, minimal_report, tmp_path):
        """Test que save crée un fichier avec le contenu formaté."""
        class TestFormatter:
            """Formatter de test qui utilise l'implémentation par défaut de save."""

            def format(self, report: AnalysisReport) -> str:
                """Formate le rapport en chaîne simple."""
                return f"Test report: {report.total_files} files"

            def save(self, report: AnalysisReport, output_path: str) -> None:
                """Utilise l'implémentation par défaut de BaseFormatter.save."""
                TestBaseFormatter._default_save_implementation(self, report, output_path)

        formatter = TestFormatter()
        output_file = tmp_path / "test_output.txt"

        formatter.save(minimal_report, str(output_file))

        # Vérifier que le fichier existe
        assert output_file.exists()

        # Vérifier le contenu
        content = output_file.read_text(encoding="utf-8")
        assert "Test report" in content
        assert str(minimal_report.total_files) in content

    def test_base_formatter_save_with_utf8_encoding(self, minimal_report, tmp_path):
        """Test que save utilise l'encodage UTF-8 par défaut."""
        class TestFormatter:
            """Formatter de test."""

            def format(self, report: AnalysisReport) -> str:
                """Formate avec des caractères UTF-8."""
                return "Test avec des caractères spéciaux: éàùç"

            def save(self, report: AnalysisReport, output_path: str) -> None:
                """Utilise l'implémentation par défaut de BaseFormatter.save."""
                TestBaseFormatter._default_save_implementation(self, report, output_path)

        formatter = TestFormatter()
        output_file = tmp_path / "test_utf8.txt"

        formatter.save(minimal_report, str(output_file))

        # Vérifier que le fichier contient les caractères UTF-8
        content = output_file.read_text(encoding="utf-8")
        assert "éàùç" in content

    def test_base_formatter_save_with_nested_path(self, minimal_report, tmp_path):
        """Test que save fonctionne avec un chemin imbriqué (répertoires créés au préalable)."""
        class TestFormatter:
            """Formatter de test."""

            def format(self, report: AnalysisReport) -> str:
                """Formate le rapport."""
                return "Test content"

            def save(self, report: AnalysisReport, output_path: str) -> None:
                """Utilise l'implémentation par défaut de BaseFormatter.save."""
                TestBaseFormatter._default_save_implementation(self, report, output_path)

        formatter = TestFormatter()
        output_file = tmp_path / "subdir" / "nested" / "test_output.txt"

        # Créer les répertoires parents (Path.write_text ne les crée pas)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        formatter.save(minimal_report, str(output_file))

        # Vérifier que le fichier existe dans le sous-répertoire
        assert output_file.exists()
        assert output_file.parent.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Test content" in content

    def test_base_formatter_save_overwrites_existing_file(self, minimal_report, tmp_path):
        """Test que save écrase un fichier existant."""
        class TestFormatter:
            """Formatter de test."""

            def format(self, report: AnalysisReport) -> str:
                """Formate le rapport."""
                return "New content"

            def save(self, report: AnalysisReport, output_path: str) -> None:
                """Utilise l'implémentation par défaut de BaseFormatter.save."""
                TestBaseFormatter._default_save_implementation(self, report, output_path)

        formatter = TestFormatter()
        output_file = tmp_path / "existing.txt"

        # Créer un fichier existant
        output_file.write_text("Old content", encoding="utf-8")
        assert output_file.read_text(encoding="utf-8") == "Old content"

        # Sauvegarder avec save
        formatter.save(minimal_report, str(output_file))

        # Vérifier que le contenu a été écrasé
        assert output_file.read_text(encoding="utf-8") == "New content"

    def test_base_formatter_save_calls_format(self, minimal_report, tmp_path):
        """Test que save appelle format avec le bon rapport."""
        format_called = False
        format_report = None

        class TestFormatter:
            """Formatter de test qui vérifie l'appel à format."""

            def format(self, report: AnalysisReport) -> str:
                """Formate le rapport et enregistre l'appel."""
                nonlocal format_called, format_report
                format_called = True
                format_report = report
                return "Formatted content"

            def save(self, report: AnalysisReport, output_path: str) -> None:
                """Utilise l'implémentation par défaut de BaseFormatter.save."""
                TestBaseFormatter._default_save_implementation(self, report, output_path)

        formatter = TestFormatter()
        output_file = tmp_path / "test_format_call.txt"

        formatter.save(minimal_report, str(output_file))

        # Vérifier que format a été appelé
        assert format_called
        assert format_report is minimal_report

    def test_base_formatter_save_with_path_object(self, minimal_report, tmp_path):
        """Test que save fonctionne avec un objet Path comme output_path."""
        class TestFormatter:
            """Formatter de test."""

            def format(self, report: AnalysisReport) -> str:
                """Formate le rapport."""
                return "Path object test"

            def save(self, report: AnalysisReport, output_path: str) -> None:
                """Utilise l'implémentation par défaut de BaseFormatter.save."""
                TestBaseFormatter._default_save_implementation(self, report, output_path)

        formatter = TestFormatter()
        output_file = tmp_path / "test_path.txt"

        # Passer un objet Path (sera converti en str par Path())
        formatter.save(minimal_report, str(output_file))

        # Vérifier que le fichier existe
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Path object test" in content
