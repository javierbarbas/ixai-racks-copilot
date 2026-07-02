"""Genera calendario ISO 2026 para conversion Semana -> Fecha lunes."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import csv

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "Calendario_Produccion_2026.csv"


def iso_monday(year: int, week: int) -> date:
    return date.fromisocalendar(year, week, 1)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Semana", "Año", "Fecha_Lunes_Inicio"])
        for week in range(1, 54):
            monday = iso_monday(2026, week)
            writer.writerow([week, 2026, monday.isoformat()])
    print(f"Calendario generado: {OUT_PATH}")


if __name__ == "__main__":
    main()
