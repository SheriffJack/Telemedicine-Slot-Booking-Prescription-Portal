import pytest
from amusement_park_ride_access import process_ride_admissions, inspect_safety_restraints


def make_group(ride_type="family", patrons=None, is_open=True, fast_lane=False):
    return {
        "is_open": is_open,
        "ride_type": ride_type,
        "has_fast_lane": fast_lane,
        "patrons": patrons if patrons is not None else [],
    }


def make_patron(height_cm=150, health_warning=False, is_child=False):
    return {"height_cm": height_cm, "health_warning": health_warning, "is_child": is_child}


# ---------- process_ride_admissions: input validation ----------

def test_single_adult_family_ride():
    groups = [make_group("family", [make_patron()])]
    result = process_ride_admissions(groups, 5.0)
    assert result["total_revenue"] == 10.0
    assert result["status"] == "COMPLETED"


def test_groups_not_a_list_raises():
    with pytest.raises(ValueError):
        process_ride_admissions("not a list", 5.0)


def test_negative_fee_raises():
    with pytest.raises(ValueError):
        process_ride_admissions([], -1.0)


def test_zero_fee_is_valid():
    assert process_ride_admissions([], 0.0)["status"] == "ZERO_ADMISSIONS"


def test_empty_groups_list():
    assert process_ride_admissions([], 5.0) == {"total_revenue": 0.0, "status": "ZERO_ADMISSIONS"}


# ---------- group-level branches ----------

def test_closed_group_is_skipped():
    groups = [make_group(is_open=False, patrons=[make_patron()]), make_group("family", [make_patron()])]
    assert process_ride_admissions(groups, 5.0) == {"total_revenue": 10.0, "status": "COMPLETED"}


def test_group_missing_keys_uses_defaults():
    # no "is_open" key -> treated as closed
    assert process_ride_admissions([{}], 5.0)["status"] == "ZERO_ADMISSIONS"


def test_ride_type_defaults_to_family():
    group = {"is_open": True, "patrons": [make_patron()]}
    assert process_ride_admissions([group], 5.0)["total_revenue"] == 10.0


def test_roller_coaster_adult():
    assert process_ride_admissions([make_group("roller_coaster", [make_patron()])], 5.0)["total_revenue"] == 25.0


def test_water_ride_adult():
    assert process_ride_admissions([make_group("water_ride", [make_patron()])], 5.0)["total_revenue"] == 18.0


def test_unknown_ride_type_rejected_and_skipped():
    groups = [make_group("bumper_cars", [make_patron()]), make_group("family", [make_patron()])]
    assert process_ride_admissions(groups, 5.0) == {"total_revenue": 10.0, "status": "COMPLETED"}


def test_group_with_no_patrons():
    assert process_ride_admissions([make_group("family", [])], 5.0)["status"] == "ZERO_ADMISSIONS"


def test_group_with_no_patrons_but_fast_lane_still_charges_fee():
    result = process_ride_admissions([make_group("family", [], fast_lane=True)], 5.0)
    assert result == {"total_revenue": 5.0, "status": "COMPLETED"}


# ---------- patron-level branches ----------

@pytest.mark.parametrize("height", [0, -10])
def test_non_positive_height_rejected(height):
    result = process_ride_admissions([make_group("family", [make_patron(height_cm=height)])], 5.0)
    assert result["status"] == "ZERO_ADMISSIONS"


def test_height_119_rejected_but_120_accepted():
    assert process_ride_admissions([make_group("family", [make_patron(height_cm=119)])], 5.0)["status"] == "ZERO_ADMISSIONS"
    assert process_ride_admissions([make_group("family", [make_patron(height_cm=120)])], 5.0)["total_revenue"] == 10.0


def test_missing_patron_fields_use_defaults():
    # no height -> 0 -> rejected
    result = process_ride_admissions([make_group("family", [{}])], 5.0)
    assert result["status"] == "ZERO_ADMISSIONS"


def test_child_discount_family():
    result = process_ride_admissions([make_group("family", [make_patron(is_child=True)])], 5.0)
    assert result["total_revenue"] == pytest.approx(6.0)


def test_child_discount_roller_coaster():
    result = process_ride_admissions([make_group("roller_coaster", [make_patron(is_child=True)])], 5.0)
    assert result["total_revenue"] == pytest.approx(15.0)


