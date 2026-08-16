"""Dependency Mapper for Python Projects.

This script analyzes the AST of a Python project to build a flat dependency map.
It identifies internal dependencies within a specified root
package and outputs the resulting structure to a YAML file.

Analytical Blueprint:
---------------------
- **Objective:** To generate a flat dependency map for a Python package, showing
  direct dependencies for each module.
- **Components:**
  - `main`: Orchestrates the entire process from argument parsing to file output.
  - `_find_modules`: Scans a directory to find all relevant Python modules.
  - `_get_module_dependencies`: Parses a single Python file's AST to extract
    its internal dependencies.
  - `_build_dependency_graphs`: Creates forward and reverse dependency maps for
    the entire project.
- **Analytical Steps:**
  1. Parse command-line arguments: `root_package`, `excluded_paths`, `output_file`.
  2. Locate all `.py` files within the `root_package` directory, filtering out
     any specified exclusions.
  3. For each module, parse its AST to find all `import` and `from ... import`
     statements.
  4. Filter these imports to retain only those that reference other modules
     within the `root_package`. `__future__` imports are ignored.
  5. Construct a `dependencies` graph (`module` -> `set of its dependencies`).
  6. Convert this graph into a dictionary sorted by module name, with each
     module's dependencies also sorted.
- **Output:** A YAML file containing a dictionary where keys are module names
  and values are lists of their direct dependencies.
"""

import argparse
import ast
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "[✖] Missing required dependency. Please run: pip install PyYAML",
        file=sys.stderr,
    )
    sys.exit(1)


def _is_file_excluded(py_file: Path, excluded_set: set[Path]) -> bool:
    """Checks if a given Python file should be excluded from analysis.

    Args:
        py_file: The path to the Python file to check.
        excluded_set: A set of absolute paths (files or directories) to exclude.

    Returns:
        True if the file should be excluded, False otherwise.
    """
    if py_file.name == "__init__.py":
        return True

    return any(
        (item.is_dir() and item in py_file.parents) or (item == py_file)
        for item in excluded_set
    )


def _find_modules(root_path: Path, excluded_paths: list[str]) -> list[Path]:
    """Finds all Python modules in a directory, respecting exclusions.

    Args:
        root_path: The path to the root package directory.
        excluded_paths: A list of relative paths (files or directories) to exclude.

    Returns:
        A list of Path objects for all Python modules to be analyzed.
    """
    root_path = root_path.resolve()
    all_py_files = [py_file.resolve() for py_file in root_path.rglob("*.py")]

    # Resolve excluded paths relative to the root_path. This correctly handles
    # both absolute and relative path strings in the `excluded_paths` list.
    excluded_set = set()
    for p in excluded_paths:
        path = Path(p)
        path = path.resolve() if path.is_absolute() else (root_path / path).resolve()
        excluded_set.add(path)

    modules = []
    modules.extend(
        py_file
        for py_file in all_py_files
        if not _is_file_excluded(py_file, excluded_set)
    )
    return modules


def _handle_import(node: ast.Import, root_package_name: str, dependencies: set[str]):
    """Processes an `ast.Import` node to find internal dependencies.

    Args:
        node: The `ast.Import` node to process.
        root_package_name: The name of the root package.
        dependencies: The set of dependencies to update.
    """
    for alias in node.names:
        if alias.name == root_package_name or alias.name.startswith(
            f"{root_package_name}.",
        ):
            dependencies.add(alias.name)


def _resolve_and_add_dependency(
    base_path: Path,
    module_part: str,
    python_path_root: Path,
    root_package_name: str,
    dependencies: set[str],
    unresolved_imports: list[str],
    current_module_path: Path,
) -> None:
    """Resolves a relative module path and adds it as a dependency if valid."""
    try:
        # Attempt to construct a module path relative to the Python path root.
        # This can fail if the path is outside the expected hierarchy.
        abs_module_path = (base_path / module_part).relative_to(
            python_path_root,
        )
        module_name = ".".join(abs_module_path.parts)
        if module_name.startswith(root_package_name):
            dependencies.add(module_name)
    except ValueError:
        unresolved_import_path = (base_path / module_part).resolve()
        unresolved_imports.append(
            f"In '{current_module_path}': Could not resolve relative import for path: {unresolved_import_path}",
        )


