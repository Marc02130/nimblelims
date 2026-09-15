from models.wrappers import (
    WRAPPER_CATALOG,
    wrapper_at_capacity_detail,
    wrapper_id_for_key,
    wrapper_mate_key,
    wrapper_over_capacity_id,
    wrapper_role_taken,
)


def test_aliquot_pool_wrapper_is_cardinality_one_pair():
    spec = WRAPPER_CATALOG["aliquot_pool"]
    assert spec["keys"] == ("aliquot_pool_plan", "aliquots_pools")
    assert spec["cardinality"] == 1
    assert spec["atomic_pair"] is True
    assert spec["mint"] is True
    assert spec["source_from"] == "start_cohort"


def test_wrapper_mate_and_lookup():
    assert wrapper_id_for_key("aliquot_pool_plan") == "aliquot_pool"
    assert wrapper_mate_key("aliquot_pool_plan") == "aliquots_pools"
    assert wrapper_mate_key("aliquots_pools") == "aliquot_pool_plan"
    assert wrapper_mate_key("experiment_header") is None


def test_wrapper_capacity_one_pair_ok_two_plans_not():
    assert (
        wrapper_over_capacity_id(["aliquot_pool_plan", "aliquots_pools"]) is None
    )
    assert (
        wrapper_over_capacity_id(
            ["aliquot_pool_plan", "aliquot_pool_plan", "aliquots_pools"]
        )
        == "aliquot_pool"
    )
    assert wrapper_role_taken(
        "aliquot_pool_plan", ["aliquot_pool_plan", "aliquots_pools"]
    )
    assert not wrapper_role_taken("aliquot_pool_plan", ["aliquots_pools"])


def test_wrapper_at_capacity_detail_shape():
    detail = wrapper_at_capacity_detail("aliquot_pool")
    assert detail["code"] == "wrapper_at_capacity"
    assert detail["wrapper_id"] == "aliquot_pool"
    assert "Aliquot/pool" in detail["message"]
