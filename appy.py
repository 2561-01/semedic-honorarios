import streamlit as st
import pandas as pd
import sqlite3
import io

st.set_page_config(page_title="Hospital Semedic - Staff Médico & Sellos", layout="wide")

# --- ESTILO IGUAL A TU FOTO: AZUL OSCURO, BLANCO, VERDE ---
st.markdown("""
<style>
    .block-container {padding-top: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 1400px;}
    header {visibility: hidden;}
    .topbar {background: white; border-bottom: 1px solid #E5E7EB; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 999;}
    .logo-box {display: flex; align-items: center; gap: 10px;}
    .hs {background: #0B2A6B; color: white; width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 18px;}
    .title1 {font-weight: 800; font-size: 17px; line-height: 1.1; color: #111827;}
    .title2 {font-size: 11px; color: #2563EB; font-weight: 700; letter-spacing: 1px;}
    .nav {display: flex; gap: 18px; font-size: 13px; color: #4B5563;}
    .nav b {color: #0B2A6B; border-bottom: 2px solid #0B2A6B; padding-bottom: 4px;}
    .user-chip {background: #F3F4F6; border-radius: 10px; padding: 6px 12px; display: flex; gap: 8px; align-items: center; font-size: 12px;}
    .avatar {background: #D1D5DB; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700;}
    .btn-blue {background: #0B2A6B; color: white; border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: 600; border: none;}
    .btn-light {background: white; border: 1px solid #D1D5DB; border-radius: 8px; padding: 8px 12px; font-size: 13px;}
    .search-box {background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px; padding: 10px 14px; width: 100%;}
    .card {background: white; border: 1px solid #E5E7EB; border-radius: 16px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
    .metric-card {background: white; border: 1px solid #E5E7EB; border-radius: 14px; padding: 16px;}
    .pill-green {background: #047857; color: white; border-radius: 8px; padding: 6px 12px; font-size: 13px; font-weight: 600;}
    .pill-dark {background: #111827; color: white; border-radius: 8px; padding: 6px 12px; font-size: 13px; font-weight: 600;}
    .pill-light {background: #F3F4F6; color: #374151; border-radius: 8px; padding: 6px 12px; font-size: 13px;}
    .stButton>button {border-radius: 8px !important; font-weight: 600 !important;}
    div[data-testid="stSelectbox"] > div {border-radius: 10px !important;}
    div[data-testid="stTextInput"] input {border-radius: 12px !important; background: #F9FAFB !important;}
</style>
""", unsafe_allow_html=True)

if "login" not in st.session_state:
    st.session_state.login = False
if not st.session_state.login:
    st.markdown('<div style="display:flex;justify-content:center;padding-top:80px;"><div style="width:420px;text-align:center;"><div style="background:#0B2A6B;color:white;width:60px;height:60px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:24px;margin:0 auto;">HS</div><h2 style="margin:10px 0 0;">Hospital Semedic</h2><p style="color:#2563EB;font-weight:700;letter-spacing:1px;font-size:12px;">STAFF MÉDICO & SELLOS</p></div></div>', unsafe_allow_html=True)
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

