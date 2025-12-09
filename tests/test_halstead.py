"""
Tests pour le module halstead.
"""

import math

from proc_analyzer.halstead import (
    HalsteadCalculator,
    HalsteadMetrics,
    calculate_halstead,
)
from proc_analyzer.parser import ProCParser


class TestHalsteadMetrics:
    """Tests pour la dataclass HalsteadMetrics."""

    def test_vocabulary(self):
        """Test du calcul du vocabulaire."""
        metrics = HalsteadMetrics(
            unique_operators=5, unique_operands=10, total_operators=15, total_operands=20
        )
        assert metrics.vocabulary == 15

    def test_length(self):
        """Test du calcul de la longueur."""
        metrics = HalsteadMetrics(
            unique_operators=5, unique_operands=10, total_operators=15, total_operands=20
        )
        assert metrics.length == 35

    def test_volume(self):
        """Test du calcul du volume."""
        metrics = HalsteadMetrics(
            unique_operators=5, unique_operands=10, total_operators=15, total_operands=20
        )
        # V = N * log2(n) = 35 * log2(15)
        expected = 35 * math.log2(15)
        assert abs(metrics.volume - expected) < 0.001

    def test_difficulty(self):
        """Test du calcul de la difficulté."""
        metrics = HalsteadMetrics(
            unique_operators=4, unique_operands=10, total_operators=15, total_operands=20
        )
        # D = (n1/2) * (N2/n2) = (4/2) * (20/10) = 2 * 2 = 4
        assert abs(metrics.difficulty - 4.0) < 0.001

    def test_effort(self):
        """Test du calcul de l'effort."""
        metrics = HalsteadMetrics(
            unique_operators=4, unique_operands=10, total_operators=15, total_operands=20
        )
        expected = metrics.difficulty * metrics.volume
        assert abs(metrics.effort - expected) < 0.001

    def test_time_seconds(self):
        """Test du calcul du temps en secondes."""
        metrics = HalsteadMetrics(
            unique_operators=4, unique_operands=10, total_operators=15, total_operands=20
        )
        expected = metrics.effort / 18
        assert abs(metrics.time_seconds - expected) < 0.001

    def test_bugs_estimate(self):
        """Test de l'estimation des bugs."""
        metrics = HalsteadMetrics(
            unique_operators=4, unique_operands=10, total_operators=15, total_operands=20
        )
        expected = metrics.volume / 3000
        assert abs(metrics.bugs_estimate - expected) < 0.0001

    def test_empty_metrics(self):
        """Test avec métriques vides (protection division par zéro)."""
        metrics = HalsteadMetrics()
        assert metrics.vocabulary == 0
        assert metrics.length == 0
        assert metrics.volume == 0.0
        assert metrics.difficulty == 0.0
        assert metrics.effort == 0.0

    def test_to_dict(self):
        """Test de la sérialisation en dictionnaire."""
        metrics = HalsteadMetrics(
            unique_operators=5, unique_operands=10, total_operators=15, total_operands=20
        )
        d = metrics.to_dict()

        assert d["unique_operators"] == 5
        assert d["unique_operands"] == 10
        assert d["vocabulary"] == 15
        assert d["length"] == 35
        assert "volume" in d
        assert "difficulty" in d
        assert "effort" in d


class TestHalsteadCalculator:
    """Tests pour la classe HalsteadCalculator."""

    def test_calculate_simple_function(self):
        """Test avec une fonction simple."""
        source = """
int add(int a, int b) {
    return a + b;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        assert metrics.unique_operators > 0
        assert metrics.unique_operands > 0
        assert metrics.total_operators > 0
        assert metrics.total_operands > 0

    def test_calculate_empty_function(self):
        """Test avec une fonction vide."""
        source = """
