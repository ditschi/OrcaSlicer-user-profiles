#!/usr/bin/env python3
"""
Convert Anycubic Slicer profiles to OrcaSlicer format.

This script processes JSON profile files from Anycubic Slicer, resolves inheritance,
and converts them to OrcaSlicer-compatible format.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import yaml
except ImportError:
    yaml = None

# Constants
DEFAULT_CONFIG_FILE = "./profile_convert_config.yml"
DEFAULT_SOURCE = "~/.config/AnycubicSlicerNext/system/Anycubic/"
DEFAULT_OUTPUT = "~/.config/OrcaSlicer/user/default/"
DEFAULT_FILTER = "**/*"
DEFAULT_PREFIX = "Original "
MAX_INHERITANCE_DEPTH = 5

# Regex patterns
NOZZLE_PATTERN = re.compile(r"(\d+\.\d+) nozzle", re.IGNORECASE)
PRINTER_NAME_PATTERN = re.compile(r"(?:.*@)?\s*(.*?)\s*\d+\.\d+\s*nozzle", re.IGNORECASE)


class ProfileConverter:
    """Handles conversion of slicer profiles from Anycubic to OrcaSlicer format."""

    def __init__(
        self,
        source: Path,
        output: Path,
        prefix: str = "",
        postfix: str = "",
        filter_pattern: str = DEFAULT_FILTER,
        overwrite: bool = False,
        sort_keys: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.source = source.expanduser().resolve()
        self.output = output.expanduser().resolve()
        self.prefix = prefix
        self.postfix = postfix
        self.filter_pattern = filter_pattern
        self.overwrite = overwrite
        self.sort_keys = sort_keys
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._processed_files: Set[Path] = set()
        self._json_overwrite_rules = self._parse_json_overwrite_rules()

    def run(self) -> int:
        """Execute the conversion process."""
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
            f"Processing complete. Processed: {processed_count}, Errors: {error_count}"
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

    def _parse_json_overwrite_rules(self) -> List[Dict[str, Any]]:
        """Parse and validate JSON overwrite rules from config."""
        rules = []
        raw_rules = self.config.get("json_value_overwrite", [])

        for rule in raw_rules:
            if not rule.get("enabled", False):
                continue

            name = rule.get("name")
            if not name:
                self.logger.warning("Skipping json_value_overwrite rule without 'name'")
                continue

            if "value" not in rule:
                self.logger.warning(f"Skipping json_value_overwrite rule '{name}' without 'value'")
                continue

            rules.append({
                "name": name,
                "value": rule["value"],
                "conditions": rule.get("conditions", []),
            })

        return rules

    def _check_conditions(
        self, conditions: List[Dict[str, Any]], file_path: Path, data: Dict[str, Any]
    ) -> bool:
        """Check if all conditions are met (AND logic)."""
        if not conditions:
            return True

        for condition in conditions:
            condition_type = condition.get("type")

            if condition_type == "filename_contains":
                pattern = condition.get("pattern", "")
                if pattern not in file_path.name:
                    return False

            elif condition_type == "json_value":
                key = condition.get("key")
                expected_value = condition.get("value")

                if key is None or expected_value is None:
                    self.logger.warning(f"Invalid json_value condition: {condition}")
                    return False

                actual_value = data.get(key)
                # Exact string match
                if str(actual_value) != str(expected_value):
                    return False

            else:
                self.logger.warning(f"Unknown condition type: {condition_type}")
                return False

        return True

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

        # Apply JSON value overwrites from config
        self._apply_json_overwrites(data, file_path)

    def _apply_json_overwrites(self, data: Dict[str, Any], file_path: Path) -> None:
        """Apply JSON value overwrites based on config rules."""
        for rule in self._json_overwrite_rules:
            name = rule["name"]
            value = rule["value"]
            conditions = rule["conditions"]

            # Check if conditions are met
            if not self._check_conditions(conditions, file_path, data):
                continue

            # Only overwrite if key exists
            if name in data:
                data[name] = value
                self.logger.debug(
                    f"Applied json_value_overwrite for '{name}' in {file_path.name}"
                )
            else:
                self.logger.debug(
                    f"Skipping json_value_overwrite for '{name}' (key not found) in {file_path.name}"
                )

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


def load_config(config_path: Optional[Path]) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    logger = logging.getLogger(__name__)

    if yaml is None:
        logger.warning(
            "PyYAML not installed. Config file support disabled. "
            "Install with: pip install pyyaml"
        )
        return {}

    if config_path is None:
        config_path = Path(DEFAULT_CONFIG_FILE)

    if not config_path.exists():
        logger.warning(
            f"Config file not found: {config_path}. "
            "JSON value overwrite features will be disabled."
        )
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from: {config_path}")
        return config or {}
    except Exception as e:
        logger.error(f"Failed to load config file {config_path}: {e}")
        return {}


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert Anycubic Slicer profiles to OrcaSlicer format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help=f"Path to YAML config file (default: {DEFAULT_CONFIG_FILE})",
    )

    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help=f"Source directory path (default from config or {DEFAULT_SOURCE})",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output directory path (default from config or {DEFAULT_OUTPUT})",
    )

    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help=f"Prefix for output filenames (default from config or '{DEFAULT_PREFIX}')",
    )

    parser.add_argument(
        "--postfix",
        type=str,
        default=None,
        help="Postfix for output filenames (default from config or none)",
    )

    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help=f"Glob pattern to filter input files (default from config or '{DEFAULT_FILTER}')",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=None,
        help="Overwrite existing files in output directory (default from config or False)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="Enable debug logging (default from config or False)",
    )

    parser.add_argument(
        "--sort",
        action="store_true",
        default=None,
        help="Sort JSON keys alphabetically in output (default from config or False)",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (prompt for inputs)",
    )

    return parser.parse_args()


def get_config_default(config: Dict[str, Any], key: str, fallback: Any) -> Any:
    """Get default value from config or use fallback."""
    defaults = config.get("defaults", {})
    return defaults.get(key, fallback)


def interactive_mode(config: Dict[str, Any]) -> argparse.Namespace:
    """Run interactive mode to gather user inputs."""
    print("=== Slicer Profile Converter - Interactive Mode ===\n")

    default_source = get_config_default(config, "source", DEFAULT_SOURCE)
    source = input(f"Source path [{default_source}]: ").strip()
    source = source if source else default_source

    default_output = get_config_default(config, "output", DEFAULT_OUTPUT)
    output = input(f"Output path [{default_output}]: ").strip()
    output = output if output else default_output

    default_prefix = get_config_default(config, "prefix", DEFAULT_PREFIX)
    prefix = input(f"Filename prefix [{default_prefix}]: ").strip()
    prefix = prefix if prefix else default_prefix

    default_postfix = get_config_default(config, "postfix", "")
    postfix_prompt = f"[{default_postfix}]" if default_postfix else "[none]"
    postfix = input(f"Filename postfix {postfix_prompt}: ").strip()
    if not postfix:
        postfix = default_postfix

    default_filter = get_config_default(config, "filter", DEFAULT_FILTER)
    filter_pattern = input(f"Filter pattern [{default_filter}]: ").strip()
    filter_pattern = filter_pattern if filter_pattern else default_filter

    default_overwrite = get_config_default(config, "overwrite", False)
    overwrite_default = "Y/n" if default_overwrite else "y/N"
    overwrite_input = input(f"Overwrite existing files? [{overwrite_default}]: ").strip().lower()
    if overwrite_input:
        overwrite = overwrite_input in ("y", "yes")
    else:
        overwrite = default_overwrite

    default_debug = get_config_default(config, "debug", False)
    debug_default = "Y/n" if default_debug else "y/N"
    debug_input = input(f"Enable debug logging? [{debug_default}]: ").strip().lower()
    if debug_input:
        debug = debug_input in ("y", "yes")
    else:
        debug = default_debug

    default_sort = get_config_default(config, "sort_keys", False)
    sort_default = "Y/n" if default_sort else "y/N"
    sort_input = input(f"Sort JSON keys alphabetically? [{sort_default}]: ").strip().lower()
    if sort_input:
        sort_keys = sort_input in ("y", "yes")
    else:
        sort_keys = default_sort

    config_file = input(f"Config file path [{DEFAULT_CONFIG_FILE}]: ").strip()
    config_file = config_file if config_file else None

    # Create namespace object
    args = argparse.Namespace(
        config=config_file,
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

    # Load config file
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    # Switch to interactive mode if requested
    if args.interactive:
        args = interactive_mode(config)
        # Reload config if different path was provided in interactive mode
        if args.config:
            config = load_config(Path(args.config))

    # Merge CLI args with config defaults
    source = args.source or get_config_default(config, "source", DEFAULT_SOURCE)
    output = args.output or get_config_default(config, "output", DEFAULT_OUTPUT)
    prefix = args.prefix if args.prefix is not None else get_config_default(config, "prefix", DEFAULT_PREFIX)
    postfix = args.postfix if args.postfix is not None else get_config_default(config, "postfix", "")
    filter_pattern = args.filter or get_config_default(config, "filter", DEFAULT_FILTER)
    overwrite = args.overwrite if args.overwrite is not None else get_config_default(config, "overwrite", False)
    debug = args.debug if args.debug is not None else get_config_default(config, "debug", False)
    sort_keys = args.sort if args.sort is not None else get_config_default(config, "sort_keys", False)

    # Setup logging
    setup_logging(debug)
    logger = logging.getLogger(__name__)

    # Create converter and run
    converter = ProfileConverter(
        source=Path(source),
        output=Path(output),
        prefix=prefix,
        postfix=postfix,
        filter_pattern=filter_pattern,
        overwrite=overwrite,
        sort_keys=sort_keys,
        config=config,
    )

    try:
        return converter.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())