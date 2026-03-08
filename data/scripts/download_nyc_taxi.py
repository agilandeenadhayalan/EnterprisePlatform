#!/usr/bin/env python3
"""
NYC Taxi & Limousine Commission Trip Data Downloader
=====================================================

Downloads Yellow Taxi trip data from the NYC TLC website.
Data is stored as Parquet files (~300GB for all years 2009-2024).

Source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Usage:
    # Download 2023 data only (~3.5GB, ~37M trips)
    python download_nyc_taxi.py --years 2023

    # Download specific months
    python download_nyc_taxi.py --years 2023 --months 1,2,3

    # Download multiple years (~300GB for all)
    python download_nyc_taxi.py --years 2019,2020,2021,2022,2023,2024

    # Download everything (2009-2024, ~1.7B trips, ~300GB)
    python download_nyc_taxi.py --all

    # Dry run (show what would be downloaded)
    python download_nyc_taxi.py --years 2023 --dry-run

Dataset columns (Yellow Taxi):
    VendorID, tpep_pickup_datetime, tpep_dropoff_datetime,
    passenger_count, trip_distance, RatecodeID, store_and_fwd_flag,
    PULocationID, DOLocationID, payment_type, fare_amount,
    extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge,
    total_amount, congestion_surcharge, airport_fee
"""

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError


# NYC TLC data URL template
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
YELLOW_TEMPLATE = f"{BASE_URL}/yellow_tripdata_{{year}}-{{month:02d}}.parquet"
GREEN_TEMPLATE = f"{BASE_URL}/green_tripdata_{{year}}-{{month:02d}}.parquet"
FHV_TEMPLATE = f"{BASE_URL}/fhv_tripdata_{{year}}-{{month:02d}}.parquet"
FHVHV_TEMPLATE = f"{BASE_URL}/fhvhv_tripdata_{{year}}-{{month:02d}}.parquet"

# Taxi zone lookup
ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
ZONE_SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"

# Default output directory
DEFAULT_OUTPUT = Path(__file__).parent.parent / "raw" / "nyc-taxi"

# Approximate file sizes (MB) for progress estimation
APPROX_SIZE_MB = {
    "yellow": {"2023": 120, "2022": 130, "2021": 100, "2020": 60, "default": 150},
    "green": {"default": 15},
}


