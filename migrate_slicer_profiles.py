#!/usr/bin/env python3
"""
Migrate Anycubic Slicer profiles to OrcaSlicer format.

This script processes JSON profile files from Anycubic Slicer, resolves inheritance,
and converts them to OrcaSlicer-compatible format.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Set

# Constants
DEFAULT_SOURCE = "~/.config/AnycubicSlicerNext/system/Anycubic/"
DEFAULT_OUTPUT = "~/.config/OrcaSlicer/user/default/"
DEFAULT_FILTER = "**/*.json"
DEFAULT_PREFIX = "Original "
MAX_INHERITANCE_DEPTH = 5

# Regex patterns
NOZZLE_PATTERN = re.compile(r"(\d+\.\d+) nozzle", re.IGNORECASE)
PRINTER_NAME_PATTERN = re.compile(r"(?:.*@)?\s*(.*?)\s*\d+\.\d+\s*nozzle", re.IGNORECASE)


class ProfileMigrator:
    """Handles migration of slicer profiles from Anycubic to OrcaSlicer format."""

    def __init__(
        self,
        source: Path,
        output: Path,
        prefix: str = "",
        postfix: str = "",
        filter_pattern: str = DEFAULT_FILTER,
        overwrite: bool = False,
        sort_keys: bool = False,
    ):
        self.source = source.expanduser().resolve()
        self.output = output.expanduser().resolve()
        self.prefix = prefix
        self.postfix = postfix
        self.filter_pattern = filter_pattern
        self.overwrite = overwrite
        self.sort_keys = sort_keys
        self.logger = logging.getLogger(__name__)
        self._processed_files: Set[Path] = set()

    def run(self) -> int:
        """Execute the migration process."""
        if not self.source.exists():
            self.logger.error(f"Source path does not exist: {self.source}")
            return 1

        self.logger.info(f"Source: {self.source}")
        self.logger.info(f"Output: {self.output}")
        self.logger.info(f"Filter: {self.filter_pattern}")
        self.logger.info(f"Prefix: '{self.prefix}', Postfix: '{self.postfix}'")

        # Find all matching files
        matching_files = list(self.source.glob(self.filter_pattern))
        self.logger.info(f"Found {len(matching_files)} files matching filter")

        processed_count = 0
        error_count = 0

        for file_path in matching_files:
            if file_path.is_file():
                try:
                    if file_path.suffix.lower() == ".json":
                        self._process_json_file(file_path)
                    else:
                        self._copy_file(file_path)
                    processed_count += 1
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                    error_count += 1

        self.logger.info(
            f"Migration complete. Processed: {processed_count}, Errors: {error_count}"
        )
        return 0 if error_count == 0 else 1

    def _process_json_file(self, file_path: Path) -> None:
        """Process a JSON profile file."""
        self.logger.debug(f"Processing JSON file: {file_path}")

        # Read and parse JSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            return
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            return

        # Skip machine_model files
        if data.get("type") == "machine_model":
            self.logger.debug(f"Skipping machine_model file: {file_path}")
            return

        # Resolve inheritance
        try:
            resolved_data = self._resolve_inheritance(file_path, data)
        except Exception as e:
            self.logger.error(f"Failed to resolve inheritance for {file_path}: {e}")
            return

        # Apply transformations
        self._apply_transformations(resolved_data, file_path)

        # Write output
        self._write_output(file_path, resolved_data)

    def _resolve_inheritance(
        self, file_path: Path, data: Dict[str, Any], depth: int = 0
    ) -> Dict[str, Any]:
        """Recursively resolve inheritance in JSON data."""
        if depth > MAX_INHERITANCE_DEPTH:
            self.logger.warning(
                f"Maximum inheritance depth ({MAX_INHERITANCE_DEPTH}) exceeded for {file_path}"
            )
            return data

        inherits_value = data.get("inherits")
        if not inherits_value:
            return data

        # Find inherited file
        inherited_file = file_path.parent / f"{inherits_value}.json"

        if not inherited_file.exists():
            self.logger.warning(
                f"Inherited file not found: {inherited_file} (referenced by {file_path})"
            )
            data["inherits"] = ""
            return data

        # Load inherited file
        try:
            with open(inherited_file, "r", encoding="utf-8") as f:
                inherited_data = json.load(f)
        except Exception as e:
            self.logger.warning(
                f"Failed to load inherited file {inherited_file}: {e}"
            )
            data["inherits"] = ""
            return data

        # Recursively resolve inherited file
        resolved_inherited = self._resolve_inheritance(
            inherited_file, inherited_data, depth + 1
        )

        # Merge: inherited values first, then override with current values
        merged_data = self._merge_data(resolved_inherited, data)
        merged_data["inherits"] = ""

        return merged_data

    def _merge_data(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two dictionaries, with override values taking precedence."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                self.logger.warning(
                    f"Nested object detected for key '{key}'. Performing shallow merge."
                )
            result[key] = value

        return result

    def _apply_transformations(self, data: Dict[str, Any], file_path: Path) -> None:
        """Apply required transformations to the profile data."""
        # Set required fields
        data["is_custom_defined"] = "0"
        data["instantiation"] = "true"

        # Remove compatible_printers
        if "compatible_printers" in data:
            del data["compatible_printers"]

        # Handle compatible_printers_condition
        self._set_compatible_printers_condition(data, file_path)

        # Set support_multi_bed_types if it exists
        if "support_multi_bed_types" in data:
            data["support_multi_bed_types"] = "1"

    def _set_compatible_printers_condition(
        self, data: Dict[str, Any], file_path: Path
    ) -> None:
        """Set the compatible_printers_condition field."""
        existing_value = data.get("compatible_printers_condition")

        # If field doesn't exist, don't set it
        if "compatible_printers_condition" not in data:
            self.logger.debug(
                f"compatible_printers_condition not present in {file_path.name}, skipping"
            )
            return

        # If it has a non-empty value, warn and skip
        if existing_value and existing_value != "":
            self.logger.warning(
                f"compatible_printers_condition already set in {file_path.name}: '{existing_value}'"
            )
            return

        # Extract nozzle diameter from filename
        nozzle_match = NOZZLE_PATTERN.search(file_path.name)
        if not nozzle_match:
            self.logger.warning(
                f"No nozzle diameter found in filename: {file_path.name}. "
                "Skipping compatible_printers_condition."
            )
            return

        nozzle_diameter = nozzle_match.group(1)

        # Extract printer name from filename
        printer_match = PRINTER_NAME_PATTERN.search(file_path.name)
        if not printer_match:
            self.logger.warning(
                f"Could not extract printer name from filename: {file_path.name}"
            )
            return

        printer_name = printer_match.group(1).strip()

        # Set the value with proper escaping
        condition = (
            f'printer_model==\\"{printer_name}\\" '
            f'and nozzle_diameter[0]=={nozzle_diameter}'
        )
        data["compatible_printers_condition"] = condition

        self.logger.debug(
            f"Set compatible_printers_condition for {file_path.name}: {condition}"
        )

    def _copy_file(self, file_path: Path) -> None:
        """Copy a non-JSON file to the output directory."""
        output_path = self._get_output_path(file_path)

        if output_path.exists() and not self.overwrite:
            self.logger.warning(f"Output file exists, skipping: {output_path}")
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "rb") as src, open(output_path, "wb") as dst:
            dst.write(src.read())

        self.logger.info(f"Copied: {file_path.name} -> {output_path}")

    def _write_output(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write processed JSON data to output file."""
        output_path = self._get_output_path(file_path)

        if output_path.exists() and not self.overwrite:
            self.logger.warning(f"Output file exists, skipping: {output_path}")
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False, sort_keys=self.sort_keys)
            self.logger.info(f"Wrote: {file_path.name} -> {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write {output_path}: {e}")

    def _get_output_path(self, file_path: Path) -> Path:
        """Calculate the output path for a file."""
        # Get relative path from source
        try:
            relative_path = file_path.relative_to(self.source)
        except ValueError:
            # File is not relative to source, use just the filename
            relative_path = Path(file_path.name)

        # Apply prefix and postfix
        stem = file_path.stem
        suffix = file_path.suffix
        new_name = f"{self.prefix}{stem}{self.postfix}{suffix}"

        # Construct output path
        output_path = self.output / relative_path.parent / new_name
        return output_path


