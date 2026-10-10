# PetCare unused-code audit

Scan date: 2026-10-09. Application files were not changed or deleted.

## Scope and method

Inventoried all 2,086 Git-tracked files (82.43 MiB), reviewed all 15 project Python files and all four HTML templates, and traced template asset references into bundled CSS/font dependencies and source-map comments. The 2,056 static assets were analyzed for reference reachability, not individually reviewed for unused internal library functions. Installed packages in `petcare_env` and Git internals are excluded from cleanup candidates. The virtual environment is already excluded by its own `.gitignore`; no root `.gitignore` exists.

Python syntax parsing, import-use inspection, Django's resolved routes, template loading, and migration state were checked. Dynamic asset references, external consumers, and browser interaction coverage are not exhaustively verified. An asset with no discovered reference is a cleanup candidate, not proof that it is safe to delete.

## Confirmed unused or redundant application code

| Finding | Location | Evidence and proposed cleanup |
| --- | --- | --- |
| Entire duplicate view module, 50 lines | `proyecto/urls.py:1` | Contains six view functions but no `urlpatterns`. `ROOT_URLCONF` points to `PetCare.urls`, whose six application routes all resolve to `proyecto.views`. No project code imports or includes this module. Remove the unused module after checking for external consumers; retain `PetCare/urls.py`. |
| Unused imports | `proyecto/views.py:8`, `:9` | `get_object_or_404` and `JsonResponse` are never used. Remove the imports. |
| Duplicate decorator import | `proyecto/views.py:11` | `login_required` is already imported on line 5. Remove the duplicate. |
| Overwritten model import | `proyecto/views.py:2` | The imported `User` is replaced by `User = get_user_model()` on line 13 before any use. Import only `Tipo` on line 2 and keep the configured user-model lookup. |
| Unused local result | `proyecto/views.py:89` | The result of `User.objects.create(...)` is assigned to `user` but never read. Remove only `user =`; the database creation call is required. |
| Empty scaffold imports | `proyecto/admin.py:1`, `proyecto/tests.py:1` | `admin` and `TestCase` are imported without any registrations or tests. Imports can be removed; these files may remain as scaffolding. The unused `path` import in `proyecto/urls.py:1` disappears with that module. |
| Inactive-user branch cannot run with the configured backend | `proyecto/views.py:31` | No custom authentication backend is configured. The installed default backend rejects inactive users before returning from `authenticate`, so its nested inactive-account message cannot be reached. Simplify only if retaining that backend behavior. |

All six functions in `proyecto/views.py` are routed and must be retained. `vista_login` and `custom_login` both render the login template, but both currently have entry points.

## Copied template and JavaScript leftovers

| Finding | Location | Evidence and proposed cleanup |
| --- | --- | --- |
| Demo-site tracking scripts | `proyecto/Templates/base.html:3` and `:52` | Lines 3–34 and 52–163 contain copied Zaraz/tag-manager bootstrap code, `/cdn-cgi/zaraz/*`, `/wzrt/*`, fixed nonces, and empty immediately invoked functions. The embedded payload references the AdminLTE demo site. No matching application routes or assets exist in this repository. Remove these copied blocks unless separately configured by a deployment proxy. |
| Browser-extension attributes | `proyecto/Templates/base.html:167` | `data-new-gr-c-s-check-loaded` and `data-gr-ext-installed` are captured browser-extension metadata; remove them. |
| Table initialization with no table | `proyecto/Templates/Login/index.html:85` | The `#vistahoraria` selector has no corresponding element in any template. The surrounding script contains a copied doctor-schedule notification and permission/timer flow unrelated to the visible login form. The page also invokes `$` without loading jQuery. Remove lines 85–113 and the corresponding DataTables/Toastr CDN CSS and JS on lines 11–12 and 65–66 if the copied schedule feature is unwanted. Keep the password visibility handler on lines 68–83. |
| Unused login-page JavaScript dependencies | `proyecto/Templates/Login/index.html:63` | Popper and Bootstrap JS have no component or API consumer in this standalone login template. They are additional removal candidates; retain Bootstrap CSS and the icon stylesheet. |
| Demo content and dead navigation | `proyecto/Templates/base.html:183`, `:194`, `:282`; `proyecto/Templates/home/index.html:11`; `proyecto/Templates/usuario/index.html:42` | Links to `../../index3.html`, hardcoded notifications, “Blank Page”, “Title”, “Footer”, and “Start creating your amazing application!” are template-demo content. Replace or remove intentionally; these are visible UI, not unreachable code. Empty registration/profile links are also unfinished UI. |
| Uninitialized Select2 marker | `proyecto/Templates/usuario/index.html:83` | The `select2` class has no plugin load or initialization. The native select still works. Remove the marker if enhanced selection is not intended; keeping the class does not make the local Select2 package used. |

