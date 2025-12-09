"""
Tests pour le module cursors.
"""

from proc_analyzer.cursors import (
    CursorAnalysisResult,
    CursorAnalyzer,
    CursorInfo,
    CursorIssue,
    CursorIssueType,
    analyze_cursors,
)


class TestCursorAnalyzer:
    """Tests pour la classe CursorAnalyzer."""

    def test_analyze_simple_cursor(self):
        """Test d'un curseur simple avec DECLARE, OPEN, FETCH, CLOSE."""
        source = """
EXEC SQL DECLARE emp_cursor CURSOR FOR
    SELECT id, name FROM employees;

EXEC SQL OPEN emp_cursor;

EXEC SQL FETCH emp_cursor INTO :emp_id, :emp_name;

if (sqlca.sqlcode != 0) {
    break;
}

EXEC SQL CLOSE emp_cursor;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        assert result.total_cursors == 1
        cursor = result.cursors[0]
        assert cursor.name == "emp_cursor"
        assert len(cursor.open_lines) == 1
        assert len(cursor.fetch_lines) == 1
        assert len(cursor.close_lines) == 1

    def test_analyze_cursor_lifecycle(self):
        """Test du cycle de vie complet d'un curseur."""
        source = """
EXEC SQL DECLARE my_cursor CURSOR FOR SELECT * FROM t;
EXEC SQL OPEN my_cursor;
EXEC SQL FETCH my_cursor INTO :var;
if (sqlca.sqlcode == 0) {
    process();
}
EXEC SQL CLOSE my_cursor;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        assert result.total_cursors == 1
        cursor = result.cursors[0]
        assert cursor.name == "my_cursor"
        assert len(cursor.close_lines) == 1  # Curseur fermé

    def test_detect_unclosed_cursor(self):
        """Test de détection d'un curseur non fermé."""
        source = """
EXEC SQL DECLARE leak_cursor CURSOR FOR SELECT * FROM t;
EXEC SQL OPEN leak_cursor;
EXEC SQL FETCH leak_cursor INTO :var;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        # Devrait avoir un issue UNCLOSED_CURSOR
        unclosed_issues = [
            i for i in result.issues if i.issue_type == CursorIssueType.UNCLOSED_CURSOR
        ]
        assert len(unclosed_issues) >= 1

    def test_detect_nested_cursor(self):
        """Test de détection d'un curseur imbriqué."""
        source = """
EXEC SQL DECLARE outer_cursor CURSOR FOR SELECT id FROM t1;
EXEC SQL DECLARE inner_cursor CURSOR FOR SELECT name FROM t2;

EXEC SQL OPEN outer_cursor;

while (1) {
    EXEC SQL FETCH outer_cursor INTO :id;
    if (sqlca.sqlcode != 0) break;

    EXEC SQL OPEN inner_cursor;
    EXEC SQL FETCH inner_cursor INTO :name;
    EXEC SQL CLOSE inner_cursor;
}

EXEC SQL CLOSE outer_cursor;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        # Devrait détecter que inner_cursor est ouvert dans une boucle FETCH
        nested_issues = [i for i in result.issues if i.issue_type == CursorIssueType.NESTED_CURSOR]
        assert len(nested_issues) >= 1

    def test_detect_fetch_without_check(self):
        """Test de détection FETCH sans vérification SQLCODE."""
        source = """
EXEC SQL DECLARE my_cursor CURSOR FOR SELECT * FROM t;
EXEC SQL OPEN my_cursor;
EXEC SQL FETCH my_cursor INTO :var;
process_data();
EXEC SQL CLOSE my_cursor;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        # Devrait signaler FETCH sans check SQLCODE
        fetch_issues = [
            i for i in result.issues if i.issue_type == CursorIssueType.FETCH_WITHOUT_CHECK
        ]
        assert len(fetch_issues) >= 1

    def test_detect_reopen_without_close(self):
        """Test de détection de réouverture sans fermeture."""
        source = """
EXEC SQL DECLARE my_cursor CURSOR FOR SELECT * FROM t;
EXEC SQL OPEN my_cursor;
EXEC SQL FETCH my_cursor INTO :var;
EXEC SQL OPEN my_cursor;
EXEC SQL CLOSE my_cursor;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        # Devrait signaler plus d'OPEN que de CLOSE
        # Il peut y avoir un warning pour plus d'OPEN que de CLOSE
        assert result.total_issues >= 1

    def test_dynamic_cursor(self):
        """Test de détection de curseur dynamique avec PREPARE."""
        source = """
