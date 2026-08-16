"""Architectural Audit Orchestrator for DOM Normalizer.

This script automates the process of running architectural audits on different
subsystems of the project using the 'aider' tool with a local LLM. It reads a
YAML configuration file to determine which files to audit, what prompts to use,
and how to manage the process.

Analytical Blueprint:
---------------------
- **Objective:** To systematically generate architectural audit reports for
  pre-defined groups of source files, ensuring consistency and allowing for
  resumable, managed execution.
- **Components:**
  - `main`: The main orchestrator function.
  - `_load_config`: Loads the `audit_orchestrator.yaml` configuration.
  - `_prepare_environment`: Sets up directories and loads necessary file contents.
  - `_filter_pending_groups`: Determines which audit groups need to be run.
  - `_run_audit_for_group`: Executes the `aider` subprocess for a single group.
  - `check_temperature`: A safety function to monitor system temperature.
- **Analytical Steps:**
  1. Locate the project root and load the `audit_orchestrator.yaml` config.
  2. Prepare the environment (create report directory, load prompt).
  3. Filter the list of audit groups, skipping any that already have a report.
  4. Iterate through pending groups with a progress bar.
  5. For each group:
     a. Perform a thermal check to prevent overheating.
     b. Resolve file paths, including the `CORE_FILE` macro.
     c. Construct and execute the `aider` command as a subprocess.
     d. Capture the output and save it to a Markdown report file.
     e. Handle any errors during execution and save an error report.
     f. Pause for a configurable "cool-down" period.
- **Output:** A set of Markdown files in the configured report directory, each
  containing the output of an audit.
"""

import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

try:
    import yaml
    from tqdm import tqdm
except ImportError:
    print("[✖] Missing required dependencies. Please run: pip install PyYAML tqdm")
    sys.exit(1)


def find_project_root() -> Path:
    """Finds the project root by ascending from the script location."""
    current = Path(__file__).resolve().parent
    for parent in [current, *list(current.parents)]:
        if (parent / "audit_orchestrator.yaml").exists():
            return parent
    # Fallback to the current directory if not found
    return Path.cwd()


def _get_current_max_temperature() -> float | None:
    """Reads all thermal zones and returns the maximum temperature found in Celsius.

    This function scans `/sys/class/thermal` for temperature readings. It
    gracefully handles I/O errors or malformed temperature files by skipping
    them.

    Returns:
        The maximum temperature found as a float, or None if no temperatures
        could be read (e.g., on a non-Linux system or due to permissions).
    """
    temps = []
    # Suppress only expected OS/IO errors, allowing programming errors to surface.
    with suppress(OSError):
        thermal_path = Path("/sys/class/thermal")
        if not thermal_path.exists():
            return None

        for zone in thermal_path.glob("thermal_zone*"):
            temp_file = zone / "temp"
            if temp_file.exists():
                try:
                    temps.append(int(temp_file.read_text().strip()) / 1000.0)
                except ValueError:
                    # Skip malformed temperature files.
                    continue

    return max(temps, default=None)


def check_temperature(max_temp: int | None) -> bool:
    """Checks the system temperature against a threshold.

    This function is a safeguard to prevent overheating during intensive
    processing. It uses a helper to get the current max temperature and
    compares it against a given threshold.

    If the temperature cannot be read, it gracefully fails and returns True,
    allowing the process to continue.

    Args:
        max_temp: The maximum allowed temperature in Celsius. If None, the
            check is skipped.

    Returns:
        False if the current temperature exceeds `max_temp`, True otherwise.
    """
    if max_temp is None:
        return True

    current_max = _get_current_max_temperature()

    if current_max is not None and current_max >= max_temp:
        print(
            f"\n[!] THERMAL ALERT: Current temperature ({current_max}°C) exceeds the limit of {max_temp}°C.",
        )
        return False

    return True


