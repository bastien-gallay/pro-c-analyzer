"""
Tests pour le module comments.
"""

from proc_analyzer.comments import (
    CommentAnalyzer,
    ModuleInfo,
    ModuleInventory,
    TodoItem,
    analyze_comments,
)


class TestCommentAnalyzer:
    """Tests pour la classe CommentAnalyzer."""

    def test_analyze_single_todo(self):
        """Test avec un seul TODO."""
        source = """
// TODO: Implement this function
void process(void) {
}
"""
        analyzer = CommentAnalyzer()
        todos, module_info = analyzer.analyze(source, "test.pc")

        assert len(todos) == 1
        assert todos[0].tag == "TODO"
        assert "Implement this function" in todos[0].message
        assert todos[0].priority == "medium"

    def test_analyze_fixme_high_priority(self):
        """Test que FIXME est de priorité haute."""
        source = """
// FIXME: Critical bug here
void broken(void) {
}
"""
        analyzer = CommentAnalyzer()
        todos, _ = analyzer.analyze(source, "test.pc")

        assert len(todos) == 1
        assert todos[0].tag == "FIXME"
        assert todos[0].priority == "high"

    def test_analyze_multiple_tags(self):
        """Test avec plusieurs tags différents."""
        source = """
// TODO: Add feature
// FIXME: Fix this bug
// HACK: Temporary workaround
// NOTE: Important information
// BUG: Known issue
// XXX: Needs attention
"""
        analyzer = CommentAnalyzer()
        todos, _ = analyzer.analyze(source, "test.pc")

        assert len(todos) == 6
        tags = [t.tag for t in todos]
        assert "TODO" in tags
        assert "FIXME" in tags
        assert "HACK" in tags
        assert "NOTE" in tags
        assert "BUG" in tags
        assert "XXX" in tags

    def test_analyze_c_line_comment(self):
        """Test avec commentaire ligne //."""
        source = """
void func(void) {
    // TODO: Line comment todo
    int x = 1;
}
"""
        analyzer = CommentAnalyzer()
        todos, _ = analyzer.analyze(source, "test.pc")

        assert len(todos) == 1
        assert "Line comment todo" in todos[0].message

    def test_analyze_c_block_comment(self):
        """Test avec commentaire bloc /* */."""
        source = """
void func(void) {
    /* TODO: Block comment todo */
    int x = 1;
}
"""
        analyzer = CommentAnalyzer()
        todos, _ = analyzer.analyze(source, "test.pc")

        assert len(todos) == 1
        assert "Block comment todo" in todos[0].message

    def test_analyze_module_header(self):
        """Test d'extraction des métadonnées d'entête."""
        source = """/*
 * Module: test_module.pc
 * Description: This is a test module
 * Author: Test Author
 * Date: 2024-01-01
 * Version: 1.0.0
 */

void func(void) {
}
"""
        analyzer = CommentAnalyzer()
        _, module_info = analyzer.analyze(source, "/path/to/test.pc")

        assert module_info.filename == "test.pc"
        assert module_info.author == "Test Author"
        assert module_info.version == "1.0.0"

    def test_analyze_includes(self):
        """Test de détection des #include."""
        source = """
#include <stdio.h>
#include <stdlib.h>
#include "local.h"

void func(void) {
}
"""
        analyzer = CommentAnalyzer()
        _, module_info = analyzer.analyze(source, "test.pc")

        assert "stdio.h" in module_info.includes
        assert "stdlib.h" in module_info.includes
        assert "local.h" in module_info.includes

    def test_analyze_exec_sql_include(self):
        """Test de détection des EXEC SQL INCLUDE."""
        source = """
EXEC SQL INCLUDE sqlca;
EXEC SQL INCLUDE oraca;

void func(void) {
}
"""
        analyzer = CommentAnalyzer()
        _, module_info = analyzer.analyze(source, "test.pc")

        assert "sqlca" in module_info.exec_sql_includes
        assert "oraca" in module_info.exec_sql_includes

    def test_analyze_no_todos(self):
        """Test sans TODOs."""
        source = """
void func(void) {
    int x = 1;
    return;
}
"""
        analyzer = CommentAnalyzer()
        todos, _ = analyzer.analyze(source, "test.pc")

        assert len(todos) == 0

    def test_get_todos_by_priority(self):
        """Test de regroupement par priorité."""
        source = """
// FIXME: High priority
// TODO: Medium priority
// NOTE: Low priority
"""
        analyzer = CommentAnalyzer()
        analyzer.analyze(source, "test.pc")

        by_priority = analyzer.get_todos_by_priority()

        assert len(by_priority["high"]) == 1
        assert len(by_priority["medium"]) == 1
        assert len(by_priority["low"]) == 1

    def test_get_todos_by_tag(self):
        """Test de regroupement par tag."""
        source = """
// TODO: First todo
// TODO: Second todo
// FIXME: Fix this
"""
        analyzer = CommentAnalyzer()
        analyzer.analyze(source, "test.pc")

        by_tag = analyzer.get_todos_by_tag()

        assert len(by_tag["TODO"]) == 2
        assert len(by_tag["FIXME"]) == 1

    def test_todo_line_number(self):
        """Test que les numéros de ligne sont corrects."""
        source = """line 1
line 2
// TODO: On line 3
line 4
"""
        analyzer = CommentAnalyzer()
        todos, _ = analyzer.analyze(source, "test.pc")

        assert len(todos) == 1
        assert todos[0].line_number == 3

    def test_case_insensitive_tags(self):
        """Test que les tags sont détectés quelle que soit la casse."""
        source = """
// todo: lowercase
// TODO: uppercase
// Todo: mixed case
"""
        analyzer = CommentAnalyzer()
        todos, _ = analyzer.analyze(source, "test.pc")

        assert len(todos) == 3
        for todo in todos:
            assert todo.tag == "TODO"