EXEC SQL PREPARE stmt FROM :sql_text;
EXEC SQL DECLARE dyn_cursor CURSOR FOR stmt;
EXEC SQL OPEN dyn_cursor;
EXEC SQL FETCH dyn_cursor INTO :var;
if (sqlca.sqlcode != 0) break;
EXEC SQL CLOSE dyn_cursor;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        assert result.total_cursors == 1
        cursor = result.cursors[0]
        assert cursor.name == "dyn_cursor"
        assert cursor.is_dynamic is True

    def test_multiple_cursors(self):
        """Test avec plusieurs curseurs."""
        source = """
EXEC SQL DECLARE cursor1 CURSOR FOR SELECT * FROM t1;
EXEC SQL DECLARE cursor2 CURSOR FOR SELECT * FROM t2;
EXEC SQL DECLARE cursor3 CURSOR FOR SELECT * FROM t3;

EXEC SQL OPEN cursor1;
EXEC SQL OPEN cursor2;
EXEC SQL CLOSE cursor1;
EXEC SQL CLOSE cursor2;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        assert result.total_cursors == 3
        cursor_names = [c.name for c in result.cursors]
        assert "cursor1" in cursor_names
        assert "cursor2" in cursor_names
        assert "cursor3" in cursor_names

    def test_no_cursors(self):
        """Test avec code sans curseurs."""
        source = """
int main(void) {
    EXEC SQL SELECT name INTO :var FROM users WHERE id = 1;
    return 0;
}
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        assert result.total_cursors == 0

    def test_cursor_with_sqlcode_check(self):
        """Test avec vérification correcte de SQLCODE."""
        source = """
EXEC SQL DECLARE my_cursor CURSOR FOR SELECT * FROM t;
EXEC SQL OPEN my_cursor;
while (1) {
    EXEC SQL FETCH my_cursor INTO :var;
    if (sqlca.sqlcode != 0) {
        break;
    }
    process();
}
EXEC SQL CLOSE my_cursor;
"""
        analyzer = CursorAnalyzer()
        result = analyzer.analyze(source)

        # Pas de FETCH_WITHOUT_CHECK car on vérifie sqlca.sqlcode
        fetch_issues = [
            i for i in result.issues if i.issue_type == CursorIssueType.FETCH_WITHOUT_CHECK
        ]
        assert len(fetch_issues) == 0


class TestCursorInfo:
    """Tests pour la dataclass CursorInfo."""

    def test_cursor_info_to_dict(self):
        """Test de sérialisation en dictionnaire."""
        cursor = CursorInfo(
            name="test_cursor",
            declare_line=10,
            select_statement="SELECT * FROM t",
            is_dynamic=False,
        )
        cursor.open_lines.append(15)
        cursor.fetch_lines.append(20)
        cursor.close_lines.append(25)

        d = cursor.to_dict()

        assert d["name"] == "test_cursor"
        assert d["declare_line"] == 10
        assert d["is_dynamic"] is False
        assert d["open_count"] == 1
        assert d["fetch_count"] == 1
        assert d["close_count"] == 1


class TestCursorIssue:
    """Tests pour la dataclass CursorIssue."""

    def test_cursor_issue_to_dict(self):
        """Test de sérialisation en dictionnaire."""
        issue = CursorIssue(
            cursor_name="test_cursor",
            issue_type=CursorIssueType.UNCLOSED_CURSOR,
            line_number=10,
            message="Curseur non fermé",
            severity="warning",
        )

        d = issue.to_dict()

        assert d["cursor_name"] == "test_cursor"
        assert d["issue_type"] == "unclosed_cursor"
        assert d["line_number"] == 10
        assert d["severity"] == "warning"


class TestCursorAnalysisResult:
    """Tests pour la dataclass CursorAnalysisResult."""

    def test_analysis_result_properties(self):
        """Test des propriétés calculées."""
        result = CursorAnalysisResult()
        result.cursors.append(CursorInfo(name="c1", declare_line=1, select_statement="SELECT 1"))
        result.issues.append(
            CursorIssue(
                cursor_name="c1",
                issue_type=CursorIssueType.UNCLOSED_CURSOR,
                line_number=10,
                message="Test",
                severity="error",
            )
        )

        assert result.total_cursors == 1
        assert result.total_issues == 1
        assert result.issues_by_severity["error"] == 1

    def test_analysis_result_to_dict(self):
        """Test de sérialisation complète."""
        result = CursorAnalysisResult()
        result.cursors.append(CursorInfo(name="c1", declare_line=1, select_statement="SELECT 1"))

        d = result.to_dict()

        assert "total_cursors" in d
        assert "total_issues" in d
        assert "cursors" in d


class TestAnalyzeCursors:
    """Tests pour la fonction utilitaire analyze_cursors."""

    def test_analyze_cursors(self):
        """Test de la fonction analyze_cursors."""
        source = """
EXEC SQL DECLARE my_cursor CURSOR FOR SELECT * FROM t;
EXEC SQL OPEN my_cursor;
EXEC SQL FETCH my_cursor INTO :var;
if (sqlca.sqlcode != 0) break;
EXEC SQL CLOSE my_cursor;
"""
        result = analyze_cursors(source)

        assert isinstance(result, CursorAnalysisResult)
        assert result.total_cursors == 1
