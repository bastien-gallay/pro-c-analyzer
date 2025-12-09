"""
Tests pour le module CLI.
"""

from unittest.mock import MagicMock, patch

from proc_analyzer.analyzer import AnalysisReport, ProCAnalyzer
from proc_analyzer.cli import (
    analyze_with_progress,
    find_files_case_insensitive,
    match_case_insensitive,
    parse_patterns,
)


class TestAnalyzeWithProgress:
    """Tests pour la fonction analyze_with_progress."""

    def test_analyze_single_file(self, tmp_path, simple_proc_source):
        """Test de l'analyse d'un fichier unique."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        # Mock console.print pour éviter l'affichage dans les tests
        with patch("proc_analyzer.cli.console.print"):
            report = analyze_with_progress(analyzer, str(file_path))

        assert report is not None
        assert len(report.files) == 1
        assert report.files[0].filepath == str(file_path)

    def test_analyze_directory_empty(self, tmp_path):
        """Test avec un répertoire vide."""
        analyzer = ProCAnalyzer()

        with patch("proc_analyzer.cli.console.print"):
            report = analyze_with_progress(analyzer, str(tmp_path))

        assert report is not None
        assert len(report.files) == 0

    def test_analyze_directory_single_file(self, tmp_path, simple_proc_source):
        """Test avec un répertoire contenant un fichier."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            # Mock Progress context manager
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc")

        assert report is not None
        assert len(report.files) == 1

    def test_analyze_directory_multiple_files(self, tmp_path, simple_proc_source):
        """Test avec un répertoire contenant plusieurs fichiers."""
        (tmp_path / "file1.pc").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(
            """
            int multiply(int a, int b) {
                return a * b;
            }
            """
        )
        (tmp_path / "file3.pc").write_text(
            """
            void process(void) {
                return;
            }
            """
        )

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            # Mock Progress context manager
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc")

        assert report is not None
        assert len(report.files) == 3

    def test_analyze_directory_with_pattern(self, tmp_path, simple_proc_source):
        """Test avec un pattern spécifique."""
        (tmp_path / "test.pc").write_text(simple_proc_source)
        (tmp_path / "test.txt").write_text("Not a Pro*C file")

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc")

        assert report is not None
        assert len(report.files) == 1  # Seulement le fichier .pc

    def test_analyze_directory_non_recursive(self, tmp_path, simple_proc_source):
        """Test avec recherche non récursive."""
        # Fichier dans le répertoire racine
        (tmp_path / "file1.pc").write_text(simple_proc_source)

        # Fichier dans un sous-répertoire
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.pc").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc", recursive=False)

        assert report is not None
        assert len(report.files) == 1  # Seulement le fichier à la racine

    def test_analyze_directory_recursive(self, tmp_path, simple_proc_source):
        """Test avec recherche récursive."""
        # Fichier dans le répertoire racine
        (tmp_path / "file1.pc").write_text(simple_proc_source)

        # Fichier dans un sous-répertoire
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.pc").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc", recursive=True)

        assert report is not None
        assert len(report.files) == 2  # Les deux fichiers

    def test_progress_callback_called(self, tmp_path, simple_proc_source):
        """Test que le callback de progression est appelé."""
        (tmp_path / "file1.pc").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()
        callback_calls = []

        def mock_callback(filepath: str, current: int, total: int):
            callback_calls.append((filepath, current, total))

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            # Mock Progress pour capturer les appels
            mock_progress_instance = MagicMock()
            mock_task = MagicMock()
            mock_progress_instance.add_task.return_value = mock_task
            mock_progress.return_value.__enter__.return_value = mock_progress_instance
            mock_progress.return_value.__exit__.return_value = None

            # Injecter directement le callback dans analyze_directory
            with patch.object(analyzer, "analyze_directory") as mock_analyze:
                mock_report = AnalysisReport()
                mock_report.files = [analyzer.analyze_file(str(tmp_path / "file1.pc"))]
                mock_analyze.return_value = mock_report

                analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc")

                # Vérifier que analyze_directory a été appelé avec progress_callback
                assert mock_analyze.called
                call_kwargs = mock_analyze.call_args[1]
                assert "progress_callback" in call_kwargs
                assert callable(call_kwargs["progress_callback"])

    def test_analyze_directory_multiple_patterns(self, tmp_path, simple_proc_source):
        """Test avec plusieurs patterns séparés par des points-virgules."""
        (tmp_path / "file1.pc").write_text(simple_proc_source)
        (tmp_path / "file2.sc").write_text(simple_proc_source)
        (tmp_path / "file3.inc").write_text(simple_proc_source)
        (tmp_path / "file4.txt").write_text("Not a Pro*C file")

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc;*.sc;*.inc")

        assert report is not None
        assert len(report.files) == 3  # Les trois fichiers .pc, .sc et .inc
        filepaths = {f.filepath for f in report.files}
        assert any("file1.pc" in fp for fp in filepaths)
        assert any("file2.sc" in fp for fp in filepaths)
        assert any("file3.inc" in fp for fp in filepaths)
        assert not any("file4.txt" in fp for fp in filepaths)

    def test_analyze_directory_multiple_patterns_with_spaces(self, tmp_path, simple_proc_source):
        """Test avec plusieurs patterns avec espaces autour des points-virgules."""
        (tmp_path / "file1.pc").write_text(simple_proc_source)
        (tmp_path / "file2.sc").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc ; *.sc")

        assert report is not None
        assert len(report.files) == 2  # Les deux fichiers

    def test_analyze_directory_multiple_patterns_no_duplicates(self, tmp_path, simple_proc_source):
        """Test que les fichiers correspondant à plusieurs patterns ne sont pas dupliqués."""
        (tmp_path / "file1.pc").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            # Le fichier .pc correspond aux deux patterns
            report = analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc;*.pc")

        assert report is not None
        assert len(report.files) == 1  # Pas de duplication

    def test_analyze_directory_case_insensitive_pattern(self, tmp_path, simple_proc_source):
        """Test avec un pattern insensible à la casse."""
        (tmp_path / "file1.PC").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(simple_proc_source)
        (tmp_path / "FILE3.PC").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            # Utiliser ipattern avec pattern en majuscules
            report = analyze_with_progress(analyzer, str(tmp_path), ipattern="*.PC")

        assert report is not None
        assert len(report.files) == 3  # Tous les fichiers .pc/PC/PC

    def test_analyze_directory_case_insensitive_multiple_patterns(
        self, tmp_path, simple_proc_source
    ):
        """Test avec plusieurs patterns insensibles à la casse."""
        (tmp_path / "file1.PC").write_text(simple_proc_source)
        (tmp_path / "file2.SC").write_text(simple_proc_source)
        (tmp_path / "file3.inc").write_text(simple_proc_source)
        (tmp_path / "file4.txt").write_text("Not a Pro*C file")

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(analyzer, str(tmp_path), ipattern="*.PC;*.SC;*.INC")

        assert report is not None
        assert len(report.files) == 3  # Les trois fichiers PC, SC, inc
        filepaths = {f.filepath for f in report.files}
        assert any("file1.PC" in fp for fp in filepaths)
        assert any("file2.SC" in fp for fp in filepaths)
        assert any("file3.inc" in fp for fp in filepaths)
        assert not any("file4.txt" in fp for fp in filepaths)

    def test_analyze_directory_ipattern_priority_over_pattern(self, tmp_path, simple_proc_source):
        """Test que ipattern est prioritaire sur pattern."""
        (tmp_path / "file1.PC").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            # Fournir pattern et ipattern - ipattern doit être utilisé
            report = analyze_with_progress(
                analyzer,
                str(tmp_path),
                pattern="*.txt",  # Ne devrait pas matcher
                ipattern="*.PC",  # Devrait matcher les deux fichiers
            )

        assert report is not None
        assert len(report.files) == 2  # Les deux fichiers PC et pc

    def test_analyze_directory_case_insensitive_non_recursive(self, tmp_path, simple_proc_source):
        """Test avec recherche insensible à la casse non récursive."""
        (tmp_path / "file1.PC").write_text(simple_proc_source)

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.PC").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(
                analyzer, str(tmp_path), ipattern="*.PC", recursive=False
            )

        assert report is not None
        assert len(report.files) == 1  # Seulement le fichier à la racine


