"""Variantenvergleich (1:1-Port aus core/variant_comparison.py)."""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class Variant:
    label: str
    crane_height_m: float = 0.0
    total_cut_m3: float = 0.0
    total_fill_m3: float = 0.0
    gravel_m3: float = 0.0
    total_cost_eur: float = 0.0
    total_co2_kg: float = 0.0
    notes: str = ""

    @property
    def total_volume_moved_m3(self) -> float:
        return self.total_cut_m3 + self.total_fill_m3

    @property
    def net_volume_m3(self) -> float:
        return self.total_cut_m3 - self.total_fill_m3


_METRICS: list = [
    ("Kranstellflächen-Höhe", lambda v: v.crane_height_m, " m", None, 2),
    ("Gesamt-Abtrag", lambda v: v.total_cut_m3, " m³", None, 0),
    ("Gesamt-Auftrag", lambda v: v.total_fill_m3, " m³", None, 0),
    ("Erdbewegung gesamt", lambda v: v.total_volume_moved_m3, " m³", True, 0),
    ("Netto-Bilanz (Cut−Fill)", lambda v: v.net_volume_m3, " m³", None, 0),
    ("Externer Schotter", lambda v: v.gravel_m3, " m³", True, 0),
    ("Geschätzte Kosten", lambda v: v.total_cost_eur, " €", True, 0),
    ("CO₂e", lambda v: v.total_co2_kg, " kg", True, 0),
]


class VariantComparisonReport:
    def __init__(self, variants: Sequence[Variant]):
        if not variants:
            raise ValueError("at least one variant is required")
        self.variants = list(variants)

    def best_variant(self, metric: str = "total_volume_moved_m3") -> Variant:
        return min(self.variants, key=lambda v: getattr(v, metric))

    def to_html(self, project_name: str = "Variantenvergleich") -> str:
        title = html.escape(project_name, quote=True)
        when = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        header_cells = "".join(
            f'<th>{html.escape(v.label, quote=True)}</th>' for v in self.variants
        )
        rows = []
        for label, accessor, unit, lower_is_better, places in _METRICS:
            values = [accessor(v) for v in self.variants]
            best_idx = None
            if lower_is_better and len(values) > 1:
                best_idx = min(range(len(values)), key=lambda i: values[i])
            cells = []
            for i, val in enumerate(values):
                formatted = f"{val:,.{places}f}{unit}"
                style = ' style="font-weight: bold; background: #e8f5e9;"' if i == best_idx else ""
                cells.append(f"<td{style}>{formatted}</td>")
            rows.append(f"<tr><th>{html.escape(label)}</th>{''.join(cells)}</tr>")

        notes_row = ""
        if any(v.notes for v in self.variants):
            notes_cells = "".join(f'<td>{html.escape(v.notes)}</td>' for v in self.variants)
            notes_row = f"<tr><th>Notizen</th>{notes_cells}</tr>"

        rows_html = "\n".join(rows + ([notes_row] if notes_row else []))
        return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><title>{title}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2rem; color: #222; }}
  h1 {{ color: #335; }}
  table {{ border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ border: 1px solid #ccc; padding: 0.5rem 0.8rem; text-align: right; }}
  thead th, tbody th {{ background: #f4f4f4; text-align: left; }}
</style></head><body>
<h1>{title}</h1>
<p>Erstellt am {when}. Beste Werte pro Zeile sind grün hinterlegt.</p>
<table>
  <thead><tr><th>Kennwert</th>{header_cells}</tr></thead>
  <tbody>
{rows_html}
  </tbody>
</table>
</body></html>
"""

    def write(self, path: str, project_name: str = "Variantenvergleich") -> str:
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(self.to_html(project_name=project_name))
        return abs_path
