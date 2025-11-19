import re
import pandas as pd
from pathlib import Path
from typing import Iterable

YEAR_SUFFIX_RE = re.compile(r"(\d{4})$")


def extract_year_from_filename(filename: str) -> int:
    stem = Path(filename).stem
    match = YEAR_SUFFIX_RE.search(stem)
    if not match:
        raise ValueError(f"Filename '{filename}' does not end with a 4-digit year")
    year = int(match.group(1))
    return year


def build_reporting_period(year: int) -> str:
    return f"{year-1}-{year}"


def iter_csv_files(input_dir: Path) -> Iterable[Path]:
    for p in sorted(input_dir.glob("*.csv")):
        if p.is_file() and p.name.lower().endswith(".csv"):
            yield p


def add_reporting_period_to_file(input_file: Path, output_file: Path) -> None:
    year = extract_year_from_filename(input_file.name)
    reporting_period = build_reporting_period(year)
    df = pd.read_csv(input_file, low_memory=False)
    df["reporting_period"] = reporting_period
    df.to_csv(output_file, index=False)


def process_all(input_dir: Path, output_dir: Path) -> None:
    for csv_path in iter_csv_files(input_dir):
        output_filename = f"{csv_path.stem}_preprocessed{csv_path.suffix}"
        target = output_dir / output_filename
        add_reporting_period_to_file(csv_path, target)
        print(f"Processed {csv_path.name} -> {target}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    process_all(input_dir, output_dir)