def setup_logging(debug: bool) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Migrate Anycubic Slicer profiles to OrcaSlicer format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-s", "--source",
        type=str,
        default=DEFAULT_SOURCE,
        help=f"Source directory path (default: {DEFAULT_SOURCE})",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Output directory path (default: {DEFAULT_OUTPUT})",
    )

    parser.add_argument(
        "-p", "--prefix",
        type=str,
        default=DEFAULT_PREFIX,
        help=f"Prefix for output filenames (default: '{DEFAULT_PREFIX}')",
    )

    parser.add_argument(
        "-P", "--postfix",
        type=str,
        default="",
        help="Postfix for output filenames (default: none)",
    )

    parser.add_argument(
        "-f", "--filter",
        type=str,
        default=DEFAULT_FILTER,
        help=f"Glob pattern to filter input files (default: '{DEFAULT_FILTER}')",
    )

    parser.add_argument(
        "-w", "--overwrite",
        action="store_true",
        help="Overwrite existing files in output directory (default: False)",
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging (default: False)",
    )

    parser.add_argument(
        "-S", "--sort",
        action="store_true",
        help="Sort JSON keys alphabetically in output (default: False)",
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode (prompt for inputs)",
    )

    return parser.parse_args()


def interactive_mode() -> argparse.Namespace:
    """Run interactive mode to gather user inputs."""
    print("=== Slicer Profile Migrator - Interactive Mode ===\n")

    source = input(f"Source path [{DEFAULT_SOURCE}]: ").strip()
    source = source if source else DEFAULT_SOURCE

    output = input(f"Output path [{DEFAULT_OUTPUT}]: ").strip()
    output = output if output else DEFAULT_OUTPUT

    prefix = input(f"Filename prefix [{DEFAULT_PREFIX}]: ").strip()
    prefix = prefix if prefix else DEFAULT_PREFIX

    postfix = input(f"Filename postfix [none]: ").strip()

    filter_pattern = input(f"Filter pattern [{DEFAULT_FILTER}]: ").strip()
    filter_pattern = filter_pattern if filter_pattern else DEFAULT_FILTER

    overwrite_input = input(f"Overwrite existing files? [y/N]: ").strip().lower()
    overwrite = overwrite_input in ("y", "yes")

    debug_input = input(f"Enable debug logging? [y/N]: ").strip().lower()
    debug = debug_input in ("y", "yes")

    sort_input = input(f"Sort JSON keys alphabetically? [y/N]: ").strip().lower()
    sort_keys = sort_input in ("y", "yes")

    # Create namespace object
    args = argparse.Namespace(
        source=source,
        output=output,
        prefix=prefix,
        postfix=postfix,
        filter=filter_pattern,
        overwrite=overwrite,
        debug=debug,
        sort=sort_keys,
        interactive=True,
    )

    return args


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Switch to interactive mode if requested
    if args.interactive:
        args = interactive_mode()

    # Setup logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    # Create migrator and run
    migrator = ProfileMigrator(
        source=Path(args.source),
        output=Path(args.output),
        prefix=args.prefix,
        postfix=args.postfix,
        filter_pattern=args.filter,
        overwrite=args.overwrite,
        sort_keys=args.sort,
    )

    try:
        return migrator.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