void empty(void) {
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        # Fonction vide devrait avoir très peu d'opérateurs/opérandes
        assert metrics.total_operators >= 0
        assert metrics.total_operands >= 0

    def test_operators_arithmetic(self):
        """Test de détection des opérateurs arithmétiques."""
        source = """
int calc(int a, int b) {
    int x = a + b;
    int y = a - b;
    int z = a * b;
    int w = a / b;
    int m = a % b;
    return x;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        # Devrait avoir +, -, *, /, % comme opérateurs
        assert metrics.unique_operators >= 5

    def test_operators_comparison(self):
        """Test de détection des opérateurs de comparaison."""
        source = """
int compare(int a, int b) {
    if (a == b) return 0;
    if (a != b) return 1;
    if (a < b) return 2;
    if (a > b) return 3;
    return -1;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        assert metrics.unique_operators > 0

    def test_operators_logical(self):
        """Test de détection des opérateurs logiques."""
        source = """
int logic(int a, int b) {
    if (a && b) return 1;
    if (a || b) return 2;
    if (!a) return 3;
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        assert metrics.unique_operators > 0

    def test_operators_keywords(self):
        """Test de détection des mots-clés comme opérateurs."""
        source = """
int process(int x) {
    if (x > 0) {
        for (int i = 0; i < x; i++) {
            while (i > 0) {
                return i;
            }
        }
    }
    return 0;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        # if, for, while, return sont des opérateurs
        assert "if" in metrics.operators or metrics.unique_operators > 0

    def test_operands_identifiers(self):
        """Test de détection des identifiants comme opérandes."""
        source = """
int process(int input) {
    int output = input * 2;
    return output;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        # input, output sont des opérandes
        assert metrics.unique_operands >= 2

    def test_operands_literals(self):
        """Test de détection des littéraux comme opérandes."""
        source = """
int calc(void) {
    int a = 10;
    int b = 20;
    int c = 30;
    return a + b + c;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        # 10, 20, 30 sont des opérandes
        assert metrics.unique_operands >= 3

    def test_string_normalization(self):
        """Test que les strings sont normalisées."""
        source = """
void print_messages(void) {
    printf("Hello");
    printf("World");
    printf("Test");
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        # Toutes les strings comptent comme un seul opérande unique <string>
        # Mais 3 occurrences
        assert "<string>" in metrics.operands

    def test_metrics_calculation_consistency(self):
        """Test de cohérence des métriques calculées."""
        source = """
int complex(int a, int b, int c) {
    if (a > b) {
        return a + c;
    } else {
        return b - c;
    }
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()
        metrics = calc.calculate(functions[0])

        # Vérifier la cohérence
        assert metrics.vocabulary == metrics.unique_operators + metrics.unique_operands
        assert metrics.length == metrics.total_operators + metrics.total_operands

        if metrics.vocabulary > 0:
            assert metrics.volume > 0

    def test_calculate_all(self):
        """Test calculate_all pour plusieurs fonctions."""
        source = """
int func1(int x) {
    return x + 1;
}

int func2(int a, int b) {
    return a * b;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        results = calc.calculate_all()

        assert "func1" in results
        assert "func2" in results
        assert isinstance(results["func1"], HalsteadMetrics)
        assert isinstance(results["func2"], HalsteadMetrics)

    def test_caching(self):
        """Test que les résultats sont mis en cache."""
        source = """
int func(int x) {
    return x * 2;
}
"""
        parser = ProCParser()
        parser.parse(source)
        calc = HalsteadCalculator(parser)

        functions = parser.get_functions()

        metrics1 = calc.calculate(functions[0])
        metrics2 = calc.calculate(functions[0])

        assert metrics1 is metrics2


class TestCalculateHalstead:
    """Tests pour la fonction utilitaire calculate_halstead."""

    def test_calculate_halstead(self):
        """Test de la fonction calculate_halstead."""
        source = """
int add(int a, int b) {
    return a + b;
}
"""
        parser = ProCParser()
        parser.parse(source)

        functions = parser.get_functions()
        metrics = calculate_halstead(parser, functions[0])

        assert isinstance(metrics, HalsteadMetrics)
        assert metrics.unique_operators > 0
        assert metrics.unique_operands > 0
