# OrcaSlicer Printer Profiles for Anycubic Kobra S1 Combo

This repo contains Profiles for the Anycubic Kobra S1 Combo. The profiles were extracted from AnycubicSlicerNext and adapted to be used as user profiles. Also some "Optimized" profiles were created, for better and faster performance.

## Extracting form AnycubicSlicerNext  to OrcaSlicer

It is  possible to get the `filament`, `machine` and `process` configuration from the AnycubicSlicerNext installation.

Prerequisite: AnycubicSlicerNext and OrcaSlicer is installed and was startet at least once (so the tool creates the needed files in the user profile).

You can fine the original files from AnycubicSlicerNext in  `.copy_from_AnycubicSlicerNext` sub-folders for reference or to compare. As OrcaSlicer will sort the json files when changing a profile the a `sorted_*.json` was added to be able to compare.

Steps:

1. locate the `filament`, `machine` and `process` folders in `~/.config/AnycubicSlicerNext/system/Anycubic`
2. Search for the files for your printer in one of the folders
3. copy them to corresponding `machine` and `process` folder of the OrcaSlicer user profile in `~/.config/OrcaSlicer/user/default/`
4. Optional: Rename files and prepend "Original" and prepare "optimized"
    - Prepare Optimized Profiles for doing custom adaptions with possibility to compare to original
           `for file in Anycubic*.json; do cp "$file" "Optimized $file"; done`
    - Rename Original `for file in Anycubic*.json; do mv "$file" "Original $file"; done`
5. adapt the json files so they are accepted
    - json files in `filament`, `machine` and `process`
        - ensure `"is_custom_defined": "0"` is set
        - ensure `"instantiation": "true",` is set
        - If files were renamed: ensure to update `"inherits":` values to match the new filenames.
    - json files in `filament`, and `process`
        - For better comatibilety:
          - remove `"compatible_printers":` key value pair to apply profiles to all matching printers
          - use `"compatible_printers_condition": "printer_model==\\\"Anycubic Kobra S1\\\" and nozzle_diameter[0]==0.XXX",` while setting the matching nozzle diameter based on the profile filename
    - json files in `filament`
      - ensure all `Anycubic PLA @Anycubic Kobra S1 * nozzle.json` files  contain `"inherits": "Anycubic PLA @acbase",`
    - json files in `machine`
        - Optional: For `machines` you can choose to set `"support_multi_bed_types": "1"`
    - json files in  `process`
        - ensure to remove values for `"inherits": "fdm_process_common"` to `"inherits": ""`
        - as inherits does not work as expected you need to combine user profiles that inherit other user profiles. When writing this, 0.6 and 0.8 nozzle files were affected. A script can be used to do this: [./process/fix_inherits.sh](./process/fix_inherits.sh)

### Generic logic

A python script that has two basic modes --interactive where the user is prompted or normal (with arguments only)

Inputs/Questions:

source path (~/.config/AnycubicSlicerNext/system/Anycubic/)
output path (~/.config/OrcaSlicer/user/default/)
prefix -- Prefix  copied filename (Original)
postfix (None)
filter (**/*) -- glob  the user can use to filter input to be copied from source. (e.g only process */*S1* or machine/*)
debug

Logic:

Every file in source that matches the glob is processed.
In case we have a json file the content is read, analyzed and updated.
Files with "type": "machine_model" are skipped.
If content contains `"inherits":` value
 - find file with <value>.json in the same folder than the current file
 - change the value to ""
 - merge the two json while overwriting the values from the inherited file with existing values
 - if the included file also contains `"inherits":` value the same logic applies recursively


ensure `"is_custom_defined": "0"` is set
ensure `"instantiation": "true",` is set

remove `"compatible_printers":` key value pair
set `"compatible_printers_condition": "printer_model==\\\"Anycubic Kobra S1\\\" and nozzle_diameter[0]==<diameter>",` while setting the matching nozzle diameter extracted from the profile filename  (xxxx <diameter> nozzle.json)
If key "support_multi_bed_types" exists  set the value to 1

The final content is written to the output location while preserving the relative paths of the files to source. The destination filename is the filename from source combined with te specified pre/postfix


The script shall use logging and Path argparse.  Follow the python best practices for clean code

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
