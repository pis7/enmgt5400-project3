"""
SDC (Synopsys Design Constraints) file parser.

Parses .sdc timing constraint files and returns structured Python objects.
Handles common SDC commands used in ASIC synthesis and place-and-route flows.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ClockConstraint:
    name: str
    period: float
    waveform: tuple[float, float] = (0.0, 0.0)
    source: str = ""

    def __post_init__(self):
        if self.period <= 0:
            raise ValueError(f"Clock period must be positive, got {self.period}")
        if not self.waveform:
            self.waveform = (0.0, self.period / 2)


@dataclass
class IODelay:
    pin: str
    clock: str
    delay_value: float
    delay_type: str = "input"
    min_delay: float | None = None
    max_delay: float | None = None


@dataclass
class TimingException:
    exception_type: str
    from_list: list[str] = field(default_factory=list)
    to_list: list[str] = field(default_factory=list)
    value: float | None = None


@dataclass
class SDCConstraintSet:
    clocks: list[ClockConstraint] = field(default_factory=list)
    io_delays: list[IODelay] = field(default_factory=list)
    exceptions: list[TimingException] = field(default_factory=list)
    raw_commands: list[str] = field(default_factory=list)


class SDCParser:
    def __init__(self, strict=False):
        self.strict = strict
        self.result = SDCConstraintSet()
        self._line_num = 0

    def parse_file(self, path):
        text = open(str(path), "r").read()
        return self.parse_string(text)

    def parse_string(self, content):
        self.result = SDCConstraintSet()
        lines = self._join_continuation_lines(content)

        for i, line in enumerate(lines):
            self._line_num = i + 1
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            self.result.raw_commands.append(line)

            if line.startswith("create_clock"):
                self._parse_create_clock(line)
            elif line.startswith("set_input_delay"):
                self._parse_io_delay(line, "input")
            elif line.startswith("set_output_delay"):
                self._parse_io_delay(line, "output")
            elif line.startswith("set_false_path"):
                self._parse_false_path(line)
            elif line.startswith("set_multicycle_path"):
                self._parse_multicycle_path(line)
            elif line.startswith("set_max_delay"):
                self._parse_max_min_delay(line, "max")
            elif line.startswith("set_min_delay"):
                self._parse_max_min_delay(line, "min")
            elif line.startswith("set_clock_groups"):
                self._parse_clock_groups(line)
            elif line.startswith("set_clock_uncertainty"):
                self._parse_clock_uncertainty(line)
            elif line.startswith("set_load"):
                pass
            elif line.startswith("set_driving_cell"):
                pass
            else:
                if self.strict:
                    raise ValueError(f"Unknown SDC command at line {self._line_num}: {line[:60]}")
                else:
                    logger.warning(f"Skipping unknown command at line {self._line_num}: {line[:60]}")

        return self.result

    def _join_continuation_lines(self, content):
        joined = content.replace("\\\n", " ").replace("\\\r\n", " ")
        return joined.splitlines()

    def _parse_create_clock(self, line):
        period_match = re.search(r"-period\s+(\S+)", line)
        name_match = re.search(r"-name\s+(\S+)", line)
        waveform_match = re.search(r"-waveform\s+\{([^}]+)\}", line)
        source_match = re.search(r"\[get_ports\s+(\S+?)\]", line)
        if not source_match:
            source_match = re.search(r"\[get_pins\s+(\S+?)\]", line)

        if not period_match:
            if self.strict:
                raise ValueError(f"create_clock missing -period at line {self._line_num}")
            logger.warning(f"create_clock missing -period at line {self._line_num}")
            return

        period = float(period_match.group(1))
        name = name_match.group(1) if name_match else ""
        source = source_match.group(1) if source_match else ""

        waveform = (0.0, period / 2)
        if waveform_match:
            parts = waveform_match.group(1).split()
            if len(parts) == 2:
                waveform = (float(parts[0]), float(parts[1]))

        if not name and source:
            name = source

        clock = ClockConstraint(
            name=name,
            period=period,
            waveform=waveform,
            source=source,
        )
        self.result.clocks.append(clock)
        logger.debug(f"Parsed clock: {clock.name} period={clock.period}")

    def _parse_io_delay(self, line, delay_type):
        clock_match = re.search(r"-clock\s+(?:\[get_clocks\s+)?(\S+?)[\]\s]", line)
        value_match = re.search(r"(?:-max|-min)?\s+(-?\d+\.?\d*)\s", line)
        pin_match = re.search(r"\[(?:get_ports|get_pins)\s+(\S+?)\]", line)
        is_min = "-min" in line
        is_max = "-max" in line

        if not clock_match or not pin_match:
            if self.strict:
                raise ValueError(f"Incomplete IO delay at line {self._line_num}")
            logger.warning(f"Incomplete IO delay at line {self._line_num}")
            return

        val = float(value_match.group(1)) if value_match else 0.0

        delay = IODelay(
            pin=pin_match.group(1),
            clock=clock_match.group(1),
            delay_value=val,
            delay_type=delay_type,
            min_delay=val if is_min else None,
            max_delay=val if is_max else None,
        )
        self.result.io_delays.append(delay)

    def _parse_false_path(self, line):
        from_match = re.findall(r"-from\s+\[get_clocks\s+\{?([^}\]]+)\}?\]", line)
        to_match = re.findall(r"-to\s+\[get_clocks\s+\{?([^}\]]+)\}?\]", line)

        from_list = []
        for m in from_match:
            from_list.extend(m.split())
        to_list = []
        for m in to_match:
            to_list.extend(m.split())

        exc = TimingException(
            exception_type="false_path",
            from_list=from_list,
            to_list=to_list,
        )
        self.result.exceptions.append(exc)

    def _parse_multicycle_path(self, line):
        multiplier_match = re.search(r"-path_multiplier\s+(\d+)", line)
        setup_match = re.search(r"-setup\s+(\d+)", line)
        hold_match = re.search(r"-hold\s+(\d+)", line)
        from_match = re.findall(r"-from\s+\[get_clocks\s+\{?([^}\]]+)\}?\]", line)
        to_match = re.findall(r"-to\s+\[get_clocks\s+\{?([^}\]]+)\}?\]", line)

        from_list = []
        for m in from_match:
            from_list.extend(m.split())
        to_list = []
        for m in to_match:
            to_list.extend(m.split())

        value = None
        if setup_match:
            value = float(setup_match.group(1))
        elif hold_match:
            value = float(hold_match.group(1))
        elif multiplier_match:
            value = float(multiplier_match.group(1))

        exc = TimingException(
            exception_type="multicycle_path",
            from_list=from_list,
            to_list=to_list,
            value=value,
        )
        self.result.exceptions.append(exc)

    def _parse_max_min_delay(self, line, kind):
        value_match = re.search(r"(?:set_max_delay|set_min_delay)\s+(-?\d+\.?\d*)", line)
        from_match = re.findall(r"-from\s+\[get_clocks\s+\{?([^}\]]+)\}?\]", line)
        to_match = re.findall(r"-to\s+\[get_clocks\s+\{?([^}\]]+)\}?\]", line)

        from_list = []
        for m in from_match:
            from_list.extend(m.split())
        to_list = []
        for m in to_match:
            to_list.extend(m.split())

        value = float(value_match.group(1)) if value_match else None

        exc = TimingException(
            exception_type=f"{kind}_delay",
            from_list=from_list,
            to_list=to_list,
            value=value,
        )
        self.result.exceptions.append(exc)

    def _parse_clock_groups(self, line):
        group_matches = re.findall(r"-group\s+\{([^}]+)\}", line)
        for group_str in group_matches:
            clocks = group_str.split()
            logger.debug(f"Clock group: {clocks}")

    def _parse_clock_uncertainty(self, line):
        value_match = re.search(r"set_clock_uncertainty\s+(-?\d+\.?\d*)", line)
        if value_match:
            logger.debug(f"Clock uncertainty: {value_match.group(1)}")


def analyze_constraints(constraint_set):
    total_clocks = len(constraint_set.clocks)
    total_exceptions = len(constraint_set.exceptions)
    total_io = len(constraint_set.io_delays)

    clock_periods = {}
    for c in constraint_set.clocks:
        clock_periods[c.name] = c.period

    fastest_clock = None
    if clock_periods:
        fastest_clock = min(clock_periods, key=clock_periods.get)

    false_paths = [e for e in constraint_set.exceptions if e.exception_type == "false_path"]
    multicycles = [e for e in constraint_set.exceptions if e.exception_type == "multicycle_path"]

    report = {
        "total_clocks": total_clocks,
        "total_io_delays": total_io,
        "total_exceptions": total_exceptions,
        "clock_periods": clock_periods,
        "fastest_clock": fastest_clock,
        "false_path_count": len(false_paths),
        "multicycle_count": len(multicycles),
    }
    return report


def print_summary(path):
    p = SDCParser()
    result = p.parse_file(path)
    report = analyze_constraints(result)
    print(f"SDC Summary for: {path}")
    print(f"  Clocks: {report['total_clocks']}")
    for name, period in report["clock_periods"].items():
        freq_mhz = 1000.0 / period
        print(f"    {name}: {period} ns ({freq_mhz:.1f} MHz)")
    if report["fastest_clock"]:
        print(f"  Fastest clock: {report['fastest_clock']}")
    print(f"  IO delays: {report['total_io_delays']}")
    print(f"  False paths: {report['false_path_count']}")
    print(f"  Multicycle paths: {report['multicycle_count']}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python sdc_parser.py <file.sdc>")
        sys.exit(1)
    print_summary(sys.argv[1])
