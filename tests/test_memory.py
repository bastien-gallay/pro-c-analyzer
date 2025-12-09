"""
Tests pour le module memory.
"""

from proc_analyzer.memory import (
    AllocationInfo,
    MemoryAnalysisResult,
    MemoryAnalyzer,
    MemoryIssue,
    MemoryIssueType,
    MemorySeverity,
    analyze_memory,
)


class TestMemoryAnalyzer:
    """Tests pour la classe MemoryAnalyzer."""

    def test_analyze_malloc_with_check(self):
        """Test malloc avec vérification NULL correcte."""
        source = """
void process(void) {
    char *ptr = malloc(100);
    if (ptr == NULL) {
        return;
    }
    strcpy(ptr, "test");
    free(ptr);
    ptr = NULL;
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # Pas d'erreur MALLOC_NO_CHECK car on vérifie NULL
        no_check_issues = [
            i for i in result.issues if i.issue_type == MemoryIssueType.MALLOC_NO_CHECK
        ]
        assert len(no_check_issues) == 0

    def test_detect_malloc_no_check(self):
        """Test malloc sans vérification NULL."""
        source = """
void process(void) {
    char *buffer = malloc(100);
    strcpy(buffer, "test");
    free(buffer);
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # Devrait avoir MALLOC_NO_CHECK
        no_check_issues = [
            i for i in result.issues if i.issue_type == MemoryIssueType.MALLOC_NO_CHECK
        ]
        assert len(no_check_issues) >= 1

    def test_detect_malloc_no_free(self):
        """Test malloc sans free correspondant."""
        source = """
void leak(void) {
    char *ptr = malloc(100);
    if (ptr == NULL) return;
    strcpy(ptr, "leaked");
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # Devrait avoir MALLOC_NO_FREE
        no_free_issues = [
            i for i in result.issues if i.issue_type == MemoryIssueType.MALLOC_NO_FREE
        ]
        assert len(no_free_issues) >= 1

    def test_detect_free_no_null(self):
        """Test free sans mise à NULL."""
        source = """
void process(void) {
    char *ptr = malloc(100);
    if (ptr == NULL) return;
    free(ptr);
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # Devrait avoir FREE_NO_NULL
        no_null_issues = [i for i in result.issues if i.issue_type == MemoryIssueType.FREE_NO_NULL]
        assert len(no_null_issues) >= 1

    def test_detect_buffer_overflow_strcpy(self):
        """Test détection de strcpy dangereux."""
        source = """
void copy_string(char *input) {
    char buffer[10];
    strcpy(buffer, input);
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # Devrait détecter strcpy comme fonction dangereuse
        dangerous_issues = [
            i
            for i in result.issues
            if i.issue_type in (MemoryIssueType.BUFFER_OVERFLOW, MemoryIssueType.DANGEROUS_FUNCTION)
        ]
        assert len(dangerous_issues) >= 1

    def test_detect_buffer_overflow_sprintf(self):
        """Test détection de sprintf dangereux."""
        source = """
void format_string(char *input) {
    char buffer[100];
    sprintf(buffer, "Hello %s", input);
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # Devrait détecter sprintf
        dangerous_issues = [
            i for i in result.issues if i.issue_type == MemoryIssueType.DANGEROUS_FUNCTION
        ]
        assert len(dangerous_issues) >= 1

    def test_detect_dangerous_gets(self):
        """Test détection de gets (CRITICAL)."""
        source = """
void read_input(void) {
    char buffer[100];
    gets(buffer);
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # gets devrait être CRITICAL / BUFFER_OVERFLOW
        critical_issues = [i for i in result.issues if i.severity == MemorySeverity.CRITICAL]
        assert len(critical_issues) >= 1

    def test_detect_sizeof_pointer(self):
        """Test détection de sizeof sur pointeur."""
        source = """
void alloc_wrong(void) {
    int *ptr;
    ptr = malloc(sizeof(ptr));
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # Devrait détecter sizeof(ptr) sur un pointeur
        sizeof_issues = [i for i in result.issues if i.issue_type == MemoryIssueType.SIZEOF_POINTER]
        assert len(sizeof_issues) >= 1

    def test_calloc_detection(self):
        """Test que calloc est détecté comme malloc."""
        source = """
void process(void) {
    int *arr = calloc(10, sizeof(int));
    use_array(arr);
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # calloc devrait être tracké
        assert len(result.allocations) >= 1
        assert result.allocations[0].function == "calloc"

    def test_realloc_detection(self):
        """Test que realloc est détecté."""
        source = """
void resize(void) {
    char *ptr = malloc(100);
    if (ptr == NULL) return;
    ptr = realloc(ptr, 200);
    if (ptr == NULL) return;
    free(ptr);
    ptr = NULL;
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        # realloc devrait être tracké
        realloc_allocs = [a for a in result.allocations if a.function == "realloc"]
        assert len(realloc_allocs) >= 1

    def test_multiple_allocations(self):
        """Test avec plusieurs allocations."""
        source = """
void multi_alloc(void) {
    char *a = malloc(10);
    char *b = malloc(20);
    char *c = malloc(30);
    if (a) { free(a); a = NULL; }
    if (b) { free(b); b = NULL; }
    if (c) { free(c); c = NULL; }
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        assert len(result.allocations) == 3

    def test_no_memory_issues(self):
        """Test avec code sans problèmes mémoire."""
        source = """
int add(int a, int b) {
    return a + b;
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        assert len(result.allocations) == 0
        assert len(result.dangerous_calls) == 0

    def test_strdup_detection(self):
        """Test que strdup est détecté comme allocation."""
        source = """
void duplicate(const char *s) {
    char *copy = strdup(s);
    if (copy == NULL) return;
    use_string(copy);
    free(copy);
    copy = NULL;
}
"""
        analyzer = MemoryAnalyzer()
        result = analyzer.analyze(source)

        strdup_allocs = [a for a in result.allocations if a.function == "strdup"]
        assert len(strdup_allocs) >= 1


class TestMemoryIssue:
    """Tests pour la dataclass MemoryIssue."""

    def test_memory_issue_to_dict(self):
        """Test de sérialisation en dictionnaire."""
        issue = MemoryIssue(
            issue_type=MemoryIssueType.MALLOC_NO_CHECK,
            severity=MemorySeverity.ERROR,
            line_number=10,
            message="malloc sans vérification NULL",
            code_snippet="char *ptr = malloc(100);",
            recommendation="Ajouter if (ptr == NULL)",
        )

        d = issue.to_dict()

        assert d["type"] == "malloc_unchecked"
        assert d["severity"] == "error"
        assert d["line_number"] == 10
        assert "recommendation" in d


class TestAllocationInfo:
    """Tests pour la dataclass AllocationInfo."""

    def test_allocation_info_creation(self):
        """Test de création d'AllocationInfo."""
        alloc = AllocationInfo(
            variable="ptr",
            line_number=10,
            function="malloc",
            has_null_check=True,
            has_free=True,
            free_line=20,
        )

        assert alloc.variable == "ptr"
        assert alloc.function == "malloc"
        assert alloc.has_null_check is True
        assert alloc.has_free is True


class TestMemoryAnalysisResult:
    """Tests pour la dataclass MemoryAnalysisResult."""

    def test_analysis_result_properties(self):
        """Test des propriétés calculées."""
        result = MemoryAnalysisResult()
        result.issues.append(
            MemoryIssue(
                issue_type=MemoryIssueType.MALLOC_NO_CHECK,
                severity=MemorySeverity.CRITICAL,
                line_number=10,
                message="Test",
                code_snippet="test",
            )
        )
        result.issues.append(
            MemoryIssue(
                issue_type=MemoryIssueType.FREE_NO_NULL,
                severity=MemorySeverity.WARNING,
                line_number=20,
                message="Test2",
                code_snippet="test2",
            )
        )

        assert result.total_issues == 2
        assert result.critical_count == 1
        assert result.warning_count == 1

    def test_analysis_result_to_dict(self):
        """Test de sérialisation complète."""
        result = MemoryAnalysisResult()
        result.allocations.append(AllocationInfo(variable="ptr", line_number=10, function="malloc"))

        d = result.to_dict()

        assert "total_issues" in d
        assert "critical_count" in d
        assert "allocations_count" in d


class TestAnalyzeMemory:
    """Tests pour la fonction utilitaire analyze_memory."""

    def test_analyze_memory(self):
        """Test de la fonction analyze_memory."""
        source = """
void process(void) {
    char *ptr = malloc(100);
    free(ptr);
}
"""
        result = analyze_memory(source)

        assert isinstance(result, MemoryAnalysisResult)
        assert len(result.allocations) >= 1