## Static-asset candidates

Only seven local assets are directly referenced by templates:

- `static/dist/css/adminlte.min.css`
- `static/dist/js/adminlte.min.js`
- `static/plugins/jquery/jquery.min.js`
- `static/plugins/bootstrap/js/bootstrap.bundle.min.js`
- `static/plugins/fontawesome-free/css/all.min.css`
- `static/img/logo.png`
- `static/img/user.jpg`

The conservative dependency walk retains 26 assets, including font variants and discovered source maps. It finds **2,030 assets totaling 70.90 MiB with no discovered reference path**. This figure includes alternative builds, source maps, demo assets, and license documents; it is not an automatic deletion list. `UNREFERENCED_ASSETS.txt` lists the exact candidates and byte sizes.

The largest entirely unreferenced plugin directories are:

| Directory | Files | MiB |
| --- | ---: | ---: |
| `static/plugins/pdfmake` | 5 | 12.010 |
| `static/plugins/summernote` | 224 | 6.669 |
| `static/plugins/flag-icon-css` | 536 | 5.113 |
| `static/plugins/jqvmap` | 32 | 4.043 |
| `static/plugins/moment` | 143 | 2.640 |
| `static/plugins/codemirror` | 262 | 2.287 |
| `static/plugins/popper` | 25 | 1.533 |
| `static/plugins/chart.js` | 6 | 1.344 |

`static/dist/img` contains 33 unreferenced demo images (2.884 MiB). `static/dist/js/demo.js` and the three `static/dist/js/pages/dashboard*.js` files are not loaded. Much of `static/dist/css` consists of alternative theme builds and maps. Libraries loaded from a CDN on the login page do not reference the local copies of DataTables, Toastr, or Popper.

Do not trim unused methods from minified vendor libraries. Keep required fonts and associated licensing for any retained packages. Source maps and readable library builds can be useful for debugging even when the application does not load them.

## Generated files

Eleven `.pyc` files inside tracked `__pycache__` directories are reproducible Python bytecode. They should be removed from version control and ignored with root rules for `__pycache__/` and `*.py[cod]`. They are listed by `git ls-files '*.pyc'`. The scan used `python -B` so validation would not rewrite these tracked caches.

Keep `__init__.py`, migrations, `apps.py`, and the ASGI/WSGI entry points. Framework loading and deployment use them even when a plain reference search finds no caller. The configured mail backend was also checked against the installed Django package; `MAILERS` is supported here and was not marked obsolete.

## Related defects: repair instead of deleting

1. **Missing template:** `proyecto/views.py:120` renders `usuario/crear.html`, which does not exist. The GET branch of the routed `crear_usuario` view is reachable, so its user-list queries and context are not safely classified as dead code. Implement the intended template/response or explicitly make the endpoint POST-only.
2. **Migration gap:** `proyecto/models.py:6` defines `Tipo` and line 13 defines `User.tipo`, but the only checked-in migration creates `User` without either. Django's migration state confirms this. Add an appropriate new migration; do not delete the models or existing migration. The live database schema was not inspected.

## Validation and suggested cleanup order

- Parsed every project Python file successfully.
- Verified all six application URL callbacks resolve to `proyecto.views`.
- Loaded all four existing templates successfully; separately confirmed `usuario/crear.html` is missing.
- Ran `petcare_env/Scripts/python.exe -B manage.py check`: **passed with no issues** after the authorized retry outside the sandbox allowed access to local MySQL. This check does not establish migration parity or exercise browser behavior.
- No functional tests exist in `proyecto/tests.py`; no end-to-end user flow was run.

First remove the disconnected module, redundant imports, and tracked caches. Then clean the copied scripts and visible demo content. Prune unused asset directories in a separate change and verify login/password visibility, dashboard sidebar/fullscreen/card controls, logout, and the user-creation modal. Address the missing template and migration gap as functional fixes.
