from dataclasses import replace

from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.database import Database
from integration.agriweave_pipeline import AgriweavePipeline


def _build_pipeline_and_baseline():
    marketplace = MarketplaceService(
        database=Database("integration_demo.db")
    )

    pipeline = AgriweavePipeline(
        marketplace=marketplace,
        dry_run=True,
    )

    data = pipeline.get_market_data(crop="Tomato")
    demand = data["demands"][0]

    # The emergency backup is intentionally excluded from the
    # original planning pool.
    original_supplies = [
        supply
        for supply in data["supplies"]
        if supply.id != "SUP-DEMO-004"
    ]

    ai_result = pipeline.run_ai_matching(
        demand=demand,
        supplies=original_supplies,
    )

    selected = pipeline.select_supply_set(
        demand=demand,
        supplies=original_supplies,
        ai_result=ai_result,
    )

    optimization = pipeline.run_optimization(
        demand=demand,
        supplies=selected,
    )

    order = pipeline.build_order(
        demand=demand,
        supplies=selected,
        optimization=optimization,
    )

    return (
        pipeline,
        demand,
        selected,
        optimization,
        order,
        data["supplies"],
    )


def test_supply_rescue_recovers_full_shortfall():
    (
        pipeline,
        demand,
        selected,
        optimization,
        order,
        all_supplies,
    ) = _build_pipeline_and_baseline()

    result = pipeline.run_supply_rescue(
        demand=demand,
        order=order,
        supplies=selected,
        optimization=optimization,
        failed_supply_id="SUP-DEMO-001",
        replacement_supplies=all_supplies,
    )

    assert result["recovered"] is True
    assert result["decision"] == "RECOVERY_VERIFIED"
    assert result["failed_supply_id"] == "SUP-DEMO-001"
    assert result["failed_allocated_quantity_kg"] == 200.0
    assert result["shortfall_quantity_kg"] == 200.0
    assert result["verified_recovered_quantity_kg"] == 200.0
    assert result["recovery_ratio"] == 1.0
    assert result["replacement_supply_ids"] == ["SUP-DEMO-004"]
    assert result["errors"] == []


def test_supply_rescue_rejects_insufficient_recovery():
    (
        pipeline,
        demand,
        selected,
        optimization,
        _order,
        all_supplies,
    ) = _build_pipeline_and_baseline()

    # Provide only 150 kg of valid replacement capacity.
    backup = next(
        supply
        for supply in all_supplies
        if supply.id == "SUP-DEMO-004"
    )

    insufficient_backup = replace(
        backup,
        quantity_kg=150.0,
    )

    result = pipeline.run_supply_rescue(
        demand=demand,
        order=(
            pipeline.build_order(
                demand=demand,
                supplies=selected,
                optimization=optimization,
            )
        ),
        supplies=selected,
        optimization=optimization,
        failed_supply_id="SUP-DEMO-001",
        replacement_supplies=[insufficient_backup],
    )

    assert result["recovered"] is False
    assert result["decision"] == "RECOVERY_REJECTED"
    assert result["shortfall_quantity_kg"] == 200.0
    assert result["verified_recovered_quantity_kg"] == 150.0
    assert result["recovery_ratio"] == 0.75
    assert result["replacement_supply_ids"] == ["SUP-DEMO-004"]
