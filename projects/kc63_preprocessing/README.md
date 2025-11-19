# KC63 Preprocessing

A Python toolkit for preprocessing KC63 data by adding reporting period information to CSV files.

## Overview

This toolkit processes KC63 CSV files and adds a reporting period column based on the year extracted from the filename. The reporting period follows the format `{YYYY-1}-{YYYY}`, representing the fiscal year running April-March.

Key features:

- Extracts year from filename (expects files ending with a 4-digit year)
- Automatically generates reporting period in the format `{YYYY-1}-{YYYY}`
- Batch processes all CSV files in an input directory
- Copies the original data while adding the new reporting period column

## Installation

### Prerequisites

- Python 3.11 or higher

### Setup

1. Install the requirements:

```bash
poetry install
```

This will install the requirements in the `poetry.lock` file.

## Usage

### Add Reporting Period to CSV Files

The script processes CSV files located in the `reporting_period/input/` directory and outputs the results to `reporting_period/output/`.

1. Place your CSV files in the `reporting_period/input/` directory. Filenames must end with a 4-digit year (e.g., `data_2023.csv`).

2. Run the script:

```bash
cd reporting_period
poetry run python add_reporting_period.py
```

The script will:

- Read each CSV file from the input directory
- Extract the year from the filename
- Add a `reporting_period` column with the value `{YYYY-1}-{YYYY}`
- Save the processed file to the output directory with the same filename

### Example

For a file named `kc63_data_2023.csv`, the script will:

- Extract year: `2023`
- Generate reporting period value: `2022-2023`
- Add this value to a new `reporting_period` column in the outgoing CSV

## Project Structure

- `reporting_period/` — Main module for adding reporting periods
  - `add_reporting_period.py` — Script to process CSV files
  - `input/` — Directory for input CSV files
  - `output/` — Directory for processed output files

## Notes

- Input filenames must end with a 4-digit year for the script to work correctly
- The output directory is created automatically if it doesn't exist
- Original data is preserved; only the `reporting_period` column is added
