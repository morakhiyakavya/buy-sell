import math
from typing import Dict, Any

def compute_category(data: Dict[str, Any], premium: float) -> Dict[str, Any]:
    """
    Compute all per‑category costings, totals and rate allocations.
    Expects data keys:
      SUB_1_FORMS, SUB_1_AVG_PRICE,
      SUB_2_FORMS, SUB_2_AVG_PRICE,
      SUB_3_FORMS, SUB_3_AVG_PRICE,
      LOT_SIZE, REQUIRED, EXPECTATION, RATES/MARGIN
    """
    # 1) Validate required fields
    for key in ("LOT_SIZE", "REQUIRED", "EXPECTATION", "RATES/MARGIN"):
        if data.get(key) is None:
            raise KeyError(f"{key} is required for this category")

    # 2) Total forms and individual costing
    total_forms = sum(data[f"SUB_{i}_FORMS"] for i in (1, 2, 3))
    costings = {
        f"sub_{i}_cost": data[f"SUB_{i}_FORMS"] * data[f"SUB_{i}_AVG_PRICE"]
        for i in (1, 2, 3)
    }

    # 3) Rate allocations
    sub_1_rate = round(
        premium * data["LOT_SIZE"] * data["REQUIRED"]
        / data["EXPECTATION"]
    )
    sub_2_rate = round(
        data["LOT_SIZE"] * (data["RATES/MARGIN"] / 100) * premium
    )

    return {
        "total_forms": total_forms,
        **costings,
        "sub_1_rate": sub_1_rate,
        "sub_2_rate": sub_2_rate,
    }


def make_calculation(
    company_data: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Runs compute_category for Retail, SHNI, HNI (with full costings),
    and handles SHARE purely as a total‑forms bucket.
    Aggregates into expected / pending shares & costs.
    """
    premium = company_data.get("premium", 1.0)

    # --- 1) Per‑category breakdown for costed groups ---
    costed_cats = ("Retail", "SHNI", "HNI")
    results_by_cat: Dict[str, Dict[str, Any]] = {}
    for cat in costed_cats:
        results_by_cat[cat] = compute_category(company_data[cat], premium)

    # --- 2) SHARE: totals only (no costings/rates) ---
    share = company_data.get("SHARE", {})
    share_total_forms = sum(share.get(f"SUB_{i}_FORMS", 0) for i in (1, 2, 3))
    results_by_cat["SHARE"] = {
        "total_forms": share_total_forms
    }

    # --- 3) Expected shares = sum of rounded allocations for Retail, SHNI, HNI ---
    expected_share = sum(
        math.ceil(
            results_by_cat[cat]["total_forms"]
            * company_data[cat]["LOT_SIZE"]
            * company_data[cat]["REQUIRED"]
            / company_data[cat]["EXPECTATION"]
        )
        for cat in costed_cats
    )

    # --- 4) Pending shares = SHARE total forms + expected_share ---
    pending_share = share_total_forms + expected_share

    # --- 5) Total costings (only Retail, SHNI, HNI) ---
    expected_total_cost = sum(
        sum(results_by_cat[cat][f"sub_{i}_cost"] for i in (1, 2, 3))
        for cat in costed_cats
    )
    # We have no share‑costs, so pending_total_cost = expected_total_cost
    pending_total_cost = expected_total_cost

    # --- 6) Cost per share ---
    expected_per_share_cost = expected_total_cost / expected_share
    pending_per_share_cost = pending_total_cost / pending_share

    return {
        "results_by_category": results_by_cat,
        "expected_share": expected_share,
        "pending_share": pending_share,
        "expected_total_cost": expected_total_cost,
        "pending_total_cost": pending_total_cost,
        "expected_per_share_cost": expected_per_share_cost,
        "pending_per_share_cost": pending_per_share_cost,
    }


if __name__ == "__main__":
    # === Example data (you can load this dict from Excel via pandas) ===
    company_data = {
        "Retail": {
            "SUB_1_FORMS":  5, "SUB_1_AVG_PRICE":  10,
            "SUB_2_FORMS":  0, "SUB_2_AVG_PRICE":   0,
            "SUB_3_FORMS":  0, "SUB_3_AVG_PRICE":   0,
            "LOT_SIZE":    63, "REQUIRED":     46782,
            "EXPECTATION": 800000, "RATES/MARGIN": 80,
        },
        "SHNI": {
            "SUB_1_FORMS":  0, "SUB_1_AVG_PRICE":   0,
            "SUB_2_FORMS":  0, "SUB_2_AVG_PRICE":   0,
            "SUB_3_FORMS":  0, "SUB_3_AVG_PRICE":   0,
            "LOT_SIZE":   882, "REQUIRED":      1671,
            "EXPECTATION":30000, "RATES/MARGIN": 80,
        },
        "HNI": {
            "SUB_1_FORMS":  0, "SUB_1_AVG_PRICE":   0,
            "SUB_2_FORMS":  0, "SUB_2_AVG_PRICE":   0,
            "SUB_3_FORMS":  0, "SUB_3_AVG_PRICE":   0,
            "LOT_SIZE":   882, "REQUIRED":      3342,
            "EXPECTATION":10000, "RATES/MARGIN": 80,
        },
        "SHARE": {
            "SUB_1_FORMS": 0, "SUB_1_AVG_PRICE": 0,
            "SUB_2_FORMS":  0, "SUB_2_AVG_PRICE": 0,
            "SUB_3_FORMS":  0, "SUB_3_AVG_PRICE": 0,
            # no LOT_SIZE, REQUIRED, etc.
        },
        "premium": 23
    }

    results = make_calculation(company_data)

    # Display
    print("=== Results by Category ===")
    for cat, rez in results["results_by_category"].items():
        print(f"{cat}: {rez}")
    print("\n=== Aggregates ===")
    print(f"Expected Shares:      {results['expected_share']}")
    print(f"Pending Shares:       {results['pending_share']}")
    print(f"Expected Total Cost:  {results['expected_total_cost']}")
    print(f"Pending Total Cost:   {results['pending_total_cost']}")
    print(f"Cost per Expected:    {results['expected_per_share_cost']:.2f}")
    print(f"Cost per Pending:     {results['pending_per_share_cost']:.2f}")