class TestParsePatterns:
    """Tests pour la fonction parse_patterns."""

    def test_single_pattern(self):
        """Test avec un seul pattern."""
        result = parse_patterns("*.pc")
        assert result == ["*.pc"]

    def test_multiple_patterns(self):
        """Test avec plusieurs patterns."""
        result = parse_patterns("*.pc;*.sc;*.inc")
        assert result == ["*.pc", "*.sc", "*.inc"]

    def test_patterns_with_spaces(self):
        """Test avec des espaces autour des points-virgules."""
        result = parse_patterns("*.pc ; *.sc ; *.inc")
        assert result == ["*.pc", "*.sc", "*.inc"]

    def test_empty_pattern(self):
        """Test avec un pattern vide."""
        result = parse_patterns("")
        assert result == ["*.pc"]  # Retourne le défaut

    def test_pattern_with_only_spaces(self):
        """Test avec seulement des espaces."""
        result = parse_patterns("   ")
        assert result == ["*.pc"]  # Retourne le défaut

    def test_pattern_with_empty_segments(self):
        """Test avec des segments vides."""
        result = parse_patterns("*.pc;;*.sc")
        assert result == ["*.pc", "*.sc"]  # Ignore les segments vides


class TestCaseInsensitiveMatching:
    """Tests pour les fonctions de matching insensible à la casse."""

    def test_match_case_insensitive_exact(self):
        """Test de matching exact (même casse)."""
        assert match_case_insensitive("file.pc", "*.pc") is True
        assert match_case_insensitive("file.txt", "*.pc") is False

    def test_match_case_insensitive_different_case(self):
        """Test de matching avec casse différente."""
        assert match_case_insensitive("FILE.PC", "*.pc") is True
        assert match_case_insensitive("file.pc", "*.PC") is True
        assert match_case_insensitive("FiLe.Pc", "*.pC") is True

    def test_match_case_insensitive_wildcards(self):
        """Test avec wildcards."""
        assert match_case_insensitive("test_file.PC", "test_*.PC") is True
        assert match_case_insensitive("TEST_FILE.pc", "test_*.pc") is True
        assert match_case_insensitive("other.PC", "test_*.PC") is False

    def test_find_files_case_insensitive(self, tmp_path, simple_proc_source):
        """Test de recherche de fichiers insensible à la casse."""
        (tmp_path / "file1.PC").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(simple_proc_source)
        (tmp_path / "file3.txt").write_text("Not a Pro*C file")

        files = find_files_case_insensitive(tmp_path, ["*.PC"], recursive=False)

        assert len(files) == 2  # file1.PC et file2.pc
        filenames = {f.name for f in files}
        assert "file1.PC" in filenames
        assert "file2.pc" in filenames
        assert "file3.txt" not in filenames

    def test_find_files_case_insensitive_multiple_patterns(self, tmp_path, simple_proc_source):
        """Test avec plusieurs patterns insensibles à la casse."""
        (tmp_path / "file1.PC").write_text(simple_proc_source)
        (tmp_path / "file2.SC").write_text(simple_proc_source)
        (tmp_path / "file3.inc").write_text(simple_proc_source)
        (tmp_path / "file4.txt").write_text("Not a Pro*C file")

        files = find_files_case_insensitive(tmp_path, ["*.PC", "*.SC", "*.INC"], recursive=False)

        assert len(files) == 3  # Les trois fichiers PC, SC, inc
        filenames = {f.name for f in files}
        assert "file1.PC" in filenames
        assert "file2.SC" in filenames
        assert "file3.inc" in filenames
        assert "file4.txt" not in filenames

    def test_find_files_case_insensitive_recursive(self, tmp_path, simple_proc_source):
        """Test avec recherche récursive insensible à la casse."""
        (tmp_path / "file1.PC").write_text(simple_proc_source)

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.pc").write_text(simple_proc_source)

        files = find_files_case_insensitive(tmp_path, ["*.PC"], recursive=True)

        assert len(files) == 2  # Les deux fichiers PC et pc
        filenames = {f.name for f in files}
        assert "file1.PC" in filenames
        assert "file2.pc" in filenames

    def test_find_files_case_insensitive_all_files_found(self, tmp_path, simple_proc_source):
        """Test que tous les fichiers correspondant aux patterns sont trouvés récursivement."""
        # Créer plusieurs fichiers avec différentes casses dans plusieurs sous-répertoires
        (tmp_path / "file1.PC").write_text(simple_proc_source)
        (tmp_path / "file2.pc").write_text(simple_proc_source)

        subdir1 = tmp_path / "subdir1"
        subdir1.mkdir()
        (subdir1 / "file3.PC").write_text(simple_proc_source)
        (subdir1 / "file4.sc").write_text(simple_proc_source)

        subdir2 = tmp_path / "subdir2"
        subdir2.mkdir()
        (subdir2 / "file5.INC").write_text(simple_proc_source)
        (subdir2 / "file6.inc").write_text(simple_proc_source)

        nested = subdir2 / "nested"
        nested.mkdir()
        (nested / "file7.PC").write_text(simple_proc_source)
        (nested / "file8.SC").write_text(simple_proc_source)

        # Fichiers qui ne doivent pas être trouvés
        (tmp_path / "ignore.txt").write_text("Not a Pro*C file")
        (subdir1 / "ignore2.txt").write_text("Not a Pro*C file")

        files = find_files_case_insensitive(tmp_path, ["*.PC", "*.SC", "*.INC"], recursive=True)

        # Doit trouver tous les fichiers PC, SC, INC (insensible à la casse)
        # Racine: file1.PC, file2.pc (2 PC)
        # subdir1: file3.PC (1 PC), file4.sc (1 SC)
        # subdir2: file5.INC, file6.inc (2 INC)
        # subdir2/nested: file7.PC (1 PC), file8.SC (1 SC)
        # Total: 4 PC + 2 SC + 2 INC = 8 fichiers
        assert len(files) == 8, f"Attendu 8 fichiers, trouvé {len(files)}"

        filenames = {f.name for f in files}
        expected_files = {
            "file1.PC",
            "file2.pc",
            "file3.PC",
            "file4.sc",
            "file5.INC",
            "file6.inc",
            "file7.PC",
            "file8.SC",
        }
        assert (
            filenames == expected_files
        ), f"Fichiers manquants: {expected_files - filenames}, fichiers inattendus: {filenames - expected_files}"

        # Vérifier qu'aucun fichier .txt n'est présent
        assert not any("ignore" in f.name for f in files)

    def test_analyze_with_ipattern_all_files_analyzed(self, tmp_path, simple_proc_source):
        """Test que tous les fichiers trouvés avec ipattern sont analysés."""
        # Créer plusieurs fichiers dans plusieurs sous-répertoires
        (tmp_path / "file1.PC").write_text(simple_proc_source)
        (tmp_path / "file2.sc").write_text(simple_proc_source)

        subdir1 = tmp_path / "subdir1"
        subdir1.mkdir()
        (subdir1 / "file3.INC").write_text(simple_proc_source)
        (subdir1 / "file4.pc").write_text(simple_proc_source)

        nested = subdir1 / "nested"
        nested.mkdir()
        (nested / "file5.SC").write_text(simple_proc_source)

        analyzer = ProCAnalyzer()

        with (
            patch("proc_analyzer.cli.console.print"),
            patch("proc_analyzer.cli.Progress") as mock_progress,
        ):
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"

            report = analyze_with_progress(
                analyzer, str(tmp_path), ipattern="*.PC;*.SC;*.INC", recursive=True
            )

        # Doit analyser tous les 5 fichiers trouvés
        assert report is not None
        assert len(report.files) == 5, f"Attendu 5 fichiers analysés, trouvé {len(report.files)}"

        filepaths = {f.filepath for f in report.files}
        assert any("file1.PC" in fp for fp in filepaths)
        assert any("file2.sc" in fp for fp in filepaths)
        assert any("file3.INC" in fp for fp in filepaths)
        assert any("file4.pc" in fp for fp in filepaths)
        assert any("file5.SC" in fp for fp in filepaths)
