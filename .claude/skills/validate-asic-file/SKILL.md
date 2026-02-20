---
name: validate-asic-file
description: Validates ASIC design files (SDC, LEF, DEF, Liberty, SDF, SPEF, Verilog netlist) against format-specific structural and syntax rules. Reports errors (blocking), warnings (non-blocking), and a VALID / VALID WITH WARNINGS / INVALID verdict with line numbers. Use when checking whether an EDA file is well-formed before feeding it to a tool.
argument-hint: <file-path>
disable-model-invocation: true
---

Validate the ASIC file at: $ARGUMENTS

## Step 1: Detect Format

Determine the format from the file extension:

| Extension          | Format           |
|--------------------|------------------|
| `.sdc`             | SDC              |
| `.lib`, `.liberty` | Liberty          |
| `.lef`             | LEF              |
| `.def`             | DEF              |
| `.sdf`             | SDF              |
| `.spef`            | SPEF             |
| `.v`, `.vg`        | Verilog Netlist  |

If the extension is unrecognized, report `Unknown format — cannot validate.` and stop.

## Step 2: Load Rules

Read [format-rules.md](format-rules.md) and locate the section for the detected format. Note every **REQUIRED** rule (errors on violation) and **RECOMMENDED** rule (warnings on violation).

## Step 3: Read and Validate

Read the file content. Work through the rules from Step 2 line by line:

- Record **ERROR** for any REQUIRED rule violation. The file is invalid.
- Record **WARNING** for any RECOMMENDED rule violation. The file is suspect but may still work.
- Include the line number for every finding where locatable.
- If a rule is conditional, verify the condition before applying it.

## Step 4: Output Report

```
### Validation Report: `<filename>` (<FORMAT>)

**Verdict**: VALID | VALID WITH WARNINGS | INVALID

| Severity | Count |
|----------|-------|
| Errors   | N     |
| Warnings | N     |

#### Errors
- Line N: <description>

#### Warnings
- Line N: <description>

#### Summary
<One paragraph: overall state of the file and most critical issue to fix, if any.>
```
