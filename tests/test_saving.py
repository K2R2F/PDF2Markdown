import tempfile
import unittest
from pathlib import Path

from saving import save_file


class SavingTests(unittest.TestCase):
    def test_no_overwrite_and_utf8(self):
        with tempfile.TemporaryDirectory() as folder:
            first = save_file(folder, 'report.md', '元の文書')
            second = save_file(folder, 'report.md', '追加の文書')
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(encoding='utf-8'), '元の文書')
            self.assertEqual(second.read_text(encoding='utf-8'), '追加の文書')

    def test_nested_folder_and_untrusted_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / 'nested'
            result = save_file(str(directory), '../../report.md', '本文')
            self.assertEqual(result.parent, directory.resolve())
            self.assertTrue(result.is_file())

    def test_invalid_destination(self):
        with self.assertRaises(ValueError):
            save_file('', 'report.md', 'text')
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'file'
            file.write_text('existing')
            with self.assertRaises(OSError):
                save_file(str(file), 'report.md', 'text')