def _handle_relative_import(
    node: ast.ImportFrom,
    module_path: Path,
    root_package_name: str,
    python_path_root: Path,
    dependencies: set[str],
    unresolved_imports: list[str],
):
    """Handles relative imports by resolving the base path and delegating.

    Args:
        node: The `ast.ImportFrom` node for the relative import.
        module_path: The path of the module containing the import.
        root_package_name: The name of the root package.
        python_path_root: The root of the python path for module resolution.
        dependencies: The set of dependencies to update.
        unresolved_imports: A list to track imports that could not be resolved.
    """
    base_path = module_path.parent
    levels_to_walk = node.level - 1
    walked_levels = 0
    for _ in range(levels_to_walk):
        # Stop if we reach filesystem root to avoid walking above it
        if base_path.parent == base_path:
            break
        base_path = base_path.parent
        walked_levels += 1

    if walked_levels < levels_to_walk:
        unresolved_imports.append(
            f"In '{module_path}': Invalid relative import level ({node.level}) "
            "attempts to go above the filesystem root.",
        )
        return

    # If base_path has walked outside of python_path_root, treat as invalid
    try:
        base_path.relative_to(python_path_root)
    except ValueError:
        unresolved_imports.append(
            f"In '{module_path}': Invalid relative import level ({node.level}) "
            f"goes outside python_path_root '{python_path_root}'",
        )
        return

    if node.module is None:  # Case: `from . import sibling`
        for alias in node.names:
            _resolve_and_add_dependency(
                base_path,
                alias.name,
                python_path_root,
                root_package_name,
                dependencies,
                unresolved_imports,
                module_path,
            )
    else:  # Case: `from .subpackage import something`
        _resolve_and_add_dependency(
            base_path,
            node.module,
            python_path_root,
            root_package_name,
            dependencies,
            unresolved_imports,
            module_path,
        )


def _handle_import_from(
    node: ast.ImportFrom,
    module_path: Path,
    root_package_name: str,
    python_path_root: Path,
    dependencies: set[str],
    unresolved_imports: list[str],
):
    """Processes an `ast.ImportFrom` node to find internal dependencies.

    Handles both absolute and relative imports, including `from . import ...` style.

    Args:
        node: The `ast.ImportFrom` node to process.
        module_path: The path of the module containing the import.
        root_package_name: The name of the root package.
        python_path_root: The root of the python path for module resolution.
        dependencies: The set of dependencies to update.
        unresolved_imports: A list to track imports that could not be resolved.
    """
    if node.module == "__future__":
        return

    if node.level > 0:  # Relative import
        _handle_relative_import(
            node,
            module_path,
            root_package_name,
            python_path_root,
            dependencies,
            unresolved_imports,
        )

    # Absolute import within the project
    elif node.module and node.module.startswith(root_package_name):
        dependencies.add(node.module)


