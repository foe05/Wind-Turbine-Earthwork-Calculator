"""
Cost Calculation API endpoints
"""
from fastapi import APIRouter, HTTPException
import logging

from app.schemas.cost import (
    MaterialBalanceRequest, MaterialBalanceResponse,
    CostCalculationRequest, CostCalculationResponse,
    CostRatesPreset
)

# Import shared modules (PYTHONPATH is set in docker-compose.yml)
from shared.core.material_balance import calculate_material_balance
from shared.core.costs import calculate_costs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/costs", tags=["Costs"])


@router.post("/material-balance", response_model=MaterialBalanceResponse)
async def calculate_material_balance_endpoint(request: MaterialBalanceRequest):
    """
    Calculate material balance

    Determines how much excavated material can be reused for fill,
    accounting for swell and compaction factors.
    """
    logger.info(
        f"Calculating material balance: "
        f"foundation={request.foundation_volume}m³, "
        f"cut={request.crane_cut}m³, fill={request.crane_fill}m³"
    )

    result = calculate_material_balance(
        foundation_volume=request.foundation_volume,
        crane_cut=request.crane_cut,
        crane_fill=request.crane_fill,
        swell_factor=request.swell_factor,
        compaction_factor=request.compaction_factor
    )

    logger.info(
        f"  → Available: {result['available']:.1f}m³, "
        f"Required: {result['required']:.1f}m³, "
        f"Surplus: {result['surplus']:.1f}m³, "
        f"Deficit: {result['deficit']:.1f}m³"
    )

    return MaterialBalanceResponse(**result)


@router.post("/calculate", response_model=CostCalculationResponse)
async def calculate_costs_endpoint(request: CostCalculationRequest):
    """
    Calculate detailed earthwork costs

    Includes:
    - Excavation costs
    - Transport costs
    - Fill material costs
    - Gravel layer costs
    - Compaction costs
    - Savings from material reuse
    """
    logger.info("=" * 70)
    logger.info("Cost Calculation")
    logger.info("=" * 70)
    logger.info(f"Foundation: {request.foundation_volume:.1f} m³")
    logger.info(f"Crane Cut: {request.crane_cut:.1f} m³")
    logger.info(f"Crane Fill: {request.crane_fill:.1f} m³")
    logger.info(f"Platform Area: {request.platform_area:.1f} m²")
    logger.info(f"Material Reuse: {request.material_reuse}")

    # Calculate material balance if not provided
    if request.material_balance is None:
        material_balance_result = calculate_material_balance(
            foundation_volume=request.foundation_volume,
            crane_cut=request.crane_cut,
            crane_fill=request.crane_fill,
            swell_factor=request.swell_factor,
            compaction_factor=request.compaction_factor
        )
    else:
        # Use provided material balance
        material_balance_result = {
            'available': request.material_balance.available,
            'required': request.material_balance.required,
            'surplus': request.material_balance.surplus,
            'deficit': request.material_balance.deficit,
            'reused': request.material_balance.reused
        }

    # Calculate costs
    cost_result = calculate_costs(
        foundation_volume=request.foundation_volume,
        crane_cut=request.crane_cut,
        crane_fill=request.crane_fill,
        platform_area=request.platform_area,
        material_balance=material_balance_result,
        material_reuse=request.material_reuse,
        swell_factor=request.swell_factor,
        compaction_factor=request.compaction_factor,
        cost_excavation=request.cost_excavation,
        cost_transport=request.cost_transport,
        cost_fill_import=request.cost_fill_import,
        cost_gravel=request.cost_gravel,
        cost_compaction=request.cost_compaction,
        gravel_thickness=request.gravel_thickness
    )

    logger.info("\nCost Breakdown:")
    logger.info(f"  Excavation:  {cost_result['cost_excavation']:>10,.2f} €")
    logger.info(f"  Transport:   {cost_result['cost_transport']:>10,.2f} €")
    logger.info(f"  Fill:        {cost_result['cost_fill']:>10,.2f} €")
    logger.info(f"  Gravel:      {cost_result['cost_gravel']:>10,.2f} €")
    logger.info(f"  Compaction:  {cost_result['cost_compaction']:>10,.2f} €")
    logger.info(f"  {'─' * 40}")
    logger.info(f"  TOTAL:       {cost_result['cost_total']:>10,.2f} €")
    logger.info(f"  Savings:     {cost_result['cost_saving']:>10,.2f} € ({cost_result['saving_pct']:.1f}%)")
    logger.info("=" * 70 + "\n")

    return CostCalculationResponse(
        cost_total=cost_result['cost_total'],
        cost_excavation=cost_result['cost_excavation'],
        cost_transport=cost_result['cost_transport'],
        cost_fill=cost_result['cost_fill'],
        cost_gravel=cost_result['cost_gravel'],
        cost_compaction=cost_result['cost_compaction'],
        cost_saving=cost_result['cost_saving'],
        saving_pct=cost_result['saving_pct'],
        gravel_vol=cost_result['gravel_vol'],
        cost_total_without_reuse=cost_result['cost_total_without_reuse'],
        cost_total_with_reuse=cost_result['cost_total_with_reuse'],
        material_balance=MaterialBalanceResponse(**material_balance_result)
    )


@router.get("/presets", response_model=list[CostRatesPreset])
async def get_cost_presets():
    """
    Get predefined cost rate presets

    Returns common cost rate scenarios for quick selection.
    """
    presets = [
        CostRatesPreset(
            name="standard",
            description="Standard-Kosten (Deutschland, Durchschnitt)",
            cost_excavation=8.0,
            cost_transport=12.0,
            cost_fill_import=15.0,
            cost_gravel=25.0,
            cost_compaction=5.0,
            gravel_thickness=0.5
        ),
        CostRatesPreset(
            name="low",
            description="Niedrige Kosten (günstige Region)",
            cost_excavation=6.0,
            cost_transport=9.0,
            cost_fill_import=12.0,
            cost_gravel=20.0,
            cost_compaction=4.0,
            gravel_thickness=0.5
        ),
        CostRatesPreset(
            name="high",
            description="Hohe Kosten (teure Region, schwieriges Gelände)",
            cost_excavation=12.0,
            cost_transport=18.0,
            cost_fill_import=22.0,
            cost_gravel=35.0,
            cost_compaction=7.0,
            gravel_thickness=0.5
        ),
        CostRatesPreset(
            name="premium",
            description="Premium-Kosten (große Entfernungen, spezielle Anforderungen)",
            cost_excavation=15.0,
            cost_transport=25.0,
            cost_fill_import=30.0,
            cost_gravel=45.0,
            cost_compaction=10.0,
            gravel_thickness=0.6
        )
    ]

    return presets