def test_health_warning_family_only_rejects_that_patron():
    patrons = [make_patron(health_warning=True), make_patron()]
    result = process_ride_admissions([make_group("family", patrons)], 5.0)
    assert result == {"total_revenue": 10.0, "status": "COMPLETED"}


def test_health_warning_water_ride_only_rejects_that_patron():
    patrons = [make_patron(), make_patron(health_warning=True)]
    result = process_ride_admissions([make_group("water_ride", patrons)], 5.0)
    assert result == {"total_revenue": 18.0, "status": "COMPLETED"}


def test_health_warning_roller_coaster_voids_whole_group():
    patrons = [make_patron(), make_patron(health_warning=True), make_patron()]
    result = process_ride_admissions([make_group("roller_coaster", patrons)], 5.0)
    assert result == {"total_revenue": 0.0, "status": "ZERO_ADMISSIONS"}


def test_health_warning_roller_coaster_with_fast_lane_still_pays_fee():
    patrons = [make_patron(health_warning=True)]
    result = process_ride_admissions([make_group("roller_coaster", patrons, fast_lane=True)], 5.0)
    assert result == {"total_revenue": 5.0, "status": "COMPLETED"}


# ---------- fast lane ----------

def test_fast_lane_fee_added():
    result = process_ride_admissions([make_group("family", [make_patron()], fast_lane=True)], 5.0)
    assert result["total_revenue"] == 15.0


def test_no_fast_lane_no_fee():
    result = process_ride_admissions([make_group("family", [make_patron()], fast_lane=False)], 5.0)
    assert result["total_revenue"] == 10.0


# ---------- final status branches ----------

def test_exactly_four_rejections_is_not_audit():
    patrons = [make_patron(height_cm=100) for _ in range(4)] + [make_patron()]
    result = process_ride_admissions([make_group("family", patrons)], 5.0)
    assert result == {"total_revenue": 10.0, "status": "COMPLETED"}


def test_five_rejections_triggers_safety_audit():
    patrons = [make_patron(height_cm=100) for _ in range(5)] + [make_patron()]
    result = process_ride_admissions([make_group("family", patrons)], 5.0)
    assert result == {"total_revenue": 10.0, "status": "SAFETY_AUDIT"}


def test_rejections_accumulate_across_groups():
    groups = [make_group("bumper_cars"), make_group("bumper_cars"), make_group("bumper_cars"),
              make_group("family", [make_patron(height_cm=100), make_patron(height_cm=100)])]
    assert process_ride_admissions(groups, 5.0)["status"] == "SAFETY_AUDIT"


def test_zero_revenue_status():
    result = process_ride_admissions([make_group("family", [make_patron(height_cm=50)])], 5.0)
    assert result == {"total_revenue": 0.0, "status": "ZERO_ADMISSIONS"}


def test_revenue_is_rounded_to_two_decimals():
    result = process_ride_admissions([make_group("water_ride", [make_patron(is_child=True)] * 3)], 0.0)
    assert result["total_revenue"] == 32.4


# ---------- inspect_safety_restraints ----------

@pytest.mark.parametrize("streams", [[], None])
def test_restraints_no_data(streams):
    assert inspect_safety_restraints(streams) == "NO_DATA"


def test_restraints_two_consecutive_unlatched_locks():
    assert inspect_safety_restraints([[1, 0, 0]]) == "EMERGENCY_LOCK"


def test_restraints_single_unlatched_is_safe():
    assert inspect_safety_restraints([[1, 0, 1]]) == "SAFE"


def test_restraints_streak_resets_after_latched():
    assert inspect_safety_restraints([[0, 1, 0, 1, 0]]) == "SAFE"


def test_restraints_streak_does_not_carry_between_streams():
    assert inspect_safety_restraints([[1, 0], [0, 1]]) == "SAFE"


def test_restraints_lock_found_in_later_stream():
    assert inspect_safety_restraints([[1, 1], [1, 0, 0]]) == "EMERGENCY_LOCK"


def test_restraints_empty_sensor_stream():
    assert inspect_safety_restraints([[]]) == "SAFE"


def test_restraints_all_latched():
    assert inspect_safety_restraints([[1, 1, 1], [1, 1]]) == "SAFE"
