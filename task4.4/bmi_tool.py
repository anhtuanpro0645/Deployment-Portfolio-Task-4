"""Task 4.4 - BMI Calculator CLI: a non-web, run-to-completion containerised tool.

Single  : bmi_tool.py --name Tuan --height 172 --weight 65
Batch   : bmi_tool.py --input /data/people.csv --output /data/output/bmi_report.txt
History : bmi_tool.py --show-history

Single calculations are appended to a history file (default /data/bmi_history.log).
Mount a host folder or Docker volume on /data so all files persist after exit.
BMI is a general screening measure only and is not medical advice.
"""

import argparse
import csv
import logging
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

EXIT_OK = 0
EXIT_STORAGE_ERROR = 1
EXIT_INVALID_INPUT = 2
EXIT_NO_VALID_ROWS = 3

MIN_HEIGHT_CM, MAX_HEIGHT_CM = 100, 250
MIN_WEIGHT_KG, MAX_WEIGHT_KG = 20, 300
CENTIMETRES_PER_METRE = 100
DECIMAL_PLACES = 1
DEFAULT_HISTORY_FILE = "/data/bmi_history.log"

# WHO adult BMI categories: (upper limit, category, general advice).
CATEGORIES = (
    (
        18.5,
        "Underweight",
        "Consider talking to a GP or dietitian about healthy ways to gain weight.",
    ),
    (
        25.0,
        "Healthy weight",
        "Keep up balanced meals, regular activity and good sleep.",
    ),
    (
        30.0,
        "Overweight",
        "Small, sustainable changes to activity and eating habits can help.",
    ),
    (
        float("inf"),
        "Obese",
        "A GP can offer personalised support and check overall health.",
    ),
)

DISCLAIMER = (
    "Note: BMI is a general screening measure. It does not account for muscle "
    "mass, age, sex or ethnicity and is not medical advice."
)

logger = logging.getLogger("bmi-tool")


@dataclass(frozen=True)
class BmiResult:
    name: str
    height_cm: float
    weight_kg: float
    bmi: float
    category: str
    advice: str


# ---------- Core calculation ----------


def validate_measurements(height_cm, weight_kg):
    if not MIN_HEIGHT_CM <= height_cm <= MAX_HEIGHT_CM:
        raise ValueError(
            f"height must be {MIN_HEIGHT_CM}-{MAX_HEIGHT_CM} cm, got {height_cm}"
        )
    if not MIN_WEIGHT_KG <= weight_kg <= MAX_WEIGHT_KG:
        raise ValueError(
            f"weight must be {MIN_WEIGHT_KG}-{MAX_WEIGHT_KG} kg, got {weight_kg}"
        )


def calculate_bmi(name, height_cm, weight_kg):
    validate_measurements(height_cm, weight_kg)
    height_m = height_cm / CENTIMETRES_PER_METRE
    bmi = round(weight_kg / (height_m**2), DECIMAL_PLACES)
    for upper_limit, category, advice in CATEGORIES:
        if bmi < upper_limit:
            return BmiResult(name, height_cm, weight_kg, bmi, category, advice)
    raise AssertionError("unreachable: last category has no upper limit")


# ---------- Arguments ----------


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        description="Calculate BMI and give general advice."
    )
    parser.add_argument(
        "--name", default="Anonymous", help="Name to record (single mode)"
    )
    parser.add_argument("--height", type=float, help="Height in cm (single mode)")
    parser.add_argument("--weight", type=float, help="Weight in kg (single mode)")
    parser.add_argument(
        "--input", help="CSV with name,height_cm,weight_kg (batch mode)"
    )
    parser.add_argument("--output", help="Report file to write (batch mode)")
    parser.add_argument(
        "--show-history", action="store_true", help="Print saved history"
    )
    parser.add_argument(
        "--history-file",
        default=os.environ.get("HISTORY_FILE", DEFAULT_HISTORY_FILE),
        help=f"History file path (default {DEFAULT_HISTORY_FILE})",
    )
    arguments = parser.parse_args(argv)

    single_mode = arguments.height is not None or arguments.weight is not None
    batch_mode = arguments.input is not None or arguments.output is not None
    chosen_modes = sum([single_mode, batch_mode, arguments.show_history])
    if chosen_modes != 1:
        parser.error(
            "choose ONE mode: --height/--weight, --input/--output, or --show-history"
        )
    if single_mode and (arguments.height is None or arguments.weight is None):
        parser.error("single mode needs both --height and --weight")
    if batch_mode and (arguments.input is None or arguments.output is None):
        parser.error("batch mode needs both --input and --output")
    return arguments