# --- BARRA SUPERIOR IGUAL A TU FOTO ---
st.markdown(f"""
<div class="topbar">
  <div style="display:flex;align-items:center;gap:30px;">
    <div class="logo-box"><div class="hs">HS</div><div><div class="title1">Hospital Semedic</div><div class="title2">STAFF MÉDICO & SELLOS</div></div></div>
    <div class="nav"><b>Directorio Médico</b><span>Honorarios</span><span>Importar</span><span>Auditoría</span><span>Gestión de Usuarios</span></div>
  </div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span>🔔 <b style="background:#EF4444;color:white;border-radius:50%;padding:1px 6px;font-size:11px;">71</b></span>
    <div class="user-chip"><div class="avatar">M</div><div><b>{st.session_state.usuario}</b><br><span style="font-size:10px;color:#6B7280;">{st.session_state.rol}</span></div><span>↗</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

conn = sqlite3.connect("honorarios.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS honorarios (
    paciente TEXT, medico TEXT, fecha TEXT, codigo TEXT,
    descripcion TEXT, valor REAL, seguro TEXT, tramite TEXT,
    mes_anio TEXT, valor_40 REAL, valor_50 REAL, valor_60 REAL,
    estado TEXT, estado_tramite TEXT, estado_pago TEXT, valor_pagado REAL,
    es_paquete INTEGER DEFAULT 0
)""")
for col, tipo in [("estado_pago","TEXT DEFAULT 'Pendiente'"), ("valor_pagado","REAL DEFAULT 0"), ("es_paquete","INTEGER DEFAULT 0"), ("valor_40","REAL DEFAULT 0"), ("valor_50","REAL DEFAULT 0"), ("valor_60","REAL DEFAULT 0"), ("estado_tramite","TEXT DEFAULT 'Pendiente'"), ("estado","TEXT DEFAULT 'Pendiente'"), ("paciente","TEXT"), ("medico","TEXT"), ("tramite","TEXT"), ("codigo","TEXT")]:
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

# --- DATOS ---
try:
    df_all_hon = arreglar_df(cargar_honorarios())
    df_med = pd.read_sql("SELECT * FROM medicos", conn)
except:
    df_all_hon = pd.DataFrame()
    df_med = pd.DataFrame()

# --- PESTAÑAS ESTILO TU FOTO: Directorio | Honorarios | Importar | etc ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Directorio Médico", "💰 Honorarios", "📂 Importar Archivos", "🔄 Actualizar Estados por Excel", "⚙️ Gestión"])

