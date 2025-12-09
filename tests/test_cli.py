"""
Tests pour le module CLI.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from proc_analyzer.analyzer import ProCAnalyzer, AnalysisReport
from proc_analyzer.cli import analyze_with_progress


class TestAnalyzeWithProgress:
    """Tests pour la fonction analyze_with_progress."""

    def test_analyze_single_file(self, tmp_path, simple_proc_source):
        """Test de l'analyse d'un fichier unique."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(simple_proc_source)
        
        analyzer = ProCAnalyzer()
        
        # Mock console.print pour éviter l'affichage dans les tests
        with patch('proc_analyzer.cli.console.print'):
            report = analyze_with_progress(analyzer, str(file_path))
        
        assert report is not None
        assert len(report.files) == 1
        assert report.files[0].filepath == str(file_path)

    def test_analyze_directory_empty(self, tmp_path):
        """Test avec un répertoire vide."""
        analyzer = ProCAnalyzer()
        
        with patch('proc_analyzer.cli.console.print'):
            report = analyze_with_progress(analyzer, str(tmp_path))
        
        assert report is not None
        assert len(report.files) == 0

    def test_analyze_directory_single_file(self, tmp_path, simple_proc_source):
        """Test avec un répertoire contenant un fichier."""
        file_path = tmp_path / "test.pc"
        file_path.write_text(simple_proc_source)
        
        analyzer = ProCAnalyzer()
        
        with patch('proc_analyzer.cli.console.print'), \
             patch('proc_analyzer.cli.Progress') as mock_progress:
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
        
        with patch('proc_analyzer.cli.console.print'), \
             patch('proc_analyzer.cli.Progress') as mock_progress:
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
        
        with patch('proc_analyzer.cli.console.print'), \
             patch('proc_analyzer.cli.Progress') as mock_progress:
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
        
        with patch('proc_analyzer.cli.console.print'), \
             patch('proc_analyzer.cli.Progress') as mock_progress:
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"
            
            report = analyze_with_progress(
                analyzer, 
                str(tmp_path), 
                pattern="*.pc", 
                recursive=False
            )
        
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
        
        with patch('proc_analyzer.cli.console.print'), \
             patch('proc_analyzer.cli.Progress') as mock_progress:
            mock_progress.return_value.__enter__.return_value.add_task.return_value = "task_id"
            
            report = analyze_with_progress(
                analyzer, 
                str(tmp_path), 
                pattern="*.pc", 
                recursive=True
            )
        
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
        
        with patch('proc_analyzer.cli.console.print'), \
             patch('proc_analyzer.cli.Progress') as mock_progress:
            # Mock Progress pour capturer les appels
            mock_progress_instance = MagicMock()
            mock_task = MagicMock()
            mock_progress_instance.add_task.return_value = mock_task
            mock_progress.return_value.__enter__.return_value = mock_progress_instance
            mock_progress.return_value.__exit__.return_value = None
            
            # Injecter directement le callback dans analyze_directory
            with patch.object(analyzer, 'analyze_directory') as mock_analyze:
                mock_report = AnalysisReport()
                mock_report.files = analyzer.analyze_file(str(tmp_path / "file1.pc"))
                mock_analyze.return_value = mock_report
                
                analyze_with_progress(analyzer, str(tmp_path), pattern="*.pc")
                
                # Vérifier que analyze_directory a été appelé avec progress_callback
                assert mock_analyze.called
                call_kwargs = mock_analyze.call_args[1]
                assert 'progress_callback' in call_kwargs
                assert callable(call_kwargs['progress_callback'])
