class TravelRecommender:
    """
    Basic recommendation engine for the AI Smart Travel Planner.

    It scores travel options based on:
    - User interests
    - Budget
    - Hotel rating
    """

    def recommend(self, options, interests, budget, hotel_rating=3):
        recommendations = []

        for option in options:
            score = 0

            # Match user's interests with the option
            option_interests = option.get("interests", [])

            for interest in interests:
                if interest.lower() in [i.lower() for i in option_interests]:
                    score += 10

            # Prefer options within the user's budget
            price = option.get("price", 0)

            if price <= budget:
                score += 20
            else:
                score -= 20

            # Match preferred hotel rating
            if option.get("rating", 0) >= hotel_rating:
                score += 10

            reasons = []
            matched_interests = [
                interest for interest in interests
                if interest.lower() in [i.lower() for i in option_interests]
            ]
            if matched_interests:
                reasons.append(f"matches {', '.join(matched_interests)} interests")
            if price <= budget:
                reasons.append("fits the available budget")
            if option.get("rating", 0) >= hotel_rating:
                reasons.append("meets the preferred rating")
            if not reasons:
                reasons.append("available in the travel catalog")

            recommendations.append({
                "option": option,
                "score": score,
                "reason": "; ".join(reasons),
            })

        # Highest score first
        recommendations.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return recommendations