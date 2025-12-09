"""
Tests d'intégration pour le module analyzer.
"""

import json
import pytest
from pathlib import Path
from proc_analyzer.analyzer import (
    ProCAnalyzer,
    FunctionMetrics,
    FileMetrics,
    AnalysisReport,
)


class TestProCAnalyzer:
    """Tests pour la classe ProCAnalyzer."""

    def test_analyze_source_simple(self):
        """Test d'analyse d'une source simple."""
        source = """
int add(int a, int b) {
    return a + b;
}
"""
        analyzer = ProCAnalyzer()
        metrics = analyzer.analyze_source(source, "test.c")

        assert metrics is not None
        assert len(metrics.functions) == 1
        assert metrics.functions[0].name == "add"

    def test_analyze_source_with_proc(self, simple_proc_source):
        """Test d'analyse avec code Pro*C."""
        analyzer = ProCAnalyzer()
        metrics = analyzer.analyze_source(simple_proc_source, "test.pc")

        assert metrics is not None
        assert metrics.total_sql_blocks > 0

    def test_analyze_file(self, tmp_proc_file):
        """Test d'analyse d'un fichier réel."""
        analyzer = ProCAnalyzer()
        metrics = analyzer.analyze_file(str(tmp_proc_file))

        assert metrics is not None
        assert metrics.filepath == str(tmp_proc_file)

    def test_analyze_directory(self, tmp_path, simple_proc_source):
        """Test d'analyse d'un répertoire."""
        # Créer plusieurs fichiers
        (tmp_path / "file1.pc").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(
            """
int multiply(int a, int b) {
    return a * b;
}
"""
        )

        analyzer = ProCAnalyzer()
        report = analyzer.analyze_directory(str(tmp_path), "*.pc")

        assert report is not None
        assert len(report.files) == 2

    def test_analyze_directory_with_progress_callback(self, tmp_path, simple_proc_source):
        """Test que le callback de progression est appelé."""
        (tmp_path / "file1.pc").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(simple_proc_source)
        
        analyzer = ProCAnalyzer()
        callback_calls = []
        
        def progress_callback(filepath: str, current: int, total: int):
            callback_calls.append((filepath, current, total))
        
        report = analyzer.analyze_directory(
            str(tmp_path), 
            "*.pc",
            progress_callback=progress_callback
        )
        
        assert report is not None
        assert len(report.files) == 2
        assert len(callback_calls) == 2
        # Vérifier que le callback a été appelé avec les bons paramètres
        assert callback_calls[0][1] == 1  # current = 1
        assert callback_calls[0][2] == 2  # total = 2
        assert callback_calls[1][1] == 2  # current = 2
        assert callback_calls[1][2] == 2  # total = 2

    def test_disabled_features(self):
        """Test avec features désactivées."""
        source = """
int process(void) {
    char *ptr = malloc(100);
    // TODO: Fix this
    EXEC SQL SELECT * FROM t;
    return 0;
}
"""
        analyzer = ProCAnalyzer(
            enable_halstead=False,
            enable_todos=False,
            enable_cursors=False,
            enable_memory=False,
        )
        metrics = analyzer.analyze_source(source, "test.pc")

        assert metrics is not None
        # Les fonctions doivent être analysées
        assert len(metrics.functions) >= 1

    def test_file_metrics_aggregation(self):
        """Test des agrégations de métriques."""
        source = """
void func1(void) {
}

int func2(int x) {
    if (x > 0) {
        if (x > 10) {
            return 2;
        }
        return 1;
    }
    return 0;
}

int func3(int a, int b) {
    return a + b;
}
"""
        analyzer = ProCAnalyzer()
        metrics = analyzer.analyze_source(source, "test.c")

        assert metrics is not None
        assert len(metrics.functions) == 3

        # Vérifier les agrégations
        assert metrics.max_cyclomatic >= 1
        assert metrics.avg_cyclomatic >= 1.0
        assert metrics.total_lines > 0

    def test_analyze_files(self, tmp_path):
        """Test d'analyse de plusieurs fichiers spécifiés."""
        file1 = tmp_path / "a.pc"
        file2 = tmp_path / "b.pc"

        file1.write_text("int f1(void) { return 0; }")
        file2.write_text("int f2(void) { return 1; }")

        analyzer = ProCAnalyzer()
        report = analyzer.analyze_files([str(file1), str(file2)])

        assert len(report.files) == 2

    def test_complexity_analysis(self, complex_function_source):
        """Test de l'analyse de complexité."""
        analyzer = ProCAnalyzer(enable_halstead=True)
        metrics = analyzer.analyze_source(complex_function_source, "test.c")

        assert len(metrics.functions) == 1
        func = metrics.functions[0]

        # La fonction complexe devrait avoir une complexité > 1
        assert func.cyclomatic_complexity > 1
        assert func.cognitive_complexity >= 0

        # Halstead devrait être calculé
        if func.halstead:
            assert func.halstead["volume"] > 0


class TestFunctionMetrics:
    """Tests pour la dataclass FunctionMetrics."""

    def test_function_metrics_to_dict(self):
        """Test de sérialisation."""
        metrics = FunctionMetrics(
            name="test_func",
            start_line=1,
            end_line=10,
            line_count=10,
            cyclomatic_complexity=5,
            cognitive_complexity=3,
            sql_blocks_count=2,
        )

        d = metrics.to_dict()

        assert d["name"] == "test_func"
        assert d["cyclomatic_complexity"] == 5
        assert d["cognitive_complexity"] == 3
        assert d["sql_blocks_count"] == 2


