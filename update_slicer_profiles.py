#!/usr/bin/env python3
"""
Update slicer profile JSON files based on configuration rules.

This script applies json_value_overwrite rules from a YAML config file to JSON profile files.
Supports conditional updates based on filename/filepath patterns and JSON values.
"""


import argparse
import json
import logging
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

# Constants
DEFAULT_CONFIG_FILE = "./profile_update.yml"
DEFAULT_FILTER = "**/*.json"


class ProfileUpdater:
    """Handles updating of slicer profile JSON files based on config rules."""

    def __init__(
        self,
        source: Path,
        output: Optional[Path],
        prefix: str = "",
        postfix: str = "",
        filter_pattern: str = DEFAULT_FILTER,
        overwrite: bool = False,
        sort_keys: bool = False,
        filename_replacements: Optional[List[tuple[str, str]]] = None,
        force_copy: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.source = source.expanduser().resolve()
        self.output = output.expanduser().resolve() if output else None
        self.prefix = prefix
        self.postfix = postfix
        self.filter_pattern = filter_pattern
        self.overwrite = overwrite
        self.sort_keys = sort_keys
        self.filename_replacements = filename_replacements or []
        self.force_copy = force_copy
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._default_conditions = self.config.get("default_conditions", [])
        self._json_overwrite_rules = self._parse_json_overwrite_rules()

        # Validate source/output logic
        self._validate_paths()

    def _validate_paths(self) -> None:
        """Validate source/output path combinations."""
        # Source must exist
        if not self.source.exists():
            raise ValueError(f"Source path does not exist: {self.source}")

        # Check for invalid combinations
        if self.source.is_file():
            # File as source
            if self.output and self.output.is_dir():
                # File -> Directory with prefix/postfix is OK
                pass
            elif self.output and (self.prefix or self.postfix):
                # File -> File with prefix/postfix is ERROR
                raise ValueError(
                    "Cannot use --prefix or --postfix when source is a file and output is a file. "
                    "Either remove prefix/postfix or use a directory as output."
                )
        else:
            # Directory as source
            if self.output and self.output.is_file():
                # Directory -> File is ERROR
                raise ValueError(
                    "Cannot use a file as output when source is a directory. "
                    "Output must be a directory or omitted for in-place updates."
                )

    def run(self) -> int:
        """Execute the update process."""
        self.logger.info(f"Source: {self.source}")
        self.logger.info(f"Output: {self.output if self.output else '(in-place)'}")
        self.logger.info(f"Filter: {self.filter_pattern}")
        if self.prefix or self.postfix:
            self.logger.info(f"Prefix: '{self.prefix}', Postfix: '{self.postfix}'")
        self.logger.info(f"Rules loaded: {len(self._json_overwrite_rules)}")

        # Find all matching files
        matching_files = self._find_matching_files()
        self.logger.info(f"Found {len(matching_files)} files matching filter")

        processed_count = 0
        error_count = 0
        skipped_no_rules = 0
        skipped_no_changes = 0

        for file_path in matching_files:
            try:
                result = self._process_json_file(file_path)
                if result == "processed":
                    processed_count += 1
                elif result == "skipped_no_rules":
                    skipped_no_rules += 1
                elif result == "skipped_no_changes":
                    skipped_no_changes += 1
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                error_count += 1

        self.logger.info(
            f"\n{'='*60}"
        )
        self.logger.info(f"Update complete:")
        self.logger.info(f"  Processed (written): {processed_count}")
        self.logger.info(f"  Skipped (no rules matched): {skipped_no_rules}")
        self.logger.info(f"  Skipped (no content changes): {skipped_no_changes}")
        self.logger.info(f"  Errors: {error_count}")
        self.logger.info(f"  Total files checked: {len(matching_files)}")
        self.logger.info(
            f"{'='*60}"
        )
        return 0 if error_count == 0 else 1

    def _find_matching_files(self) -> List[Path]:
        """Find all files matching the filter pattern."""
        if self.source.is_file():
            # Single file
            return [self.source]
        else:
            # Directory - use glob
            return [f for f in self.source.glob(self.filter_pattern) if f.is_file()]

    def _process_json_file(self, file_path: Path) -> str:
        """Process a single JSON file. Returns 'processed', 'skipped_no_rules', or 'skipped_no_changes'."""
        self.logger.debug(f"\n{'='*60}")
        self.logger.debug(f"Processing: {file_path}")
        self.logger.debug(f"{'='*60}")

        # Read and parse JSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_data = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            return "error"
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            return "error"

        # Make a copy for modification
        import copy
        data = copy.deepcopy(original_data)

        # Apply rules
        modified, any_rule_matched = self._apply_rules(data, file_path)

        # Skip file if no rules matched (e.g., default_conditions filtered it out)
        if not any_rule_matched:
            self.logger.info(f"Skipped (no rules matched): {file_path.name}")
            self.logger.debug(f"\n✗ No rules matched for {file_path.name}, skipping\n")
            return "skipped_no_rules"

        # Check if content actually changed
        content_changed = (data != original_data)

        if not content_changed and not self.force_copy:
            self.logger.info(f"Skipped (no content changes): {file_path.name}")
            self.logger.debug(f"\n✗ No content changes for {file_path.name}")
            self.logger.debug(f"  Modified flag: {modified}")
            self.logger.debug(f"  Any rule matched: {any_rule_matched}")
            return "skipped_no_changes"

        if not content_changed and self.force_copy:
            self.logger.info(f"Copying (forced, no content changes): {file_path.name}")
            self.logger.debug(f"\n→ No content changes for {file_path.name}, but copying due to --force-copy")

        # If not in-place (different filename), write the file
        if not self._is_in_place_update(file_path):
            self._write_output(file_path, data)
            return "processed"
        elif content_changed:
            # In-place update only if content changed
            self._write_output(file_path, data)
            return "processed"

        return "skipped_no_changes"

    def _is_in_place_update(self, file_path: Path) -> bool:
        """Check if this is an in-place update."""
        if not self.output:
            # If prefix, postfix, or replacements are set, it's not in-place
            if self.prefix or self.postfix or self.filename_replacements:
                return False
            return True

        # Calculate what the output path would be
        output_path = self._get_output_path(file_path)
        return output_path == file_path

    def _apply_rules(self, data: Dict[str, Any], file_path: Path) -> tuple[bool, bool]:
        """Apply all matching rules to the data. Returns (modified, any_rule_matched)."""
        modified = False
        any_rule_matched = False

        self.logger.debug(f"\nEvaluating {len(self._json_overwrite_rules)} rules...")

        for rule_idx, rule in enumerate(self._json_overwrite_rules, 1):
            name = rule["name"]
            value = rule["value"]
            conditions = rule["conditions"]
            add = rule["add"]

            # Check if conditions are met
            self.logger.debug(f"\nRule {rule_idx}/{len(self._json_overwrite_rules)}: {name}")
            if not self._check_conditions(conditions, file_path, data):
                self.logger.debug(f"  ✗ Conditions not met, skipping rule")
                continue

            # At least one rule matched this file
            any_rule_matched = True
            self.logger.debug(f"  ✓ Rule matched!")

            # Check if key exists
            key_exists = name in data

            self.logger.debug(f"  Key '{name}' exists: {key_exists}, add: {add}")

            if not key_exists and not add:
                # Key doesn't exist and we're not allowed to add it
                self.logger.debug(
                    f"  → Skipping '{name}' (key not found, add=False)"
                )
                continue

            # Apply the update
            old_value = data.get(name) if key_exists else None
            if old_value != value:
                data[name] = value
                modified = True
                action = "Updated" if key_exists else "Added"
                self.logger.info(
                    f"{action} '{name}' in {file_path.name}"
                )
                self.logger.debug(f"    Old: {old_value}")
                self.logger.debug(f"    New: {value}")
            else:
                self.logger.debug(f"  → Value unchanged for '{name}' (old={old_value}, new={value})")

        return modified, any_rule_matched

    def _parse_json_overwrite_rules(self) -> List[Dict[str, Any]]:
        """Parse and validate JSON overwrite rules from config."""
        rules = []
        raw_rules = self.config.get("json_value_overwrite", [])

        for rule in raw_rules:
            # Check if enabled (default: True)
            enabled = rule.get("enabled", True)
            if not enabled:
                continue

            name = rule.get("name")
            if not name:
                self.logger.warning("Skipping json_value_overwrite rule without 'name'")
                continue

            if "value" not in rule:
                self.logger.warning(f"Skipping json_value_overwrite rule '{name}' without 'value'")
                continue

            # Combine default conditions with rule-specific conditions
            rule_conditions = rule.get("conditions", [])
            combined_conditions = self._default_conditions + rule_conditions

            rules.append({
                "name": name,
                "value": rule["value"],

                "conditions": combined_conditions,
                "add": rule.get("add", False),
            })

        return rules

    def _check_conditions(
        self, conditions: List[Dict[str, Any]], file_path: Path, data: Dict[str, Any]
    ) -> bool:
        """Check if all conditions are met (AND logic)."""
        if not conditions:
            self.logger.debug(f"  No conditions to check for {file_path.name}")
            return True

        # Use absolute path for filepath_glob matching
        abs_path = file_path.resolve()

        self.logger.debug(f"  Checking {len(conditions)} condition(s) for {file_path.name}")
        self.logger.debug(f"    Filename: {file_path.name}")
        self.logger.debug(f"    Absolute path: {abs_path}")

        for idx, condition in enumerate(conditions, 1):
            condition_type = condition.get("type")

            if condition_type == "filename_glob":
                pattern = condition.get("pattern", "")
                matches = fnmatch(file_path.name, pattern)
                self.logger.debug(f"    [{idx}] filename_glob: '{pattern}' -> {matches}")
                if not matches:
                    return False

            elif condition_type == "exclude_filename_glob":
                pattern = condition.get("pattern", "")
                matches = fnmatch(file_path.name, pattern)
                self.logger.debug(f"    [{idx}] exclude_filename_glob: '{pattern}' -> excluded={matches}")
                if matches:
                    return False

            elif condition_type == "filepath_glob":
                pattern = condition.get("pattern", "")
                # Match against absolute path using forward slashes
                path_str = str(abs_path).replace("\\", "/")
                matches = fnmatch(path_str, pattern)
                self.logger.debug(f"    [{idx}] filepath_glob: '{pattern}' against '{path_str}' -> {matches}")
                if not matches:
                    return False

            elif condition_type == "exclude_filepath_glob":
                pattern = condition.get("pattern", "")
                # Match against absolute path using forward slashes
                path_str = str(abs_path).replace("\\", "/")
                matches = fnmatch(path_str, pattern)
                self.logger.debug(f"    [{idx}] exclude_filepath_glob: '{pattern}' against '{path_str}' -> excluded={matches}")
                if matches:
                    return False

            elif condition_type == "json_value":
                key = condition.get("key")
                expected_value = condition.get("value")
                negate = condition.get("negate", False)

                if key is None or expected_value is None:
                    self.logger.warning(f"Invalid json_value condition: {condition}")
                    return False

                actual_value = data.get(key)
                matches = str(actual_value) == str(expected_value)

                if negate:
                    # Negated: pass if values DON'T match
                    result = not matches
                    self.logger.debug(f"    [{idx}] json_value (negated): key='{key}', expected!='{expected_value}', actual='{actual_value}' -> {result}")
                    if not result:
                        return False
                else:
                    # Normal: pass if values match
                    self.logger.debug(f"    [{idx}] json_value: key='{key}', expected='{expected_value}', actual='{actual_value}' -> {matches}")
                    if not matches:
                        return False

            else:
                self.logger.warning(f"Unknown condition type: {condition_type}")
                return False

        self.logger.debug(f"  ✓ All conditions passed for {file_path.name}")
        return True

    def _write_output(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write processed JSON data to output file."""
        output_path = self._get_output_path(file_path)

        # Check if we need to create the output path
        if output_path != file_path:
            # Not in-place, check overwrite flag
            if output_path.exists() and not self.overwrite:
                self.logger.warning(f"Output file exists, skipping: {output_path}")
                return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False, sort_keys=self.sort_keys)

            if output_path == file_path:
                self.logger.info(f"Updated (in-place): {file_path.name}")
            else:
                self.logger.info(f"Wrote: {file_path.name} -> {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write {output_path}: {e}")

    def _apply_filename_transformations(self, filename: str) -> str:
        """Apply prefix, replacements, and postfix to filename."""
        stem = Path(filename).stem
        suffix = Path(filename).suffix

        # 1. Apply prefix
        result = f"{self.prefix}{stem}"

        # 2. Apply find/replace operations in order
        for find, replace in self.filename_replacements:
            result = result.replace(find, replace)

        # 3. Apply postfix
        result = f"{result}{self.postfix}"

        # 4. Add back the suffix
        return f"{result}{suffix}"

    def _get_output_path(self, file_path: Path) -> Path:
        """Calculate the output path for a file."""
        # If no output specified
        if not self.output:
            # If prefix, postfix, or replacements are provided, create new file in same directory
            if self.prefix or self.postfix or self.filename_replacements:
                new_name = self._apply_filename_transformations(file_path.name)
                return file_path.parent / new_name
            # Otherwise, update in-place
            return file_path

        # If source is a file
        if self.source.is_file():
            if self.output.is_dir():
                # File -> Directory: put file in directory with transformations
                new_name = self._apply_filename_transformations(file_path.name)
                return self.output / new_name
            else:
                # File -> File: direct mapping (no transformations)
                return self.output

        # If source is a directory
        # Get relative path from source
        try:
            relative_path = file_path.relative_to(self.source)
        except ValueError:
            # File is not relative to source, use just the filename
            relative_path = Path(file_path.name)

        # Apply filename transformations
        new_name = self._apply_filename_transformations(file_path.name)

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


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    logger = logging.getLogger(__name__)

    if yaml is None:
        logger.error(
            "PyYAML not installed. This tool requires PyYAML. "
            "Install with: pip install pyyaml"
        )
        sys.exit(1)

    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from: {config_path}")
        return config or {}
    except Exception as e:
        logger.error(f"Failed to load config file {config_path}: {e}")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update slicer profile JSON files based on configuration rules.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update files in-place
  %(prog)s --config profile_update.yml --source ./profiles/

  # Copy and update to new location
  %(prog)s --config profile_update.yml --source ./profiles/ --output ./updated/

  # Update single file in-place
  %(prog)s --config profile_update.yml --source ./profile.json

  # Copy single file with updates
  %(prog)s --config profile_update.yml --source ./profile.json --output ./new_profile.json
        """,
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        default=DEFAULT_CONFIG_FILE,
        help=f"Path to YAML config file (default: {DEFAULT_CONFIG_FILE})",
    )

    parser.add_argument(
        "-s", "--source",
        type=str,
        required=True,
        help="Source file or directory path",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file or directory path (default: update in-place)",
    )

    parser.add_argument(
        "-p", "--prefix",
        type=str,
        default="",
        help="Prefix for output filenames (default: none)",
    )

    parser.add_argument(
        "-P", "--postfix",
        type=str,
        default="",
        help="Postfix for output filenames (default: none)",
    )

    parser.add_argument(
        "-r", "--filename-replace",
        type=str,
        nargs=2,
        action="append",
        metavar=("FIND", "REPLACE"),
        help="Replace FIND with REPLACE in output filenames (can be used multiple times)",
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
        "-F", "--force-copy",
        action="store_true",
        help="Copy files even if JSON content is unchanged (default: False)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Setup logging first
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    # Load config file
    config_path = Path(args.config)
    config = load_config(config_path)

    # Parse paths
    source = Path(args.source)
    output = Path(args.output) if args.output else None

    # Parse filename replacements
    filename_replacements = []
    if args.filename_replace:
        filename_replacements = [(find, replace) for find, replace in args.filename_replace]

    # Create updater and run
    try:
        updater = ProfileUpdater(
            source=source,
            output=output,
            prefix=args.prefix,
            postfix=args.postfix,
            filter_pattern=args.filter,
            overwrite=args.overwrite,
            sort_keys=args.sort,
            filename_replacements=filename_replacements,
            force_copy=args.force_copy,
            config=config,
        )
        return updater.run()
    except ValueError as e:
        logger.error(str(e))
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
