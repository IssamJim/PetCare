# Client registration

The login page's **Regístrate** link opens `/registro/`. Successful registration redirects to `/registro/exitoso/`, where a Spanish SweetAlert2 notification offers **Iniciar sesión** and returns to the existing `/loguearse` login page. Without JavaScript, the success page retains the same message and a working login link.

## Files and integration

- `proyecto/forms.py`: `RegistroClienteForm` extends Django's `UserCreationForm` using `get_user_model()`. It requires all six fields, reuses the model's username rules and configured password validators, trims identity fields, validates email with Django's model-derived `EmailField`, and preserves passwords exactly before Django hashes them.
- `proyecto/views.py`: registration and success views, transaction handling, Spanish validation feedback, and authorization checks on the existing account-management views. Existing login and logout logic are unchanged.
- `PetCare/urls.py`: two new named routes, `registro_cliente` and `registro_exitoso`.
- `proyecto/Templates/Login/index.html`: only the registration link was connected and its label accented.
- `proyecto/Templates/Registro/`: a small public registration base plus form and success templates. This keeps the authenticated dashboard shell out of public registration without refactoring the working login template. The new templates reuse bundled AdminLTE CSS, SweetAlert2, and the existing logo/gradient style.
- `static/css/registro.css` and `static/js/registro.js`: responsive layout, accessible field errors, one consolidated pop-up per failed submission, frontend checks, and a disabled/pending submit state.
- `proyecto/models.py` and migrations `0002`/`0003`: the database email constraint and reconciliation of existing role migration history.
- `proyecto/tests.py`, `proyecto/test_browser.py`, `PetCare/test_settings.py`, and `tests/registration_browser.cjs`: backend, concurrency, and optional real-browser checks using a separate MySQL test database.

## Validation and permissions

Frontend validation checks required values, email format, and exact password confirmation. Backend validation remains authoritative with JavaScript disabled or bypassed. Invalid submissions keep the entered non-password fields, clear both password inputs, display errors next to their fields with ARIA associations, and consolidate errors in a Spanish pop-up. Django translations are scoped to registration; global language settings are unchanged.

The only accepted model fields are first name, last name, username, and email. The inherited password fields use Django's validators and hashing. The server always looks up the existing `Tipo` named `Cliente` and sets `is_staff=False` and `is_superuser=False`. Submitted role, group, or permission values are ignored. If the client role is missing, registration fails without creating an account or inventing a role.

Saving occurs inside `transaction.atomic()`. Database uniqueness handles simultaneous registration requests; integrity errors become Spanish form errors after rollback. CSRF protection is retained, registration responses are not cached, and sensitive POST parameters are marked for Django error reporting. No email-verification system or automatic login was added.

Public clients are also denied access to `vista_usuario` and `crear_usuario`. Those existing routes previously accepted every authenticated user, which would let a public registrant create an administrator. They now require a superuser or the existing `Root`/`Administrador` role. Their authorized workflows and the authentication configuration are preserved.

## Why two migrations are necessary

Inspection of local MySQL 8.4.3 found:

- `AUTH_USER_MODEL` is `proyecto.User`, stored in `petcaredb.proyecto_user`.
- The existing roles are `Root`, `Administrador`, and `Cliente`.
- Username already has a unique index and case-insensitive collation.
- Email has case-insensitive collation but no unique index.
- All three pre-existing accounts have blank email addresses.
- `proyecto_tipo` and `proyecto_user.tipo_id` already exist, although the checked-in migration history contains neither.

`0002_reconcile_existing_roles` records the missing role model/field in Django's migration state. It adopts the existing table and column without changing them or any account records; in a fresh test database it creates the missing schema. Its reverse operation deliberately preserves role data.

`0003_unique_client_email` adds a unique expression index on `NULLIF(LOWER(TRIM(email)), '')`. This enforces case-insensitive uniqueness for nonblank addresses, including concurrent writes, while leaving the existing blank addresses valid and unchanged. A plain `unique=True` would conflict with those existing blank emails. A preflight check stops if nonblank duplicates exist; it never rewrites or removes accounts. The migration requires a database supporting expression indexes (verified on this project's MySQL 8.4.3).

Both migrations were applied successfully to local `petcaredb` on 2026-10-09. A before/after comparison confirmed that all three existing account records, role records, and group/permission memberships were unchanged. The email unique index is present, Django's system check passes, and `makemigrations --check --dry-run` reports no changes. No new user table was created in the existing database.

For another installation, apply these checked-in migrations before enabling registration:

```powershell
.\petcare_env\Scripts\python.exe -B manage.py migrate proyecto
```

Fresh installations must provision the existing `Cliente` role through their authorized setup process. No public request creates or changes role definitions.

## Verification

The 25 backend tests passed on an isolated MySQL database, covering required fields, invalid email/username, duplicate username and case-insensitive email, password mismatch and configured validators, hashing, whitespace handling, permission injection, client account-management denial, rollback, database errors, CSRF, replayed submissions, success-page handling, escaped output, legacy blank emails, and existing administrator login/account creation. Two of those tests force simultaneous submissions after validation: one for the same email and one for the same username; each creates exactly one account.

The real-browser test passed in headless Microsoft Edge at 1366×1100 and 390×844. It checks the registration link, responsive layout, frontend error pop-ups without a POST, backend weak-password errors, retained identity values and cleared passwords, disabled pending state, duplicate-submit prevention, success notification and acknowledgment, existing login, duplicate-email feedback, and server-side errors with JavaScript disabled. Screenshots are saved in `artifacts/registration-*.png`.

Run the backend tests with:

```powershell
.\petcare_env\Scripts\python.exe -B manage.py test proyecto.tests --settings=PetCare.test_settings
```

The test runner creates and removes **`test_petcaredb_registration`**, not `petcaredb`. Reserve that name exclusively for tests; do not point the test configuration at a database containing real records.

The optional browser test requires Node.js, the Playwright package on Node's module path, and a supported installed browser. With those available:

```powershell
$env:PETCARE_BROWSER_TESTS = '1'
$env:PETCARE_BROWSER_CHANNEL = 'msedge'
$env:PYTHONDONTWRITEBYTECODE = '1'
.\petcare_env\Scripts\python.exe -B manage.py test proyecto.test_browser --settings=PetCare.test_settings
```

Use `NODE_PATH` if Playwright is installed outside the project's normal module lookup paths. Playwright is test tooling only; registration adds no runtime framework or downloaded dependency.

Real mobile hardware, Safari, Firefox, and production hosting were not tested. Browser account creation used only the disposable test database; no demonstration accounts were added to `petcaredb`.