# ---------- File helpers ----------


def ensure_folder(path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def append_history(path, result):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = (
        f"{timestamp} | {result.name} | {result.height_cm:.0f} cm | "
        f"{result.weight_kg:.1f} kg | BMI {result.bmi:.1f} | {result.category}"
    )
    ensure_folder(path)
    with open(path, "a", encoding="utf-8") as history_file:
        history_file.write(entry + "\n")


def read_people(path):
    """Yield (line_number, BmiResult | error message) for each CSV row."""
    with open(path, newline="", encoding="utf-8") as csv_file:
        for line_number, row in enumerate(csv.DictReader(csv_file), start=2):
            try:
                result = calculate_bmi(
                    row["name"].strip(),
                    float(row["height_cm"]),
                    float(row["weight_kg"]),
                )
            except (KeyError, TypeError, ValueError, AttributeError) as error:
                yield line_number, str(error)
            else:
                yield line_number, result


def format_report(input_path, results):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    category_counts = Counter(result.category for result in results)
    lines = [
        "BMI REPORT",
        "==========",
        f"Source file : {input_path}",
        f"People      : {len(results)}",
        f"Generated   : {generated_at}",
        "",
        f"{'Name':<12}{'Height':>8}{'Weight':>8}{'BMI':>7}  {'Category':<16}Advice",
        "-" * 110,
    ]
    for result in results:
        lines.append(
            f"{result.name:<12}{result.height_cm:>8.0f}{result.weight_kg:>8.1f}"
            f"{result.bmi:>7.1f}  {result.category:<16}{result.advice}"
        )
    lines += ["", "Summary by category:"]
    for _, category, _ in CATEGORIES:
        lines.append(f"  {category:<16}{category_counts.get(category, 0)}")
    lines += ["", DISCLAIMER]
    return "\n".join(lines) + "\n"


# ---------- Modes ----------


def run_single(arguments):
    try:
        result = calculate_bmi(arguments.name, arguments.height, arguments.weight)
    except ValueError as error:
        logger.error("Invalid measurement: %s", error)
        return EXIT_INVALID_INPUT
    logger.info("%s: BMI %.1f (%s)", result.name, result.bmi, result.category)
    logger.info("Advice: %s", result.advice)
    logger.info(DISCLAIMER)
    try:
        append_history(arguments.history_file, result)
    except OSError as error:
        logger.error("Could not save history: %s", error)
        return EXIT_STORAGE_ERROR
    logger.info("Saved to history: %s", arguments.history_file)
    return EXIT_OK


def run_batch(arguments):
    results = []
    try:
        for line_number, outcome in read_people(arguments.input):
            if isinstance(outcome, BmiResult):
                results.append(outcome)
            else:
                logger.warning("Skipping line %d: %s", line_number, outcome)
    except FileNotFoundError:
        logger.error("Input file not found: %s", arguments.input)
        return EXIT_STORAGE_ERROR
    except (csv.Error, UnicodeDecodeError) as error:
        logger.error("Could not read CSV: %s", error)
        return EXIT_STORAGE_ERROR

    if not results:
        logger.error("No valid rows found - nothing to report")
        return EXIT_NO_VALID_ROWS
    logger.info("Calculated BMI for %d people", len(results))

    try:
        ensure_folder(arguments.output)
        with open(arguments.output, "w", encoding="utf-8") as report_file:
            report_file.write(format_report(arguments.input, results))
    except OSError as error:
        logger.error("Could not write report: %s", error)
        return EXIT_STORAGE_ERROR
    logger.info("Report written to %s", arguments.output)
    return EXIT_OK


def run_show_history(arguments):
    try:
        with open(arguments.history_file, encoding="utf-8") as history_file:
            entries = history_file.read().splitlines()
    except FileNotFoundError:
        logger.info("No history yet at %s", arguments.history_file)
        return EXIT_OK
    except OSError as error:
        logger.error("Could not read history: %s", error)
        return EXIT_STORAGE_ERROR
    logger.info("History (%d entries) from %s:", len(entries), arguments.history_file)
    for entry in entries:
        logger.info("  %s", entry)
    return EXIT_OK


def run(argv):
    arguments = parse_arguments(argv)
    if arguments.show_history:
        mode, handler = "history", run_show_history
    elif arguments.input:
        mode, handler = "batch", run_batch
    else:
        mode, handler = "single", run_single
    logger.info("START bmi-tool (%s mode)", mode)
    exit_code = handler(arguments)
    logger.info("FINISHED - exiting with code %d", exit_code)
    return exit_code


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stdout,
    )
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()