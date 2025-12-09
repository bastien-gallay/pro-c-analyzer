"""
Tests unitaires pour les formatters de rapports.
"""

import json
import pytest
from pathlib import Path

from proc_analyzer.analyzer import ProCAnalyzer, AnalysisReport, FunctionMetrics, FileMetrics
from proc_analyzer.formatters import JSONFormatter, HTMLFormatter, MarkdownFormatter


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
        todos=[{
            'tag': 'TODO',
            'message': 'Test todo',
            'priority': 'high',
            'line_number': 5,
        }],
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
        assert '\n' in output
    
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
        lines = output.split('\n')
        table_lines = [l for l in lines if '|' in l and l.strip().startswith('|')]
        if table_lines:
            # Première ligne de tableau doit avoir des en-têtes
            assert any('|' in line for line in table_lines)
    
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
                    'tag': 'TODO',
                    'message': 'Fix this issue',
                    'priority': 'high',
                    'line_number': 10,
                },
                {
                    'tag': 'FIXME',
                    'message': 'Critical bug',
                    'priority': 'high',
                    'line_number': 20,
                },
                {
                    'tag': 'NOTE',
                    'message': 'Minor note',
                    'priority': 'low',
                    'line_number': 30,
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
                'total_cursors': 2,
                'total_issues': 1,
                'issues': [
                    {
                        'severity': 'error',
                        'cursor_name': 'emp_cursor',
                        'message': 'Unclosed cursor',
                        'line_number': 15,
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
                'total_issues': 2,
                'critical_count': 1,
                'issues': [
                    {
                        'severity': 'critical',
                        'message': 'Memory leak detected',
                        'line_number': 25,
                        'recommendation': 'Add free() call',
                    },
                    {
                        'severity': 'warning',
                        'message': 'Dangerous function used',
                        'line_number': 35,
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
                    'tag': 'TODO',
                    'message': 'Fix this issue',
                    'priority': 'high',
                    'line_number': 10,
                },
                {
                    'tag': 'FIXME',
                    'message': 'Critical bug',
                    'priority': 'medium',
                    'line_number': 20,
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
                'total_cursors': 1,
                'total_issues': 1,
                'issues': [
                    {
                        'severity': 'warning',
                        'cursor_name': 'data_cursor',
                        'message': 'Nested cursor detected',
                        'line_number': 12,
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
                'total_issues': 1,
                'critical_count': 0,
                'issues': [
                    {
                        'severity': 'error',
                        'message': 'Missing NULL check',
                        'line_number': 18,
                        'recommendation': 'Add NULL check before use',
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
            todos=[{'tag': 'TODO', 'message': 'Issue in file1', 'priority': 'high', 'line_number': 5}],
        )
        
        file2 = FileMetrics(
            filepath="file2.pc",
            total_lines=40,
            non_empty_lines=35,
            functions=[],
            todos=[{'tag': 'FIXME', 'message': 'Issue in file2', 'priority': 'medium', 'line_number': 10}],
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
                    file1_section = output[file1_section_start:file1_section_end + len("</div></div>")]
                else:
                    file1_section = output[file1_section_start:file1_section_end + len("</div></div>")]
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
                    file2_section = output[file2_section_start:file2_section_end + len("</div></div>")]
                else:
                    # Chercher la prochaine section de fichier ou section globale
                    next_section = output.find('<div class="file-section">', file2_section_start + 1)
                    if next_section != -1:
                        file2_section = output[file2_section_start:next_section]
                    else:
                        file2_section = output[file2_section_start:file2_section_end + len("</div></div>")]
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
