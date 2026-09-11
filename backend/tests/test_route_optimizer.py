from app.ai.optimizer.route_optimizer import RouteOptimizer


def test_route_optimizer_handles_empty_and_single_location():
    optimizer = RouteOptimizer()
    start = {"name": "Start"}
    assert optimizer.optimize([], start) == [start]
    location = {"name": "Only", "distance": 1}
    assert optimizer.optimize([location], start) == [start, location]


def test_route_optimizer_orders_by_explicit_distance():
    optimizer = RouteOptimizer()
    start = {"name": "Start", "distance": 0}
    far = {"name": "Far", "distance": 20}
    near = {"name": "Near", "distance": 5}
    assert optimizer.optimize([far, near], start) == [start, near, far]


def test_route_optimizer_uses_coordinates_when_distance_missing():
    optimizer = RouteOptimizer()
    start = {"name": "Start", "latitude": 0, "longitude": 0}
    near = {"name": "Near", "latitude": 0, "longitude": 1}
    far = {"name": "Far", "latitude": 0, "longitude": 4}
    assert optimizer.optimize([far, near], start) == [start, near, far]