#!/usr/bin/env python3
"""Generador de Skeletons AST para TDD / Black-Box Prompting.

Recorre recursivamente el directorio `src/`, analiza el AST de cada módulo Python,
conserva únicamente imports, clases, firmas y docstrings, y reemplaza el cuerpo
de cada función o método por `raise NotImplementedError()`.

El resultado se guarda en `skeletons/` manteniendo la jerarquía original.
"""

import ast
import sys
from pathlib import Path


class SkeletonTransformer(ast.NodeTransformer):
    """Transformador AST que vacía el cuerpo de las funciones preservando su docstring."""

    def _stub_function_body(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> ast.FunctionDef | ast.AsyncFunctionDef:
        # 1. Conservar el docstring si existe como primera declaración
        docstring_stmt = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring_stmt = node.body[0]

        # 2. Crear el nodo: raise NotImplementedError()
        raise_stmt = ast.Raise(
            exc=ast.Call(
                func=ast.Name(id="NotImplementedError", ctx=ast.Load()),
                args=[],
                keywords=[],
            ),
            cause=None,
        )

        # 3. Reemplazar el cuerpo
        node.body = [docstring_stmt, raise_stmt] if docstring_stmt else [raise_stmt]
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:  # pylint: disable=invalid-name
        """AST visitor for standard function definitions.

        Args:
            node: The `ast.FunctionDef` node to transform.

        Returns:
            The transformed node with a stubbed body.
        """
        self.generic_visit(node)
        return self._stub_function_body(node)  # type: ignore

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> ast.AsyncFunctionDef:  # pylint: disable=invalid-name
        """AST visitor for asynchronous function definitions.

        Args:
            node: The `ast.AsyncFunctionDef` node to transform.

        Returns:
            The transformed node with a stubbed body.
        """
        self.generic_visit(node)
        return self._stub_function_body(node)  # type: ignore


def create_skeleton_file(src_path: Path, dest_path: Path) -> None:
    """Reads a Python file, transforms its AST into a skeleton, and writes it to the destination.

    Args:
        src_path (Path): The path to the source Python file.
        dest_path (Path): The path where the skeleton file will be written.

    Returns:
        None

    Raises:
        FileNotFoundError: If the source file does not exist.
        SyntaxError: If the source file contains invalid Python syntax.
        Exception: For any other unexpected errors during processing.
    """
    source_code = src_path.read_text(encoding="utf-8")
    parsed_ast = ast.parse(source_code, filename=str(src_path))

    # Apply the AST transformation
    transformer = SkeletonTransformer()
    skeleton_ast = transformer.visit(parsed_ast)
    ast.fix_missing_locations(skeleton_ast)

    # Convert the AST back to formatted Python code
    skeleton_code = ast.unparse(skeleton_ast)

    # Create directories if they don't exist and save the skeleton
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(skeleton_code, encoding="utf-8")
    print(f"  ✓ Skeleton created: {dest_path}")


def main():
    """Main function to orchestrate the skeleton generation process.

    Scans the source directory, finds all Python files, and generates a
    corresponding skeleton file in the output directory. It reports on
    the number of files processed and exits with a non-zero status code
    if any errors occurred.
    """
    src_dir = Path("src")
    skeletons_dir = Path("skeletons")

    if not src_dir.exists():
        print("Error: No se encontró el directorio 'src/'.")
        return

    failed_files_count = 0
    print("=== GENERANDO SKELETONS AST (PURE SPEC-FIRST) ===")
    python_files = list(src_dir.rglob("*.py"))

    for src_file in python_files:
        relative_path = src_file.relative_to(src_dir)
        dest_file = skeletons_dir / relative_path
        try:
            create_skeleton_file(src_file, dest_file)
        except (SyntaxError, OSError) as e:
            print(f"  ❌ Error processing {src_file}: {e}")
            failed_files_count += 1

    print(f"\nCompleted. Processed {len(python_files)} files in '{skeletons_dir}/'.")
    if failed_files_count > 0:
        print(f"  {failed_files_count} files failed to generate skeletons.")
        sys.exit(1)


if __name__ == "__main__":
    main()
