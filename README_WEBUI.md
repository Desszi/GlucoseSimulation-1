# Glucose Simulation Web UI (MVP)

End-to-end MVP platform T1D szimulációhoz, étkezések és egyszerű szimulációs futások kezeléséhez, valamint alap beteg–orvos chat funkcióhoz.

## Mappa struktúra (részlet)
```
backend/app/            FastAPI alkalmazás (modellek, sémák, routerek)
frontend/               React + Vite kliens
simulation_core.py      Részletesebb szimuláció / RL logika (nem bekötve webbe)
Results/, SimResults/   Korábbi lokális futások / CSV-k
simruns/<run_id>/       API által generált artifaktok (chart.png, log.csv, metrics.json)
README_WEBUI.md         Ez a dokumentum
```

## Backend (FastAPI)

Indítás fejlesztői módban (automatikus reload):
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Alap endpointok (auth szükséges kivéve a websocket):
- `POST /auth/register` – új felhasználó (role: patient vagy doctor). Patient esetén automatikus üres profil.
- `POST /auth/login` – JWT token (access_token, user_id, role).
- `GET /patients/me` – Beteg saját profil adatainak lekérése.
- `PATCH /patients/me` – Profil frissítése.
- `GET /meals/` – Étkezések listázása (beteg saját étkezései).
- `POST /meals/` – Új étkezés.
- `GET /meals/{id}` / `PATCH /meals/{id}` / `DELETE /meals/{id}` – Étkezés kezelése.
- `POST /simulation/run` – Kiválasztott étkezésekből egyszerű szimuláció futtatása.
- `GET /simulation/runs` – Korábbi futások listája.
- `GET /simulation/runs/{id}` – Futás részletei.
- `GET /simulation/runs/{id}/chart` – Futás chart képe (PNG).
- `GET /chat/history?patient_id=..&doctor_id=..` – Chat előzmények.
- `WS /chat/ws/patient_<pid>_doctor_<did>` – WebSocket chat szoba (MVP: auth nélküli, minden üzenet `sender_user_id=0`).

Adatmodellek (SQLModel): User, Patient, Meal, SimulationRun, Message.

### Auth
JWT token a login válaszban. A kliens a `Authorization: Bearer <token>` fejlécet küldi. A WebSocket jelenleg nem használ authot – fejlesztési feladat.

## Frontend (React + Vite)

Fejlesztői környezet:
```bash
cd frontend
npm install
npm run dev
```
Alap port: 5173 (Vite). Backend: 8000.

### Oldalak / útvonalak
- `/login` – Bejelentkezés.
- `/` – Dashboard (linkek a többi oldalhoz).
- `/meals` – Étkezés CRUD.
- `/profile` – Beteg profil szerkesztés.
- `/simulate` – Új szimuláció indítása kiválasztott étkezésekkel.
- `/runs` – Korábbi szimulációk + chart + metrikák.
- `/chat` – Beteg chat (manuális patient/doctor ID megadás).
- `/doctor/patients` – Orvos nézet placeholder (hiányzó backend endpoint).
- `/doctor/chat` – Orvos chat nézet.

### Fő komponensek
- `AuthContext` – Token / szerep / user ID tárolás localStorage-ben.
- `useApi` – Egyszerű fetch wrapper (GET/POST/PATCH/DELETE) automatikus Authorization headerrel.
- `ChartWithMetrics` – Chart és metrikák megjelenítése egy futásból.

### Artifaktok
Szimuláció futásakor létrejönnek: `simruns/<id>/chart.png`, `log.csv`, `metrics.json`. A futás rekord a chart relatív elérési útját tartalmazza.

## Gyors kipróbálás
1. Indítsd a backendet.
2. Regisztrálj egy patient felhasználót:
	```bash
	curl -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' -d '{"username":"p1","password":"test","role":"patient"}'
	```
3. Login és token kinyerése:
	```bash
	curl -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' -d '{"username":"p1","password":"test"}'
	```
4. A tokennel hozz létre étkezéseket (`/meals/`).
5. Menj a frontend `/simulate` oldalra és futtasd a szimulációt.
6. Nézd meg az eredményt a `/runs` oldalon.

## Ismert Hiányosságok / TODO
- WebSocket auth (token átadás, valódi feladó azonosítása).
- Orvoshoz rendelt beteg lista endpoint.
- Komplexebb szimuláció (inzulin szabályok, posztprandiális fázisok).
- Biztonsági / rate limit réteg.
- Tesztek (unit/integration) hozzáadása.
- SHAP feature kiterjesztés UI felé.

## Fejlesztési ötletek
1. `doctor_patient` kapcsoló tábla (many-to-many) – orvos jogosultság ellenőrzés futások és chathez.
2. WebSocket token query param (`ws://.../chat/ws/room?token=...`) és szerver oldali dekódolás.
3. Szimuláció futás queue (BackgroundTask / Celery) hosszabb futásokhoz.
4. Metrikák bővítése: idő a cél tartományban (70-130), variancia, postprandiális csúcs késés.
5. Frontend routing refaktor (`react-router-dom`) a manuális pathname logika helyett.

## Környezet / Verziók
- Python >= 3.10
- FastAPI
- SQLModel + SQLite (dev)
- React 18 + Vite 5 + TypeScript 5

## Indítási parancsok összefoglaló
```bash
# Backend
python -m uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Biztonsági megjegyzés
MVP státusz: ne használd éles / személyes egészségügyi adatokkal. Hiányzik: titkosítás, audit log, jogosultság finomhangolás, adatvédelem.

## Licence / Felhasználás
Fejlesztési / kutatási célokra. Klinikai döntéstámogatásra nem alkalmas.
