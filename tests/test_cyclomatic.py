"""
Tests pour le module cyclomatic.
"""

import pytest
from proc_analyzer.parser import ProCParser
from proc_analyzer.cyclomatic import CyclomaticCalculator, calculate_cyclomatic


class TestCyclomaticCalculator:
    """Tests pour la classe CyclomaticCalculator."""

    def test_calculate_empty_function(self):
        """Fonction vide -> complexité 1."""
        source = """
void empty(void) {
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        assert len(functions) == 1

        complexity = calc.calculate(functions[0])
        assert complexity == 1

    def test_calculate_single_if(self):
        """Un if -> complexité 2."""
        source = """
int check(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 2

    def test_calculate_if_else(self):
        """if/else -> complexité 2 (else ne compte pas)."""
        source = """
int check(int x) {
    if (x > 0) {
        return 1;
    } else {
        return 0;
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 2

    def test_calculate_nested_if(self):
        """if imbriqués -> complexité 3."""
        source = """
int check(int x, int y) {
    if (x > 0) {
        if (y > 0) {
            return 1;
        }
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 3

    def test_calculate_while_loop(self):
        """Boucle while -> complexité 2."""
        source = """
void loop(int n) {
    while (n > 0) {
        n--;
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 2

    def test_calculate_for_loop(self):
        """Boucle for -> complexité 2."""
        source = """
void loop(int n) {
    for (int i = 0; i < n; i++) {
        printf("%d", i);
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 2

    def test_calculate_do_while(self):
        """Boucle do-while -> complexité 2."""
        source = """
void loop(int n) {
    do {
        n--;
    } while (n > 0);
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 2

    def test_calculate_switch_cases(self):
        """Switch avec N cases -> N + 1."""
        source = """
int process(int x) {
    switch (x) {
        case 1:
            return 10;
        case 2:
            return 20;
        case 3:
            return 30;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # 1 (base) + 3 (cases) = 4
        assert complexity == 4

    def test_calculate_ternary(self):
        """Opérateur ternaire -> complexité 2."""
        source = """
int max(int a, int b) {
    return a > b ? a : b;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 2

    def test_calculate_logical_and(self):
        """&& ajoute 1 à la complexité."""
        source = """
int check(int a, int b) {
    if (a > 0 && b > 0) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # 1 (base) + 1 (if) + 1 (&&) = 3
        assert complexity == 3

    def test_calculate_logical_or(self):
        """|| ajoute 1 à la complexité."""
        source = """
int check(int a, int b) {
    if (a > 0 || b > 0) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # 1 (base) + 1 (if) + 1 (||) = 3
        assert complexity == 3

    def test_calculate_complex_expression(self):
        """Expression complexe a && b || c && d."""
        source = """
int check(int a, int b, int c, int d) {
    if (a && b || c && d) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # 1 (base) + 1 (if) + 3 (&&, ||, &&) = 5
        assert complexity == 5

    def test_calculate_all(self):
        """Test calculate_all pour plusieurs fonctions."""
        source = """
void func1(void) {
}

int func2(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        results = calc.calculate_all()
        assert "func1" in results
        assert "func2" in results
        assert results["func1"] == 1
        assert results["func2"] == 2

    def test_get_details(self):
        """Test get_details pour décomposition."""
        source = """
int complex(int a, int b) {
    if (a > 0) {
        while (b > 0) {
            b--;
        }
    }
    return a && b ? 1 : 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()
        details = calc.get_details(functions[0])

        assert details["if_count"] == 1
        assert details["loop_count"] == 1
        assert details["ternary_count"] == 1
        assert details["logical_and_count"] == 1
        assert "total" in details

    def test_caching(self):
        """Test que les résultats sont mis en cache."""
        source = """
int func(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CyclomaticCalculator(parser)

        functions = parser.get_functions()

        # Premier appel
        result1 = calc.calculate(functions[0])
        # Deuxième appel (devrait utiliser le cache)
        result2 = calc.calculate(functions[0])

        assert result1 == result2


class TestCalculateCyclomatic:
    """Tests pour la fonction utilitaire calculate_cyclomatic."""

    def test_calculate_cyclomatic(self):
        """Test de la fonction calculate_cyclomatic."""
        source = """
int check(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        complexity = calculate_cyclomatic(parser, functions[0])
        assert complexity == 2

    def test_calculate_function_without_node(self):
        """Test que les fonctions sans nœud AST retournent une complexité de base."""
        from proc_analyzer.parser import FunctionInfo
        
        parser = ProCParser()
        parser.parse("")  # Parser vide
        
        # Créer une fonction sans nœud AST (syntaxe non-standard)
        func = FunctionInfo(
            name="test_func",
            start_line=1,
            end_line=5,
            node=None,  # Pas de nœud AST
            parameters=[],
            return_type="void"
        )
        
        calc = CyclomaticCalculator(parser)
        complexity = calc.calculate(func)
        
        # Doit retourner la complexité de base (1)
        assert complexity == 1
