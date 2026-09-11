class ItineraryGenerator:
    """
    Generates a day-wise itinerary without repeating activities
    unnecessarily.
    """

    def generate(
        self,
        activities,
        days,
        pace="moderate",
        interests=None,
        avoid_crowds=False,
        weather_by_day=None,
    ):
        itinerary = []

        if days <= 0:
            return itinerary

        activity_list = []
        seen = set()
        for activity in activities:
            if activity.get("type") != "activity":
                continue
            key = activity.get("source_id") or activity.get("name")
            if key in seen:
                continue
            seen.add(key)
            activity_list.append(activity)

        interest_values = {
            str(interest).casefold() for interest in (interests or [])
        }
        if interest_values:
            activity_list.sort(
                key=lambda activity: (
                    not bool(
                        interest_values.intersection(
                            str(value).casefold()
                            for value in activity.get("interests", [])
                        )
                    ),
                    -activity.get("ai_score", 0),
                    str(activity.get("name", "")),
                )
            )
        else:
            activity_list.sort(
                key=lambda activity: (
                    -activity.get("ai_score", 0),
                    str(activity.get("name", "")),
                )
            )

        pace_key = (pace or "moderate").casefold()
        activities_per_day = {
            "relaxed": 1,
            "moderate": 1,
            "active": 2,
        }.get(pace_key, 1)

        if avoid_crowds:
            with_crowd_data = [
                activity for activity in activity_list
                if activity.get("crowd_level") is not None
                or activity.get("crowd_score") is not None
            ]
            if with_crowd_data:
                activity_list = sorted(
                    activity_list,
                    key=lambda activity: (
                        activity.get("crowd_level", "") not in {"low", "quiet"},
                        activity.get("crowd_score", 0),
                    ),
                )

        weather_by_day = weather_by_day or {}
        weather_used = bool(weather_by_day)
        weather_adjusted = False

        cursor = 0

        for day in range(1, days + 1):
            day_weather = weather_by_day.get(day)
            selected_for_day = []
            while cursor < len(activity_list) and len(selected_for_day) < activities_per_day:
                candidate = activity_list[cursor]
                cursor += 1
                if day_weather and day_weather.get("poor_conditions"):
                    outdoor = candidate.get("outdoor", candidate.get("is_outdoor"))
                    if outdoor is True:
                        weather_adjusted = True
                        continue
                selected_for_day.append(candidate)

            entry = {"day": day, "activities": selected_for_day}
            if not selected_for_day:
                entry["note"] = "Rest / Free Day"
            if day_weather:
                entry["weather"] = day_weather
            itinerary.append(entry)

        metadata = {
            "weather_used": weather_used,
            "weather_adjusted": weather_adjusted,
            "crowd_data_used": bool(
                avoid_crowds and any(
                    activity.get("crowd_level") is not None
                    or activity.get("crowd_score") is not None
                    for activity in activity_list
                )
            ),
            "pace": pace_key,
            "optimization_applied": True,
        }

        for entry in itinerary:
            entry["metadata"] = metadata.copy()

        return itinerary