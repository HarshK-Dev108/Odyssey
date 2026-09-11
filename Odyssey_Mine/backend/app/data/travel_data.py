TRAVEL_OPTIONS = {
    "thailand": [
        # Hotels
        {
            "name": "Premium Beach Resort",
            "type": "hotel",
            "price": 25000,
            "rating": 4,
            "interests": ["beaches", "food", "luxury"]
        },
        {
            "name": "Budget City Hotel",
            "type": "hotel",
            "price": 15000,
            "rating": 3,
            "interests": ["food", "city"]
        },
        {
            "name": "Luxury Ocean View Hotel",
            "type": "hotel",
            "price": 40000,
            "rating": 5,
            "interests": ["beaches", "food", "luxury"]
        },

        # Activities
        {
            "name": "Scuba Diving",
            "type": "activity",
            "price": 8000,
            "rating": 5,
            "interests": ["adventure", "beaches"]
        },
        {
            "name": "Island Hopping",
            "type": "activity",
            "price": 6000,
            "rating": 5,
            "interests": ["beaches", "adventure"]
        },
        {
            "name": "Thai Cooking Class",
            "type": "activity",
            "price": 3000,
            "rating": 4,
            "interests": ["food", "culture"]
        },
        {
            "name": "Bangkok City Tour",
            "type": "activity",
            "price": 2500,
            "rating": 4,
            "interests": ["city", "culture"]
        },
        {
            "name": "Jungle Adventure",
            "type": "activity",
            "price": 7000,
            "rating": 5,
            "interests": ["adventure", "nature"]
        },

        # Transport
        {
            "name": "Airport Transfer",
            "type": "transport",
            "price": 2000,
            "rating": 4,
            "interests": ["city"]
        },
        {
            "name": "Local Transport Pass",
            "type": "transport",
            "price": 5000,
            "rating": 4,
            "interests": ["city", "budget"]
        },

        # Food
        {
            "name": "Thai Street Food Experience",
            "type": "food",
            "price": 2500,
            "rating": 5,
            "interests": ["food", "culture"]
        },
        {
            "name": "Premium Thai Dinner",
            "type": "food",
            "price": 5000,
            "rating": 5,
            "interests": ["food", "luxury"]
        }
    ]
}


def get_travel_options(destination):
    """
    Return travel options for the requested destination.
    """

    destination_key = destination.lower().strip()

    return TRAVEL_OPTIONS.get(destination_key, [])