with tab1:
    st.write("")
    # Buscador grande como tu foto
    col_s, col_e = st.columns([3, 1])
    with col_s:
        buscar = st.text_input("🔍 Buscar", placeholder="Buscar por nombre, apellido, cédula, especialidad o código SENESCYT...", label_visibility="collapsed")
    with col_e:
        # Especialidades
        especialidades = ["Todas las Especialidades"] + sorted(df_med["especialidad"].dropna().astype(str).unique().tolist()) if len(df_med) > 0 and "especialidad" in df_med.columns else ["Todas las Especialidades"]
        esp_sel = st.selectbox("Especialidad", [f"{e} ({len(df_med[df_med['especialidad']==e])})" if e != "Todas las Especialidades" else f"Todas las Especialidades ({len(df_med)})" for e in especialidades], label_visibility="collapsed")
    # Píldoras como tu foto: Activos / Inactivos / Todos
    col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 1, 2])
    # Contamos
    total_medicos = len(df_med)
    con_firma = len(df_med[df_med["registro_senescyt"].astype(str).str.strip() != ""]) if len(df_med) > 0 and "registro_senescyt" in df_med.columns else 0
    sin_firma = total_medicos - con_firma
    with col_p1:
        filtro_activo = st.selectbox("Estado", [f"Activos ({total_medicos})", f"Inactivos (0)", f"Todos ({total_medicos})"], label_visibility="collapsed")
    with col_p2:
        filtro_firma = st.selectbox("Firma", [f"Todas ({total_medicos})", f"Con firma ({con_firma})", f"Sin firma ({sin_firma})"], label_visibility="collapsed")
    with col_p3:
        st.write(f"Mostrando **{total_medicos}** médicos")
    with col_p4:
        buf_med = crear_excel_bien({"Medicos": df_med})
        st.download_button("📥 Descargar Informe (Excel, Word, PDF)", data=buf_med, file_name="Directorio_Medico.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    st.divider()
    # Filtrar médicos
    df_med_mostrar = df_med.copy()
    if buscar:
        df_med_mostrar = df_med_mostrar[df_med_mostrar.apply(lambda r: buscar.lower() in str(r["nombre"]).lower() or buscar.lower() in str(r["cedula"]).lower() or buscar.lower() in str(r["especialidad"]).lower() or buscar.lower() in str(r["registro_senescyt"]).lower(), axis=1)]
    if "Con firma" in filtro_firma:
        df_med_mostrar = df_med_mostrar[df_med_mostrar["registro_senescyt"].astype(str).str.strip() != ""]
    if "Sin firma" in filtro_firma:
        df_med_mostrar = df_med_mostrar[df_med_mostrar["registro_senescyt"].astype(str).str.strip() == ""]
    # Tarjetas de médicos como en tu foto, en columnas
    if len(df_med_mostrar) == 0:
        st.info("Aún no hay médicos. Ve a Gestión > Cargar médicos por archivo o agrega uno manual.")
    else:
        # Tabla limpia estilo tu foto
        df_show = df_med_mostrar.copy()
        if "nombre" in df_show.columns:
            df_show = df_show.rename(columns={"nombre": "Médico", "cedula": "Cédula", "especialidad": "Especialidad", "registro_senescyt": "Código SENESCYT"})
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.divider()
    st.write("### ➕ Registrar Médico")
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("nm_nuevo"):
            n = st.text_input("Nombre *").upper()
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
        st.write("**O cargar archivo con todos los médicos**")
        st.write("Sube tu Excel, la app lee sola la columna Nombre. No tienes que marcar nada.")
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
    st.write("")
    # Buscador Honorarios mismo estilo
    col_s2, col_e2 = st.columns([3, 1])
    with col_s2:
        buscar_hon = st.text_input("🔍 Buscar honorarios", placeholder="Buscar por paciente, médico, trámite, código...", label_visibility="collapsed", key="buscar_hon")
    with col_e2:
        lista_med_hon = ["Todos los médicos"] + sorted([m for m in df_all_hon["medico"].dropna().astype(str).unique() if m not in ["", "nan"]]) if len(df_all_hon) > 0 else ["Todos los médicos"]
        medico_sel = st.selectbox("Médico", lista_med_hon, label_visibility="collapsed")
    col_t1, col_t2, col_t3 = st.columns([1, 1, 1])
    with col_t1:
        lista_tram = ["Todos los trámites"] + sorted([t for t in df_all_hon["tramite"].dropna().astype(str).unique() if t not in ["", "nan"]]) if len(df_all_hon) > 0 else ["Todos los trámites"]
        tramite_sel = st.selectbox("📋 N° Trámite ⬇️", lista_tram)
    with col_t2:
        filtro_tramite = st.selectbox("🔵 Estado Trámite ⬇️", ["Todos"] + sorted(df_all_hon["estado_tramite"].unique().tolist()) if len(df_all_hon) > 0 else ["Todos"])
    with col_t3:
        filtro_pago = st.selectbox("🟢 Pago al Médico ⬇️", ["Todos", "Pendiente", "Pagado"])
    df = df_all_hon.copy()
    if medico_sel != "Todos los médicos":
        df = df[df["medico"] == medico_sel]
    if tramite_sel != "Todos los trámites":
        df = df[df["tramite"].astype(str) == tramite_sel]
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
        st.write(f"Mostrando **{len(df)}** trámites")
        cols_mostrar = [c for c in ["id", "medico", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "estado_tramite", "estado_pago"] if c in df.columns]
        st.dataframe(df[cols_mostrar], use_container_width=True, hide_index=True)
        # Marcar pago
        df["seleccionar"] = False
        cols_edit = [c for c in ["seleccionar", "id", "medico", "paciente", "codigo", "tramite", "valor_60", "estado_tramite", "estado_pago"] if c in df.columns]
        df_edit = st.data_editor(df[cols_edit], use_container_width=True, hide_index=True, key="editor_pagos_new")
        # Obtener seleccionados
        try:
            ids_sel = df_edit[df_edit["seleccionar"] == True]["id"].tolist() if "seleccionar" in df_edit.columns else []
        except:
            ids_sel = []
        col1, col2 = st.columns(2)
        if col1.button(f"✅ Marcar {len(ids_sel)} como PAGADO AL MEDICO", use_container_width=True):
            for i in ids_sel:
                conn.execute("UPDATE honorarios SET estado_pago='Pagado' WHERE rowid=?", (int(i),))
            conn.commit()
            st.success("Marcado como Pagado")
            st.rerun()
        if col2.button(f"↩️ Volver {len(ids_sel)} a PENDIENTE", use_container_width=True):
            for i in ids_sel:
                conn.execute("UPDATE honorarios SET estado_pago='Pendiente' WHERE rowid=?", (int(i),))
            conn.commit()
            st.success("Vuelto a Pendiente")
            st.rerun()
        buf_hon = crear_excel_bien({"Honorarios": df[cols_mostrar]})
        st.download_button("📥 Descargar Informe (Excel)", data=buf_hon, file_name="Honorarios.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Aún no hay honorarios con esos filtros. Ve a Importar Archivos.")

with tab3:
    st.write("### 📂 Importar Archivos - Sube y listo, actualiza solo")
    st.info("Solo sube el archivo. La app lee sola el Estado y actualiza. Tú solo te encargas de que el archivo venga con los estados claros.")
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
            df2 = pd.DataFrame()
            df2["paciente"] = df_imp[c_paciente].astype(str) if c_paciente else ""
            df2["medico"] = df_imp[c_medico].astype(str) if c_medico else "SIN ASIGNAR"
            df2["tramite"] = df_imp[c_tramite].astype(str) if c_tramite else ""
            df2["codigo"] = df_imp[c_codigo].astype(str) if c_codigo else ""
            df2["descripcion"] = df_imp[c_desc].astype(str) if c_desc else ""
            df2["valor"] = pd.to_numeric(df_imp[c_valor], errors="coerce").fillna(0) if c_valor else 0
            df2["fecha"] = ""
            df2["seguro"] = ""
            df2["mes_anio"] = ""
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
                    conn.execute("UPDATE honorarios SET estado_tramite=?, estado=? WHERE rowid=?", (row["estado_tramite"], row["estado_tramite"], int(existentes[clave])))
                    actualizados += 1
                else:
                    conn.execute("INSERT INTO honorarios (paciente, medico, fecha, codigo, descripcion, valor, seguro, tramite, mes_anio, valor_40, valor_50, valor_60, estado, estado_tramite, estado_pago, valor_pagado, es_paquete) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(row["paciente"]), str(row["medico"]), str(row["fecha"]), str(row["codigo"]), str(row["descripcion"]), float(row["valor"]), str(row["seguro"]), str(row["tramite"]), str(row["mes_anio"]), float(row["valor_40"]), float(row["valor_50"]), float(row["valor_60"]), str(row["estado_tramite"]), str(row["estado_tramite"]), "Pendiente", 0, 0))
                    nuevos += 1
            conn.commit()
            st.success(f"✅ ¡Listo! Automático. Nuevos: {nuevos} | Estados actualizados: {actualizados}")
            st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

with tab4:
    st.write("### 🔄 Actualizar Estados por Excel - Solo sube, no marques nada")
    st.success("Tú solo sube el archivo con los estados claros. La app actualiza sola.")
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

with tab5:
    st.write("### ⚙️ Gestión")
    st.write("**Sin Médico Asignado**")
    df_sin = arreglar_df(cargar_honorarios())
    df_sin = df_sin[(df_sin["medico"] == "SIN ASIGNAR") | (df_sin["medico"] == "") | (df_sin["medico"].isna())] if len(df_sin) > 0 else df_sin
    st.write(f"Líneas sin médico: {len(df_sin)}")
    st.dataframe(df_sin, use_container_width=True)
    if st.button("Salir"):
        st.session_state.login = False
        st.rerun()