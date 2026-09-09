from itertools import product


class BudgetOptimizer:
    """Build and modify deterministic, budget-constrained travel packages."""

    _SINGLETON_TYPES = {"hotel", "flight", "transport", "food"}

    @staticmethod
    def _price(option):
        try:
            return max(float(option.get("price", 0)), 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _option_key(option):
        return (option.get("source_id") or option.get("name"), option.get("type", "other"))

    @staticmethod
    def _pace_limit(pace, days):
        pace_key = (pace or "moderate").casefold()
        if pace_key == "relaxed":
            return max(1, days)
        if pace_key == "active":
            return max(1, days * 2)
        return max(1, days + 1)

    @staticmethod
    def _score_option(option, recommendation_score, interests, hotel_rating, avoid_crowds):
        score = float(recommendation_score or 0)
        option_interests = {str(value).casefold() for value in option.get("interests", [])}
        score += 10 * sum(
            1 for interest in interests or []
            if str(interest).casefold() in option_interests
        )
        if option.get("type") == "hotel" and option.get("rating", 0) >= hotel_rating:
            score += 5
        crowd_value = option.get("crowd_level", option.get("crowd_score"))
        if avoid_crowds and crowd_value is not None:
            if isinstance(crowd_value, str) and crowd_value.casefold() in {"low", "quiet"}:
                score += 15
            elif isinstance(crowd_value, str) and crowd_value.casefold() in {"high", "crowded"}:
                score -= 15
            elif isinstance(crowd_value, str) and crowd_value.casefold() in {"medium", "moderate"}:
                score -= 5
            elif isinstance(crowd_value, (int, float)):
                score -= float(crowd_value)
        return score

    def optimize(
        self,
        recommendations,
        budget,
        interests=None,
        hotel_rating=3,
        pace="moderate",
        avoid_crowds=False,
        days=1,
    ):
        candidates = []
        seen = set()
        for recommendation in recommendations:
            option = recommendation.get("option", {})
            key = self._option_key(option)
            if key in seen or self._price(option) > budget:
                continue
            seen.add(key)
            candidates.append((
                self._score_option(option, recommendation.get("score", 0), interests, hotel_rating, avoid_crowds),
                option,
            ))

        candidates.sort(key=lambda item: (-item[0], self._price(item[1]), str(item[1].get("name", ""))))
        selected = []
        selected_keys = set()
        selected_types = set()
        total_cost = 0
        activity_count = 0
        activity_limit = self._pace_limit(pace, days)

        for score, option in candidates:
            option_type = option.get("type", "other")
            key = self._option_key(option)
            if key in selected_keys:
                continue
            if option_type in self._SINGLETON_TYPES and option_type in selected_types:
                continue
            if option_type == "activity" and activity_count >= activity_limit:
                continue
            price = self._price(option)
            if total_cost + price > budget:
                continue
            selected_option = dict(option)
            selected_option["ai_score"] = score
            selected.append(selected_option)
            selected_keys.add(key)
            selected_types.add(option_type)
            total_cost += price
            activity_count += option_type == "activity"

        return self._budget_result(
            selected,
            budget,
            f"Selected the highest-scoring unique options within the budget using {pace or 'moderate'} pace.",
            len(candidates),
        )

    def _budget_result(self, selected_options, budget, reason, alternatives_considered):
        total_cost = sum(self._price(option) for option in selected_options)
        return {
            "selected_options": selected_options,
            "total_cost": total_cost,
            "remaining_budget": budget - total_cost,
            "budget_utilization": round((total_cost / budget) * 100, 2) if budget > 0 else 0,
            "optimization_reason": reason,
            "alternatives_considered": alternatives_considered,
        }

    def make_cheaper(self, selected_options, target_saving, available_options=None, budget=None):
        """Find the closest saving using substitutions first, then removals."""
        current_options = [dict(option) for option in selected_options]
        current_cost = sum(self._price(option) for option in current_options)
        if target_saving <= 0:
            return {
                "selected_options": current_options,
                "old_cost": current_cost,
                "new_cost": current_cost,
                "saving": 0,
                "target_saving": target_saving,
                "optimization_reason": "No change was requested because the saving was not positive.",
            }

        alternatives_by_index = []
        for current in current_options:
            alternatives = [(current, 0, "keep")]
            for candidate in available_options or []:
                if candidate.get("type") != current.get("type"):
                    continue
                if self._option_key(candidate) == self._option_key(current):
                    continue
                saving = self._price(current) - self._price(candidate)
                if saving > 0:
                    alternatives.append((dict(candidate), saving, "substitute"))
            alternatives.append((None, self._price(current), "remove"))
            alternatives_by_index.append(alternatives)

        best = None
        for choices in product(*alternatives_by_index):
            resulting = [choice[0] for choice in choices if choice[0] is not None]
            keys = [self._option_key(option) for option in resulting]
            types = [option.get("type", "other") for option in resulting]
            if len(keys) != len(set(keys)):
                continue
            if any(types.count(option_type) > 1 for option_type in self._SINGLETON_TYPES):
                continue
            new_cost = sum(self._price(option) for option in resulting)
            saving = current_cost - new_cost
            if saving <= 0 or (budget is not None and new_cost > budget):
                continue
            substitutions = sum(choice[2] == "substitute" for choice in choices)
            removals = sum(choice[2] == "remove" for choice in choices)
            ranking = (abs(target_saving - saving), removals, -substitutions, -saving)
            if best is None or ranking < best[0]:
                best = (ranking, resulting, saving, substitutions, removals)

        if best is None:
            return {
                "selected_options": current_options,
                "old_cost": current_cost,
                "new_cost": current_cost,
                "saving": 0,
                "target_saving": target_saving,
                "optimization_reason": "No valid cheaper substitution or removal was available.",
            }

        _, best_options, saving, substitutions, removals = best
        reason_parts = []
        if substitutions:
            reason_parts.append(f"used {substitutions} cheaper equivalent substitution(s)")
        if removals:
            reason_parts.append(f"removed {removals} lower-priority option(s)")
        return {
            "selected_options": best_options,
            "old_cost": current_cost,
            "new_cost": current_cost - saving,
            "saving": saving,
            "target_saving": target_saving,
            "optimization_reason": (" and ".join(reason_parts).capitalize() + "."),
        }

    def upgrade_hotel(self, selected_options, available_hotels, budget):
        current_options = [dict(option) for option in selected_options]
        current_hotel = next((option for option in current_options if option.get("type") == "hotel"), None)
        if not current_hotel:
            return {
                "success": False,
                "message": "No hotel found in current plan.",
                "selected_options": current_options,
            }

        current_cost = sum(self._price(option) for option in current_options)
        better_hotels = [
            hotel for hotel in available_hotels
            if hotel.get("type") == "hotel"
            and hotel.get("rating", 0) > current_hotel.get("rating", 0)
            and self._option_key(hotel) != self._option_key(current_hotel)
        ]
        better_hotels.sort(key=lambda hotel: (
            -(hotel.get("rating", 0) - current_hotel.get("rating", 0)),
            self._price(hotel),
            str(hotel.get("name", "")),
        ))
        for hotel in better_hotels:
            new_total_cost = current_cost - self._price(current_hotel) + self._price(hotel)
            if new_total_cost <= budget:
                upgraded = [option for option in current_options if option is not current_hotel]
                upgraded.append(dict(hotel))
                return {
                    "success": True,
                    "message": "Hotel upgraded successfully within the original budget.",
                    "optimization_reason": (
                        f"Replaced {current_hotel.get('name')} with {hotel.get('name')} "
                        f"while keeping the total within ₹{budget:,.0f}."
                    ),
                    "old_hotel": current_hotel,
                    "new_hotel": hotel,
                    "old_cost": current_cost,
                    "new_cost": new_total_cost,
                    "remaining_budget": budget - new_total_cost,
                    "selected_options": upgraded,
                }

        return {
            "success": False,
            "message": "Could not upgrade the hotel without exceeding the original budget.",
            "optimization_reason": "Every higher-rated catalog hotel exceeded the available budget.",
            "selected_options": current_options,
            "old_hotel": current_hotel,
            "new_cost": current_cost,
            "remaining_budget": budget - current_cost,
        }
