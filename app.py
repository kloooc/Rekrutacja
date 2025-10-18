from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from dotenv import load_dotenv
from functools import wraps
from urllib.parse import urlencode
from urllib.request import urlopen
from jwt.algorithms import RSAAlgorithm
import jwt, os, json, requests

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")

def requires_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "profile" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper

def requires_api_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Brak tokena"}), 401

        token = auth_header.split(" ")[1]
        try:
            jwks = json.loads(urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json").read())
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = next(
                (
                    {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"],
                    }
                    for key in jwks["keys"]
                    if key["kid"] == unverified_header["kid"]
                ),
                None,
            )
            if not rsa_key:
                return jsonify({"error": "Klucz JWKS nie znaleziony"}), 401

            public_key = RSAAlgorithm.from_jwk(json.dumps(rsa_key))
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=AUTH0_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/",
            )
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token wygasł"}), 401
        except Exception as e:
            return jsonify({"error": "Błąd tokena", "details": str(e)}), 401
        return view(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    is_logged_in = 'profile' in session
    user_name = session['profile']['name'] if is_logged_in else None
    is_admin = session.get('is_admin', False) if is_logged_in else False # Pobranie is_admin z sesji
    return render_template('index.html', is_logged_in=is_logged_in, user_name=user_name, is_admin=is_admin)

@app.route("/login")
def login():
    params = {
        "scope": "openid profile email",
        "response_type": "code",
        "client_id": AUTH0_CLIENT_ID,
        "redirect_uri": url_for("callback", _external=True),
        "audience": AUTH0_AUDIENCE,
    }
    return redirect(f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}")

@app.route("/callback")
def callback():
    data = {
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "redirect_uri": url_for("callback", _external=True),
        "code": request.args.get("code"),
        "grant_type": "authorization_code",
    }
    res = requests.post(f"https://{AUTH0_DOMAIN}/oauth/token", json=data).json()
    if res.get("error"):
        return jsonify(res), 400

    id_token = res.get("id_token")
    if not id_token:
        return "Brak ID Tokena", 400

    try:
        jwks = json.loads(urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json").read())
        unverified_header = jwt.get_unverified_header(id_token)

        rsa_key = next(
            (
                {
                    "kty": key["kty"], "kid": key["kid"], "use": key["use"],
                    "n": key["n"], "e": key["e"],
                }
                for key in jwks["keys"]
                if key["kid"] == unverified_header["kid"]
            ),
            None,
        )
        if not rsa_key:
            return "Błąd weryfikacji ID Tokena: Klucz JWKS nie znaleziony", 401

        public_key = RSAAlgorithm.from_jwk(json.dumps(rsa_key))

        user_info = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            leeway=5,
            audience=AUTH0_CLIENT_ID,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
    except Exception as e:
        return jsonify({"error": "Błąd weryfikacji ID Tokena", "details": str(e)}), 401

    session["profile"] = {
        "sub": user_info.get("sub"),
        "name": user_info.get("name") or user_info.get("email", "Użytkownik"),
        "email": user_info.get("email"),
    }
    access_token = res.get("access_token", "")
    session["access_token"] = access_token

    if access_token:
        try:
            access_token_payload = jwt.decode(access_token, options={"verify_signature": False})
            permissions = access_token_payload.get("permissions", [])
            session["is_admin"] = "admin:access" in permissions
        except Exception:
            session["is_admin"] = False
    else:
        session["is_admin"] = False
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    params = {
        "returnTo": url_for("home", _external=True),
        "client_id": AUTH0_CLIENT_ID,
        "federated": "true",
    }
    return redirect(f"https://{AUTH0_DOMAIN}/v2/logout?{urlencode(params)}")

@app.route('/dashboard')
@requires_auth
def dashboard():
    user_data = session['profile']
    access_token = session['access_token']
    return render_template('dashboard.html', user_data=user_data, access_token=access_token)

@app.route("/api/profile")
@requires_api_auth
def api_profile():
    return jsonify({
        "status": "success",
        "message": "Dane",
        "user_id": request.user.get("sub"),
        "audience": request.user.get("aud"),
        "issuer": request.user.get("iss"),
    })

if __name__ == "__main__":
    app.run(debug=True)
