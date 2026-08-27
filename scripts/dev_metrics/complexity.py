"""1.4 복잡도 대비 결함 밀도 - 순환 복잡도(Cyclomatic Complexity) 산출 (부분 자동화)

외부 정적분석 툴(SonarQube 등) 없이, Python 표준 라이브러리 `ast`만으로 Python
소스 파일의 함수별 순환 복잡도를 계산한다. 이는 "결함 밀도"가 아니라 결함 밀도를
해석할 때 함께 참고할 복잡도 신호일 뿐이며, 실제 결함 수와 연결하려면 Jira 버그
티켓 데이터가 추가로 필요하다 (문서 1.4 참고).

복잡도 계산 규칙: 함수는 기본 복잡도 1에서 시작해 if/elif, for, while, except,
with, assert, boolean 연산자(and/or), comprehension 의 조건절마다 1씩 증가한다
(McCabe Cyclomatic Complexity의 단순화 버전).

사용 예:
    python3 complexity.py --path /path/to/repo/src
"""
from __future__ import annotations

import argparse
import ast
import os


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)


def analyze_file(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []

    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = ComplexityVisitor()
            visitor.visit(node)
            results.append(
                {
                    "file": path,
                    "function": node.name,
                    "lineno": node.lineno,
                    "complexity": visitor.complexity,
                }
            )
    return results


def iter_python_files(root: str):
    if os.path.isfile(root):
        if root.endswith(".py"):
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".venv", "venv", "node_modules")]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=".", help="분석할 파일 또는 디렉터리 경로")
    parser.add_argument("--top", type=int, default=20, help="복잡도 상위 N개 함수 출력")
    parser.add_argument("--threshold", type=int, default=10, help="경고 기준 복잡도 (기본 10)")
    args = parser.parse_args()

    all_results = []
    for path in iter_python_files(args.path):
        all_results.extend(analyze_file(path))

    if not all_results:
        print("분석할 Python 함수를 찾지 못했습니다.")
        return

    all_results.sort(key=lambda r: -r["complexity"])
    avg = sum(r["complexity"] for r in all_results) / len(all_results)
    over_threshold = [r for r in all_results if r["complexity"] > args.threshold]

    print(f"# 순환 복잡도(Cyclomatic Complexity) 분석 (함수 {len(all_results)}개, 평균 {round(avg, 2)}, "
          f"임계값({args.threshold}) 초과 {len(over_threshold)}개)\n")
    print(f"{'complexity':>10}  file:line  function")
    for r in all_results[: args.top]:
        print(f"{r['complexity']:>10}  {r['file']}:{r['lineno']}  {r['function']}")


if __name__ == "__main__":
    main()
