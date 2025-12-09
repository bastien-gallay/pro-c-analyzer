"""
Tests pour le module parser.
"""

import pytest
from proc_analyzer.parser import ProCParser, FunctionInfo, parse_source


class TestProCParser:
    """Tests pour la classe ProCParser."""

    def test_parse_simple_function(self):
        """Test de parsing d'une fonction simple."""
        source = """
int add(int a, int b) {
    return a + b;
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1
        assert functions[0].name == "add"
        assert functions[0].return_type == "int"

    def test_parse_multiple_functions(self):
        """Test de parsing de plusieurs fonctions."""
        source = """
void func1(void) {
    return;
}

int func2(int x) {
    return x * 2;
}

char* func3(void) {
    return "hello";
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 3

        names = [f.name for f in functions]
        assert "func1" in names
        assert "func2" in names
        assert "func3" in names

    def test_parse_function_with_parameters(self):
        """Test de parsing des paramètres de fonction."""
        source = """
int process(int a, char *b, float c) {
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "process"
        assert "a" in func.parameters
        assert "b" in func.parameters
        assert "c" in func.parameters

    def test_parse_pointer_return_type(self):
        """Test de parsing d'une fonction retournant un pointeur."""
        source = """
char *get_string(void) {
    return "test";
}

int *get_array(int size) {
    return malloc(size * sizeof(int));
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 2

    def test_parse_empty_source(self):
        """Test de parsing d'une source vide."""
        parser = ProCParser()
        parser.parse("")

        functions = parser.get_functions()
        assert functions == []

    def test_get_functions_no_functions(self):
        """Test avec code sans fonctions."""
        source = """
int global_var = 10;
#define MAX 100
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert functions == []

    def test_walk_ast(self):
        """Test du parcours de l'AST."""
        source = """
int main(void) {
    int x = 10;
    return x;
}
"""
        parser = ProCParser()
        parser.parse(source)

        nodes = list(parser.walk())
        assert len(nodes) > 0

        # Vérifier qu'on trouve le noeud racine
        node_types = [n.type for n in nodes]
        assert "translation_unit" in node_types
        assert "function_definition" in node_types

    def test_find_nodes(self):
        """Test de recherche de noeuds par type."""
        source = """
int main(void) {
    if (1) {
        int x = 1;
    }
    if (2) {
        int y = 2;
    }
}
"""
        parser = ProCParser()
        parser.parse(source)

        if_nodes = parser.find_nodes("if_statement")
        assert len(if_nodes) == 2

    def test_has_errors_valid_code(self):
        """Test has_errors avec code valide."""
        source = """
int main(void) {
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)

        assert parser.has_errors is False

    def test_has_errors_invalid_code(self):
        """Test has_errors avec code invalide."""
        source = """
int main(void {
    return 0
}
"""
        parser = ProCParser()
        parser.parse(source)

        assert parser.has_errors is True

    def test_get_node_text(self):
        """Test d'extraction du texte d'un noeud."""
        source = """
int main(void) {
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1

        func_text = parser.get_node_text(functions[0].node)
        assert "int main" in func_text
        assert "return 0" in func_text

    def test_line_count_methods(self):
        """Test des méthodes de comptage de lignes."""
        source = """line 1
line 2

line 4
line 5
"""
        parser = ProCParser()
        parser.parse(source)

        assert parser.get_line_count() == 6
        assert parser.get_non_empty_line_count() == 4

    def test_root_node_after_parse(self):
        """Test que root_node est disponible après parsing."""
        source = "int x = 1;"
        parser = ProCParser()
        parser.parse(source)

        assert parser.root_node is not None
        assert parser.root_node.type == "translation_unit"

    def test_root_node_before_parse(self):
        """Test que root_node est None avant parsing."""
        parser = ProCParser()
        assert parser.root_node is None


class TestFunctionInfo:
    """Tests pour la dataclass FunctionInfo."""

    def test_function_info_line_count(self):
        """Test du calcul du nombre de lignes."""
        source = """
int func(void) {
    int x = 1;
    int y = 2;
    return x + y;
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1

        func = functions[0]
        assert func.line_count == func.end_line - func.start_line + 1


class TestParseSource:
    """Tests pour la fonction utilitaire parse_source."""

    def test_parse_source(self):
        """Test de la fonction parse_source."""
        source = """
int add(int a, int b) {
    return a + b;
}
"""
        parser = parse_source(source)

        functions = parser.get_functions()
        assert len(functions) == 1
        assert functions[0].name == "add"


class TestAlternativeFunctionSyntax:
    """Tests pour la détection de fonctions avec syntaxe non-standard (VOID ...() begin/end)."""

    def test_parse_void_function_with_begin_end(self):
        """Test de parsing d'une fonction VOID avec begin/end."""
        source = """
VOID test_function()
begin
    int x = 10;
    return;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1
        assert functions[0].name == "test_function"
        assert functions[0].return_type == "void"
        assert functions[0].node is None  # Pas de nœud AST pour syntaxe non-standard
        assert functions[0].start_line == 2
        assert functions[0].end_line == 6

    def test_parse_multiple_void_functions(self):
        """Test de parsing de plusieurs fonctions VOID."""
        source = """
VOID func1()
begin
    return;
end

VOID func2()
begin
    int x = 1;
end

INT func3()
begin
    return 0;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 3

        names = [f.name for f in functions]
        assert "func1" in names
        assert "func2" in names
        assert "func3" in names

        # Vérifier les types de retour
        func_dict = {f.name: f for f in functions}
        assert func_dict["func1"].return_type == "void"
        assert func_dict["func2"].return_type == "void"
        assert func_dict["func3"].return_type == "int"

    def test_parse_void_function_with_parameters(self):
        """Test de parsing d'une fonction VOID avec paramètres."""
        source = """
VOID process_data(INT param1, STR param2)
begin
    int x = param1;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "process_data"
        assert "param1" in func.parameters
        assert "param2" in func.parameters

    def test_parse_void_function_nested_begin_end(self):
        """Test de parsing avec begin/end imbriqués."""
        source = """
VOID complex_function()
begin
    if (1) then
    begin
        int x = 1;
    end
    int y = 2;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "complex_function"
        # Le end final doit être détecté correctement malgré l'imbrication
        # Le end final est à l'index 8 (0-indexed) = ligne 9 (1-indexed)
        assert func.end_line == 9

    def test_parse_mixed_standard_and_alternative_syntax(self):
        """Test de parsing avec fonctions standard et non-standard."""
        source = """
int standard_func(void) {
    return 0;
}

VOID alternative_func()
begin
    int x = 1;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 2

        names = [f.name for f in functions]
        assert "standard_func" in names
        assert "alternative_func" in names

        # Vérifier que les fonctions standard ont un node, les autres non
        func_dict = {f.name: f for f in functions}
        assert func_dict["standard_func"].node is not None
        assert func_dict["alternative_func"].node is None

    def test_parse_void_function_begin_on_same_line(self):
        """Test de parsing avec begin sur la même ligne que la déclaration."""
        source = """
VOID inline_func() begin
    int x = 1;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1
        assert functions[0].name == "inline_func"

    def test_parse_void_function_with_void_parameter(self):
        """Test de parsing avec paramètre VOID."""
        source = """
VOID func_with_void(VOID)
begin
    return;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1
        assert functions[0].name == "func_with_void"
        # VOID dans les paramètres ne doit pas être extrait comme paramètre
        assert len(functions[0].parameters) == 0

    def test_parse_void_function_no_begin_found(self):
        """Test qu'une déclaration sans begin n'est pas détectée."""
        source = """
VOID incomplete_func()
    int x = 1;
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        # Ne doit pas détecter de fonction car pas de begin
        assert len(functions) == 0

    def test_parse_void_function_no_end_found(self):
        """Test qu'une fonction sans end correspondant n'est pas détectée."""
        source = """
VOID incomplete_func()
begin
    int x = 1;
    // Pas de end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        # Ne doit pas détecter de fonction car pas de end correspondant
        assert len(functions) == 0

    def test_parse_void_function_line_numbers(self):
        """Test que les numéros de ligne sont corrects."""
        source = """
VOID test_func()
begin
    int x = 1;
    int y = 2;
end
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        assert len(functions) == 1

        func = functions[0]
        assert func.start_line == 2  # Ligne de la déclaration
        assert func.end_line == 6    # Ligne du end
        assert func.line_count == 5   # 2 à 6 inclus
