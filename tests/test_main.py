import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
from main import Parser, tokenize


class TestParser(unittest.TestCase):

    def run_parser(self, code):
        tokens = tokenize(code)
        parser = Parser(tokens)
        return parser.parse()

    def test_numbers_parsing(self):
        res = self.run_parser("def a = 42 def b = -12.5 def c = 1.2e3")
        self.assertEqual(res["a"], 42)
        self.assertEqual(res["b"], -12.5)
        self.assertEqual(res["c"], 1200.0)

    def test_strings_and_comments(self):
        code = "* Комментарий\ndef msg = 'hello world' * Еще комментарий"
        res = self.run_parser(code)
        self.assertEqual(res["msg"], "hello world")

    def test_arrays_nested(self):
        code = "def arr = ( 1, 'text', ( 2, 3 ) )"
        res = self.run_parser(code)
        self.assertEqual(res["arr"], [1, "text", [2, 3]])

    def test_operation_add(self):
        code = "def x = 10 def y = {+ x 5}"
        res = self.run_parser(code)
        self.assertEqual(res["y"], 15)

    def test_operation_sub(self):
        code = "def x = {- 50 15}"
        res = self.run_parser(code)
        self.assertEqual(res["x"], 35)

    def test_operation_ord(self):
        code = "def code = {ord 'A'}"
        res = self.run_parser(code)
        self.assertEqual(res["code"], 65)

    def test_operation_sort(self):
        code = "def sorted_list = {sort ( 3, 1, 2 )}"
        res = self.run_parser(code)
        self.assertEqual(res["sorted_list"], [1, 2, 3])

    def test_nested_expressions(self):
        code = "def res = {+ {- 20 5} {ord 'B'}}"
        res = self.run_parser(code)
        self.assertEqual(res["res"], 15 + 66)

    def test_syntax_error_unknown_const(self):
        with self.assertRaises(SyntaxError):
            self.run_parser("def val = {+ unknown_const 1}")

    def test_syntax_error_invalid_syntax(self):
        with self.assertRaises(SyntaxError):
            self.run_parser("def val = ( 1, 2")


if __name__ == "__main__":
    unittest.main()
