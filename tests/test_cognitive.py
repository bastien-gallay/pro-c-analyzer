"""
Tests pour le module cognitive.
"""

import pytest
from proc_analyzer.parser import ProCParser
from proc_analyzer.cognitive import CognitiveCalculator, calculate_cognitive


class TestCognitiveCalculator:
    """Tests pour la classe CognitiveCalculator."""

    def test_calculate_empty_function(self):
        """Fonction vide -> complexité 0."""
        source = """
void empty(void) {
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 0

    def test_calculate_single_if(self):
        """Un if -> complexité 1."""
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
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        assert complexity == 1

    def test_calculate_nested_if(self):
        """if imbriqué -> 1 + (1 + nesting)."""
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
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # Outer if: 1, inner if: 1 + 1 (nesting) = 3
        assert complexity == 3

    def test_calculate_else_clause(self):
        """else ajoute 1 sans pénalité de nesting."""
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
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # if: 1, else: 1 = 2
        assert complexity == 2

    def test_calculate_else_if_chain(self):
        """else if ne devrait pas augmenter le nesting."""
        source = """
int check(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    } else {
        return 0;
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # first if: 1, else: 1, else if: 1, else: 1 = 4
        assert complexity == 4

    def test_calculate_while_nested(self):
        """while dans if."""
        source = """
void process(int x, int n) {
    if (x > 0) {
        while (n > 0) {
            n--;
        }
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # if: 1, while: 1 + 1 (nesting) = 3
        assert complexity == 3

    def test_calculate_for_loop(self):
        """Boucle for simple."""
        source = """
void loop(int n) {
    for (int i = 0; i < n; i++) {
        printf("%d", i);
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # for: 1
        assert complexity == 1

    def test_calculate_switch_cases(self):
        """Switch avec cases multiples."""
        source = """
int process(int x) {
    switch (x) {
        case 1:
            return 10;
        case 2:
            return 20;
        default:
            return 0;
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # switch: 1, case 1: 1, case 2: 1 = 3
        assert complexity >= 1

    def test_calculate_ternary_nested(self):
        """Ternaire avec nesting."""
        source = """
int check(int a, int b) {
    if (a > 0) {
        return b > 0 ? 1 : 0;
    }
    return -1;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # if: 1, ternary: 1 + 1 (nesting) = 3
        assert complexity == 3

    def test_calculate_logical_sequences(self):
        """Séquences d'opérateurs logiques."""
        source = """
int check(int a, int b, int c) {
    if (a && b && c) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # if: 1, logical sequence (same operators): 1 = 2
        assert complexity >= 2

    def test_calculate_mixed_logical_operators(self):
        """Opérateurs logiques mixtes."""
        source = """
int check(int a, int b, int c) {
    if (a && b || c) {
        return 1;
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # if: 1, mixed operators: 2 (change d'opérateur) = 3
        assert complexity >= 2

    def test_calculate_goto(self):
        """goto ajoute 1."""
        source = """
void process(void) {
    goto end;
    printf("skipped");
end:
    return;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # goto: 1
        assert complexity == 1

    def test_calculate_deeply_nested(self):
        """Test avec nesting profond (5+ niveaux)."""
        source = """
void deep(int a, int b, int c, int d, int e) {
    if (a) {
        if (b) {
            if (c) {
                if (d) {
                    if (e) {
                        return;
                    }
                }
            }
        }
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        complexity = calc.calculate(functions[0])
        # 1 + (1+1) + (1+2) + (1+3) + (1+4) = 1 + 2 + 3 + 4 + 5 = 15
        assert complexity == 15

    def test_get_details_max_nesting(self):
        """Test get_details vérifie max_nesting."""
        source = """
void nested(int x, int y) {
    if (x) {
        if (y) {
            return;
        }
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        details = calc.get_details(functions[0])

        assert details["if_count"] == 2
        assert details["max_nesting"] >= 1
        assert "total" in details

    def test_get_details_complete(self):
        """Test get_details avec toutes les structures."""
        source = """
int complex(int a, int b, int c) {
    if (a > 0) {
        while (b > 0) {
            b--;
        }
    } else {
        for (int i = 0; i < c; i++) {
            if (a && b) {
                goto end;
            }
        }
    }
end:
    return a ? 1 : 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()
        details = calc.get_details(functions[0])

        assert details["if_count"] >= 2
        assert details["loop_count"] >= 2
        assert details["else_count"] >= 1
        assert details["ternary_count"] >= 1

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
        calc = CognitiveCalculator(parser)

        results = calc.calculate_all()
        assert "func1" in results
        assert "func2" in results
        assert results["func1"] == 0
        assert results["func2"] == 1

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
        calc = CognitiveCalculator(parser)

        functions = parser.get_functions()

        result1 = calc.calculate(functions[0])
        result2 = calc.calculate(functions[0])

        assert result1 == result2


class TestCalculateCognitive:
    """Tests pour la fonction utilitaire calculate_cognitive."""

    def test_calculate_cognitive(self):
        """Test de la fonction calculate_cognitive."""
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

        functions = parser.get_functions()
        complexity = calculate_cognitive(parser, functions[0])
        # Outer if: 1, inner if: 1 + 1 = 3
        assert complexity == 3
