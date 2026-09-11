from app.ai.itinerary.itinerary_generator import ItineraryGenerator


def activity(name, score, interests=None, **extra):
    value = {
        "name": name,
        "type": "activity",
        "price": 100,
        "ai_score": score,
        "interests": interests or [],
    }
    value.update(extra)
    return value


def test_itinerary_respects_pace_and_avoids_duplicates():
    generator = ItineraryGenerator()
    activities = [
        activity("A", 10),
        activity("A", 9),
        activity("B", 8),
        activity("C", 7),
    ]

    relaxed = generator.generate(activities, days=2, pace="relaxed")
    assert [len(day["activities"]) for day in relaxed] == [1, 1]
    assert sum(len(day["activities"]) for day in relaxed) == 2

    active = generator.generate(activities, days=2, pace="active")
    assert [len(day["activities"]) for day in active] == [2, 1]
    assert {item["name"] for day in active for item in day["activities"]} == {"A", "B", "C"}


def test_itinerary_prefers_interests_and_applies_known_weather_only():
    generator = ItineraryGenerator()
    activities = [
        activity("Indoor", 5, ["food"], outdoor=False),
        activity("Outdoor", 20, ["adventure"], outdoor=True),
    ]
    itinerary = generator.generate(
        activities,
        days=1,
        interests=["food"],
        weather_by_day={1: {"condition": "Heavy rain", "poor_conditions": True}},
    )
    assert itinerary[0]["activities"][0]["name"] == "Indoor"
    assert itinerary[0]["metadata"]["weather_used"] is True
    assert itinerary[0]["metadata"]["weather_adjusted"] is False


def test_itinerary_uses_crowd_metadata_without_inventing_it():
    generator = ItineraryGenerator()
    itinerary = generator.generate(
        [
            activity("Busy", 20, crowd_level="high"),
            activity("Quiet", 10, crowd_level="low"),
        ],
        days=1,
        avoid_crowds=True,
    )
    assert itinerary[0]["activities"][0]["name"] == "Quiet"
    assert itinerary[0]["metadata"]["crowd_data_used"] is True

    without_data = generator.generate(
        [activity("Unknown crowd", 20)],
        days=1,
        avoid_crowds=True,
    )
    assert without_data[0]["metadata"]["crowd_data_used"] is False