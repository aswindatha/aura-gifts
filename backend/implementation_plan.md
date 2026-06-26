# Login & Signup Integration Implementation Plan

## Goal
Ensure the frontend login and signup screens are fully integrated with the FastAPI backend, correctly update the database, and meet production‑ready quality standards. This includes:
- Verifying API calls, request/response handling, and error handling.
- Securing authentication tokens.
- Adding client‑side validation and UI feedback.
- Providing integration tests (curl and optional browser automation).
- Documenting any required backend adjustments.

---

## User Review Required
> [!IMPORTANT]
> Please review the open questions below and provide any preferences or constraints. Your answers will guide the specific code changes.

---

## Open Questions
> [!CAUTION]
> 1. **Token storage** – Do you prefer storing the JWT in `localStorage` (simpler) or using an HttpOnly secure cookie set by the backend?
> 2. **Refresh token flow** – Should we implement a refresh‑token endpoint and automatic token renewal in the frontend?
> 3. **Password policy** – Any specific password complexity requirements (e.g., min length, special characters) to enforce client‑side?
> 4. **CORS configuration** – Are there specific allowed origins for production (e.g., `https://app.aura‑prints.com`) that need to be added to the backend?
> 5. **CSRF protection** – If we move to cookie‑based auth, do you need CSRF tokens for state‑changing requests?
> 6. **UI/UX expectations** – Should error messages be displayed as toast notifications, inline form errors, or both?

---

## Proposed Changes
### Frontend (`frontend/`)
- **`src/pages/Login.jsx`**
  - Ensure the form submits to `POST /api/auth/login`.
  - Add try/catch around the fetch call to display user‑friendly error messages.
  - Store the returned JWT according to the chosen token‑storage strategy.
  - On successful login, redirect to the protected dashboard route.
- **`src/pages/Signup.jsx`** (or component used for registration)
  - Submit to `POST /api/auth/register` with the required payload.
  - Perform client‑side validation (email format, password length, confirm password match).
  - Display success toast and automatically log the user in (call login endpoint) after registration.
- **`src/context/AuthContext.jsx`**
  - Refactor `login` and `register` functions to return a consistent `{ success, data, error }` shape.
  - Centralise token handling (set/remove token, configure `Authorization` header for subsequent API calls).
  - Add a `logout` function that clears token and redirects to login page.
- **CORS & Environment**
  - Add a `.env` file with `REACT_APP_API_URL` pointing to the backend URL (e.g., `http://localhost:8000`).
  - Ensure `fetch` requests use this base URL.
- **UI Enhancements**
  - Use a modern component library (e.g., Material‑UI) for polished inputs and loading spinners.
  - Add inline validation feedback and a global toast system (e.g., `react-toastify`).

### Backend (`backend/app/`)
- **CORS Middleware** – Update `main.py` to allow the production origin(s) defined by the user.
- **Set‑Cookie for JWT** (if cookie‑based storage chosen)
  - Modify the login endpoint to return `Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Strict`.
  - Add a `POST /api/auth/refresh` endpoint if a refresh‑token strategy is required.
- **Input Validation** – Ensure Pydantic models for registration enforce password length and email format.
- **Logging** – (Already added) ensure request/response bodies are logged for debugging.

### Testing & Verification
- **Automated curl suite** – Generate a script that:
  1. Registers a new test user.
  2. Logs in to obtain a JWT.
  3. Calls a protected endpoint (e.g., `/api/users/me`) to verify token works.
  4. Checks the DB (via a simple `SELECT` using `sqlite3` or the project's ORM) that the user row was created.
- **Browser automation** (optional) – Use the `browser_subagent` tool to:
  - Navigate to `/login` page.
  - Fill the form with the test credentials, submit, and verify redirection.
  - Repeat for the signup flow.
- **Unit tests** – Add Jest tests for the AuthContext functions (mocking fetch) to ensure proper error handling.

## Verification Plan
### Automated Tests
- Run the curl script and capture output.
- Verify HTTP status codes are `200`/`201` for successful calls.
- Confirm the JWT is present in the response and can be used for a subsequent request.
- Query the database to ensure a new user row exists with the expected email.

### Manual Checks
- Launch the React dev server (`npm run dev`) and the FastAPI server (`uvicorn app.main:app`).
- Manually test the login and signup pages in a browser.
- Observe the terminal logs for request/response payloads.
- Ensure no sensitive fields (passwords, tokens) are logged in plain text.

---

**Next Steps**
1. Await your answers to the open questions.
2. Upon approval, I will implement the frontend and backend changes, add the test scripts, and run the verification suite.

*All changes will be committed to the existing repository paths; no new directories will be created outside the project.*
