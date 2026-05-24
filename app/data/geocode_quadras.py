from __future__ import annotations

import csv
import re
from pathlib import Path
from time import sleep

from geopy.exc import GeocoderRateLimited, GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim

from app.data.seed import find_csv_path, get_row_value


def build_queries(row: dict[str, str]) -> list[str]:
    name = get_row_value(row, "NOME").strip()
    address = get_row_value(row, "ENDERECO", "ENDERECO").strip()
    clean_address = re.sub(r"\s*-\s*PE", ", Pernambuco", address)
    clean_address = re.sub(r",?\s*\d{5}-?\d{3}", "", clean_address).strip()
    expanded_address = (
        clean_address.replace("Av.", "Avenida")
        .replace("Gov.", "Governador")
        .replace("Dr.", "Doutor")
    )
    city = clean_address.split(",")[-2].strip() if "," in clean_address else ""
    return [
        f"{name}, {clean_address}, Brasil",
        f"{clean_address}, Brasil",
        f"{expanded_address}, Brasil",
        f"{name}, {city}, Pernambuco, Brasil" if city else f"{name}, Pernambuco, Brasil",
    ]


def geocode_row(geolocator: Nominatim, row: dict[str, str]) -> str | None:
    for query in build_queries(row):
        for attempt in range(3):
            try:
                location = geolocator.geocode(
                    query,
                    timeout=15,
                    country_codes="br",
                    addressdetails=False,
                )
                if location:
                    return f"{location.latitude:.8f}, {location.longitude:.8f}"
                break
            except GeocoderRateLimited:
                sleep(10)
                break
            except (GeocoderTimedOut, GeocoderUnavailable):
                if attempt == 2:
                    break
                sleep(1.5)

    return None


def geocode_csv() -> None:
    csv_path = find_csv_path()
    if not csv_path:
        raise FileNotFoundError("Quadras.csv nao encontrado.")

    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "LAT LONG" not in fieldnames:
        fieldnames.append("LAT LONG")

    geolocator = Nominatim(user_agent="jogayjoga_quadras_geocoder")
    updated = 0
    missing = 0

    for row in rows:
        if get_row_value(row, "LAT LONG").strip():
            continue

        lat_long = geocode_row(geolocator, row)
        if lat_long:
            row["LAT LONG"] = lat_long
            updated += 1
            print(f"OK  {get_row_value(row, 'NOME')}: {lat_long}")
        else:
            missing += 1
            print(f"SEM {get_row_value(row, 'NOME')}")

        sleep(1.1)

    write_csv(csv_path, fieldnames, rows)
    print(f"{updated} coordenadas preenchidas.")
    print(f"{missing} locais sem resultado.")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    geocode_csv()
