import argparse
import re
import sys
import xml.dom.minidom
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

TOKEN_SPEC = [
    ("STRING", r"'[^']*'"),
    ("NUMBER", r"[+-]?\d+(?:\.\d*)?[eE][+-]?\d+|[+-]?\d+\.\d*|[+-]?\d+"),
    ("DEF", r"\bdef\b"),
    ("NAME", r"[a-zA-Z][_a-zA-Z0-9]*"),
    ("OP", r"[+-]"),
    ("EQUAL", r"="),
    ("COMMA", r","),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("WS", r"\s+"),
    ("MISMATCH", r"."),
]


def strip_comments(text):
    res = []
    in_str = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "'":
            in_str = not in_str
            res.append(ch)
        elif ch == "*" and not in_str:
            while i < len(text) and text[i] != "\n":
                i += 1
            if i < len(text):
                res.append("\n")
        else:
            res.append(ch)
        i += 1
    return "".join(res)


def tokenize(text):
    clean = strip_comments(text)
    joint_re = "|".join(f"(?P<{p}>{r})" for p, r in TOKEN_SPEC)
    tokens = []
    for m in re.finditer(joint_re, clean):
        kind = m.lastgroup
        val = m.group()
        if kind == "WS":
            continue
        if kind == "MISMATCH":
            raise SyntaxError(f"Неизвестный символ: {val}")
        tokens.append((kind, val))
    return tokens


def op_add(args):
    if len(args) != 2:
        raise SyntaxError("Операция '+' требует 2 аргумента")
    if isinstance(args[0], list) and isinstance(args[1], list):
        return args[0] + args[1]
    if isinstance(args[0], str) or isinstance(args[1], str):
        return str(args[0]) + str(args[1])
    return args[0] + args[1]


def op_sub(args):
    if len(args) != 2:
        raise SyntaxError("Операция '-' требует 2 аргумента")
    return args[0] - args[1]


def op_ord(args):
    if len(args) != 1 or not isinstance(args[0], str):
        raise SyntaxError("ord() требует 1 строку")
    return ord(args[0][0]) if args[0] else 0


def op_sort(args):
    if len(args) != 1 or not isinstance(args[0], list):
        raise SyntaxError("sort() требует массив")
    return sorted(args[0])


OPERATIONS = {
    "+": op_add,
    "-": op_sub,
    "ord": op_ord,
    "sort": op_sort,
}


class Parser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.constants = {}

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None, None

    def consume(self, expected=None):
        kind, val = self.peek()
        if kind is None:
            raise SyntaxError("Неожиданный конец файла")
        if expected and kind != expected:
            raise SyntaxError(
                f"Ожидался {expected}, получен {kind} ('{val}')"
            )
        self.pos += 1
        return val

    def parse_value(self):
        kind, val = self.peek()
        if kind == "NUMBER":
            self.consume()
            return float(val) if ("." in val or "e" in val.lower()) else int(val)
        if kind == "STRING":
            self.consume()
            return val[1:-1]
        if kind == "LPAREN":
            return self.parse_array()
        if kind == "LBRACE":
            return self.parse_expression()
        if kind == "NAME":
            self.consume()
            if val not in self.constants:
                raise SyntaxError(f"Неизвестная константа '{val}'")
            return self.constants[val]
        raise SyntaxError(f"Неожиданный токен: {kind} ('{val}')")

    def parse_array(self):
        self.consume("LPAREN")
        items = []
        if self.peek()[0] == "RPAREN":
            self.consume("RPAREN")
            return items
        while True:
            items.append(self.parse_value())
            kind, _ = self.peek()
            if kind == "COMMA":
                self.consume("COMMA")
                if self.peek()[0] == "RPAREN":
                    break
            elif kind == "RPAREN":
                break
            else:
                raise SyntaxError("Ожидалась запятая или ')' в массиве")
        self.consume("RPAREN")
        return items

    def parse_expression(self):
        self.consume("LBRACE")
        op = self.consume()
        if op not in OPERATIONS:
            raise SyntaxError(f"Неизвестная операция '{op}'")
        args = []
        while self.peek()[0] != "RBRACE":
            args.append(self.parse_value())
        self.consume("RBRACE")
        return OPERATIONS[op](args)

    def parse(self):
        result = {}
        while self.peek()[0] is not None:
            kind, _ = self.peek()
            if kind == "DEF":
                self.consume("DEF")
                name = self.consume("NAME")
                self.consume("EQUAL")
                val = self.parse_value()
                self.constants[name] = val
                result[name] = val
            else:
                val = self.parse_value()
                result[f"item_{len(result)}"] = val
        return result


def value_to_xml(tag, val):
    elem = ET.Element(tag)
    if isinstance(val, list):
        for item in val:
            elem.append(value_to_xml("item", item))
    else:
        elem.text = str(val)
    return elem


def to_xml_string(data):
    root = ET.Element("configuration")
    for key, val in data.items():
        root.append(value_to_xml(key, val))
    raw = ET.tostring(root, encoding="utf-8")
    dom = xml.dom.minidom.parseString(raw)
    return dom.toprettyxml(indent="    ")


def parse_args():
    p = argparse.ArgumentParser(description="Транслятор в XML")
    p.add_argument("-i", "--input", dest="file", help="Входной файл")
    p.add_argument("pos_file", nargs="?", help="Позиционный файл")
    return p.parse_args()


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="cp1251") as f:
            return f.read()


def main():
    args = parse_args()
    path = args.file or args.pos_file
    if not path:
        sys.stderr.write("Ошибка: Не указан входной файл.\n")
        sys.exit(1)
    try:
        tokens = tokenize(read_file(path))
        parser = Parser(tokens)
        print(to_xml_string(parser.parse()))
    except (SyntaxError, FileNotFoundError) as err:
        sys.stderr.write(f"Ошибка синтаксиса: {err}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
