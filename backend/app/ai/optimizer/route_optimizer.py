class RouteOptimizer:
    """
    Creates an efficient route for visiting multiple locations.
    """

    def optimize(self, locations, start_location):
        if not locations:
            return [start_location]

        remaining = locations.copy()
        route = [start_location]
        current = start_location

        while remaining:
            nearest = min(
                remaining,
                key=lambda location: self._distance(current, location)
            )

            route.append(nearest)
            remaining.remove(nearest)
            current = nearest

        return route

    @staticmethod
    def _distance(origin, destination):
        if destination.get("distance") is not None:
            return float(destination["distance"])

        origin_lat = origin.get("latitude")
        origin_lon = origin.get("longitude")
        destination_lat = destination.get("latitude")
        destination_lon = destination.get("longitude")
        if None in {origin_lat, origin_lon, destination_lat, destination_lon}:
            return float("inf")

        latitude_delta = float(destination_lat) - float(origin_lat)
        longitude_delta = float(destination_lon) - float(origin_lon)
        return (latitude_delta ** 2 + longitude_delta ** 2) ** 0.5