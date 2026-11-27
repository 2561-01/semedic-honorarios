import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import datetime, date

st.set_page_config(page_title="Hospital Semedic - Honorarios Médicos", layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1rem !important; max-width: 1400px;}
    header {visibility: hidden;}
    .header-real {display:flex; align-items:center; gap:12px; padding: 8px 0 4px 0; border-bottom: 1px solid #E5E7EB; margin-bottom: 10px;}
    .hs {background: #0B2A6B; color: white; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 20px;}
    .title1 {font-weight: 800; font-size: 20px; line-height: 1.1; color: #111827; margin:0;}
    .title2 {font-size: 12px; color: #0B2A6B; font-weight: 800; letter-spacing: 1.5px; margin:0;}
    .box-verde {background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 14px; padding: 16px;}
    .box-azul {background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 14px; padding: 16px;}
    .stButton>button {border-radius: 8px !important; font-weight: 600 !important;}
    div[data-testid="stSelectbox"] > div {border-radius: 10px !important;}
    div[data-testid="stTextInput"] input {border-radius: 12px !important; background: #F9FAFB !important;}
    button[data-baseweb="tab"] {font-size: 15px !important; font-weight: 600 !important; padding: 10px 16px !important;}
    button[data-baseweb="tab"][aria-selected="true"] {color: #0B2A6B !important; border-bottom: 3px solid #0B2A6B !important;}
</style>
""", unsafe_allow_html=True)

if "login" not in st.session_state:
    st.session_state.login = False
if not st.session_state.login:
    st.markdown('<div style="display:flex;justify-content:center;padding-top:60px;"><div style="width:420px;text-align:center;"><div style="background:#0B2A6B;color:white;width:60px;height:60px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:24px;margin:0 auto;">HS</div><h2 style="margin:10px 0 0;">Hospital Semedic</h2><p style="color:#0B2A6B;font-weight:800;letter-spacing:1px;font-size:13px;">HONORARIOS MÉDICOS</p></div></div>', unsafe_allow_html=True)
    c = st.columns([1,1,1])[1]
    with c:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar", use_container_width=True):
            if u == "admin" and p == "semedic2026":
                st.session_state.login = True
                st.session_state.usuario = "mseijas"
                st.session_state.rol = "ADMINISTRADOR"
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrecta")
    st.stop()

col_logo, col_user = st.columns([4, 1])
with col_logo:
    st.markdown("""
    <div class="header-real">
      <div class="hs">HS</div>
      <div>
        <p class="title1">Hospital Semedic</p>
        <p class="title2">HONORARIOS MÉDICOS</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
with col_user:
    st.write(f"👤 **{st.session_state.usuario}**")
    st.caption(st.session_state.rol)
    if st.button("Salir", use_container_width=True):
        st.session_state.login = False
        st.rerun()

conn = sqlite3.connect("honorarios.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS honorarios (
    paciente TEXT, medico TEXT, fecha TEXT, codigo TEXT,
    descripcion TEXT, valor REAL, seguro TEXT, tramite TEXT,
    mes_anio TEXT, valor_40 REAL, valor_50 REAL, valor_60 REAL,
    estado TEXT, estado_tramite TEXT, estado_pago TEXT, valor_pagado REAL,
    es_paquete INTEGER DEFAULT 0
)""")
for col, tipo in [("estado_pago","TEXT DEFAULT 'Pendiente'"), ("valor_pagado","REAL DEFAULT 0"), ("es_paquete","INTEGER DEFAULT 0"), ("valor_40","REAL DEFAULT 0"), ("valor_50","REAL DEFAULT 0"), ("valor_60","REAL DEFAULT 0"), ("estado_tramite","TEXT DEFAULT 'Pendiente'"), ("estado","TEXT DEFAULT 'Pendiente'"), ("paciente","TEXT"), ("medico","TEXT"), ("tramite","TEXT"), ("codigo","TEXT"), ("mes_anio","TEXT"), ("fecha","TEXT")]:
    try:
        cols_ex = [r[1] for r in conn.execute("PRAGMA table_info(honorarios)").fetchall()]
        if col not in cols_ex:
            conn.execute(f"ALTER TABLE honorarios ADD COLUMN {col} {tipo}")
    except:
        pass
conn.execute("""CREATE TABLE IF NOT EXISTS medicos (
    nombre TEXT, cedula TEXT, especialidad TEXT, registro_senescyt TEXT
)""")
conn.commit()

MESES_ES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
MESES_INV = {v: k for k, v in MESES_ES.items()}
def solo_fecha(valor):
    if pd.isna(valor) or str(valor).strip() == "" or str(valor).strip().lower() in ["nan", "none", "nat"]:
        return ""
    s = str(valor).strip()
    if " " in s:
        s = s.split(" ")[0]
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except:
        pass
    return s[:10]

def mes_anio_de_fecha(valor_fecha, valor_mes_anio=""):
    if valor_mes_anio and str(valor_mes_anio).strip() != "" and str(valor_mes_anio).strip().lower() not in ["nan", "none"]:
        vm = str(valor_mes_anio).strip()
        if "-" in vm and len(vm) == 7 and vm[:4].isdigit():
            try:
                anio = int(vm[:4]); mes = int(vm[5:7])
                return f"{MESES_ES.get(mes, '')}-{anio}"
            except:
                pass
        return vm
    f = solo_fecha(valor_fecha)
    if f == "":
        return ""
    try:
        dt = pd.to_datetime(f, errors="coerce")
        if pd.notna(dt):
            return f"{MESES_ES.get(dt.month, '')}-{dt.year}"
    except:
        pass
    return ""

def ordenar_mes_anio(m):
    try:
        nombre, anio = str(m).split("-")
        return (int(anio), MESES_INV.get(nombre, 0))
    except:
        return (0, 0)

def cargar_honorarios():
    df = pd.read_sql("SELECT rowid as id, * FROM honorarios", conn)
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def arreglar_df(df):
    if len(df) == 0:
        return df
    if "id" not in df.columns:
        df["id"] = range(1, len(df)+1)
    if "valor" not in df.columns:
        df["valor"] = 0
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    if "valor_60" not in df.columns or df["valor_60"].isna().all():
        df["valor_60"] = (df["valor"] * 0.60).round(2)
    df["valor_60"] = pd.to_numeric(df["valor_60"], errors="coerce").fillna(0)
    if "estado_pago" not in df.columns:
        df["estado_pago"] = "Pendiente"
    df["estado_pago"] = df["estado_pago"].fillna("Pendiente").astype(str).str.strip()
    if "estado_tramite" not in df.columns:
        df["estado_tramite"] = df["estado"].fillna("Pendiente") if "estado" in df.columns else "Pendiente"
    df["estado_tramite"] = df["estado_tramite"].fillna("Pendiente").astype(str).str.strip()
    df.loc[df["estado_tramite"].isin(["", "nan"]), "estado_tramite"] = "Pendiente"
    df.loc[df["estado_pago"].isin(["", "nan"]), "estado_pago"] = "Pendiente"
    if "tramite" not in df.columns:
        df["tramite"] = ""
    df["tramite"] = df["tramite"].fillna("").astype(str).str.strip()
    if "fecha" not in df.columns:
        df["fecha"] = ""
    df["fecha"] = df["fecha"].apply(solo_fecha)
    if "mes_anio" not in df.columns:
        df["mes_anio"] = ""
    df["Mes - Año"] = df.apply(lambda r: mes_anio_de_fecha(r["fecha"], r["mes_anio"]), axis=1)
    if "medico" in df.columns:
        df["Nombre de Médico"] = df["medico"]
    if "paciente" in df.columns:
        df["Nombre de Paciente"] = df["paciente"]
    return df

def crear_excel_bien(dfs_dict):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for hoja, df in dfs_dict.items():
            df_limpio = df.copy()
            if "seleccionar" in df_limpio.columns:
                df_limpio = df_limpio.drop(columns=["seleccionar"])
            df_limpio.to_excel(writer, index=False, sheet_name=hoja)
            ws = writer.sheets[hoja]
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    try:
                        if cell.value:
                            max_len = max(max_len, len(str(cell.value)))
                    except:
                        pass
                ws.column_dimensions[col_letter].width = min(max_len + 2, 60)
    buffer.seek(0)
    return buffer

def limpiar_estado(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return "Pendiente"
    v = str(valor).strip()
    vu = v.upper()
    if vu in ["PAGADO", "PAGADA"]:
        return "Pagado"
    if vu in ["LIQUIDADO", "LIQUIDADA"]:
        return "Liquidado"
    if vu in ["DESPACHADO", "DESPACHADA"]:
        return "Despachado"
    if vu in ["PENDIENTE"]:
        return "Pendiente"
    return v

def buscar_col(cols, posibles):
    cols_norm = {str(c).strip().upper().replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U"): c for c in cols}
    for p in posibles:
        pn = p.upper().replace("Á","A").replace("É","E")
        if pn in cols_norm:
            return cols_norm[pn]
        for cn, orig in cols_norm.items():
            if pn in cn:
                return orig
    return None

def leer_excel_auto(archivo):
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        xls = pd.ExcelFile(archivo)
        hoja = "FORMATO FINAL  " if "FORMATO FINAL  " in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(archivo, sheet_name=hoja)
    df.columns = [str(c).strip() for c in df.columns]
    return df

try:
    df_all_hon = arreglar_df(cargar_honorarios())
    df_med = pd.read_sql("SELECT * FROM medicos", conn)
except:
    df_all_hon = pd.DataFrame()
    df_med = pd.DataFrame()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📋 Directorio Médico", "💰 Honorarios Médicos", "⚠️ Sin Médico Asignado", "📂 Importar Archivos", "🔄 Actualizar Estados por Excel", "⚙️ Gestión", "✅ Verificación - Mes / Año"])

with tab1:
    st.write("")
    col_s, col_e = st.columns([3, 1])
    with col_s:
        buscar = st.text_input("🔍 Buscar", placeholder="Buscar por nombre, apellido, cédula, especialidad o código SENESCYT...", label_visibility="collapsed")
    with col_e:
        especialidades = ["Todas las Especialidades"] + sorted(df_med["especialidad"].dropna().astype(str).unique().tolist()) if len(df_med) > 0 and "especialidad" in df_med.columns else ["Todas las Especialidades"]
        esp_sel = st.selectbox("Especialidad", [f"{e} ({len(df_med[df_med['especialidad']==e])})" if e != "Todas las Especialidades" else f"Todas las Especialidades ({len(df_med)})" for e in especialidades], label_visibility="collapsed")
    total_medicos = len(df_med)
    con_firma = len(df_med[df_med["registro_senescyt"].astype(str).str.strip() != ""]) if len(df_med) > 0 and "registro_senescyt" in df_med.columns else 0
    sin_firma = total_medicos - con_firma
    col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 1, 2])
    with col_p1:
        filtro_activo = st.selectbox("Estado", [f"Activos ({total_medicos})", f"Inactivos (0)", f"Todos ({total_medicos})"], label_visibility="collapsed")
    with col_p2:
        filtro_firma = st.selectbox("Firma", [f"Todas ({total_medicos})", f"Con firma ({con_firma})", f"Sin firma ({sin_firma})"], label_visibility="collapsed")
    with col_p3:
        st.write(f"Mostrando **{total_medicos}** médicos")
    with col_p4:
        buf_med = crear_excel_bien({"Medicos": df_med})
        st.download_button("📥 Descargar Informe (Excel)", data=buf_med, file_name="Directorio_Medico.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    st.divider()
    df_med_mostrar = df_med.copy()
    if buscar:
        df_med_mostrar = df_med_mostrar[df_med_mostrar.apply(lambda r: buscar.lower() in str(r["nombre"]).lower() or buscar.lower() in str(r["cedula"]).lower() or buscar.lower() in str(r["especialidad"]).lower() or buscar.lower() in str(r["registro_senescyt"]).lower(), axis=1)]
    if "Con firma" in filtro_firma:
        df_med_mostrar = df_med_mostrar[df_med_mostrar["registro_senescyt"].astype(str).str.strip() != ""]
    if "Sin firma" in filtro_firma:
        df_med_mostrar = df_med_mostrar[df_med_mostrar["registro_senescyt"].astype(str).str.strip() == ""]
    if len(df_med_mostrar) == 0:
        st.info("Aún no hay médicos.")
    else:
        df_show = df_med_mostrar.copy()
        if "nombre" in df_show.columns:
            df_show = df_show.rename(columns={"nombre": "Nombre de Médico", "cedula": "Cédula", "especialidad": "Especialidad", "registro_senescyt": "Código SENESCYT"})
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.divider()
    st.write("### ➕ Registrar Médico")
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("nm_nuevo"):
            n = st.text_input("Nombre de Médico *").upper()
            ced = st.text_input("Cédula")
            esp = st.text_input("Especialidad")
            sen = st.text_input("Registro SENESCYT / Código")
            if st.form_submit_button("+ Registrar Médico", use_container_width=True):
                if n.strip() == "":
                    st.warning("Escribe el nombre")
                else:
                    conn.execute("INSERT OR REPLACE INTO medicos (nombre,cedula,especialidad,registro_senescyt) VALUES (?,?,?,?)", (n, ced, esp, sen))
                    conn.commit()
                    st.success(f"Médico {n} registrado")
                    st.rerun()
    with col_b:
        buf_plantilla = crear_excel_bien({"Medicos": pd.DataFrame([{"Nombre": "MARIO PEREZ", "Cedula": "0912345678", "Especialidad": "Cirugia", "Registro Senescyt": "12345"}])})
        st.download_button("📥 Descargar plantilla", data=buf_plantilla, file_name="Plantilla_Medicos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        archivo_medicos = st.file_uploader("Sube Excel de médicos", type=["xlsx", "xls"], key="upload_medicos_nuevo")
        if archivo_medicos is not None:
            try:
                df_m_imp = leer_excel_auto(archivo_medicos)
                cols_m = list(df_m_imp.columns)
                c_nombre_m = buscar_col(cols_m, ["NOMBRE DEL MEDICO", "NOMBRE", "MEDICO", "DOCTOR"])
                c_ced_m = buscar_col(cols_m, ["CEDULA", "CI"])
                c_esp_m = buscar_col(cols_m, ["ESPECIALIDAD"])
                c_sen_m = buscar_col(cols_m, ["SENESCYT", "REGISTRO"])
                if not c_nombre_m:
                    st.error("No encontré columna Nombre.")
                else:
                    df_nuevos = pd.DataFrame()
                    df_nuevos["nombre"] = df_m_imp[c_nombre_m].astype(str).str.strip().str.upper()
                    df_nuevos["cedula"] = df_m_imp[c_ced_m].astype(str).str.strip() if c_ced_m else ""
                    df_nuevos["especialidad"] = df_m_imp[c_esp_m].astype(str).str.strip() if c_esp_m else ""
                    df_nuevos["registro_senescyt"] = df_m_imp[c_sen_m].astype(str).str.strip() if c_sen_m else ""
                    df_nuevos = df_nuevos[df_nuevos["nombre"] != ""]
                    df_nuevos = df_nuevos[~df_nuevos["nombre"].isin(["NAN", "NONE"])]
                    df_nuevos = df_nuevos.drop_duplicates(subset=["nombre"])
                    ya_existentes = set(df_med["nombre"].astype(str).str.strip().str.upper().tolist()) if len(df_med) > 0 else set()
                    df_nuevos_f = df_nuevos[~df_nuevos["nombre"].isin(ya_existentes)]
                    for _, r in df_nuevos_f.iterrows():
                        conn.execute("INSERT INTO medicos (nombre,cedula,especialidad,registro_senescyt) VALUES (?,?,?,?)", (r["nombre"], r["cedula"], r["especialidad"], r["registro_senescyt"]))
                    conn.commit()
                    st.success(f"✅ Se cargaron {len(df_nuevos_f)} médicos")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

with tab2:
    lista_medicos_todos = ["Todos los médicos"] + sorted([m for m in df_all_hon["medico"].dropna().astype(str).unique() if m not in ["", "nan", "SIN ASIGNAR"]]) if len(df_all_hon) > 0 else ["Todos los médicos"]
    medico_elegido = st.selectbox("👨‍⚕️ Médico ⬇️", lista_medicos_todos, key="medico_cascada")
    df_por_medico = df_all_hon.copy()
    if medico_elegido != "Todos los médicos":
        df_por_medico = df_all_hon[df_all_hon["medico"] == medico_elegido]
    if len(df_por_medico) > 0 and "Mes - Año" in df_por_medico.columns:
        conteo_mes = df_por_medico["Mes - Año"].value_counts()
        meses_del_medico = sorted([m for m in df_por_medico["Mes - Año"].dropna().astype(str).unique() if m not in ["", "nan"]], key=ordenar_mes_anio)
        opciones_mes = ["Todos los meses de este médico"] + [f"{m} ({conteo_mes[m]} cargos)" for m in meses_del_medico]
    else:
        opciones_mes = ["Todos los meses de este médico"]
    mes_elegido_raw = st.selectbox("📅 Mes - Año ⬇️", opciones_mes, key="mes_cascada")
    mes_elegido = mes_elegido_raw.split(" (")[0] if " (" in mes_elegido_raw else mes_elegido_raw
    df_por_medico_mes = df_por_medico.copy()
    if mes_elegido != "Todos los meses de este médico":
        df_por_medico_mes = df_por_medico[df_por_medico["Mes - Año"] == mes_elegido]
    if len(df_por_medico_mes) > 0:
        conteo_tram = df_por_medico_mes["tramite"].value_counts()
        tramites_del_medico = sorted([t for t in df_por_medico_mes["tramite"].dropna().astype(str).unique() if t not in ["", "nan"]])
        opciones_tram = ["Todos los trámites de este médico en este mes"] + [f"{t} ({conteo_tram[t]} cargos)" for t in tramites_del_medico]
    else:
        opciones_tram = ["Todos los trámites de este médico en este mes"]
    tramite_elegido_raw = st.selectbox("📋 N° de Trámite ⬇️", opciones_tram, key="tramite_cascada")
    tramite_elegido = tramite_elegido_raw.split(" (")[0] if " (" in tramite_elegido_raw else tramite_elegido_raw
    buscar_hon = st.text_input("🔍 Buscar", placeholder="Nombre de Paciente, código...", key="buscar_hon_facil")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        filtro_tramite = st.selectbox("🔵 Estado Trámite ⬇️", ["Todos"] + sorted(df_all_hon["estado_tramite"].unique().tolist()) if len(df_all_hon) > 0 else ["Todos"], key="f_tram_facil")
    with col_e2:
        filtro_pago = st.selectbox("🟢 Pago al Médico ⬇️", ["Todos", "Pendiente", "Pagado"], key="f_pago_facil")
    df = df_por_medico_mes.copy()
    if tramite_elegido != "Todos los trámites de este médico en este mes":
        df = df[df["tramite"].astype(str) == tramite_elegido]
    if buscar_hon:
        df = df[df.apply(lambda r: buscar_hon.lower() in str(r["paciente"]).lower() or buscar_hon.lower() in str(r["medico"]).lower() or buscar_hon.lower() in str(r["tramite"]).lower() or buscar_hon.lower() in str(r["codigo"]).lower(), axis=1)]
    if filtro_tramite != "Todos":
        df = df[df["estado_tramite"] == filtro_tramite]
    if filtro_pago != "Todos":
        df = df[df["estado_pago"] == filtro_pago]
    if len(df) > 0:
        total_general = df["valor"].sum()
        total_60 = df["valor_60"].sum()
        pagado_60 = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
        pendiente_60 = total_60 - pagado_60
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total General", f"${total_general:,.2f}")
        c2.metric("Total 60%", f"${total_60:,.2f}")
        c3.metric("Pagado AL MEDICO", f"${pagado_60:,.2f}")
        c4.metric("Pendiente AL MEDICO", f"${pendiente_60:,.2f}")
        df_edit_base = df.copy()
        df_edit_base["seleccionar"] = False
        df_para_mostrar = df_edit_base.copy()
        df_para_mostrar["Nombre de Médico"] = df_para_mostrar["medico"]
        df_para_mostrar["Nombre de Paciente"] = df_para_mostrar["paciente"]
        df_para_mostrar["Fecha"] = df_para_mostrar["fecha"]
        df_para_mostrar["Código"] = df_para_mostrar["codigo"]
        df_para_mostrar["Descripción"] = df_para_mostrar["descripcion"]
        df_para_mostrar["N° Trámite"] = df_para_mostrar["tramite"]
        df_para_mostrar["Valor"] = df_para_mostrar["valor"]
        df_para_mostrar["Valor 60%"] = df_para_mostrar["valor_60"]
        df_para_mostrar["Estado Trámite"] = df_para_mostrar["estado_tramite"]
        df_para_mostrar["Pago al Médico"] = df_para_mostrar["estado_pago"]
        cols_edit = ["seleccionar", "id", "Nombre de Médico", "Nombre de Paciente", "Fecha", "Mes - Año", "Código", "Descripción", "N° Trámite", "Valor", "Valor 60%", "Estado Trámite", "Pago al Médico"]
        cols_edit = [c for c in cols_edit if c in df_para_mostrar.columns]
        df_edit = st.data_editor(df_para_mostrar[cols_edit], use_container_width=True, hide_index=True, key="editor_pagos_facil", column_config={"seleccionar": st.column_config.CheckboxColumn("✅ Marcar")}, disabled=["id", "Nombre de Médico", "Nombre de Paciente", "Fecha", "Mes - Año", "Código", "Descripción", "N° Trámite", "Valor", "Valor 60%", "Estado Trámite", "Pago al Médico"])
        try:
            ids_sel = df_edit[df_edit["seleccionar"] == True]["id"].tolist() if "seleccionar" in df_edit.columns else []
            total_sel_60 = df_edit[df_edit["seleccionar"] == True]["Valor 60%"].sum() if len(ids_sel) > 0 else 0
        except:
            ids_sel = []
            total_sel_60 = 0
        st.markdown('<div class="box-verde">', unsafe_allow_html=True)
        col_n1, col_n2, col_btn = st.columns([1, 1, 1])
        with col_n1:
            nuevo_estado_tramite = st.selectbox("🔵 Nuevo Estado TRÁMITE ⬇️", ["No cambiar trámite", "Pagado", "Liquidado", "Despachado", "Auditado Documental", "Auditado Médico", "Recibido ISSPOL", "En Trámite", "Observado", "Pendiente", "Rechazado"], key="nuevo_tramite_facil")
        with col_n2:
            nuevo_estado_pago = st.selectbox("🟢 Nuevo Estado PAGO AL MÉDICO ⬇️", ["No cambiar pago", "Pagado", "Pendiente"], key="nuevo_pago_facil")
        with col_btn:
            st.write(f"Marcados: **{len(ids_sel)}** | Total 60%: **${total_sel_60:,.2f}**")
            boton_actualizar = st.button(f"💾 ACTUALIZAR {len(ids_sel)} SELECCIONADOS", type="primary", use_container_width=True, key="btn_actualizar_facil")
        st.markdown('</div>', unsafe_allow_html=True)
        if boton_actualizar:
            if len(ids_sel) == 0:
                st.warning("⚠️ Primero marca con el cuadrito cuáles quieres actualizar.")
            elif nuevo_estado_tramite == "No cambiar trámite" and nuevo_estado_pago == "No cambiar pago":
                st.warning("⚠️ Elige al menos un nuevo estado.")
            else:
                for i in ids_sel:
                    if nuevo_estado_tramite != "No cambiar trámite" and nuevo_estado_pago != "No cambiar pago":
                        conn.execute("UPDATE honorarios SET estado_tramite=?, estado=?, estado_pago=? WHERE rowid=?", (nuevo_estado_tramite, nuevo_estado_tramite, nuevo_estado_pago, int(i)))
                    elif nuevo_estado_tramite != "No cambiar trámite":
                        conn.execute("UPDATE honorarios SET estado_tramite=?, estado=? WHERE rowid=?", (nuevo_estado_tramite, nuevo_estado_tramite, int(i)))
                    elif nuevo_estado_pago != "No cambiar pago":
                        conn.execute("UPDATE honorarios SET estado_pago=? WHERE rowid=?", (nuevo_estado_pago, int(i)))
                conn.commit()
                st.success(f"✅ ¡Listo! Se actualizaron {len(ids_sel)} cargos.")
                st.balloons()
                st.rerun()
        st.divider()
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button(f"✅ Marcar TODOS los {len(df)} como PAGADO AL MÉDICO", use_container_width=True):
                for i in df["id"].tolist():
                    conn.execute("UPDATE honorarios SET estado_pago='Pagado' WHERE rowid=?", (int(i),))
                conn.commit()
                st.success(f"Se marcaron {len(df)} como Pagado")
                st.rerun()
        with col_r2:
            if st.button(f"↩️ Volver TODOS los {len(df)} a PENDIENTE", use_container_width=True):
                for i in df["id"].tolist():
                    conn.execute("UPDATE honorarios SET estado_pago='Pendiente' WHERE rowid=?", (int(i),))
                conn.commit()
                st.success(f"Se volvieron {len(df)} a Pendiente")
                st.rerun()
        df_desc = df_para_mostrar[cols_edit].copy()
        df_desc = df_desc.drop(columns=["seleccionar"], errors="ignore")
        buf_hon = crear_excel_bien({"Honorarios": df_desc})
        st.download_button("📥 Descargar este listado en Excel", data=buf_hon, file_name="Honorarios.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Ese médico no tiene cargos en ese mes / trámite.")

with tab3:
    st.write("### ⚠️ Pacientes SIN Médico Asignado")
    df_sin_all = arreglar_df(cargar_honorarios())
    df_sin = df_sin_all[(df_sin_all["medico"] == "SIN ASIGNAR") | (df_sin_all["medico"] == "") | (df_sin_all["medico"].isna())] if len(df_sin_all) > 0 else df_sin_all.copy()
    if len(df_sin) == 0:
        st.success("🎉 ¡Perfecto! No hay ningún cargo sin médico.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Cargos sin médico", len(df_sin))
        c2.metric("Total sin asignar", f"${df_sin['valor'].sum():,.2f}")
        c3.metric("Total 60% sin asignar", f"${df_sin['valor_60'].sum():,.2f}")
        buscar_sin = st.text_input("🔍 Buscar por paciente, código / cargo, trámite o descripción", placeholder="Ej: 12345, A-2763, MARIA...", label_visibility="collapsed", key="buscar_sin")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            lista_tram_sin = ["Todos los trámites"] + sorted([t for t in df_sin["tramite"].dropna().astype(str).unique() if t not in ["", "nan"]])
            f_tram_sin = st.selectbox("📋 N° Trámite ⬇️", lista_tram_sin, key="f_tram_sin")
        with col_f2:
            lista_cod_sin = ["Todos los códigos / cargos"] + sorted([c for c in df_sin["codigo"].dropna().astype(str).unique() if c not in ["", "nan"]])
            f_cod_sin = st.selectbox("🏷️ Código / Cargo ⬇️", lista_cod_sin, key="f_cod_sin")
        with col_f3:
            lista_mes_sin = ["Todos los meses"] + sorted([m for m in df_sin["Mes - Año"].dropna().astype(str).unique() if m not in ["", "nan"]]) if "Mes - Año" in df_sin.columns else ["Todos los meses"]
            f_mes_sin = st.selectbox("📅 Mes - Año ⬇️", lista_mes_sin, key="f_mes_sin")
        df_f_sin = df_sin.copy()
        if buscar_sin:
            df_f_sin = df_f_sin[df_f_sin.apply(lambda r: buscar_sin.lower() in str(r["paciente"]).lower() or buscar_sin.lower() in str(r["codigo"]).lower() or buscar_sin.lower() in str(r["tramite"]).lower() or buscar_sin.lower() in str(r["descripcion"]).lower(), axis=1)]
        if f_tram_sin != "Todos los trámites":
            df_f_sin = df_f_sin[df_f_sin["tramite"].astype(str) == f_tram_sin]
        if f_cod_sin != "Todos los códigos / cargos":
            df_f_sin = df_f_sin[df_f_sin["codigo"].astype(str) == f_cod_sin]
        if f_mes_sin != "Todos los meses":
            df_f_sin = df_f_sin[df_f_sin["Mes - Año"] == f_mes_sin]
        df_sin_show = df_f_sin.copy()
        df_sin_show["Nombre de Paciente"] = df_sin_show["paciente"]
        df_sin_show["Código / Cargo"] = df_sin_show["codigo"]
        df_sin_show["Descripción / Cargo"] = df_sin_show["descripcion"]
        df_sin_show["N° Trámite"] = df_sin_show["tramite"]
        df_sin_show["Fecha"] = df_sin_show["fecha"]
        df_sin_show["Valor 60%"] = df_sin_show["valor_60"]
        df_sin_show["Estado Trámite"] = df_sin_show["estado_tramite"]
        df_sin_show["Pago al Médico"] = df_sin_show["estado_pago"]
        if "seguro" in df_sin_show.columns:
            df_sin_show["Seguro"] = df_sin_show["seguro"]
        cols_sin_final = [c for c in ["Nombre de Paciente", "Código / Cargo", "Descripción / Cargo", "N° Trámite", "Fecha", "Mes - Año", "Seguro", "Valor", "Valor 60%", "Estado Trámite", "Pago al Médico"] if c in df_sin_show.columns]
        st.dataframe(df_sin_show[cols_sin_final], use_container_width=True, hide_index=True)
        if len(df_f_sin) > 0:
            resumen_cod = df_f_sin.groupby(["codigo", "descripcion"]).agg(Cantidad=("codigo", "count"), Total_Valor=("valor", "sum"), Total_60=("valor_60", "sum")).reset_index().sort_values("Cantidad", ascending=False)
            resumen_cod = resumen_cod.rename(columns={"codigo": "Código / Cargo", "descripcion": "Descripción", "Cantidad": "N° Cargos sin médico", "Total_Valor": "Total Valor", "Total_60": "Total 60%"})
            st.dataframe(resumen_cod, use_container_width=True, hide_index=True)
        st.divider()
        df_med_all = pd.read_sql("SELECT * FROM medicos", conn)
        df_hon_all = cargar_honorarios()
        lista_med_asignar = sorted(set(df_med_all["nombre"].dropna().astype(str).tolist() + df_hon_all["medico"].dropna().astype(str).tolist()) - set(["", "SIN ASIGNAR", "nan"])) if len(df_hon_all) > 0 else sorted(df_med_all["nombre"].dropna().astype(str).tolist())
        if len(lista_med_asignar) == 0:
            st.warning("Primero registra un médico.")
        else:
            df_f_sin["seleccionar"] = False
            df_f_sin["Nombre de Paciente"] = df_f_sin["paciente"]
            df_f_sin["Código / Cargo"] = df_f_sin["codigo"]
            df_f_sin["Fecha"] = df_f_sin["fecha"]
            cols_asignar = [c for c in ["seleccionar", "id", "Nombre de Paciente", "Código / Cargo", "descripcion", "tramite", "Fecha", "Mes - Año", "valor", "valor_60", "estado_tramite"] if c in df_f_sin.columns]
            df_edit_sin = st.data_editor(df_f_sin[cols_asignar], use_container_width=True, hide_index=True, key="editor_sin_medico_new")
            try:
                ids_sin_sel = df_edit_sin[df_edit_sin["seleccionar"] == True]["id"].tolist() if "seleccionar" in df_edit_sin.columns else []
            except:
                ids_sin_sel = []
            medico_elegido_sin = st.selectbox("👨‍⚕️ ¿A qué médico le asignas los seleccionados? ⬇️", lista_med_asignar, key="med_asignar_sin")
            if st.button(f"✅ Asignar {len(ids_sin_sel)} cargos a {medico_elegido_sin}", type="primary", use_container_width=True):
                if len(ids_sin_sel) == 0:
                    st.warning("Marca primero con el cuadrito cuáles cargos quieres asignar")
                else:
                    for i in ids_sin_sel:
                        conn.execute("UPDATE honorarios SET medico=? WHERE rowid=?", (medico_elegido_sin, int(i)))
                    conn.commit()
                    st.success(f"✅ Se asignaron {len(ids_sin_sel)} cargos a {medico_elegido_sin}")
                    st.balloons()
                    st.rerun()

with tab4:
    st.write("### 📂 Importar Archivos")
    df_existente = arreglar_df(cargar_honorarios())
    st.write(f"Ya tienes: **{len(df_existente)}** registros")
    archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls", "csv"], key="import1_new")
    if archivo is not None:
        try:
            df_imp = leer_excel_auto(archivo)
            cols = list(df_imp.columns)
            c_paciente = buscar_col(cols, ["NOMBRES DEL PACIENTE", "PACIENTE"])
            c_medico = buscar_col(cols, ["NOMBRE DEL MEDICO", "MEDICO", "DOCTOR"])
            c_codigo = buscar_col(cols, ["CODIGO PLANILLADO", "CODIGO"])
            c_valor = buscar_col(cols, ["VALOR DE CODIGO", "VALOR"])
            c_tramite = buscar_col(cols, ["N TRAMITE", "TRAMITE", "NUMERO TRAMITE"])
            c_desc = buscar_col(cols, ["DESCRIPCION"])
            c_estado = buscar_col(cols, ["ESTADO DEL TRAMITE", "ESTADO TRAMITE", "ESTADO", "SITUACION"])
            c_fecha = buscar_col(cols, ["FECHA", "FECHA DE ATENCION", "FECHA ATENCION"])
            c_mes = buscar_col(cols, ["MES", "MES ANIO", "MES-AÑO"])
            df2 = pd.DataFrame()
            df2["paciente"] = df_imp[c_paciente].astype(str) if c_paciente else ""
            df2["medico"] = df_imp[c_medico].astype(str) if c_medico else "SIN ASIGNAR"
            df2["tramite"] = df_imp[c_tramite].astype(str) if c_tramite else ""
            df2["codigo"] = df_imp[c_codigo].astype(str) if c_codigo else ""
            df2["descripcion"] = df_imp[c_desc].astype(str) if c_desc else ""
            df2["valor"] = pd.to_numeric(df_imp[c_valor], errors="coerce").fillna(0) if c_valor else 0
            if c_fecha:
                df2["fecha"] = df_imp[c_fecha].apply(solo_fecha)
            else:
                df2["fecha"] = ""
            if c_mes:
                df2["mes_anio"] = df_imp[c_mes].astype(str)
            else:
                df2["mes_anio"] = df2["fecha"].apply(lambda f: mes_anio_de_fecha(f, ""))
            df2["mes_anio"] = df2.apply(lambda r: mes_anio_de_fecha(r["fecha"], r["mes_anio"]), axis=1)
            df2["seguro"] = ""
            df2 = df2[df2["paciente"].str.strip() != ""]
            df2 = df2[~df2["paciente"].str.contains("Suma|Total|Etiquetas", na=False)]
            df2["medico"] = df2["medico"].fillna("").str.strip()
            df2.loc[df2["medico"] == "", "medico"] = "SIN ASIGNAR"
            df2["estado_tramite"] = df_imp[c_estado].apply(limpiar_estado) if c_estado else "Pendiente"
            df2["estado"] = df2["estado_tramite"]
            df2["estado_pago"] = "Pendiente"
            df2["valor_40"] = (df2["valor"] * 0.40).round(2)
            df2["valor_50"] = (df2["valor"] * 0.50).round(2)
            df2["valor_60"] = (df2["valor"] * 0.60).round(2)
            df2["valor_pagado"] = 0
            df2["es_paquete"] = 0
            nuevos = 0
            actualizados = 0
            existentes = {}
            if len(df_existente) > 0:
                for _, r in df_existente.iterrows():
                    clave = (str(r["paciente"]).strip(), str(r["tramite"]).strip(), str(r["codigo"]).strip())
                    existentes[clave] = r["id"]
            for _, row in df2.iterrows():
                clave = (str(row["paciente"]).strip(), str(row["tramite"]).strip(), str(row["codigo"]).strip())
                if clave in existentes:
                    conn.execute("UPDATE honorarios SET estado_tramite=?, estado=?, fecha=?, mes_anio=? WHERE rowid=?", (row["estado_tramite"], row["estado_tramite"], str(row["fecha"]), str(row["mes_anio"]), int(existentes[clave])))
                    actualizados += 1
                else:
                    conn.execute("INSERT INTO honorarios (paciente, medico, fecha, codigo, descripcion, valor, seguro, tramite, mes_anio, valor_40, valor_50, valor_60, estado, estado_tramite, estado_pago, valor_pagado, es_paquete) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(row["paciente"]), str(row["medico"]), str(row["fecha"]), str(row["codigo"]), str(row["descripcion"]), float(row["valor"]), str(row["seguro"]), str(row["tramite"]), str(row["mes_anio"]), float(row["valor_40"]), float(row["valor_50"]), float(row["valor_60"]), str(row["estado_tramite"]), str(row["estado_tramite"]), "Pendiente", 0, 0))
                    nuevos += 1
            conn.commit()
            st.success(f"✅ ¡Listo! Nuevos: {nuevos} | Actualizados: {actualizados}")
            st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

with tab5:
    st.write("### 🔄 Actualizar Estados por Excel")
    archivo2 = st.file_uploader("Sube el Excel con los estados", type=["xlsx", "xls", "csv"], key="import_estados_new")
    if archivo2 is not None:
        try:
            df_imp = leer_excel_auto(archivo2)
            cols = list(df_imp.columns)
            c_estado2 = buscar_col(cols, ["ESTADO DEL TRAMITE", "ESTADO TRAMITE", "ESTADO", "SITUACION", "ESTATUS"])
            c_tramite2 = buscar_col(cols, ["N TRAMITE", "TRAMITE", "NUMERO TRAMITE", "NUMERO DE TRAMITE"])
            c_paciente2 = buscar_col(cols, ["NOMBRES DEL PACIENTE", "PACIENTE"])
            c_codigo2 = buscar_col(cols, ["CODIGO PLANILLADO", "CODIGO"])
            if not c_estado2 or not c_tramite2:
                st.error("No encontré ESTADO o TRÁMITE.")
                st.write("Columnas:", cols)
            else:
                st.write(f"Leído: Estado = {c_estado2} | Trámite = {c_tramite2}")
                st.dataframe(df_imp[c_estado2].astype(str).value_counts().reset_index(), use_container_width=True)
                actualizados = 0
                no_encontrados = 0
                for _, row in df_imp.iterrows():
                    tram = str(row[c_tramite2]).strip()
                    pac = str(row[c_paciente2]).strip() if c_paciente2 else ""
                    cod = str(row[c_codigo2]).strip() if c_codigo2 else ""
                    estado_nuevo = limpiar_estado(row[c_estado2])
                    cur = None
                    if pac and tram and cod:
                        cur = conn.execute("SELECT rowid FROM honorarios WHERE paciente=? AND tramite=? AND codigo=?", (pac, tram, cod)).fetchone()
                    if not cur and tram != "" and tram.lower() != "nan":
                        cur = conn.execute("SELECT rowid FROM honorarios WHERE tramite=?", (tram,)).fetchone()
                    if not cur and pac and cod:
                        cur = conn.execute("SELECT rowid FROM honorarios WHERE paciente=? AND codigo=?", (pac, cod)).fetchone()
                    if cur:
                        conn.execute("UPDATE honorarios SET estado_tramite=?, estado=? WHERE rowid=?", (estado_nuevo, estado_nuevo, int(cur[0])))
                        actualizados += 1
                    else:
                        no_encontrados += 1
                conn.commit()
                st.success(f"✅ ¡Actualizado solo! Actualizados: {actualizados} | No encontrados: {no_encontrados}")
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

with tab6:
    st.write("### ⚙️ Gestión")
    st.write(f"Total registros: {len(df_all_hon)} | Médicos: {len(df_med)}")

# --- NUEVA PESTAÑA: VERIFICACIÓN - DESDE HASTA QUÉ FECHA / MES TIENES CARGADO ---
with tab7:
    st.write("### ✅ Verificación - ¿Desde cuándo hasta cuándo tienes trámites cargados?")
    if len(df_all_hon) == 0:
        st.info("Aún no hay trámites cargados.")
    else:
        # Calculamos desde-hasta con la fecha real
        df_fechas = df_all_hon[df_all_hon["fecha"] != ""].copy()
        if len(df_fechas) > 0:
            df_fechas["fecha_dt"] = pd.to_datetime(df_fechas["fecha"], errors="coerce")
            df_fechas = df_fechas.dropna(subset=["fecha_dt"])
            fecha_desde = df_fechas["fecha_dt"].min()
            fecha_hasta = df_fechas["fecha_dt"].max()
            mes_desde = mes_anio_de_fecha(fecha_desde.strftime("%Y-%m-%d"), "")
            mes_hasta = mes_anio_de_fecha(fecha_hasta.strftime("%Y-%m-%d"), "")
        else:
            fecha_desde = None
            fecha_hasta = None
            mes_desde = ""
            mes_hasta = ""
        # CAJA AZUL ARRIBA: DESDE - HASTA
        st.markdown('<div class="box-azul">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("**Desde:**")
            st.write(f"### {fecha_desde.strftime('%Y-%m-%d') if fecha_desde is not None else 'Sin fecha'}")
            st.write(f"Mes: **{mes_desde}**")
        with c2:
            st.write("**Hasta:**")
            st.write(f"### {fecha_hasta.strftime('%Y-%m-%d') if fecha_hasta is not None else 'Sin fecha'}")
            st.write(f"Mes: **{mes_hasta}**")
        with c3:
            st.write("**Último mes actualizado:**")
            st.write(f"### {mes_hasta}")
            st.write(f"Total trámites: **{df_all_hon['tramite'].nunique()}** | Total cargos: **{len(df_all_hon)}**")
        st.markdown('</div>', unsafe_allow_html=True)
        st.write("")
        # FILTRO DESDE-HASTA PARA VERIFICAR UN RANGO
        st.write("**Verificar un rango:** Elige desde qué Mes-Año hasta qué Mes-Año quieres verificar")
        meses_todos = sorted([m for m in df_all_hon["Mes - Año"].dropna().astype(str).unique() if m not in ["", "nan"]], key=ordenar_mes_anio)
        col_d, col_h = st.columns(2)
        with col_d:
            mes_desde_sel = st.selectbox("📅 Desde Mes - Año ⬇️", meses_todos, index=0, key="verif_desde")
        with col_h:
            mes_hasta_sel = st.selectbox("📅 Hasta Mes - Año ⬇️", meses_todos, index=len(meses_todos)-1 if len(meses_todos) > 0 else 0, key="verif_hasta")
        # Filtramos por rango de meses
        idx_desde = meses_todos.index(mes_desde_sel) if mes_desde_sel in meses_todos else 0
        idx_hasta = meses_todos.index(mes_hasta_sel) if mes_hasta_sel in meses_todos else len(meses_todos)-1
        if idx_desde > idx_hasta:
            idx_desde, idx_hasta = idx_hasta, idx_desde
        meses_en_rango = meses_todos[idx_desde:idx_hasta+1]
        df_rango = df_all_hon[df_all_hon["Mes - Año"].isin(meses_en_rango)].copy()
        st.write(f"En el rango **{mes_desde_sel} hasta {mes_hasta_sel}** tienes: **{df_rango['tramite'].nunique()}** trámites, **{len(df_rango)}** cargos, Total 60%: **${df_rango['valor_60'].sum():,.2f}**")
        st.divider()
        st.write("**Resumen por Mes - Año - ¿Qué tienes cargado en cada mes?**")
        # Resumen por mes
        resumen_mes = []
        for mes in meses_todos:
            df_m = df_all_hon[df_all_hon["Mes - Año"] == mes]
            if len(df_m) == 0:
                continue
            resumen_mes.append({
                "Mes - Año": mes,
                "N° Trámites": df_m["tramite"].nunique(),
                "N° Cargos": len(df_m),
                "N° Médicos": df_m["medico"].nunique(),
                "Total Valor": round(df_m["valor"].sum(), 2),
                "Total 60%": round(df_m["valor_60"].sum(), 2),
                "Pagado al Médico (60%)": round(df_m[df_m["estado_pago"] == "Pagado"]["valor_60"].sum(), 2),
                "Pendiente al Médico (60%)": round(df_m[df_m["estado_pago"] == "Pendiente"]["valor_60"].sum(), 2),
                "Desde": df_m["fecha"].min() if len(df_m[df_m["fecha"] != ""]) > 0 else "",
                "Hasta": df_m["fecha"].max() if len(df_m[df_m["fecha"] != ""]) > 0 else "",
            })
        df_resumen_mes = pd.DataFrame(resumen_mes).sort_values("Mes - Año", key=lambda s: s.map(ordenar_mes_anio))
        st.dataframe(df_resumen_mes, use_container_width=True, hide_index=True)
        st.divider()
        st.write("**Resumen por Estado Trámite en el rango elegido**")
        if len(df_rango) > 0:
            resumen_estado = df_rango.groupby("estado_tramite").agg(Cargos=("estado_tramite", "count"), Total_60=("valor_60", "sum")).reset_index().sort_values("Cargos", ascending=False)
            resumen_estado = resumen_estado.rename(columns={"estado_tramite": "Estado Trámite", "Cargos": "N° Cargos", "Total_60": "Total 60%"})
            st.dataframe(resumen_estado, use_container_width=True, hide_index=True)
        st.divider()
        st.write("**Detalle del rango elegido - por Trámite**")
        if len(df_rango) > 0:
            resumen_tram = df_rango.groupby(["tramite", "Mes - Año", "medico"]).agg(Cargos=("tramite", "count"), Total_60=("valor_60", "sum")).reset_index().sort_values("Mes - Año", key=lambda s: s.map(ordenar_mes_anio))
            resumen_tram = resumen_tram.rename(columns={"tramite": "N° Trámite", "medico": "Nombre de Médico", "Cargos": "N° Cargos", "Total_60": "Total 60%"})
            st.dataframe(resumen_tram, use_container_width=True, hide_index=True)
            buf_verif = crear_excel_bien({"Resumen_por_Mes": df_resumen_mes, "Detalle_por_Tramite": resumen_tram})
            st.download_button("📥 Descargar verificación en Excel", data=buf_verif, file_name="Verificacion_Mes_Anio.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)