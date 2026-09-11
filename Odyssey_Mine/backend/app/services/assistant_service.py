from copy import deepcopy

from app.ai.agent.travel_agent import TravelAgent
from app.ai.assistant.intent import AssistantIntent
from app.ai.assistant.parser import parse_assistant_message
from app.ai.itinerary.itinerary_generator import ItineraryGenerator
from app.ai.llm.provider import LLMProvider
from app.ai.optimizer.budget_optimizer import BudgetOptimizer
from app.ai.recommendation.recommender import TravelRecommender
from app.models.trip import Trip
from app.schemas.assistant import AssistantIntentResult
from app.services.tourism_service import get_tourism_options
from pydantic import ValidationError


HELP_MESSAGE = (
    "I can make your trip cheaper, upgrade your hotel, show your remaining "
    "budget, add an adventure activity, avoid crowded places, or change "
    "a specific itinerary day."
)


class AssistantService:
    def __init__(self):
        self.recommender = TravelRecommender()
        self.budget_optimizer = BudgetOptimizer()
        self.itinerary_generator = ItineraryGenerator()
        self.travel_agent = TravelAgent(
            recommender=self.recommender,
            budget_optimizer=self.budget_optimizer,
            itinerary_generator=self.itinerary_generator,
        )
        self.llm_provider = LLMProvider()

    @staticmethod
    def _days(trip: Trip) -> int:
        return max((trip.end_date - trip.start_date).days, 1)

    def _initial_plan(self, trip: Trip, options: list[dict]) -> dict:
        return self.travel_agent.plan_trip(
            options=options,
            interests=trip.interests or [],
            budget=trip.budget,
            hotel_rating=trip.hotel_rating,
            days=self._days(trip),
            pace=trip.pace,
            avoid_crowds=trip.avoid_crowds,
        )

    @staticmethod
    def _selected_cost(selected_options: list[dict]) -> float:
        return sum(float(option.get("price", 0)) for option in selected_options)

    def _sync_budget_plan(
        self,
        plan: dict,
        selected_options: list[dict],
        budget: float,
        reason: str = "Updated the package while preserving the original budget.",
    ) -> None:
        total_cost = self._selected_cost(selected_options)
        plan["budget_plan"] = {
            "selected_options": selected_options,
            "total_cost": total_cost,
            "remaining_budget": budget - total_cost,
            "budget_utilization": round((total_cost / budget) * 100, 2) if budget else 0,
            "optimization_reason": reason,
        }

    @staticmethod
    def _sync_itinerary(plan: dict, selected_options: list[dict]) -> None:
        selected_names = {option.get("name") for option in selected_options}
        for day in plan.get("itinerary", []):
            day["activities"] = [
                activity
                for activity in day.get("activities", [])
                if activity.get("name") in selected_names
            ]

    async def respond(self, trip: Trip, message: str, tourism_db) -> dict:
        parsed: AssistantIntentResult = parse_assistant_message(message)
        if parsed.intent == AssistantIntent.UNKNOWN:
            llm_result = await self.llm_provider.structured_json(
                "Classify this travel request as one supported intent. Return JSON with intent, amount, amount_requested, day, confidence. Never invent facts.",
                message,
            )
            if llm_result:
                try:
                    parsed = AssistantIntentResult.model_validate(llm_result)
                except ValidationError:
                    parsed = AssistantIntentResult(
                        intent=AssistantIntent.UNKNOWN,
                        confidence=0,
                    )
        options = await get_tourism_options(
            db=tourism_db,
            destination=trip.destination,
            from_city=trip.from_city,
            nights=self._days(trip),
            travellers=trip.travellers,
        )

        if trip.ai_plan:
            current_plan = deepcopy(trip.ai_plan)
        else:
            current_plan = self._initial_plan(trip, options)

        unchanged_plan = deepcopy(current_plan)
        result = {
            "trip_id": trip.id,
            "message": HELP_MESSAGE,
            "intent": parsed.intent.value,
            "changed": False,
            "ai_plan": current_plan,
            "confidence": parsed.confidence,
        }

        if parsed.parse_error:
            result["message"] = parsed.parse_error
            result["action"] = "make_cheaper"
            return result

        selected_options = current_plan.get("budget_plan", {}).get("selected_options", [])

        if parsed.intent == AssistantIntent.REMAINING_BUDGET:
            result.update({
                "message": (
                    f"You have ₹{current_plan.get('budget_plan', {}).get('remaining_budget', trip.budget)} "
                    f"remaining from your ₹{trip.budget} budget."
                ),
                "action": "show_budget",
                "budget_plan": current_plan.get("budget_plan", {}),
            })
            return result

        if parsed.intent == AssistantIntent.EXPLAIN_RECOMMENDATION:
            recommendations = current_plan.get("recommendations", [])
            selected_names = {
                option.get("name")
                for option in selected_options
            }
            selected_recommendations = [
                recommendation for recommendation in recommendations
                if recommendation.get("option", {}).get("name") in selected_names
            ]
            if selected_recommendations:
                explanations = [
                    recommendation.get("reason", "Selected by the deterministic budget optimizer.")
                    for recommendation in selected_recommendations
                ]
                result["message"] = "I chose these options because " + "; ".join(explanations) + "."
            else:
                result["message"] = "The current plan does not contain recommendation details to explain."
            result["action"] = "explain_recommendation"
            return result

        if parsed.intent == AssistantIntent.MAKE_CHEAPER:
            target_saving = parsed.amount if parsed.amount is not None else 10000
            current_cost = self._selected_cost(selected_options)
            if target_saving <= 0:
                result["message"] = "The requested saving must be greater than zero."
                return result
            if target_saving > current_cost:
                result["message"] = (
                    f"The current plan costs ₹{current_cost:,.0f}, so it cannot save "
                    f"₹{target_saving:,.0f} without removing the entire plan."
                )
                return result

            cheaper = self.budget_optimizer.make_cheaper(
                selected_options,
                target_saving,
                available_options=options,
                budget=trip.budget,
            )
            if cheaper["saving"] <= 0:
                result["message"] = "I could not find a safe saving in the current plan."
                return result
            current_plan["budget_plan"]["selected_options"] = cheaper["selected_options"]
            self._sync_budget_plan(
                current_plan,
                cheaper["selected_options"],
                trip.budget,
                cheaper["optimization_reason"],
            )
            self._sync_itinerary(current_plan, cheaper["selected_options"])
            result.update({
                "message": f"I reduced your trip cost by ₹{cheaper['saving']:,.0f}.",
                "action": "make_cheaper",
                "requested_saving": target_saving,
                "result": cheaper,
            })

        elif parsed.intent == AssistantIntent.UPGRADE_HOTEL:
            upgraded = self.budget_optimizer.upgrade_hotel(
                selected_options=selected_options,
                available_hotels=options,
                budget=trip.budget,
            )
            if not upgraded.get("success"):
                result["message"] = upgraded.get("message", "No hotel upgrade fits within your budget.")
                result["action"] = "upgrade_hotel"
                return result
            self._sync_budget_plan(
                current_plan,
                upgraded["selected_options"],
                trip.budget,
                upgraded.get("optimization_reason", upgraded["message"]),
            )
            result.update({
                "message": upgraded["message"],
                "action": "upgrade_hotel",
                "result": upgraded,
            })

        elif parsed.intent == AssistantIntent.ADD_ADVENTURE:
            existing_names = {option.get("name") for option in selected_options}
            candidates = [
                option for option in options
                if option.get("type") == "activity"
                and "adventure" in [str(item).casefold() for item in option.get("interests", [])]
                and option.get("name") not in existing_names
            ]
            candidates.sort(key=lambda option: (-option.get("rating", 0), option.get("price", 0)))
            candidate = next(
                (option for option in candidates if self._selected_cost(selected_options) + option.get("price", 0) <= trip.budget),
                None,
            )
            if candidate is None:
                result["message"] = "I could not find an available adventure activity within your budget."
                return result
            selected_options = selected_options + [candidate]
            self._sync_budget_plan(
                current_plan,
                selected_options,
                trip.budget,
                f"Added {candidate['name']} while keeping the package within the original budget.",
            )
            current_plan["itinerary"] = self.itinerary_generator.generate(
                activities=selected_options,
                days=self._days(trip),
            )
            result.update({
                "message": f"I added {candidate['name']} to your plan.",
                "action": "add_adventure",
            })

        elif parsed.intent == AssistantIntent.AVOID_CROWDS:
            trip.avoid_crowds = True
            current_plan.setdefault("preferences", {})["avoid_crowds"] = True
            result.update({
                "message": "I saved your preference to avoid crowded places. Crowd data is unavailable in the current catalog, so no crowd-based filtering was applied.",
                "action": "avoid_crowds",
            })

        elif parsed.intent == AssistantIntent.CHANGE_ITINERARY:
            if parsed.day is None:
                result["message"] = "Which itinerary day should I change?"
                return result
            itinerary = current_plan.get("itinerary", [])
            day_entry = next((day for day in itinerary if day.get("day") == parsed.day), None)
            if day_entry is None:
                result["message"] = f"Day {parsed.day} is not present in the current itinerary."
                return result
            if "relaxed" not in message.casefold():
                result["message"] = "I need a specific safe change for that day, such as 'make day 2 relaxed'."
                return result
            day_entry["activities"] = []
            day_entry["note"] = "Relaxed / Free Day"
            result.update({
                "message": f"Day {parsed.day} is now a relaxed day.",
                "action": "change_itinerary",
            })

        elif parsed.intent == AssistantIntent.HELP:
            result["action"] = "help"
            return result
        else:
            result["action"] = "help"
            result["intent"] = AssistantIntent.UNKNOWN.value
            return result

        total_cost = self._selected_cost(current_plan.get("budget_plan", {}).get("selected_options", []))
        if total_cost > trip.budget:
            result["message"] = "That change would exceed your budget, so I left the plan unchanged."
            result["ai_plan"] = unchanged_plan
            result["action"] = parsed.intent.value.casefold()
            return result

        trip.ai_plan = current_plan
        result["ai_plan"] = current_plan
        result["changed"] = True
        return result