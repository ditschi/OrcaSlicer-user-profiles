# OrcaSlicer Printer Profiles for Anycubic Printers

This repo contains Profiles for the Anycubic Kobra S1 Combo. The profiles were extracted from AnycubicSlicerNext and adapted to be used as user profiles. Also some "Optimized" profiles were created, for better and faster performance.

The profiles from this repo can simply be copied to `~/.config/OrcaSlicer/user/default/` to add them to OrcaSlicer

Using the [python script](./convert_slicer_profiles.py) can be used to migrate profiles for all other printers from AnycubicSlicerNext as well. Check the [detailed documentation](#automated-conversion-with-python-script) for more details.

## Extracting form AnycubicSlicerNext to OrcaSlicer

It is  possible to get the `filament`, `machine` and `process` configuration from the AnycubicSlicerNext installation.

Prerequisite: AnycubicSlicerNext and OrcaSlicer is installed and was started at least once (so the tool creates the needed files in the user profile).

When manually copying the files to the OrcaSlicer user profiles many adaptions  were needed so a script was created to perform the required step so that the profiles are actually visible in OrcaSlicer.

### Automated Conversion with Python Script

The `convert_slicer_profiles.py` script automates the entire conversion process from AnycubicSlicerNext to OrcaSlicer format.

#### Quick Start Examples

**Convert Original Profiles (Kobra S1):**
```bash
./convert_slicer_profiles.py --filter '**/*S1*'
```

**Convert Optimized Profiles (with machine limits and G-code improvements):**
```bash
./convert_slicer_profiles.py --filter 'machine/*S1*' --prefix 'Optimized ' --config ./profile_convert_config_optimize.yml
```

**Convert Optimized Profiles (with machine limits and G-code improvements):**
**Interactive Mode (guided prompts):**
```bash
./convert_slicer_profiles.py --interactive
```

**Print all commandline arguments:**
```bash
./convert_slicer_profiles.py --help
```

#### Prerequisites

- Python 3.7+
- PyYAML (for config file support): `pip install pyyaml`

#### What the Script Does

1. **File Discovery & Filtering**
   - Scans source directory for files matching the glob pattern
   - Supports filtering by printer model (e.g., `**/*S1*` for Kobra S1 only)

2. **Inheritance Resolution** (Recursive, up to 5 levels)
   - Locates and loads inherited profile files (`"inherits": "base_profile"`)
   - Merges inherited values with current profile (current values take precedence)
   - Flattens the inheritance chain by setting `"inherits": ""`
   - Warns if inherited files are missing or maximum depth is exceeded

3. **Required Field Transformations**
   - Sets `"is_custom_defined": "0"` (marks as user profile)
   - Sets `"instantiation": "true"` (enables profile instantiation)
   - Sets `"from": "User"` (indicates custom profile source)
   - Removes `"compatible_printers"` array (improves compatibility)
   - Updates `"compatible_printers_condition"` (if field exists and is empty):
     - Extracts printer name from filename (e.g., "Anycubic Kobra S1")
     - Extracts nozzle diameter from filename (e.g., `0.4 nozzle` → `0.4`)
     - Sets condition: `printer_model=="<name>" and nozzle_diameter[0]==<diameter>`
   - Sets `"support_multi_bed_types": "1"` (if field exists)

4. **Config-Based Value Overrides** (Optional)
   - Applies JSON value overwrites from YAML config file
   - Supports conditional rules based on:
     - Filename patterns (e.g., only "Optimized" profiles)
     - JSON field values (e.g., `type: "machine"`)
   - Can set G-code fields, machine limits, and nozzle-specific parameters

5. **Output Generation**
   - Preserves relative directory structure from source
   - Applies prefix/postfix to filenames (e.g., `Original <filename>.json`)
   - Writes formatted JSON with optional key sorting
   - Skips existing files unless `--overwrite` is specified

#### Configuration Files

**`profile_convert_config.yml`** - Default configuration for "Original" profiles:
- Sets G-code fixes for parser compatibility
- Minimal changes to preserve original behavior

**`profile_convert_config_optimize.yml`** - Configuration for "Optimized" profiles:
- Applies all G-code improvements (start, end, filament change)
- Sets optimized machine limits (acceleration, jerk, speed)
- Configures nozzle-specific parameters (retraction, wipe distance)
- All rules enabled by default for Kobra S1

#### Common Use Cases

**Process only specific profile types:**
```bash
# Only machine profiles
./convert_slicer_profiles.py --filter 'machine/*'

# Only process profiles
./convert_slicer_profiles.py --filter 'process/*'

# Only filament profiles
./convert_slicer_profiles.py --filter 'filament/*'
```

**Create both Original and Optimized profiles:**
```bash
# First: Create Original profiles
./convert_slicer_profiles.py --filter '**/*S1*' --prefix 'Original '

# Second: Create Optimized profiles
./convert_slicer_profiles.py --filter '**/*S1*' --prefix 'Optimized ' --config ./profile_convert_config_optimize.yml
```

**Debug mode for troubleshooting:**
```bash
./convert_slicer_profiles.py --filter '**/*S1*' --debug
```

#### How Config-Based Overrides Work

The YAML configuration allows you to define rules that overwrite specific JSON fields based on conditions:

```yaml
json_value_overwrite:
  - name: "machine_max_acceleration_e"  # JSON key to overwrite
    enabled: true                         # Enable this rule
    value: ["20000", "20000"]            # New value (supports strings, numbers, arrays, objects)
    conditions:                           # Optional conditions (AND logic)
      - type: "filename_contains"         # Condition type
        pattern: "Kobra S1"               # Pattern to match in filename
      - type: "json_value"                # Check JSON field value
        key: "type"                       # JSON key to check
        value: "machine"                  # Expected value
```

**Key Features:**

- Only overwrites if the JSON key already exists in the file
- Multiple conditions use AND logic (all must match)
- Empty conditions list applies to all files
- Supports complex values (strings, arrays, objects, multiline text)

#### Error Handling & Logging

The script provides comprehensive logging:
- **INFO**: Progress updates, files processed, summary
- **WARNING**: Missing inherited files, existing output files, missing nozzle diameters
- **ERROR**: Invalid JSON, file I/O errors, processing failures
- **DEBUG**: Detailed transformation steps, condition checks, field updates

Enable debug logging with `--debug` to troubleshoot issues.

## Issue: The device cannot parse the file

When using OrcaSlicer, either with the included the default profile or the ones imported from AnycubicSlicerNext the printer doese not accept the g-code but throws a  `The device cannot parse the file` error.

As workaround the Machine Start g-Code was adapted. See [Machine Start G-code](#machine-start-g-code)

## Optimized Printer Profile Changes

In the optimized profiles the following changes were done compared to the original

### Machine Limits (Standardized Across All Nozzles)

Some profile (especially the 0.25 one) had really conservative limits. In all optimized profiles the values have been updated to reflect Hardware capabilities and are identical regardless of nozzle size:

| Parameter  | Optimized Value |
|-----------|---------------|---------|
| `machine_max_acceleration_e`  | **20000** |
| `machine_max_acceleration_z`  | **1000** |
| `machine_max_jerk_e/x/y/z` | **15** |
| `machine_max_speed_e` | **600** |
| `machine_max_speed_z` | **15** |

### Nozzle-Specific Settings (Vary by Diameter)

Flow-related parameters adjusted per nozzle size:

| Parameter | 0.25mm | 0.4mm | 0.6mm | 0.8mm |
|-----------|---------|--------|--------|--------|
| `retraction_speed` | 30 | 40 | 40 | 40 |
| `wipe_distance` | 1 | 1 | 2 | 2 |
| `retract_lift_above` | 0 | 0 | 0 | 0 |

**Key Principle:** Machine limits define hardware capabilities (same for all). Nozzle-specific settings handle flow characteristics (vary by diameter).

## Improved machine G-code

### Machine Start G-code

__This fixes [The device cannot parse the file](#issue-the-device-cannot-parse-the-file)__

- Added clear start and end block
- Added machine limit g-codes

This was applied in all files (Original and Optimized)

```ini

; ================================
; Begin of Machine Start G-code
; ================================
; Added as contained in AnycubicSlicerNext g-code to fix issues with error:  The device cannot parse the file
C X20000 Y20000 Z1000 E20000 ; Set maximum accelerations (mm/sec^2)
M203 X600 Y600 Z15 E600 ; Set maximum feedrates (mm/sec) (mm/sec)
M204 P20000 R20000 T20000 ; Set Starting Acceleration (mm/sec^2)
M205 X15.00 Y15.00 Z15.00 E15.00 ; Set jerk limits (mm/sec)
M106 S0 ; Turn off part cooling fan (Fan 0)
M106 P2 S0 ; Turn off auxiliary fan (Fan 2)

; start of original Machine Start G-code
G9111 bedTemp=[first_layer_bed_temperature] extruderTemp=[first_layer_temperature[initial_tool]]
M117 Clear LCD display message
; end of original Machine Start G-code
; ================================
; End of Machine Start G-code
; ================================

```

### Machine End G-code

- Added clear start and end block

This was applied in all files (Original and Optimized)

```ini

; ================================
; Begin of Machine End G-code
; ================================
G92 E0
G1 E-2 F3000
{if max_layer_z < max_print_height-1}G1 Z{z_offset+min(max_layer_z+2, max_print_height)} F900 ; Move print head further up{endif}
G1 F12000; present print
G1 X44;  throw_position_x
G1 Y270; throw_position_y
M140 S0 ; turn off heatbed
M104 S0 ; turn off temperature
M106 P1 S0 ; turn off fan
M106 P2 S0
M106 P3 S0
M84; disable motors
; disable stepper motors
; ================================
; End of Machine End G-code
; ================================

```

### Filament Change G-code

- Added clear start and end block
- added improved sequence for faster change

This was applied only in Optimized files.

```ini

; ================================
; Begin of filament change
; ================================
; NOTE: This manual sequence replaces the default firmware routine executed by:
;       T[next_extruder] in the original Kobra S1 profile
;       Original routine includes long retraction, slow XY/Z moves,
;       multi-pass purge/wipe, and long dwell times
;       This optimized version is faster and more efficient while safe

; 1. Retract old filament
; ----------------------
; Original firmware retracts a lot and waits a long time.
; Here we retract only as much as needed to safely remove the filament (~60 mm typical for Bowden path)
G1 E-60 F600 ; retract 60mm at 10mm/s

; 2. Move to safe purge/wipe position
; -----------------------------------
; Original firmware moves very slowly, multiple Z lifts, long XY wipes
G1 Z{toolchange_z+5} F1200 ; lift 5mm fast but safe
G1 X260 Y25 F12000        ; fast travel to purge bucket / wipe area

; 3. Start heating for new filament (overlaps with filament change)
; -----------------------------------------------------------------
; Original firmware waits for full nozzle heat sequentially
M104 S{next_filament_temp} ; set nozzle temp (non-blocking)
; Optional: preheat bed if needed (overlaps with movement)
M140 S{first_layer_bed_temp} ; set bed temp (non-blocking)

; 4. Remove old filament manually (or via Rinkhals actuator)
; ----------------------------------------------------------
; Original firmware does automated unload + long dwell/ooze
; Here, operator or auto feeder removes old filament while hotend heats

; 5. Insert new filament
; ---------------------
; Feed new filament until it reaches nozzle
G1 E10 F400 ; small initial extrusion to check flow
; Optional small back-and-forth wipe
G1 Y1 F600
G1 Y25 F3000

; 6. Purge minimal amount
; ----------------------
; Original firmware purges for 76s + 35s
; Here, we purge only enough to get clean filament at nozzle
G1 E10 F400 ; extrude 10mm

; 7. Return to print height
; ------------------------
; Original firmware has extra Z moves and waits
G1 Z{toolchange_z} F1200
M400 ; wait for moves to finish

;# ; Original Filament Change G-code BEGIN ###
;# ; FLUSH_START ; Marker: Start of filament purge/flush sequence
;# ;;; M400 P0 ; Wait for all moves to complete, with 0ms dwell time
;# T[next_extruder] ; Switch to the next extruder (tool change command)
;# ; 1 ; Section 1: Move to purge position and initial purge
;# ;;; G90 ; Set to absolute positioning mode
;# ;;; G1 Z{toolchange_z+2} F480 ; Raise Z axis 2mm above tool change height at 480mm/min (slow, safe move)
;# ;;; G1 X261 Y25 F12000 ; Move to purge position X=261, Y=25 at 12000mm/min (200mm/sec - fast travel)
;# ;;; G1 Y1 F600 ; Move to Y=1 at 600mm/min (10mm/sec - slow move to wipe nozzle on purge bucket/brush)
;# ;;; M400 P2730 ; Wait for moves to complete, then dwell for 2730ms (2.73 seconds - allows purge to ooze)
;# ;;; G1 Y25 F3000 ; Move back to Y=25 at 3000mm/min (50mm/sec - medium speed)
;# ;;; M400 P76250 ; Wait for moves, then dwell for 76250ms (76.25 seconds - long purge/ooze time)
;# ;;; M400 P35780 ; Wait for moves, then dwell for 35780ms (35.78 seconds - additional ooze time)
;# ; 2.1 ; Section 2.1: Move to wipe tower area
;# ;;; G90 ; Set to absolute positioning mode (redundant, already absolute)
;# ;;; G1 Z{toolchange_z+2} F480 ; Raise Z axis 2mm above tool change height at 480mm/min
;# ;;; G1 X47 Y230 F12000 ; Move to wipe tower position X=47, Y=230 at 12000mm/min (fast travel)
;# ;;; M400 P0 ; Wait for moves to complete with no dwell
;# ; 2.2 ; Section 2.2: Wipe/clean sequence (back and forth movements)
;# ;;; G1 X47 Y276 F600 ; Move to Y=276 at 600mm/min (slow wipe movement - brushing/cleaning nozzle)
;# ;;; G1 X47 Y230 F12000 ; Move back to Y=230 at 12000mm/min (fast return)
;# ;;; G1 X47 Y276 F600 ; Move to Y=276 at 600mm/min (second wipe pass)
;# ;;; G1 X47 Y230 F12000 ; Move back to Y=230 at 12000mm/min (fast return)
;# ; 3.1 ; Section 3.1: Position for final wipe pattern
;# ;;; G1 F36000 ; Set feedrate to 36000mm/min (600mm/sec - very fast for positioning)
;# ;;; G1 Y250 ; Move to Y=250 (using feedrate from previous command)
;# ;;; G1 F8000 ; Set feedrate to 8000mm/min (133mm/sec - medium speed for wiping)
;# ;;; G1 X81 ; Move to X=81 (horizontal wipe movement)
;# ;;; G1 Y273 ; Move to Y=273 (vertical positioning)
;# ; 3.2 ; Section 3.2: Zigzag wipe pattern (back and forth X movements to clean nozzle)
;# ;;; G1 F8000 ; Set feedrate to 8000mm/min (wiping speed)
;# ;;; G1 X96 ; Move to X=96 (wipe right)
;# ;;; G1 X81 ; Move to X=81 (wipe left)
;# ;;; G1 F8000 ; Set feedrate to 8000mm/min (redundant, already set)
;# ;;; G1 X96 ; Move to X=96 (wipe right - pass 2)
;# ;;; G1 X81 ; Move to X=81 (wipe left - pass 2)
;# ;;; G1 F8000 ; Set feedrate to 8000mm/min (redundant)
;# ;;; G1 X96 ; Move to X=96 (wipe right - pass 3)
;# ;;; G1 X81 ; Move to X=81 (wipe left - pass 3)
;# ;;; G1 X96 ; Move to X=96 (wipe right - pass 4)
;# ;;; G1 X81 ; Move to X=81 (wipe left - pass 4)
;# ;;; G1 X96 ; Move to X=96 (wipe right - pass 5)
;# ;;; G1 X81 ; Move to X=81 (wipe left - pass 5)
;# ;;; G1 X96 ; Move to X=96 (wipe right - pass 6)
;# ;;; G1 X81 ; Move to X=81 (wipe left - pass 6)
;# ; 3.3 ; Section 3.3: Final positioning and return to print height
;# ;;; G1 X72 ; Move to X=72 (final wipe position)
;# ;;; G1 X77 ; Move to X=77 (final nozzle clean position)
;# ;;; G1 Z{toolchange_z} ; Return Z axis to original tool change height
;# ;;; M400 P0 ; Wait for all moves to complete with no dwell
;# ; FLUSH_END ; Marker: End of filament purge/flush sequence
;# ; Original Filament Change G-code END ###

; ================================
; End of filament change
; ================================

```