def _load_config(root_dir: Path) -> dict[str, Any]:
    """Loads the orchestrator configuration from the YAML file.

    Args:
        root_dir: The project's root directory.

    Returns:
        A dictionary containing the loaded configuration.
    """
    yaml_path = root_dir / "audit_orchestrator.yaml"
    if not yaml_path.exists():
        print(f"[✖] Configuration file not found at: {yaml_path}")
        sys.exit(1)
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _prepare_environment(config: dict[str, Any], root_dir: Path) -> dict[str, Any]:
    """Prepares the environment by creating directories and loading files.

    Args:
        config: The configuration dictionary.
        root_dir: The project's root directory.

    Returns:
        A dictionary containing environment details like paths and file contents.
    """
    report_dir = root_dir / config.get("report_dir", "audit_reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    prompt_path_rel = config.get("prompt_path")
    if not prompt_path_rel:
        print("[✖] 'prompt_path' is not defined in the configuration.")
        sys.exit(1)

    prompt_file = root_dir / prompt_path_rel
    if not prompt_file.exists():
        print(f"[✖] Prompt file not found at: {prompt_file}")
        sys.exit(1)
    prompt_content = prompt_file.read_text(encoding="utf-8")

    core_file_rel = config.get("core_file")
    if not core_file_rel:
        print("[✖] 'core_file' is not defined in the configuration.")
        sys.exit(1)
    core_abs_path = str(root_dir / core_file_rel)

    model = config.get("model")
    if not model:
        print("[✖] 'model' is not defined in the configuration.")
        sys.exit(1)

    return {
        "report_dir": report_dir,
        "prompt_content": prompt_content,
        "core_abs_path": core_abs_path,
        "model": model,
        "time_sleep": config.get("time_sleep", 10),
        "max_temp": config.get("max_temperature_celsius"),
    }


def _filter_pending_groups(
    groups: list[dict[str, Any]],
    report_dir: Path,
) -> list[dict[str, Any]]:
    """Filters out audit groups that already have a report generated.

    Args:
        groups: The list of all audit groups from the configuration.
        report_dir: The directory where reports are stored.

    Returns:
        A list of groups that do not have a corresponding report file.
    """
    pending_groups = []
    for group in groups:
        name = group["name"]
        report_file = report_dir / f"audit_{name}.md"
        if report_file.exists():
            print(
                f"[i] Skipping '{name}': Report already exists (delete file to regenerate).",
            )
        else:
            pending_groups.append(group)
    return pending_groups


def _run_audit_for_group(group: dict[str, Any], env: dict[str, Any], root_dir: Path):
    """Runs the Aider audit for a single group.

    This function constructs and executes the `aider` command as a subprocess,
    captures its output, and writes it to a report file. It handles errors
    gracefully by creating an error report.

    Args:
        group: The audit group dictionary.
        env: The environment dictionary with paths and settings.
        root_dir: The project's root directory.
    """
    name = group["name"]
    report_file = env["report_dir"] / f"audit_{name}.md"

    # Resolve file paths, including CORE_FILE macro
    resolved_files = []
    for f in group["files"]:
        if f == "CORE_FILE":
            resolved_files.append(env["core_abs_path"])
        else:
            resolved_files.append(str(root_dir / f))

    cmd = [
        "aider",
        "--model",
        env["model"],
        "--yes",
        "--no-auto-commits",
        "--message",
        env["prompt_content"],
        *resolved_files,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(root_dir),
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        report_file.write_text(result.stdout, encoding="utf-8")
    except subprocess.CalledProcessError as e:
        err_msg = (
            f"# Audit Error\n\n"
            f"**Group:** `{name}`\n\n"
            f"**Exit Code:** `{e.returncode}`\n\n"
            f"**Command:**\n```sh\n{' '.join(e.cmd)}\n```\n\n"
            f"**Stderr:**\n```\n{e.stderr}\n```"
        )
        report_file.write_text(err_msg, encoding="utf-8")
        print(
            f"\n[✖] Error running Aider on group '{name}' "
            f"(exit code {e.returncode}). Error log saved.",
        )
    except FileNotFoundError:
        err_msg = "# Audit Error\n\n**Error:** `aider` command not found. Is it installed and in your PATH?"
        report_file.write_text(err_msg, encoding="utf-8")
        print(
            "\n[✖] `aider` command not found. Please ensure it is installed and in your system's PATH.",
        )
        # Exit because this error will repeat for all groups
        sys.exit(1)


def main():
    """Orchestrates the architectural audit process based on a YAML config."""
    root_dir = find_project_root()
    config = _load_config(root_dir)
    env = _prepare_environment(config, root_dir)

    all_groups = config.get("audit_groups", [])
    pending_groups = _filter_pending_groups(all_groups, env["report_dir"])

    if not pending_groups:
        print("\n[✔] All audit groups already have reports. Nothing to process.")
        return

    print(f"\n[i] Starting audit process for {len(pending_groups)} pending group(s)...")

    all_groups_processed = True
    with tqdm(pending_groups, desc="Audit Progress", unit="group") as pbar:
        for i, group in enumerate(pbar):
            if not check_temperature(env["max_temp"]):
                print("\n[!] Process stopped due to thermal safety.")
                all_groups_processed = False
                break

            pbar.set_postfix_str(f"Processing: {group['name']}")
            start_time = time.time()

            _run_audit_for_group(group, env, root_dir)

            elapsed = time.time() - start_time
            pbar.set_postfix_str(f"'{group['name']}' completed in {elapsed:.1f}s")

            # Cooling pause if not the last item
            is_last_group = i == len(pending_groups) - 1
            if not is_last_group and env["time_sleep"] > 0:
                pbar.set_postfix_str(f"Cooling down for {env['time_sleep']}s...")
                time.sleep(env["time_sleep"])

    if all_groups_processed:
        print(
            "\n[✔] Audit batch finished successfully, adhering to system principles.",
        )
    else:
        print("\n[!] Audit batch was interrupted and did not complete all groups.")


if __name__ == "__main__":
    main()
