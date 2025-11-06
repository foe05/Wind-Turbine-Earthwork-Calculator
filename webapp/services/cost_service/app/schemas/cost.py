"""
Pydantic schemas for cost service
"""
from pydantic import BaseModel, Field
from typing import Optional


class MaterialBalanceRequest(BaseModel):
    """Request for material balance calculation"""
    foundation_volume: float = Field(..., ge=0, description="Fundament-Aushub in m³")
    crane_cut: float = Field(..., ge=0, description="Kranflächen-Aushub in m³")
    crane_fill: float = Field(..., ge=0, description="Kranflächen-Auftrag in m³")
    swell_factor: float = Field(1.25, gt=1.0, le=2.0, description="Auflockerungsfaktor")
    compaction_factor: float = Field(0.85, gt=0.5, lt=1.0, description="Verdichtungsfaktor")


class MaterialBalanceResponse(BaseModel):
    """Response with material balance"""
    available: float = Field(..., description="Verfügbares Material (aufgelockert) in m³")
    required: float = Field(..., description="Benötigtes Material (anstehend) in m³")
    surplus: float = Field(..., description="Überschuss in m³")
    deficit: float = Field(..., description="Mangel in m³")
    reused: float = Field(..., description="Wiederverwendetes Material in m³")


class CostCalculationRequest(BaseModel):
    """Request for cost calculation"""
    foundation_volume: float = Field(..., ge=0, description="Fundament-Aushub in m³")
    crane_cut: float = Field(..., ge=0, description="Kranflächen-Aushub in m³")
    crane_fill: float = Field(..., ge=0, description="Kranflächen-Auftrag in m³")
    platform_area: float = Field(..., ge=0, description="Plattformfläche in m²")

    # Material balance (can be pre-computed or will be computed)
    material_balance: Optional[MaterialBalanceResponse] = Field(None, description="Vorberechnete Material-Bilanz")

    # Options
    material_reuse: bool = Field(True, description="Material-Wiederverwendung aktiv")
    swell_factor: float = Field(1.25, gt=1.0, le=2.0, description="Auflockerungsfaktor")
    compaction_factor: float = Field(0.85, gt=0.5, lt=1.0, description="Verdichtungsfaktor")

    # Cost rates (€/m³ or €/m²)
    cost_excavation: float = Field(8.0, ge=0, description="Kosten Aushub (€/m³)")
    cost_transport: float = Field(12.0, ge=0, description="Kosten Transport (€/m³)")
    cost_fill_import: float = Field(15.0, ge=0, description="Kosten Material-Einkauf (€/m³)")
    cost_gravel: float = Field(25.0, ge=0, description="Kosten Schotter (€/m³)")
    cost_compaction: float = Field(5.0, ge=0, description="Kosten Verdichtung (€/m³)")
    gravel_thickness: float = Field(0.5, gt=0, le=2.0, description="Schotterschicht-Dicke (m)")


class CostCalculationResponse(BaseModel):
    """Response with cost breakdown"""
    # Total
    cost_total: float = Field(..., description="Gesamtkosten (€)")

    # By category
    cost_excavation: float = Field(..., description="Kosten Aushub (€)")
    cost_transport: float = Field(..., description="Kosten Transport (€)")
    cost_fill: float = Field(..., description="Kosten Auftrag/Einkauf (€)")
    cost_gravel: float = Field(..., description="Kosten Schotter (€)")
    cost_compaction: float = Field(..., description="Kosten Verdichtung (€)")

    # Savings
    cost_saving: float = Field(..., description="Einsparung durch Wiederverwendung (€)")
    saving_pct: float = Field(..., description="Einsparung in Prozent")

    # Gravel volume
    gravel_vol: float = Field(..., description="Schottervolumen (m³)")

    # Comparison
    cost_total_without_reuse: float = Field(..., description="Kosten ohne Wiederverwendung (€)")
    cost_total_with_reuse: float = Field(..., description="Kosten mit Wiederverwendung (€)")

    # Material balance (included)
    material_balance: MaterialBalanceResponse = Field(..., description="Material-Bilanz")


class CostRatesPreset(BaseModel):
    """Predefined cost rate presets"""
    name: str = Field(..., description="Preset name")
    description: str = Field(..., description="Preset description")
    cost_excavation: float
    cost_transport: float
    cost_fill_import: float
    cost_gravel: float
    cost_compaction: float
    gravel_thickness: float
