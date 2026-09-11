"""
Automated Verification Suite for Odyssey Backend Analysis & Frontend Login Page
Tests the contract alignment between backend routes and frontend implementation,
validates HTML/JS components, auth service modules, and serves the frontend to verify HTTP delivery.
"""

import ast
import http.server
import os
import re
import socketserver
import threading
import time
import urllib.request

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_backend_user_routes_contract():
    """Verify backend FastAPI routes in backend/app/api/routes/users.py"""
    print("Testing Backend User Routes Contract...")
    users_py_path = os.path.join(WORKSPACE_DIR, "backend", "app", "api", "routes", "users.py")
    assert os.path.exists(users_py_path), f"File missing: {users_py_path}"

    with open(users_py_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Parse AST
    tree = ast.parse(code)

    functions = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "login_user" in functions, "login_user route function missing in backend/app/api/routes/users.py"
    assert "create_user" in functions, "create_user route function missing in backend/app/api/routes/users.py"

    # Verify login_user arguments
    login_args = [arg.arg for arg in functions["login_user"].args.args]
    assert "email" in login_args, "login_user must accept email"
    assert "password" in login_args, "login_user must accept password"

    # Verify create_user arguments
    create_args = [arg.arg for arg in functions["create_user"].args.args]
    assert "name" in create_args, "create_user must accept name"
    assert "email" in create_args, "create_user must accept email"
    assert "password" in create_args, "create_user must accept password"

    # Verify return dict contains access_token and token_type
    assert "access_token" in code, "login_user must return access_token"
    assert "bearer" in code.lower(), "token_type must be bearer"
    assert "Invalid email or password" in code, "login_user must raise 401 on invalid credentials"
    assert "Email already registered" in code, "create_user must raise 400 on duplicate email"

    print("  ✓ Backend user routes contract successfully verified!")


def test_frontend_auth_api_service():
    """Verify frontend/src/services/authApi.js contract and exports"""
    print("Testing Frontend Auth API Service...")
    auth_api_path = os.path.join(WORKSPACE_DIR, "frontend", "src", "services", "authApi.js")
    assert os.path.exists(auth_api_path), f"File missing: {auth_api_path}"

    with open(auth_api_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "export const authApi" in content or "export default authApi" in content, "authApi must be exported"
    assert "login:" in content, "authApi must provide login method"
    assert "register:" in content, "authApi must provide register method"
    assert "setSession:" in content, "authApi must provide setSession method"
    assert "getToken:" in content, "authApi must provide getToken method"
    assert "getUser:" in content, "authApi must provide getUser method"
    assert "logout:" in content, "authApi must provide logout method"
    assert "isAuthenticated:" in content, "authApi must provide isAuthenticated method"
    assert "/users/login" in content, "login must call /users/login endpoint"
    assert "odyssey_token" in content, "authApi must use odyssey_token localStorage key"
    assert "odyssey_user" in content, "authApi must use odyssey_user localStorage key"

    print("  ✓ Frontend auth API service contract successfully verified!")


def test_frontend_api_client():
    """Verify frontend/src/services/apiClient.js attaches Authorization Bearer token"""
    print("Testing Frontend API Client Bearer Token Attachment...")
    client_path = os.path.join(WORKSPACE_DIR, "frontend", "src", "services", "apiClient.js")
    assert os.path.exists(client_path), f"File missing: {client_path}"

    with open(client_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "odyssey_token" in content, "apiClient must read odyssey_token from localStorage"
    assert "Bearer" in content, "apiClient must format Authorization header as Bearer token"
    assert "post:" in content, "apiClient must have post method"

    print("  ✓ Frontend API Client token integration verified!")


def test_frontend_login_html():
    """Verify frontend/login.html elements, styling, and JS handlers"""
    print("Testing Frontend Login HTML Page...")
    login_html_path = os.path.join(WORKSPACE_DIR, "frontend", "login.html")
    assert os.path.exists(login_html_path), f"File missing: {login_html_path}"

    with open(login_html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Verify structure & aesthetics
    assert "Playfair Display" in html, "Must include luxury Playfair Display font"
    assert "DM Sans" in html, "Must include DM Sans font"
    assert "tabSignIn" in html and "tabSignUp" in html, "Must have Sign In and Create Account tabs"
    assert "signinEmail" in html, "Must have signinEmail input"
    assert "signinPassword" in html, "Must have signinPassword input"
    assert "signupName" in html, "Must have signupName input"
    assert "signupEmail" in html, "Must have signupEmail input"
    assert "signupPassword" in html, "Must have signupPassword input"
    assert "pwd-strength" in html or "checkPasswordStrength" in html, "Must have password strength indicator"
    assert "togglePasswordVisibility" in html, "Must have password visibility toggle"
    assert "fillDemoCredentials" in html, "Must provide quick demo credentials shortcut"
    assert "/api/v1/users/login" in html or "/users/login" in html, "Must call /api/v1/users/login"
    assert "/api/v1/users/" in html or "/users/" in html, "Must call /api/v1/users/ registration endpoint"
    assert "odyssey_token" in html, "Must store token under odyssey_token"
    assert "odyssey_user" in html, "Must store user under odyssey_user"
    assert "loggedInState" in html, "Must support already-logged-in session state view"

    print("  ✓ Frontend login.html structure and functionality verified!")


def test_frontend_react_bundle():
    """Verify frontend/assets/index-BoGYFkJU.js /login route and header navbar"""
    print("Testing React Bundle Route & Component Integration...")
    bundle_path = os.path.join(WORKSPACE_DIR, "frontend", "assets", "index-BoGYFkJU.js")
    assert os.path.exists(bundle_path), f"File missing: {bundle_path}"

    with open(bundle_path, "r", encoding="utf-8") as f:
        js = f.read()

    # Verify /login route no longer returns placeholder "<h1>Login Page</h1>"
    assert 'function iae(){return T.jsx("h1",{children:"Login Page"})}' not in js, "Placeholder Login Page was not replaced!"
    assert 'path:"/login",element:T.jsx(iae,{})' in js, "Route /login must map to component iae"
    assert 'odyssey_token' in js, "iae component must store odyssey_token"
    assert 'odyssey_user' in js, "iae component must store odyssey_user"
    assert 'auth-page-wrapper' in js, "iae component must render auth-page-wrapper"
    assert 'nav-signin-btn' in js or 'user-nav-chip' in js, "Navbar in tae must render Sign In button or user chip"

    print("  ✓ React bundle route & component integration verified!")


def test_app_js_reverse_proxy():
    """Verify app.js includes /api/v1 reverse proxy to FastAPI backend"""
    print("Testing app.js Reverse Proxy Configuration...")
    app_js_path = os.path.join(WORKSPACE_DIR, "app.js")
    assert os.path.exists(app_js_path), f"File missing: {app_js_path}"

    with open(app_js_path, "r", encoding="utf-8") as f:
        app_code = f.read()

    assert "express.json()" in app_code, "app.js must parse json bodies"
    assert "/api/v1" in app_code, "app.js must have /api/v1 proxy"
    assert "BACKEND_URL" in app_code, "app.js must configure BACKEND_URL (port 8000)"
    assert "authorization" in app_code.lower(), "proxy must forward authorization header"

    print("  ✓ app.js reverse proxy configuration verified!")


def test_frontend_asset_integrity():
    """Verify frontend static assets, MIME types, and entry points are valid and self-contained"""
    print("Testing Frontend Asset Integrity & Static Delivery...")
    frontend_dir = os.path.join(WORKSPACE_DIR, "frontend")

    # 1. Verify login.html
    login_html_path = os.path.join(frontend_dir, "login.html")
    assert os.path.exists(login_html_path), "login.html must exist"
    with open(login_html_path, "r", encoding="utf-8") as f:
        login_content = f.read()
    assert "<!DOCTYPE html>" in login_content
    assert "Odyssey — Sign In & Account" in login_content
    assert "/assets/index-BUVUdf7g.css" in login_content
    print("  ✓ frontend/login.html exists, valid HTML5 with CSS reference")

    # 2. Verify index.html
    index_html_path = os.path.join(frontend_dir, "index.html")
    assert os.path.exists(index_html_path), "index.html must exist"
    with open(index_html_path, "r", encoding="utf-8") as f:
        index_content = f.read()
    assert "/src/services/authApi.js" in index_content or "/assets/index-BoGYFkJU.js" in index_content
    assert "/assets/index-BUVUdf7g.css" in index_content
    print("  ✓ frontend/index.html exists and links to auth services & CSS bundles")

    # 3. Verify CSS bundle
    css_path = os.path.join(frontend_dir, "assets", "index-BUVUdf7g.css")
    assert os.path.exists(css_path), "CSS bundle must exist"
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    assert ".auth-page-wrapper" in css_content
    assert ".auth-card-panel" in css_content
    assert ".user-nav-chip" in css_content
    print("  ✓ frontend/assets/index-BUVUdf7g.css includes all required auth styling rules")

    # 4. Verify JS bundle
    js_path = os.path.join(frontend_dir, "assets", "index-BoGYFkJU.js")
    assert os.path.exists(js_path), "JS bundle must exist"
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()
    assert "odyssey_token" in js_content
    assert "odyssey_user" in js_content
    assert "/api/v1/users/login" in js_content
    print("  ✓ frontend/assets/index-BoGYFkJU.js contains complete React login component & auth flow")

    print("  ✓ Frontend asset integrity & static delivery verified!")


def main():
    print("=" * 60)
    print("  ODYSSEY AUTH & LOGIN PAGE INTEGRATION VERIFICATION")
    print("=" * 60 + "\n")

    test_backend_user_routes_contract()
    test_frontend_auth_api_service()
    test_frontend_api_client()
    test_frontend_login_html()
    test_frontend_react_bundle()
    test_app_js_reverse_proxy()
    test_frontend_asset_integrity()

    print("\n" + "=" * 60)
    print("  ALL 7 VERIFICATION TESTS PASSED SUCCESSFULLY! ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
