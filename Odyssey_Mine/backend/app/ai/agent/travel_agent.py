class TravelAgent:
    """
    Main AI travel agent that coordinates
    recommendation, budget optimization,
    and itinerary generation.
    """

    def __init__(self, recommender, budget_optimizer, itinerary_generator):
        self.recommender = recommender
        self.budget_optimizer = budget_optimizer
        self.itinerary_generator = itinerary_generator

    def plan_trip(
        self,
        options,
        interests,
        budget,
        hotel_rating,
        days,
        pace="moderate",
        avoid_crowds=False,
        weather_by_day=None,
    ):

        # Step 1: Recommend suitable options
        recommendations = self.recommender.recommend(
            options=options,
            interests=interests,
            budget=budget,
            hotel_rating=hotel_rating
        )

        # Step 2: Optimize using recommendation scores
        optimized_plan = self.budget_optimizer.optimize(
            recommendations=recommendations,
            budget=budget,
            interests=interests,
            hotel_rating=hotel_rating,
            pace=pace,
            avoid_crowds=avoid_crowds,
            days=days,
        )

        # Step 3: Generate itinerary
        itinerary = self.itinerary_generator.generate(
            activities=optimized_plan["selected_options"],
            days=days,
            pace=pace,
            interests=interests,
            avoid_crowds=avoid_crowds,
            weather_by_day=weather_by_day,
        )

        return {
            "recommendations": recommendations,
            "budget_plan": optimized_plan,
            "itinerary": itinerary
        }