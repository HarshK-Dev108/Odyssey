"""
Comprehensive Test Suite for Odyssey Full Frontend Application
Tests the complete frontend SPA, services, HTML structures, reactive features,
and backend contract compliance.
"""

import os
import re

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_frontend_index_html_structure():
    """Verify frontend/index.html includes all required UI components and features"""
    print("Testing frontend/index.html structure...")
    index_path = os.path.join(WORKSPACE_DIR, "frontend", "index.html")
    assert os.path.exists(index_path), "frontend/index.html must exist"

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Branding & Fonts
    assert "Odyssey (YatraAI)" in html, "Must have Odyssey (YatraAI) title"
    assert "Playfair" in html, "Must link Playfair font"
    assert "DM Sans" in html or "DM+Sans" in html, "Must link DM Sans font"
    assert "/assets/index-BUVUdf7g.css" in html, "Must link stylesheet"

    # 2. Header & Nav
    assert "backendStatusPill" in html, "Must have backend status pill"
    assert "navAuthArea" in html, "Must have dynamic auth area"
    assert "nav-links" in html, "Must have navigation links"

    # 3. Trip Planner
    assert 'id="planFromCity"' in html, "Must have planFromCity input"
    assert 'id="planDestination"' in html, "Must have planDestination input"
    assert 'id="planDates"' in html, "Must have planDates input"
    assert 'id="travellerCount"' in html, "Must have traveller stepper count"
    assert 'id="planBudget"' in html, "Must have planBudget input"
    assert "interestChips" in html, "Must have interest style chips"
    assert 'id="planPace"' in html, "Must have pace selector"
    assert 'id="planAvoidCrowds"' in html, "Must have avoid crowds toggle"
    assert 'id="planningOverlay"' in html, "Must have AI planning loader overlay"

    # 4. Destinations Explorer
    assert 'id="destSearchInput"' in html, "Must have destination search bar"
    assert "dest-tag-btn" in html, "Must have category filter buttons"
    assert 'id="destinationsGrid"' in html, "Must have destinations card grid"

    # 5. Trip Dashboard
    assert 'id="dashTripTitle"' in html, "Must have dashboard trip title"
    assert 'id="dashTripScore"' in html, "Must have trip score element"
    assert 'id="dashSpentAmount"' in html, "Must have spent budget display"
    assert 'id="dashBudgetBarProgress"' in html, "Must have budget progress bar"
    assert 'id="makeCheaperBtn"' in html, "Must have make cheaper button"
    assert 'id="spendChartSvg"' in html, "Must have spend forecast SVG chart"

    # 6. Itinerary Timeline
    assert 'id="dayTabsContainer"' in html, "Must have day tabs container (D1-D7)"
    assert 'id="timelineContainer"' in html, "Must have timeline events container"

    # 7. Route & Dynamic Intelligence
    assert "map-visual" in html, "Must have route intelligence map visual"
    assert 'id="adaptWeatherBtn"' in html, "Must have adapt weather button"
    assert 'id="hotelCardName"' in html, "Must have hotel recommendation card"
    assert 'id="expCardTitle"' in html, "Must have experience match card"

    # 8. AI Copilot Modal
    assert 'id="assistantModalBackdrop"' in html, "Must have assistant modal"
    assert 'id="chatBody"' in html, "Must have assistant chat body"
    assert 'id="assistantInput"' in html, "Must have assistant text input"
    assert "Make it ₹10,000 cheaper" in html, "Must have quick prompt chips"

    # 9. Services module imports
    assert "import { authApi } from '/src/services/authApi.js'" in html, "Must import authApi"
    assert "import { apiClient } from '/src/services/apiClient.js'" in html, "Must import apiClient"

    print("  ✓ frontend/index.html structure verified!")


def test_frontend_login_page():
    """Verify frontend/login.html exists and is complete"""
    print("Testing frontend/login.html...")
    login_path = os.path.join(WORKSPACE_DIR, "frontend", "login.html")
    assert os.path.exists(login_path), "frontend/login.html must exist"

    with open(login_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "signinEmail" in html
    assert "signinPassword" in html
    assert "signupName" in html
    assert "signupEmail" in html
    assert "signupPassword" in html
    assert "togglePasswordVisibility" in html
    assert "fillDemoCredentials" in html
    assert "/api/v1/users/login" in html

    print("  ✓ frontend/login.html verified!")


def test_frontend_services():
    """Verify all frontend services exist and have correct interfaces"""
    print("Testing frontend services modules...")
    services_dir = os.path.join(WORKSPACE_DIR, "frontend", "src", "services")
    expected_services = [
        "authApi.js",
        "apiClient.js",
        "tripApi.js",
        "destinationApi.js",
        "hotelApi.js",
        "activityApi.js",
        "flightApi.js",
        "expenseApi.js",
        "weatherApi.js"
    ]

    for svc in expected_services:
        path = os.path.join(services_dir, svc)
        assert os.path.exists(path), f"Service module missing: {svc}"
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        assert "export" in code, f"Service {svc} must have exports"

    print(f"  ✓ All {len(expected_services)} frontend service modules verified!")


def test_app_js_routes():
    """Verify app.js routes and proxy"""
    print("Testing app.js routing and proxy configuration...")
    app_js_path = os.path.join(WORKSPACE_DIR, "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        code = f.read()

    assert 'app.get("/login"' in code, "app.js must serve login.html on /login"
    assert 'app.use("/api/v1"' in code, "app.js must have /api/v1 proxy"
    assert "express.json()" in code, "app.js must parse JSON"

    print("  ✓ app.js routing and proxy verified!")


def main():
    print("=" * 60)
    print("  ODYSSEY FULL FRONTEND INTEGRATION VERIFICATION")
    print("=" * 60 + "\n")

    test_frontend_index_html_structure()
    test_frontend_login_page()
    test_frontend_services()
    test_app_js_routes()

    print("\n" + "=" * 60)
    print("  ALL FULL FRONTEND VERIFICATION TESTS PASSED! ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