def download_file(url: str, output_path: Path, dry_run: bool = False) -> bool:
    """Download a file with progress reporting."""
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  SKIP {output_path.name} (already exists, {size_mb:.1f}MB)")
        return True

    if dry_run:
        print(f"  WOULD DOWNLOAD {url}")
        print(f"  TO {output_path}")
        return True

    print(f"  Downloading {output_path.name}...", end="", flush=True)
    start = time.time()

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def progress(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(100, block_num * block_size * 100 / total_size)
                mb = block_num * block_size / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                print(f"\r  Downloading {output_path.name}... {pct:.0f}% ({mb:.0f}/{total_mb:.0f}MB)", end="", flush=True)

        urlretrieve(url, str(output_path), reporthook=progress)
        elapsed = time.time() - start
        size_mb = output_path.stat().st_size / (1024 * 1024)
        speed = size_mb / elapsed if elapsed > 0 else 0
        print(f"\r  OK {output_path.name} ({size_mb:.1f}MB in {elapsed:.0f}s, {speed:.1f}MB/s)")
        return True

    except (URLError, HTTPError) as e:
        print(f"\r  FAIL {output_path.name}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def download_taxi_data(
    years: list[int],
    months: list[int] | None = None,
    output_dir: Path = DEFAULT_OUTPUT,
    taxi_types: list[str] | None = None,
    dry_run: bool = False,
    include_zones: bool = True,
) -> dict:
    """Download NYC taxi trip data for specified years and months."""
    if months is None:
        months = list(range(1, 13))

    if taxi_types is None:
        taxi_types = ["yellow"]

    templates = {
        "yellow": YELLOW_TEMPLATE,
        "green": GREEN_TEMPLATE,
        "fhv": FHV_TEMPLATE,
        "fhvhv": FHVHV_TEMPLATE,
    }

    stats = {"downloaded": 0, "skipped": 0, "failed": 0, "total_mb": 0}

    print(f"\n{'='*60}")
    print(f"NYC Taxi Data Downloader")
    print(f"{'='*60}")
    print(f"Years: {', '.join(map(str, years))}")
    print(f"Months: {', '.join(map(str, months))}")
    print(f"Types: {', '.join(taxi_types)}")
    print(f"Output: {output_dir}")
    if dry_run:
        print(f"MODE: DRY RUN (no files will be downloaded)")
    print(f"{'='*60}\n")

    # Download zone lookup first
    if include_zones:
        print("--- Taxi Zone Lookup ---")
        zone_csv = output_dir / "taxi_zone_lookup.csv"
        download_file(ZONE_LOOKUP_URL, zone_csv, dry_run)

        zone_shp = output_dir / "taxi_zones.zip"
        download_file(ZONE_SHAPEFILE_URL, zone_shp, dry_run)
        print()

    # Download trip data
    for taxi_type in taxi_types:
        template = templates.get(taxi_type)
        if not template:
            print(f"Unknown taxi type: {taxi_type}")
            continue

        for year in years:
            print(f"--- {taxi_type.upper()} Taxi {year} ---")
            for month in months:
                url = template.format(year=year, month=month)
                filename = f"{taxi_type}_tripdata_{year}-{month:02d}.parquet"
                output_path = output_dir / filename

                if output_path.exists():
                    stats["skipped"] += 1
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    stats["total_mb"] += size_mb
                    print(f"  SKIP {filename} ({size_mb:.1f}MB)")
                elif dry_run:
                    print(f"  WOULD DOWNLOAD {filename}")
                    stats["downloaded"] += 1
                else:
                    success = download_file(url, output_path, dry_run)
                    if success:
                        stats["downloaded"] += 1
                        if output_path.exists():
                            stats["total_mb"] += output_path.stat().st_size / (1024 * 1024)
                    else:
                        stats["failed"] += 1
            print()

    # Summary
    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"  Downloaded: {stats['downloaded']} files")
    print(f"  Skipped:    {stats['skipped']} files (already exist)")
    print(f"  Failed:     {stats['failed']} files")
    print(f"  Total size: {stats['total_mb']:.1f}MB ({stats['total_mb']/1024:.1f}GB)")
    print(f"{'='*60}\n")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Download NYC Taxi & Limousine Commission trip data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --years 2023                    # Download 2023 (~3.5GB)
  %(prog)s --years 2023 --months 1,2,3     # Download Jan-Mar 2023
  %(prog)s --years 2022,2023               # Download 2 years
  %(prog)s --all                           # Download everything (2009-2024, ~300GB)
  %(prog)s --years 2023 --type yellow,green # Yellow + green taxi
  %(prog)s --years 2023 --dry-run          # Show what would be downloaded
        """,
    )
    parser.add_argument("--years", type=str, help="Comma-separated years (e.g., 2022,2023)")
    parser.add_argument("--months", type=str, help="Comma-separated months (e.g., 1,2,3). Default: all 12")
    parser.add_argument("--type", type=str, default="yellow", help="Taxi types: yellow,green,fhv,fhvhv (default: yellow)")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help=f"Output directory (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--all", action="store_true", help="Download all years (2009-2024)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without downloading")
    parser.add_argument("--no-zones", action="store_true", help="Skip taxi zone lookup download")

    args = parser.parse_args()

    if args.all:
        years = list(range(2009, 2025))
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(",")]
    else:
        print("ERROR: Specify --years or --all")
        print("  Example: python download_nyc_taxi.py --years 2023")
        sys.exit(1)

    months = None
    if args.months:
        months = [int(m.strip()) for m in args.months.split(",")]

    taxi_types = [t.strip() for t in args.type.split(",")]
    output_dir = Path(args.output)

    download_taxi_data(
        years=years,
        months=months,
        output_dir=output_dir,
        taxi_types=taxi_types,
        dry_run=args.dry_run,
        include_zones=not args.no_zones,
    )


if __name__ == "__main__":
    main()
