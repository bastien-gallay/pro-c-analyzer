"""
Fixtures partagées pour les tests pytest.
"""

import pytest

from proc_analyzer.parser import ProCParser
from proc_analyzer.preprocessor import ProCPreprocessor


@pytest.fixture
def simple_c_source():
    """Code C simple sans EXEC SQL."""
    return """
int main(void) {
    int x = 10;
    return x;
}
"""


@pytest.fixture
def simple_proc_source():
    """Code Pro*C avec un EXEC SQL simple."""
    return """
#include <stdio.h>

EXEC SQL BEGIN DECLARE SECTION;
    char username[32];
    char password[32];
EXEC SQL END DECLARE SECTION;

int main(void) {
    EXEC SQL CONNECT :username IDENTIFIED BY :password;

    EXEC SQL SELECT name INTO :buffer FROM users WHERE id = 1;

    printf("Connected\\n");
    return 0;
}
"""


@pytest.fixture
def complex_function_source():
    """Code C avec structures de contrôle complexes."""
    return """
int complex_function(int a, int b, int c) {
    int result = 0;

    if (a > 0) {
        if (b > 0) {
            result = a + b;
        } else {
            result = a - b;
        }
    } else if (a < 0) {
        while (b > 0) {
            result += c;
            b--;
        }
    } else {
        for (int i = 0; i < c; i++) {
            if (i % 2 == 0) {
                result++;
            }
        }
    }

    switch (c) {
        case 1:
            result *= 2;
            break;
        case 2:
            result *= 3;
            break;
        default:
            result *= 4;
    }

    return result > 0 ? result : -result;
}
"""


@pytest.fixture
def cursor_source():
    """Code Pro*C avec des curseurs."""
    return """
EXEC SQL BEGIN DECLARE SECTION;
    int emp_id;
    char emp_name[50];
    float emp_salary;
EXEC SQL END DECLARE SECTION;

void fetch_employees(void) {
    EXEC SQL DECLARE emp_cursor CURSOR FOR
        SELECT id, name, salary FROM employees WHERE active = 1;

    EXEC SQL OPEN emp_cursor;

    while (1) {
        EXEC SQL FETCH emp_cursor INTO :emp_id, :emp_name, :emp_salary;

        if (sqlca.sqlcode != 0) {
            break;
        }

        printf("Employee: %s\\n", emp_name);
    }

    EXEC SQL CLOSE emp_cursor;
}
"""


@pytest.fixture
def memory_issues_source():
    """Code C avec des problèmes de gestion mémoire."""
    return """
#include <stdlib.h>
#include <string.h>

void memory_problems(void) {
    char *buffer = malloc(100);

    strcpy(buffer, "Hello World");

    char *ptr = malloc(50);

    if (ptr == NULL) {
        return;
    }

    free(ptr);

    gets(input);

    sprintf(output, "%s", user_input);
}
"""


@pytest.fixture
def todo_comments_source():
    """Code avec des commentaires TODO/FIXME."""
    return """
/*
 * Module: test_module.pc
 * Description: Module de test
 * Author: Test Author
 * Date: 2024-01-01
 * Version: 1.0
 */

#include <stdio.h>

// TODO: Implement proper error handling
void process_data(void) {
    /* FIXME: This is a critical bug that needs attention */
    int x = 10;

    // HACK: Temporary workaround for performance issue
    for (int i = 0; i < x; i++) {
        /* NOTE: This loop is intentionally slow */
        printf("%d\\n", i);
    }

    // XXX: Security vulnerability here
    // BUG: Memory leak detected
}
"""


@pytest.fixture
def parser(simple_c_source):
    """Parser initialisé avec du code C simple."""
    p = ProCParser()
    p.parse(simple_c_source)
    return p


@pytest.fixture
def parser_complex(complex_function_source):
    """Parser initialisé avec une fonction complexe."""
    p = ProCParser()
    p.parse(complex_function_source)
    return p


@pytest.fixture
def preprocessor():
    """Instance de ProCPreprocessor."""
    return ProCPreprocessor()


@pytest.fixture
def tmp_proc_file(tmp_path, simple_proc_source):
    """Fichier Pro*C temporaire."""
    file_path = tmp_path / "test.pc"
    file_path.write_text(simple_proc_source)
    return file_path
