import streamlit as st
import pandas as pd, sqlite3, unicodedata, re
from difflib import get_close_matches
from datetime import date

st.set_page_config(page_title="SEMEDIC - Honorarios", layout="wide")

# --- LOGIN ---
USUARIOS = {
    "admin": {"password": "semedic2026", "rol": "ADMINISTRADOR"},
    "consulta": {"password": "consulta2026", "rol": "CONSULTA"},
}
if "logueado" not in st.session_state:
    st.session_state.logueado = False
if not st.session_state.logueado:
    st.title("SEMEDIC - Honorarios Médicos")
    st.subheader("Iniciar Sesión")
    u = st.text_input("Usuario")
    c = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if u in USUARIOS and USUARIOS[u]["password"] == c:
            st.session_state.logueado = True
            st.session_state.usuario = u
            st.session_state.rol = USUARIOS[u]["rol"]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

es_admin = st.session_state.rol == "ADMINISTRADOR"
st.sidebar.write(f"👤 {st.session_state.usuario} | Rol: {st.session_state.rol}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logueado = False
    st.rerun()

# --- BASE DE DATOS ---
conn = sqlite3.connect("honorarios.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS honorarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, medico TEXT, paciente TEXT,
  codigo TEXT, descripcion TEXT, seguro TEXT, tramite TEXT, mes_anio TEXT,
  participacion TEXT, valor REAL, valor_institucional REAL, valor_medico REAL,
  valor_objetado REAL DEFAULT 0, valor_final_medico REAL, estado TEXT,
  es_paquete INTEGER DEFAULT 0, valor_hospitalario REAL DEFAULT 0, observacion TEXT)""")
conn.execute("""CREATE TABLE IF NOT EXISTS medicos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, cedula TEXT, especialidad TEXT, registro_senescyt TEXT, activo INTEGER DEFAULT 1)""")
conn.execute("""CREATE TABLE IF NOT EXISTS desglose_paquete (
  id INTEGER PRIMARY KEY AUTOINCREMENT, id_paquete INTEGER, codigo_paquete TEXT,
  paciente TEXT, medico TEXT, rol TEXT, codigo_individual TEXT, valor_individual REAL)""")
conn.commit()

def normalizar_nombre(n):
    if not n: return ""
    n = n.upper().strip()
    n = ''.join(x for x in unicodedata.normalize('NFD', n) if unicodedata.category(x) != 'Mn')
    n = re.sub(r'[^A-Z ]', '', n); n = re.sub(r'\s+', ' ', n).strip()
    return ' '.join(sorted(n.split()))

CODIGOS_PAQUETE = ["70200003","70200004","70200005","999999"]
MEDICOS_DEFAULT = ["GARCIA LOPEZ MARIO GIOVANNY","PILLIGUA HOLGUIN LUIS HERNAN","FREIRE MOREJON PAUL XAVIER","SALGADO ROSADO PABLO RAFAEL"]
SEGUROS = ["ISSPOL","ISSFA","SPPAT","MSP","IESS","IESS-CA"]
ESTADOS = ["PENDIENTE","ENTREGADO","RECIBIDO ISSPOL","AUDITADO DOCUMENTAL","LIQUIDADO","PAGADO","OBJETADO"]

st.title("SEMEDIC • Honorarios Médicos")
menu = st.sidebar.selectbox("Menú", ["Dashboard","Nuevo Honorario","Importar Archivos","Sin Médico Asignado","Médicos","Actualizar Trámites","Paquetes Desglosados","Listado / Buscar"])

if menu == "Dashboard":
    df = pd.read_sql("SELECT * FROM honorarios", conn)
    if len(df)==0: st.info("Aún no hay registros. Ve a Nuevo Honorario.")
    else:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Planillado", f"${df['valor'].sum():,.2f}")
        c2.metric("Institucional 40%", f"${df['valor_institucional'].sum():,.2f}")
        c3.metric("A Pagar Médicos", f"${df['valor_final_medico'].sum():,.2f}")
        c4.metric("Objetado", f"${df['valor_objetado'].sum():,.2f}")
        st.subheader("Por Médico"); st.bar_chart(df.groupby("medico")["valor_final_medico"].sum())
        st.subheader("Por Seguro"); st.bar_chart(df.groupby("seguro")["valor_final_medico"].sum())

if menu == "Nuevo Honorario":
    if not es_admin: st.info("🔒 Solo consulta. Necesitas ser Administrador para registrar.")
    else:
        with st.form("form"):
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha", date.today()); medico = st.selectbox("Médico", ["SIN ASIGNAR"]+MEDICOS_DEFAULT)
                paciente = st.text_input("Paciente *").upper(); codigo = st.text_input("Código *")
            with col2:
                descripcion = st.text_area("Descripción"); seguro = st.selectbox("Seguro", SEGUROS)
                tramite = st.text_input("N° Trámite"); valor = st.number_input("Valor Total $", min_value=0.0, step=0.01)
                estado = st.selectbox("Estado", ESTADOS)
            es_paquete = st.checkbox("¿Es Paquete? (Total estancia, no solo honorarios)")
            enviar = st.form_submit_button("Guardar")
            if enviar:
                inst = round(valor*0.40,2); med = round(valor*0.60,2)
                conn.execute("INSERT INTO honorarios (fecha,medico,paciente,codigo,descripcion,seguro,tramite,mes_anio,valor,valor_institucional,valor_medico,valor_final_medico,estado,es_paquete,valor_hospitalario) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(fecha),medico,paciente,codigo,descripcion,seguro,tramite,fecha.strftime("%B-%Y").upper(),valor,inst,med,med,estado,1 if es_paquete else 0,0))
                conn.commit(); st.success(f"Guardado! Institucional ${inst} | Médico ${med}")

if menu == "Sin Médico Asignado":
    df = pd.read_sql("SELECT * FROM honorarios WHERE medico='SIN ASIGNAR' OR medico='' OR medico IS NULL", conn)
    st.write(f"Hay {len(df)} honorarios sin médico"); st.dataframe(df, use_container_width=True)
    if es_admin and len(df)>0:
        for _, fila in df.iterrows():
            with st.expander(f"{fila['paciente']} - {fila['codigo']} - ${fila['valor']}"):
                nm = st.selectbox(f"Asignar a {fila['id']}", MEDICOS_DEFAULT, key=f"m_{fila['id']}")
                if st.button("Guardar", key=f"b_{fila['id']}"):
                    conn.execute("UPDATE honorarios SET medico=? WHERE id=?", (nm, fila['id'])); conn.commit(); st.success("Asignado"); st.rerun()

if menu == "Médicos":
    st.subheader("Listado de Médicos")
    archivo = st.file_uploader("Subir listado actualizado Staff (Excel)", type=["xlsx"])
    if archivo and es_admin:
        dfm = pd.read_excel(archivo); st.success(f"Se cargaron {len(dfm)} médicos"); st.dataframe(dfm)
    if es_admin:
        with st.form("nm"):
            n = st.text_input("Nombre *").upper(); ced = st.text_input("Cédula"); esp = st.text_input("Especialidad"); sen = st.text_input("SENESCYT")
            if st.form_submit_button("Agregar Médico"):
                conn.execute("INSERT OR REPLACE INTO medicos (nombre,cedula,especialidad,registro_senescyt) VALUES (?,?,?,?)", (n,ced,esp,sen)); conn.commit(); st.success("Médico agregado")
    st.dataframe(pd.read_sql("SELECT * FROM medicos", conn))

if menu == "Actualizar Trámites":
    if not es_admin: st.info("🔒 Solo consulta.")
    else:
        st.subheader("Actualizar con Excel de Trámites")
        st.info("Tu Excel solo necesita: N° TRAMITE y ESTADO")
        arch = st.file_uploader("Sube Excel de trámites", type=["xlsx"])
        if arch:
            dft = pd.read_excel(arch); st.dataframe(dft.head())
            if st.button("Aplicar actualización"):
                for _, r in dft.iterrows():
                    # Busca columna trámite y estado aunque tenga otro nombre
                    cols = {c.strip().upper(): c for c in dft.columns}
                    col_t = next((cols[c] for c in cols if "TRAMITE" in c or "OFICIO" in c), None)
                    col_e = next((cols[c] for c in cols if "ESTADO" in c), None)
                    if col_t and col_e:
                        conn.execute("UPDATE honorarios SET estado=? WHERE tramite=?", (str(r[col_e]).upper(), str(r[col_t])))
                conn.commit(); st.success("Trámites actualizados")

if menu == "Paquetes Desglosados":
    df = pd.read_sql("SELECT * FROM honorarios WHERE es_paquete=1", conn)
    st.dataframe(df, use_container_width=True)
    st.info("El total del paquete es por toda la estancia. Lo que sobra después de desglosar honorarios queda como Valor Hospitalario.")

if menu == "Listado / Buscar":
    df = pd.read_sql("SELECT * FROM honorarios ORDER BY fecha DESC", conn)
    bus = st.text_input("Buscar paciente, médico, código, trámite")
    if bus: df = df[df.apply(lambda r: bus.upper() in str(r.values).upper(), axis=1)]
    st.dataframe(df, use_container_width=True)
