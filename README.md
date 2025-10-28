# OrcaSlicer Printer Profiles for Anycubic Printers

This repo contains Profiles for the Anycubic Kobra S1 Combo. The profiles were extracted from AnycubicSlicerNext and adapted to be used as user profiles. Also some "Optimized" profiles were created, for better and faster performance.

The profiles from this repo can simply be copied to `~/.config/OrcaSlicer/user/default/` to add them to OrcaSlicer


## Extracting form AnycubicSlicerNext to OrcaSlicer

It is  possible to get the `filament`, `machine` and `process` configuration from the AnycubicSlicerNext installation.

Prerequisite: AnycubicSlicerNext and OrcaSlicer is installed and was started at least once (so the tool creates the needed files in the user profile).

When manually copying the files to the OrcaSlicer user profiles many adaptions  were needed so a script was created to perform the required step so that the profiles are actually visible in OrcaSlicer.

Two Python scripts are available for working with profiles:
- **[migrate_slicer_profiles.py](#migration-tool)** - Migrates profiles from AnycubicSlicerNext to OrcaSlicer
- **[update_slicer_profiles.py](#update-tool)** - Updates existing profiles with custom values

Ensure to check the [default workflow](#default-workflow) for a quick start guide.

### Default Workflow

The default workflow to migrate and adapt the profiles can be found below.
For more advances use cases check the individual sections documentation for the [migration](#migration-tool) and [update](#update-tool) tool.

```bash
# 1. First migrate profiles from AnycubicSlicerNext
./migrate_slicer_profiles.py --filter '**/*Kobra S1*.json'

# 2. Then update needed firlds to be usable in OrcaSlicer
./update_slicer_profiles.py --source ./ --output ./ --config ./profile_update.yml

# 3. Then create optimized versions (this will only create profile where actually content was changed)
./update_slicer_profiles.py --source ./ --output ./ --config ./profile_update_optimize.yml --filename-replace "Original" "Optimized"

./update_slicer_profiles.py --source ./ --output ./ --config ./profile_update_optimize_speed.yml --filename-replace "Original" "Speed"
```

For updating existing profiles after updating the configuration you can run.

```bash
# Update Base profiles
./update_slicer_profiles.py --source ./ --output ./ --config ./profile_update.yml --filter "**/Original*"

# Update optimized profiles
./update_slicer_profiles.py --source ./ --output ./ --config ./profile_update_optimize.yml --filter "**/Optimized*"

# Update speed profiles
./update_slicer_profiles.py --source ./ --config ./profile_update_optimize_speed.yml --filter "**/Speed*"
```

### Migration Tool

The `migrate_slicer_profiles.py` script automates the process of moving the matching profiles from AnycubicSlicerNext to OrcaSlicer.

Thus tool only aims t select and mocve the needed profiles but does not modify the content yet. Without running the [update tool](#update-tool)afterwards, the profiles will not show up in the slicer.

#### Quick Start Examples

**Migrate all Kobra S1 profiles:**
```bash
./migrate_slicer_profiles.py --filter '**/*Kobra S1*'

# or without default prefix
./migrate_slicer_profiles.py --filter '**/*Kobra S1*' --prefix ""
```

**Interactive Mode (guided prompts):**
```bash
./migrate_slicer_profiles.py --interactive
```

**Print all command line arguments:**
```bash
./migrate_slicer_profiles.py --help
```

#### What the Migration Tool Does

1. **File Discovery & Filtering**
   - Scans source directory for files matching the glob pattern
   - Supports filtering by printer model (e.g., `**/*S1*` for Kobra S1 only)
   -
2. **Output Generation**
   - Preserves relative directory structure from source
   - Applies prefix/postfix to filenames (e.g., `Original <filename>.json`)
   - Writes formatted JSON with optional key sorting
   - Skips existing files unless `--overwrite` is specified


#### Common Use Cases

**Migrate only specific profile types:**
```bash
# Only machine profiles
./migrate_slicer_profiles.py --filter 'machine/*S1*' --prefix 'Original '

# Only process profiles
./migrate_slicer_profiles.py --filter 'process/*S1*' --prefix 'Original '

# Only filament profiles
./migrate_slicer_profiles.py --filter 'filament/*S1*' --prefix 'Original '
```

**Debug mode for troubleshooting:**
```bash
./migrate_slicer_profiles.py --filter '**/*S1*' --debug
```


### Update Tool

The `update_slicer_profiles.py` script applies custom value updates to JSON profile files based on YAML configuration rules.

#### Quick Start Examples

**Update profiles in-place:**
```bash
./update_slicer_profiles.py --config profile_update.yml --source ./machine/

# Using shorthands
./update_slicer_profiles.py -c profile_update.yml -s ./machine/
```

**Update and copy to new location:**
```bash
./update_slicer_profiles.py --config profile_update_optimize.yml \
  --source ./machine/ --output ./optimized/ --prefix 'Optimized '

# Using shorthands
./update_slicer_profiles.py -c profile_update_optimize.yml \
  -s ./machine/ -o ./optimized/ -p 'Optimized '
```

**Update single file:**
```bash
./update_slicer_profiles.py --config profile_update.yml \
  --source "./machine/Kobra S1 0.4 nozzle.json"
```

**Print all command line arguments:**
```bash
./update_slicer_profiles.py --help
```

#### What the Update Tool Does

1. **File Discovery**
   - Processes single file or directory with glob filtering
   - Supports in-place updates or copy-and-update workflow

2. **Rule-Based Updates**
   - Loads JSON value overwrite rules from YAML config
   - Applies conditional updates based on filename, filepath, or JSON content
   - Can update existing keys or add new keys (controlled by `add` parameter)

3. **Output Options**
   - **In-place**: Overwrites source files (when `--output` not specified)
   - **Copy mode**: Creates new files with optional prefix/postfix
   - Preserves directory structure when copying

#### Configuration Files

**`profile_update.yml`** - Basic updates for all profiles:
- Sets `"from": "User"` for all files
- Adds G-code fixes for parser compatibility
- Minimal changes to preserve original behavior

**`profile_update_optimize.yml`** - Advanced optimizations:
- All basic updates from above
- Optimized G-code (start, end, filament change)
- Machine limits tuned for hardware capabilities
- Nozzle-specific parameters (retraction, wipe distance)

#### Configuration Rule Format

YAML rules define which JSON keys to update and when:

```yaml
# Default conditions applied to ALL rules
default_conditions:
  - type: "filename_glob"
    pattern: "*Kobra S1*"  # Only process files with "Kobra S1" in name
  - type: "exclude_filepath_glob"
    pattern: "**/copy_from_AnycubicSlicerNext/*"  # Exclude backup files

json_value_overwrite:
  - name: "machine_max_acceleration_e"  # JSON key to update
    enabled: true                         # Enable rule (default: true)
    value: ["20000", "20000"]            # New value (any JSON type)
    add: false                            # Add key if missing (default: false)
    conditions:                           # Optional: when to apply (AND logic)
      - type: "filename_glob"             # Match filename with glob
        pattern: "*Kobra S1*.json"        # Glob pattern
      - type: "filepath_glob"             # Match absolute path with glob
        pattern: "*/machine/*.json"       # Absolute path pattern
      - type: "exclude_filepath_glob"     # Exclude files matching pattern
        pattern: "*/backup/*"             # Don't process backup files
      - type: "json_value"                # Check JSON field value
        key: "type"                       # JSON key to check
        value: "machine"                  # Expected value (exact match)
        negate: false                     # Optional: negate condition (default: false)
```

**Rule Behavior:**

- **enabled**: If `false`, rule is skipped; if omitted, defaults to `true` (rule is active)
- **add**: If `true`, adds key if it doesn't exist; if `false` (default), only updates existing keys
- **default_conditions**: Conditions applied to ALL rules (combined with rule-specific conditions using AND logic)
- **conditions**: Rule-specific conditions (optional)
  - If omitted or empty list `[]`, only default_conditions apply
  - Multiple conditions use **AND logic** (all must match)
  - Available condition types:
    - `filename_glob`: Match filename with glob pattern (e.g., `*Kobra S1*.json`)
    - `exclude_filename_glob`: Exclude filenames matching pattern
    - `filepath_glob`: Match absolute file path with glob pattern (e.g., `*/machine/*.json`)
    - `exclude_filepath_glob`: Exclude files where absolute path matches pattern
    - `json_value`: Check if JSON key has specific value
      - `negate: true`: Condition passes if value does NOT match (optional)
- **value**: Supports any JSON type (string, number, array, object, multiline text)
- **Content change detection**: Files are only written if JSON content actually changes (unless `--force-copy` is used)

#### Common Use Cases

**Generate Optimized profiles**
```bash

./update_slicer_profiles.py --source ~/.config/OrcaSlicer/user/default/ \
  --config ./profile_update_optimize.yml \
  --filename-replace "Original" "Optimized"
```

**Update specific profile types:**
```bash
# Only update machine profiles
./update_slicer_profiles.py --config profile_update.yml \
  --source ./machine/ --filter '*.json'

# Only update filament profiles
./update_slicer_profiles.py --config profile_update.yml \
  --source ./filament/ --filter '*.json'
```

**In-place updates (modify files directly):**
```bash
# Update all profiles in directory (modifies original files)
./update_slicer_profiles.py --config profile_update.yml --source ./profiles/

# Update single file in-place
./update_slicer_profiles.py --config profile_update.yml \
  --source "./profiles/my_profile.json"
```

**Using filename replacements:**
```bash
# Create "Optimized" variants from "Original" profiles
./update_slicer_profiles.py --config profile_update_optimize.yml \
  --source ./profiles/ \
  --filename-replace "Original" "Optimized"

# Multiple replacements
./update_slicer_profiles.py --config profile_update.yml \
  --source ./profiles/ --output ./updated/ \
  --filename-replace "Original" "Updated" \
  --filename-replace "Standard" "Premium"
```


## Issue: The device cannot parse the file

When using OrcaSlicer, either with the included the default profile or the ones imported from AnycubicSlicerNext the printer doese not accept the g-code but throws a  `The device cannot parse the file` error.

The cause is the default thumbnail configuration from the AnycubicSlicerNext machine profiles. The issue can be resolved by setting `"thumbnails": "32x32/PNG, 400x300/PNG"` thus update is included in the configurations for the  update tool.

## Printer Profile

In the profiles contained in this repo the following changes were done compared to the original

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
