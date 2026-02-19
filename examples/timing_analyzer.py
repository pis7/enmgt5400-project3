"""
Timing report analyzer for ASIC design flows.

Reads timing reports (e.g., from PrimeTime or similar STA tools) and extracts
path information, slack values, and violation summaries.
"""
from __future__ import annotations

import re
import os
from dataclasses import dataclass, field


@dataclass
class TimingPathElement:
    instance: str
    cell: str
    delay: float
    transition: float
    fanout: int = 0
    capacitance: float = 0.0


@dataclass
class TimingPath:
    startpoint: str
    endpoint: str
    path_group: str
    slack: float
    elements: list[TimingPathElement] = field(default_factory=list)
    data_arrival: float = 0.0
    data_required: float = 0.0
    is_violation: bool = False
    path_type: str = "setup"

    def __post_init__(self):
        self.is_violation = self.slack < 0


@dataclass
class TimingReport:
    paths: list[TimingPath] = field(default_factory=list)
    worst_slack: float = float("inf")
    total_violations: int = 0
    wns: float = 0.0
    tns: float = 0.0


def parse_timing_report(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r") as f:
        content = f.read()

    report = TimingReport()
    path_blocks = re.split(r"-{40,}", content)

    for block in path_blocks:
        block = block.strip()
        if not block:
            continue

        startpoint_match = re.search(r"Startpoint:\s*(\S+)", block)
        endpoint_match = re.search(r"Endpoint:\s*(\S+)", block)
        slack_match = re.search(r"slack\s*\((?:MET|VIOLATED)\)\s*(-?\d+\.?\d*)", block)
        group_match = re.search(r"Path Group:\s*(\S+)", block)
        type_match = re.search(r"Path Type:\s*(\S+)", block)
        arrival_match = re.search(r"data arrival time\s+(-?\d+\.?\d*)", block)
        required_match = re.search(r"data required time\s+(-?\d+\.?\d*)", block)

        if not startpoint_match or not endpoint_match:
            continue

        slack_val = float(slack_match.group(1)) if slack_match else 0.0

        path = TimingPath(
            startpoint=startpoint_match.group(1),
            endpoint=endpoint_match.group(1),
            path_group=group_match.group(1) if group_match else "default",
            slack=slack_val,
            path_type=type_match.group(1).lower() if type_match else "setup",
            data_arrival=float(arrival_match.group(1)) if arrival_match else 0.0,
            data_required=float(required_match.group(1)) if required_match else 0.0,
        )

        path_lines = block.splitlines()
        in_path_section = False
        for line in path_lines:
            if re.match(r"\s*-+\s*$", line):
                in_path_section = True
                continue
            if in_path_section:
                elem_match = re.match(
                    r"\s*(\S+)\s+\((\S+)\)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)"
                    r"(?:\s+(\d+))?"
                    r"(?:\s+(-?\d+\.?\d*))?",
                    line,
                )
                if elem_match:
                    element = TimingPathElement(
                        instance=elem_match.group(1),
                        cell=elem_match.group(2),
                        delay=float(elem_match.group(3)),
                        transition=float(elem_match.group(4)),
                        fanout=int(elem_match.group(5)) if elem_match.group(5) else 0,
                        capacitance=float(elem_match.group(6)) if elem_match.group(6) else 0.0,
                    )
                    path.elements.append(element)

        report.paths.append(path)

    # compute summary stats
    for p in report.paths:
        if p.slack < report.worst_slack:
            report.worst_slack = p.slack
        if p.is_violation:
            report.total_violations += 1
            report.tns += p.slack

    report.wns = report.worst_slack if report.worst_slack != float("inf") else 0.0

    return report


def find_critical_paths(report, count=10):
    sorted_paths = sorted(report.paths, key=lambda p: p.slack)
    return sorted_paths[:count]


def group_violations_by_clock(report):
    groups = {}
    for path in report.paths:
        if path.is_violation:
            group = path.path_group
            if group not in groups:
                groups[group] = {"count": 0, "worst_slack": 0.0, "tns": 0.0, "paths": []}
            groups[group]["count"] += 1
            groups[group]["tns"] += path.slack
            if path.slack < groups[group]["worst_slack"]:
                groups[group]["worst_slack"] = path.slack
            groups[group]["paths"].append(path)
    return groups


def check_high_fanout(report, threshold=32):
    flagged = []
    for path in report.paths:
        for elem in path.elements:
            if elem.fanout > threshold:
                flagged.append({
                    "path_start": path.startpoint,
                    "path_end": path.endpoint,
                    "instance": elem.instance,
                    "cell": elem.cell,
                    "fanout": elem.fanout,
                    "slack": path.slack,
                })
    return flagged


def check_long_transitions(report, threshold=0.5):
    flagged = []
    for path in report.paths:
        for elem in path.elements:
            if elem.transition > threshold:
                flagged.append({
                    "path_start": path.startpoint,
                    "path_end": path.endpoint,
                    "instance": elem.instance,
                    "cell": elem.cell,
                    "transition": elem.transition,
                    "slack": path.slack,
                })
    return flagged


def generate_text_summary(report):
    lines = []
    lines.append("=" * 60)
    lines.append("TIMING ANALYSIS SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Total paths analyzed: {len(report.paths)}")
    lines.append(f"Total violations:     {report.total_violations}")
    lines.append(f"WNS (worst slack):    {report.wns:.3f}")
    lines.append(f"TNS (total slack):    {report.tns:.3f}")
    lines.append("")

    if report.total_violations > 0:
        lines.append("--- Top 5 Critical Paths ---")
        for i, p in enumerate(find_critical_paths(report, 5)):
            lines.append(f"  {i+1}. {p.startpoint} -> {p.endpoint}")
            lines.append(f"     Group: {p.path_group}  Slack: {p.slack:.3f}  Type: {p.path_type}")
        lines.append("")

        groups = group_violations_by_clock(report)
        lines.append("--- Violations by Clock Group ---")
        for group_name, info in sorted(groups.items(), key=lambda x: x[1]["worst_slack"]):
            lines.append(f"  {group_name}: {info['count']} violations, WNS={info['worst_slack']:.3f}, TNS={info['tns']:.3f}")

    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python timing_analyzer.py <timing_report.rpt>")
        sys.exit(1)
    rpt = parse_timing_report(sys.argv[1])
    print(generate_text_summary(rpt))