class TestTodoItem:
    """Tests pour la dataclass TodoItem."""

    def test_todo_item_to_dict(self):
        """Test de sérialisation en dictionnaire."""
        todo = TodoItem(
            tag="TODO",
            message="Test message",
            line_number=10,
            priority="medium",
            context="// TODO: Test message",
        )
        d = todo.to_dict()

        assert d["tag"] == "TODO"
        assert d["message"] == "Test message"
        assert d["line_number"] == 10
        assert d["priority"] == "medium"


class TestModuleInfo:
    """Tests pour la dataclass ModuleInfo."""

    def test_module_info_to_dict(self):
        """Test de sérialisation en dictionnaire."""
        info = ModuleInfo(
            filepath="/path/to/test.pc",
            filename="test.pc",
            directory="path/to",
            title="Test Module",
            author="Author",
        )
        d = info.to_dict()

        assert d["filepath"] == "/path/to/test.pc"
        assert d["filename"] == "test.pc"
        assert d["title"] == "Test Module"
        assert d["author"] == "Author"


class TestModuleInventory:
    """Tests pour la classe ModuleInventory."""

    def test_add_module(self):
        """Test d'ajout d'un module à l'inventaire."""
        inventory = ModuleInventory()

        info = ModuleInfo(
            filepath="/path/to/test.pc",
            filename="test.pc",
            directory="to",
        )
        inventory.add_module(info)

        assert len(inventory.modules) == 1
        assert "/path/to/test.pc" in inventory.modules

    def test_modules_by_directory(self):
        """Test de regroupement par répertoire."""
        inventory = ModuleInventory()

        info1 = ModuleInfo(filepath="/a/test1.pc", filename="test1.pc", directory="a")
        info2 = ModuleInfo(filepath="/a/test2.pc", filename="test2.pc", directory="a")
        info3 = ModuleInfo(filepath="/b/test3.pc", filename="test3.pc", directory="b")

        inventory.add_module(info1)
        inventory.add_module(info2)
        inventory.add_module(info3)

        assert len(inventory.by_directory["a"]) == 2
        assert len(inventory.by_directory["b"]) == 1

    def test_get_summary(self):
        """Test du résumé de l'inventaire."""
        inventory = ModuleInventory()

        info1 = ModuleInfo(filepath="/a/test1.pc", filename="test1.pc", directory="a")
        info2 = ModuleInfo(filepath="/b/test2.pc", filename="test2.pc", directory="b")

        inventory.add_module(info1)
        inventory.add_module(info2)

        summary = inventory.get_summary()

        assert summary["total_modules"] == 2
        assert "a" in summary["directories"]
        assert "b" in summary["directories"]

    def test_to_dict(self):
        """Test de l'export complet."""
        inventory = ModuleInventory()

        info = ModuleInfo(filepath="/path/test.pc", filename="test.pc", directory="path")
        inventory.add_module(info)

        d = inventory.to_dict()

        assert "summary" in d
        assert "by_directory" in d
        assert "modules" in d


class TestAnalyzeComments:
    """Tests pour la fonction utilitaire analyze_comments."""

    def test_analyze_comments(self):
        """Test de la fonction analyze_comments."""
        source = """
// TODO: Test todo
void func(void) {
}
"""
        todos, module_info = analyze_comments(source, "test.pc")

        assert len(todos) == 1
        assert module_info.filename == "test.pc"