def _get_module_dependencies(
    module_path: Path,
    root_package_name: str,
    python_path_root: Path,
    unresolved_imports: list[str],
) -> set[str]:
    """Parses a module's AST to find its internal dependencies.

    Args:
        module_path: The path to the Python module file.
        root_package_name: The name of the root package.
        unresolved_imports: A list to track imports that could not be resolved.

    Returns:
        A set of fully qualified names of internal modules it depends on.
    """
    dependencies = set()
    try:
        with open(module_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(module_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {module_path}. Reason: {e}", file=sys.stderr)
        return dependencies

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            _handle_import(node, root_package_name, dependencies)
        elif isinstance(node, ast.ImportFrom):
            _handle_import_from(
                node,
                module_path,
                root_package_name,
                python_path_root,
                dependencies,
                unresolved_imports,
            )

    return dependencies


def _build_dependency_graphs(
    modules: list[Path],
    root_package_name: str,
    python_path_root: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Builds forward and reverse dependency graphs for all modules.

    Args:
        modules: A list of paths to the Python modules.
        root_package_name: The name of the root package.
        python_path_root: The root of the python path for module resolution.

    Returns:
        A tuple containing two dictionaries:
        - dependencies: Maps a module to the set of modules it depends on.
        - dependents: Maps a module to the set of modules that depend on it.
    """
    dependencies: dict[str, set[str]] = {}
    dependents: dict[str, set[str]] = {}
    unresolved_imports: list[str] = []

    module_paths_to_names = {}
    invalid_module_paths: list[str] = []
    for m in modules:
        try:
            module_name = ".".join(
                m.relative_to(python_path_root).with_suffix("").parts,
            )
            module_paths_to_names[m] = module_name
        except ValueError:
            invalid_module_paths.append(
                f"Module path '{m}' is outside of the python_path_root '{python_path_root}' and will be ignored.",
            )
    module_names = set(module_paths_to_names.values())

    if invalid_module_paths:
        print("\n[!] Warnings for invalid module paths:", file=sys.stderr)
        for warning in sorted(set(invalid_module_paths)):
            print(f"  - {warning}", file=sys.stderr)

    for module_path, module_name in module_paths_to_names.items():
        dependencies[module_name] = set()
        dependents.setdefault(module_name, set())

        module_deps = _get_module_dependencies(
            module_path,
            root_package_name,
            python_path_root,
            unresolved_imports,
        )
        filtered_deps = {dep for dep in module_deps if dep in module_names}

        dependencies[module_name] = filtered_deps
        for dep in filtered_deps:
            dependents.setdefault(dep, set()).add(module_name)

    if unresolved_imports:
        print("\n[!] Warnings for unresolved relative imports:", file=sys.stderr)
        for warning in sorted(set(unresolved_imports)):
            print(f"  - {warning}", file=sys.stderr)

    return dependencies, dependents


def _find_python_path_root(root_path: Path, root_package_name: str) -> Path:
    """Calculates the source root for Python imports by traversing up from the package path.

    Args:
        root_path: The file system path to the root package.
        root_package_name: The dotted name of the root package.

    Returns:
        The inferred Python path root.
    """
    num_parts = len(root_package_name.split("."))
    python_path_root = root_path
    for _ in range(num_parts):
        python_path_root = python_path_root.parent
    return python_path_root


def main():
    """Main function to orchestrate dependency mapping."""
    parser = argparse.ArgumentParser(
        description="Generate a dependency map for a Python package.",
    )
    parser.add_argument(
        "root_package",
        help="The name of the root package to analyze (e.g., 'dom_normalizer').",
    )
    parser.add_argument(
        "output_file",
        help="The path to the output YAML file.",
    )
    parser.add_argument(
        "--python-path-root",
        help="Explicitly set the Python path root. If not set, it's inferred from the project structure.",
    )
    parser.add_argument(
        "--excluded",
        nargs="*",
        default=[],
        help=(
            "A list of packages or modules to exclude, relative to the root package "
            "(e.g., 'my_pkg.utils', 'my_pkg/tests'). Dotted names are converted to paths."
        ),
    )
    args = parser.parse_args()

    # Convert dotted module names in --excluded to path fragments for correct resolution.
    def _is_module_like(value: str, root_package_name: str) -> bool:
        """Checks if a string resembles a dotted module name within the target package."""
        # A value is "module-like" if it contains dots, no path separators, and
        # starts with the root package name. This prevents mis-classifying
        # file names like 'build.out'.
        return (
            "." in value
            and "/" not in value
            and "\\" not in value
            and value.startswith(root_package_name)
        )

    excluded_paths = [
        p.replace(".", "/")
        if _is_module_like(p, args.root_package) and not p.endswith(".py")
        else p
        for p in args.excluded
    ]

    project_root = Path.cwd()
    src_path = project_root / "src"
    package_path_part = args.root_package.replace(".", "/")
    root_path = (
        src_path / package_path_part
        if (src_path / package_path_part).is_dir()
        else project_root / package_path_part
    )

    if args.python_path_root:
        python_path_root = Path(args.python_path_root).resolve()
    else:
        python_path_root = _find_python_path_root(root_path, args.root_package)

    if not root_path.is_dir():
        print(
            f"Error: Root package directory not found at '{root_path}' or '{project_root / package_path_part}'",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Analyzing package '{args.root_package}' at: {root_path}")

    modules = _find_modules(root_path, excluded_paths)
    print(f"Found {len(modules)} modules to analyze.")

    dependencies, _ = _build_dependency_graphs(
        modules,
        args.root_package,
        python_path_root,
    )

    # Convert sets to sorted lists for clean YAML output
    dependency_map = {module: sorted(deps) for module, deps in dependencies.items()}

    # Sort the map by module name for consistent output
    sorted_dependency_map = dict(sorted(dependency_map.items()))

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            sorted_dependency_map,
            f,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
        )

    print(f"\n[✔] Dependency map successfully generated at: {output_path}")


if __name__ == "__main__":
    main()
