from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import sqlite3
from datetime import date, timedelta

# =====================
# APP
# =====================
app = FastAPI()

# =====================
# STATIC FILES
# =====================
app.mount("/static", StaticFiles(directory="web/templates/static"), name="static")

# =====================
# SESSIONS
# =====================
app.add_middleware(
    SessionMiddleware,
    secret_key="CAMBIA_ESTE_SECRETO"
)

# =====================
# TEMPLATES
# =====================
templates = Jinja2Templates(directory="web/templates")

# =====================
# DATABASE
# =====================
def db_connect():
    return sqlite3.connect("bot.db")

# =====================
# AUTH
# =====================
def require_admin(request: Request):
    return request.session.get("admin")

# =====================
# DASHBOARD
# =====================
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM cuentas")
    total_cuentas = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM cuentas
        WHERE vencimiento IS NOT NULL
        AND date(vencimiento) < date('now')
    """)
    cuentas_vencidas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cur.fetchone()[0]

    conn.close()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "title": "Dashboard",
            "total_cuentas": total_cuentas,
            "cuentas_vencidas": cuentas_vencidas,
            "total_usuarios": total_usuarios,
        }
    )

# =====================
# CUENTAS
# =====================
@app.get("/cuentas", response_class=HTMLResponse)
def cuentas(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, categoria, nombre, correo, password, pantalla, pin, vencimiento
        FROM cuentas
        ORDER BY categoria, nombre
    """)
    cuentas = cur.fetchall()
    conn.close()

    hoy = date.today().isoformat()

    return templates.TemplateResponse(
        request,
        "cuentas.html",
        {
            "request": request,
            "title": "Cuentas",
            "cuentas": cuentas,
            "hoy": hoy,
        }
    )

@app.get("/cuentas/eliminar/{cuenta_id}")
def eliminar_cuenta(request: Request, cuenta_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM cuentas WHERE id = ?", (cuenta_id,))
    conn.commit()
    conn.close()

    return RedirectResponse("/cuentas", status_code=302)

@app.get("/cuentas/renovar/{cuenta_id}")
def renovar_cuenta(request: Request, cuenta_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    nueva_fecha = (date.today() + timedelta(days=30)).isoformat()

    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE cuentas SET vencimiento = ? WHERE id = ?",
        (nueva_fecha, cuenta_id)
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/cuentas", status_code=302)

@app.get("/cuentas/editar/{cuenta_id}", response_class=HTMLResponse)
def editar_cuenta_form(request: Request, cuenta_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, categoria, nombre, correo, password, pantalla, pin, vencimiento
        FROM cuentas
        WHERE id = ?
    """, (cuenta_id,))

    cuenta = cur.fetchone()
    conn.close()

    if not cuenta:
        return RedirectResponse("/cuentas", status_code=302)

    return templates.TemplateResponse(
        request,
        "editar_cuenta.html",
        {
            "request": request,
            "title": "Editar cuenta",
            "cuenta": cuenta,
        }
    )


@app.post("/cuentas/editar/{cuenta_id}")
def editar_cuenta_guardar(
    request: Request,
    cuenta_id: int,
    categoria: str = Form(...),
    nombre: str = Form(...),
    correo: str = Form(...),
    password: str = Form(...),
    pantalla: str = Form(...),
    pin: str = Form(...),
    vencimiento: str = Form("")
):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    vencimiento = vencimiento.strip() or None

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE cuentas
        SET categoria = ?,
            nombre = ?,
            correo = ?,
            password = ?,
            pantalla = ?,
            pin = ?,
            vencimiento = ?
        WHERE id = ?
    """, (
        categoria,
        nombre,
        correo,
        password,
        pantalla,
        pin,
        vencimiento,
        cuenta_id
    ))

    conn.commit()
    conn.close()

    return RedirectResponse("/cuentas", status_code=302)

# =====================
# CREAR CUENTA
# =====================
@app.get("/cuentas/nueva", response_class=HTMLResponse)
def nueva_cuenta_form(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse(
        request,
        "nueva_cuenta.html",
        {"request": request, "title": "Nueva cuenta"}
    )


@app.post("/cuentas/nueva")
def crear_cuenta(
    request: Request,
    categoria: str = Form(...),
    nombre: str = Form(...),
    correo: str = Form(...),
    password: str = Form(...),
    pantalla: str = Form(""),
    pin: str = Form(""),
    vencimiento: str = Form("")
):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    vencimiento = vencimiento.strip() or None

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO cuentas (categoria, nombre, correo, password, pantalla, pin, vencimiento)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        categoria,
        nombre,
        correo,
        password,
        pantalla,
        pin,
        vencimiento
    ))

    conn.commit()
    conn.close()

    return RedirectResponse("/cuentas", status_code=302)
# =====================
# USUARIOS
# =====================
@app.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, password, rol
        FROM usuarios
        ORDER BY username
    """)
    usuarios = cur.fetchall()

    conn.close()

    return templates.TemplateResponse(
        request,
        "usuarios.html",
        {
            "request": request,
            "title": "Usuarios",
            "usuarios": usuarios,
        }
    )


@app.post("/usuarios/crear")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    rol: str = Form(...)
):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
            (username, password, rol)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return RedirectResponse("/usuarios", status_code=302)

    conn.close()
    return RedirectResponse("/usuarios", status_code=302)


@app.get("/usuarios/eliminar/{usuario_id}")
def eliminar_usuario_web(request: Request, usuario_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()

    return RedirectResponse("/usuarios", status_code=302)

# =====================
# VENCIMIENTOS
# =====================
@app.get("/vencimientos", response_class=HTMLResponse)
def vencimientos(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, categoria, nombre, correo, password, pantalla, pin, vencimiento
        FROM cuentas
        WHERE vencimiento IS NOT NULL
        ORDER BY date(vencimiento) ASC
    """)
    cuentas = cur.fetchall()

    conn.close()

    hoy = date.today().isoformat()

    return templates.TemplateResponse(
        request,
        "vencimientos.html",
        {
            "request": request,
            "title": "Vencimientos",
            "cuentas": cuentas,
            "hoy": hoy,
        }
    )

# =====================
# LOGIN
# =====================
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "title": "Login"
        }
    )

@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT rol
        FROM usuarios
        WHERE username = ? AND password = ?
    """, (username, password))

    user = cur.fetchone()
    conn.close()

    if not user or user[0] != "admin":
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "title": "Login",
                "error": "Credenciales inválidas"
            }
        )

    request.session["admin"] = True
    request.session["username"] = username

    return RedirectResponse("/", status_code=302)

# =====================
# LOGOUT
# =====================
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)