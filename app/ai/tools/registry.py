TOOL_DEFINITIONS = {
    "get_trip": "Read the authenticated user's persisted trip.",
    "get_remaining_budget": "Read the authenticated user's remaining budget.",
    "make_trip_cheaper": "Request a validated budget reduction.",
    "upgrade_hotel": "Request a budget-constrained hotel upgrade.",
    "add_activity": "Add an activity that exists in the catalog and fits budget.",
    "remove_activity": "Remove an existing activity from the persisted plan.",
    "change_itinerary": "Modify a specifically identified itinerary day.",
    "set_crowd_preference": "Persist a crowd preference without inventing crowd data.",
    "get_weather": "Read weather from the weather provider.",
    "search_destinations": "Search the tourism destination catalog.",
    "search_hotels": "Search the tourism hotel catalog.",
    "search_activities": "Search the tourism activity catalog.",
    "search_flights": "Search the tourism flight catalog.",
    "optimize_trip": "Run the validated deterministic optimizer.",
}


def get_tool_definitions() -> list[dict[str, str]]:
    return [
        {"name": name, "description": description}
        for name, description in TOOL_DEFINITIONS.items()
    ]