class TestFileMetrics:
    """Tests pour la dataclass FileMetrics."""

    def test_file_metrics_properties(self):
        """Test des propriétés calculées."""
        file_metrics = FileMetrics(
            filepath="/test.pc",
            total_lines=100,
            non_empty_lines=80,
        )

        # Ajouter quelques fonctions
        file_metrics.functions.append(
            FunctionMetrics(
                name="f1",
                start_line=1,
                end_line=10,
                line_count=10,
                cyclomatic_complexity=2,
                cognitive_complexity=1,
            )
        )
        file_metrics.functions.append(
            FunctionMetrics(
                name="f2",
                start_line=15,
                end_line=30,
                line_count=16,
                cyclomatic_complexity=5,
                cognitive_complexity=4,
            )
        )

        assert file_metrics.function_count == 2
        assert file_metrics.max_cyclomatic == 5
        assert file_metrics.max_cognitive == 4
        assert file_metrics.avg_cyclomatic == 3.5  # (2+5)/2

    def test_file_metrics_to_dict(self):
        """Test de sérialisation."""
        file_metrics = FileMetrics(
            filepath="/test.pc",
            total_lines=100,
            non_empty_lines=80,
        )

        d = file_metrics.to_dict()

        assert d["filepath"] == "/test.pc"
        assert d["total_lines"] == 100
        assert "functions" in d


class TestAnalysisReport:
    """Tests pour la dataclass AnalysisReport."""

    def test_report_to_json(self, tmp_path, simple_proc_source):
        """Test d'export JSON."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(simple_proc_source)

        analyzer = ProCAnalyzer()
        report = analyzer.analyze_directory(str(tmp_path), "*.pc")

        json_str = report.to_json()
        data = json.loads(json_str)

        assert "files" in data
        assert len(data["files"]) > 0

    def test_report_to_csv_rows(self, tmp_path):
        """Test d'export CSV."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(
            """
int func(int x) {
    if (x > 0) return 1;
    return 0;
}
"""
        )

        analyzer = ProCAnalyzer()
        report = analyzer.analyze_directory(str(tmp_path), "*.pc")

        rows = list(report.to_csv_rows())

        # Au moins une ligne d'en-tête et une de données
        assert len(rows) >= 1

    def test_get_high_complexity_functions(self, tmp_path):
        """Test du filtrage par complexité."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(
            """
void simple(void) {
}

int complex_func(int a, int b, int c, int d) {
    if (a > 0) {
        if (b > 0) {
            if (c > 0) {
                if (d > 0) {
                    return 1;
                }
            }
        }
    }
    return 0;
}
"""
        )

        analyzer = ProCAnalyzer()
        report = analyzer.analyze_directory(str(tmp_path), "*.pc")

        high_complexity = report.get_high_complexity_functions(
            cyclo_threshold=3, cognitive_threshold=5
        )

        # La fonction 'complex_func' devrait être dans la liste (tuple: filepath, FunctionMetrics)
        assert any(func.name == "complex_func" for _, func in high_complexity)

    def test_get_all_todos(self, tmp_path):
        """Test de récupération de tous les TODOs."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(
            """
// TODO: First todo
// FIXME: Critical fix needed
void func(void) {
    // TODO: Another todo
}
"""
        )

        analyzer = ProCAnalyzer(enable_todos=True)
        report = analyzer.analyze_directory(str(tmp_path), "*.pc")

        todos = report.get_all_todos()

        assert len(todos) >= 2

    def test_parse_errors_handled(self, tmp_path):
        """Test que les erreurs de parsing sont gérées."""
        file_path = tmp_path / "broken.pc"
        file_path.write_text(
            """
int broken(void {
    return
}
"""
        )

        analyzer = ProCAnalyzer()
        metrics = analyzer.analyze_file(str(file_path))

        # Le fichier devrait être analysé malgré les erreurs
        assert metrics is not None
        assert metrics.parse_errors is True


class TestIntegration:
    """Tests d'intégration complets."""

    def test_full_analysis_pipeline(self, tmp_path):
        """Test du pipeline complet d'analyse."""
        # Créer un fichier Pro*C complet
        source = """
/*
 * Module: test.pc
 * Description: Test module
 * Author: Test
 */

#include <stdio.h>
#include <stdlib.h>

EXEC SQL INCLUDE sqlca;

EXEC SQL BEGIN DECLARE SECTION;
    int emp_id;
    char emp_name[50];
EXEC SQL END DECLARE SECTION;

// TODO: Add error handling
void fetch_data(void) {
    char *buffer = malloc(100);

    EXEC SQL DECLARE emp_cursor CURSOR FOR
        SELECT id, name FROM employees;

    EXEC SQL OPEN emp_cursor;

    while (1) {
        EXEC SQL FETCH emp_cursor INTO :emp_id, :emp_name;
        if (sqlca.sqlcode != 0) break;

        if (emp_id > 0) {
            printf("%s\\n", emp_name);
        }
    }

    EXEC SQL CLOSE emp_cursor;
    free(buffer);
}

int main(void) {
    fetch_data();
    return 0;
}
"""
        file_path = tmp_path / "complete.pc"
        file_path.write_text(source)

        # Analyse complète
        analyzer = ProCAnalyzer(
            enable_halstead=True,
            enable_todos=True,
            enable_cursors=True,
            enable_memory=True,
        )
        report = analyzer.analyze_directory(str(tmp_path), "*.pc")

        # Vérifications
        assert len(report.files) == 1
        file_metrics = report.files[0]

        # Fonctions détectées
        assert file_metrics.function_count >= 2

        # SQL blocs
        assert file_metrics.total_sql_blocks > 0

        # TODOs
        todos = report.get_all_todos()
        assert len(todos) >= 1

        # Export JSON
        json_data = json.loads(report.to_json())
        assert "files" in json_data
