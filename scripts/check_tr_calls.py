#  Copyright 2026 casaGeo Data + Services GmbH <info@casageo.de>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  SPDX-License-Identifier: Apache-2.0

"""
Check for issues with calls to ``tr()`` and ``__tr()``.

There is a very specific bug in ``lupdate``, where a call to ``tr()``
with two positional arguments and a trailing comma is treated as if it
were a call with three positional arguments. This causes ``lupdate`` to
generate plural form translations instead of singular form translations.
When Qt looks up the translation at runtime, it searches for a singular
form translation, which doesn’t exist.
"""

import ast
import sys
import tokenize
from io import StringIO
from pathlib import Path

TR_FUNCTIONS = ("tr", "__tr")

SKIP_TOKENS = {
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.COMMENT,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
}


def getname(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def two_argument_call(call: ast.Call) -> bool:
    return (
        len(call.args) == 2
        and not any(isinstance(a, ast.Starred) for a in call.args)
        and not call.keywords
    )


def trailing_comma(segment: str) -> bool:
    tokens = [
        t.string
        for t in tokenize.generate_tokens(StringIO(segment).readline)
        if t.type not in SKIP_TOKENS
    ]
    return len(tokens) >= 2 and tokens[-2] == "," and tokens[-1] == ")"


def main(args: list[str] | None = None):
    paths = args if args is not None else sys.argv[1:]
    errors = 0
    for path in paths:
        source = Path(path).read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source, path)):
            if (
                isinstance(node, ast.Call)
                and getname(node.func) in TR_FUNCTIONS
                and two_argument_call(node)
            ):
                segment = ast.get_source_segment(source, node)
                if segment and trailing_comma(segment):
                    print(
                        f"{path}:{node.lineno}: {getname(node.func)}() must not be called with two arguments and a trailing comma",
                        file=sys.stderr,
                    )
                    errors += 1

    if errors:
        print(f"{errors} error(s) found", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
