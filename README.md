# Zadanie Rekrutacyjne

To rozwiązanie stanowi prostą aplikację webową (**Frontend + Backend w jednej aplikacji Flask**) demonstrującą integrację z platformą tożsamości **Auth0**.  

---


## Technologie użyte w projekcie

- **Backend / Frontend (Monolit):** Python 3.x z frameworkiem Flask  
- **Zarządzanie zależnościami:** `python-dotenv`, `requests`, `PyJWT`, `Flask`, 
- **Autoryzacja:** Auth0 (Universal Login + Machine-to-Machine API dla walidacji tokena)

## Instrukcja uruchomienia

### 1. Wymagania wstępne

- Python 3.6+  
- Konto **Auth0** z utworzoną aplikacją (typ: *Regular Web Application*) i API  

---

### 2. Instalacja zależności

```bash
pip install Flask python-dotenv requests PyJWT
```
lub
```bash
pip install -r requirements.txt
```
---
### 3. Konfiguracja Auth0
W repozytorium znajduje się przykładowy plik .env.example, który można wykorzystać, zmieniając nazwę na .env lub

Utwórz plik .env w katalogu głównym projektu z następującymi zmiennymi:
```bash
FLASK_SECRET_KEY="bardzo_tajny_klucz_sesji"

AUTH0_DOMAIN="twoja-domena.eu.auth0.com"     
AUTH0_CLIENT_ID="Twoj_Client_ID"
AUTH0_CLIENT_SECRET="Twoj_Client_Secret"

AUTH0_CALLBACK_URL="http://127.0.0.1:5000/callback"

AUTH0_AUDIENCE="https://twoje-api.example.com"

```

**Uwaga:**  
Upewnij się, że następujące adresy URL są skonfigurowane w ustawieniach Twojej aplikacji w panelu Auth0:  
- **Allowed Callback URLs:** `http://127.0.0.1:5000/callback`  
- **Allowed Logout URLs:** `http://127.0.0.1:5000/`

---

### 4. Uruchomienie aplikacji
`python app.py`

Aplikacja będzie dostępna pod adresem:  
[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---
## Testowanie uprawnień Administratora

Aplikacja sprawdza, czy użytkownik ma uprawnienia administratora, weryfikując pole `permissions` w Access Tokenie.

Aby przetestować logowanie jako administrator:

1.  W panelu Auth0 dla utworzonego API (Audience: `AUTH0_AUDIENCE`), utwórz uprawnienie o nazwie: `admin:access`.
2.  Skonfiguruj regułę w panelu Auth0, która przypisze uprawnienie `admin:access` do wybranego użytkownika testowego.

---

## Opis architektoniczny

### Wybór technologii (Flask)

Wybrano **Flask** ze względu na:
- szybkość prototypowania,  
- możliwość połączenia frontendu i backendu w jednej aplikacji,  
- doświadczenie.

---

### Architektura uwierzytelniania

Aplikacja wykorzystuje Authorization Code Grant Flow dla interaktywnego logowania:

1. Klient (przeglądarka) → `/login`  
2. Flask → przekierowanie do Auth0 `/authorize`  
3. Auth0 → Universal Login → przekierowanie do `/callback`  
4. `/callback` → wymiana kodu autoryzacyjnego na tokeny w `/oauth/token`

---

### Bezpieczeństwo sesji i tokenów

#### Sesja
Stan uwierzytelnienia po stronie serwera (Flask) jest utrzymywany przy użyciu zaszyfrowanych **cookies sesyjnych**.  
Dzięki temu widoki takie jak `/dashboard` są chronione.

#### Weryfikacja JWT
Dla ochrony endpointu **/api/profile** zaimplementowano walidację tokena JWT, z pomocą `PyJWT`.  
Proces obejmuje:

1. Weryfikację nagłówka (`Bearer token`)  
2. Pobranie kluczy publicznych Auth0 (JWKS) w czasie rzeczywistym  
3. Dopasowanie `kid` do właściwego klucza publicznego  
4. Dekodowanie tokena z weryfikacją:
   - sygnatury,  
   - pól `aud`, `iss`, `exp`.


---

*Damian Kloch*  
