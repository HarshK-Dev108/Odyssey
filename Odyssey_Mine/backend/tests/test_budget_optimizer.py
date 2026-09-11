from app.ai.optimizer.budget_optimizer import BudgetOptimizer


def option(name, option_type, price, rating=3, interests=None, **extra):
    value = {
        "name": name,
        "type": option_type,
        "price": price,
        "rating": rating,
        "interests": interests or [],
    }
    value.update(extra)
    return value


def recommendations(options, scores=None):
    scores = scores or [0] * len(options)
    return [{"option": item, "score": score} for item, score in zip(options, scores)]


def test_initial_package_is_unique_budget_aware_and_explainable():
    optimizer = BudgetOptimizer()
    items = [
        option("Hotel A", "hotel", 4000, rating=4),
        option("Hotel Duplicate", "hotel", 3000, rating=3),
        option("Flight", "flight", 2000),
        option("Adventure", "activity", 1000, interests=["adventure"]),
        option("Food", "food", 500),
        option("Transport", "transport", 400),
    ]
    result = optimizer.optimize(
        recommendations(items, [30, 20, 25, 24, 10, 9]),
        budget=7000,
        interests=["adventure"],
        hotel_rating=4,
        pace="moderate",
        days=2,
    )
    selected = result["selected_options"]
    assert sum(item["type"] == "hotel" for item in selected) <= 1
    assert len({(item["name"], item["type"]) for item in selected}) == len(selected)
    assert result["total_cost"] <= 7000
    assert result["optimization_reason"]
    assert result["alternatives_considered"] == 6


def test_make_cheaper_prefers_exact_substitution():
    optimizer = BudgetOptimizer()
    current = [option("Hotel A", "hotel", 40000), option("Activity A", "activity", 8000)]
    alternatives = current + [option("Hotel B", "hotel", 30000)]
    result = optimizer.make_cheaper(current, 10000, alternatives, budget=50000)
    assert result["saving"] == 10000
    assert {item["name"] for item in result["selected_options"]} == {"Hotel B", "Activity A"}
    assert "substitution" in result["optimization_reason"]


def test_make_cheaper_can_substitute_an_activity():
    optimizer = BudgetOptimizer()
    current = [option("Adventure Premium", "activity", 8000, interests=["adventure"])]
    alternatives = current + [option("Adventure Value", "activity", 3000, interests=["adventure"])]
    result = optimizer.make_cheaper(current, 5000, alternatives, budget=8000)
    assert result["saving"] == 5000
    assert result["selected_options"][0]["name"] == "Adventure Value"


def test_make_cheaper_returns_closest_valid_saving_and_never_overruns():
    optimizer = BudgetOptimizer()
    current = [option("Hotel A", "hotel", 40000), option("Activity A", "activity", 8000)]
    result = optimizer.make_cheaper(current, 10000, [], budget=48000)
    assert result["saving"] == 8000
    assert result["new_cost"] == 40000
    assert result["new_cost"] <= 48000


def test_hotel_upgrade_respects_budget_and_current_plan():
    optimizer = BudgetOptimizer()
    current = [option("Current Hotel", "hotel", 30000, rating=3), option("Activity", "activity", 5000)]
    available = [option("Better Hotel", "hotel", 35000, rating=4)]
    upgraded = optimizer.upgrade_hotel(current, available, budget=70000)
    assert upgraded["success"] is True
    assert upgraded["new_hotel"]["name"] == "Better Hotel"
    assert upgraded["new_cost"] == 40000

    rejected = optimizer.upgrade_hotel(current, available, budget=34000)
    assert rejected["success"] is False
    assert rejected["selected_options"] == current


def test_pace_limits_activities_and_crowd_metadata_is_used_only_when_present():
    optimizer = BudgetOptimizer()
    items = [
        option("Quiet Activity", "activity", 100, rating=3, interests=["nature"], crowd_level="low"),
        option("Crowded Activity", "activity", 100, rating=5, interests=["nature"], crowd_level="high"),
        option("Third Activity", "activity", 100, rating=4, interests=["nature"]),
    ]
    relaxed = optimizer.optimize(
        recommendations(items, [10, 30, 20]),
        budget=1000,
        interests=["nature"],
        avoid_crowds=True,
        pace="relaxed",
        days=1,
    )
    assert len(relaxed["selected_options"]) == 1
    assert relaxed["selected_options"][0]["name"] == "Quiet Activity"

    active = optimizer.optimize(
        recommendations(items, [10, 30, 20]),
        budget=1000,
        interests=["nature"],
        pace="active",
        days=2,
    )
    assert len(active["selected_options"]) == 3