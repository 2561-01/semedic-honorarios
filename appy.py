import streamlit as st
import pandas as pd
import sqlite3
import io

st.set_page_config(page_title="SEMEDIC - Honorarios", layout="wide")

if "login" not in st.session_state:
    st.session_state.login = False
if not st.session_state.login:
    st.title("SEMEDIC - Honorarios")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "semedic2026":
            st.session_state.login = True
            st.session_state.usuario = "admin"
            st.session_state.rol = "ADMINISTRADOR"
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrecta")
    st.stop()

st.sidebar.write(f"Usuario: {st.session_state.usuario} | Rol: {st.session_state.rol}")
if st.sidebar.button("Salir"):
    st.session_state.login = False
    st.rerun()

conn = sqlite3.connect("honorarios.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS honorarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente TEXT, medico TEXT, fecha TEXT, codigo TEXT,
    descripcion TEXT, valor REAL, seguro TEXT, tramite TEXT,
    mes_anio TEXT, valor_40 REAL, valor_50 REAL, valor_60 REAL,
    estado TEXT, estado_tramite TEXT, estado_pago TEXT, valor_pagado REAL,
    es_paquete INTEGER DEFAULT 0
)""")
for col, tipo in [("estado_pago","TEXT DEFAULT 'Pendiente'"), ("valor_pagado","REAL DEFAULT 0"), ("es_paquete","INTEGER DEFAULT 0"), ("valor_40","REAL DEFAULT 0"), ("valor_50","REAL DEFAULT 0"), ("valor_60","REAL DEFAULT 0"), ("estado_tramite","TEXT DEFAULT 'Pendiente'")]:
    try:
        conn.execute(f"ALTER TABLE honorarios ADD COLUMN {col} {tipo}")
    except:
        pass
conn.execute("""CREATE TABLE IF NOT EXISTS medicos (
    nombre TEXT, cedula TEXT, especialidad TEXT, registro_senescyt TEXT
)""")
conn.commit()

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

def sacar_seleccionados(df_edit):
    try:
        if df_edit is None or len(df_edit) == 0:
            return []
        if "seleccionar" not in df_edit.columns or "id" not in df_edit.columns:
            return []
        sel = df_edit[df_edit["seleccionar"] == True]
        return sel["id"].tolist() if len(sel) > 0 else []
    except:
        return []

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
    v = str(valor).strip().upper()
    if "PAGAD" in v:
        return "Pagado"
    if "LIQUID" in v:
        return "Liquidado"
    if "DESPACH" in v:
        return "Despachado"
    if "PENDIENT" in v:
        return "Pendiente"
    if "TRAMITE" in v or "PROCESO" in v or "EN TRAM" in v:
        return "En Trámite"
    if "OBSERV" in v:
        return "Observado"
    if "RECHAZ" in v or "NEGAD" in v:
        return "Rechazado"
    return str(valor).strip().title()

def buscar_col(cols, posibles):
    # Busca la columna aunque se llame un poco diferente, ej: ESTADO ISSPOL, ESTADO TRAMITE, etc.
    cols_norm = {str(c).strip().upper().replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U"): c for c in cols}
    for p in posibles:
        pn = p.upper().replace("Á","A").replace("É","E")
        if pn in cols_norm:
            return cols_norm[pn]
        for cn, orig in cols_norm.items():
            if pn in cn:
                return orig
    return None

# Lee el Excel y lo deja listo, sin que tú marques nada
def leer_excel_auto(archivo):
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        xls = pd.ExcelFile(archivo)
        # Si tiene FORMATO FINAL usa esa, si no la primera hoja
        hoja = "FORMATO FINAL  " if "FORMATO FINAL  " in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(archivo, sheet_name=hoja)
    df.columns = [str(c).strip() for c in df.columns]
    return df

try:
    df_resumen = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    df_med = pd.read_sql("SELECT * FROM medicos", conn)
    todos_medicos = sorted(set(df_resumen["medico"].dropna().astype(str).str.strip().unique().tolist() + df_med["nombre"].dropna().astype(str).str.strip().unique().tolist()) - set(["", "SIN ASIGNAR", "nan"])) if len(df_resumen) > 0 else []
    st.success(f"📋 Total registros: {len(df_resumen)} | 👨‍⚕️ Médicos: {len(todos_medicos)}")
except:
    st.info("Aún no hay datos")

menu = st.sidebar.selectbox("Menú", ["Dashboard", "Buscador", "Importar Archivos", "Sin Médico Asignado", "Médicos", "Actualizar Estados", "Actualizar Estados por Excel"])

if menu == "Dashboard":
    st.subheader("Dashboard - Todo se paga al 60%")
    df = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df) == 0:
        st.info("Aún no hay datos.")
    else:
        total_general = df["valor"].sum()
        total_60 = df["valor_60"].sum()
        pagado_60 = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
        pendiente_60 = total_60 - pagado_60
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total General", f"${total_general:,.2f}")
        c2.metric("Total 60%", f"${total_60:,.2f}")
        c3.metric("Pagado AL MEDICO", f"${pagado_60:,.2f}")
        c4.metric("Pendiente AL MEDICO", f"${pendiente_60:,.2f}")
        st.write("**Por Estado Trámite:**")
        st.dataframe(df.groupby("estado_tramite")["valor_60"].agg(["count", "sum"]).reset_index(), use_container_width=True)
        st.dataframe(df, use_container_width=True)

if menu == "Buscador":
    st.subheader("🔍 Buscador - Todo con flechita")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df_all) == 0:
        st.info("Aún no hay datos.")
    else:
        buscar_tramite_texto = st.text_input("🔍 Escribe el N° de Trámite aquí arriba", placeholder="Ej: 12345")
        col_m, col_t = st.columns(2)
        lista_medicos = ["Todos los médicos"] + sorted([m for m in df_all["medico"].dropna().astype(str).str.strip().unique() if m not in ["", "nan"]])
        medico_sel = col_m.selectbox("👨‍⚕️ Selecciona el Médico ⬇️", lista_medicos)
        df_para_tramites = df_all.copy()
        if medico_sel != "Todos los médicos":
            df_para_tramites = df_all[df_all["medico"] == medico_sel]
        lista_tramites = ["Todos los trámites"] + sorted([t for t in df_para_tramites["tramite"].dropna().astype(str).str.strip().unique() if t not in ["", "nan"]])
        tramite_sel = col_t.selectbox("📋 Selecciona el N° de Trámite ⬇️", lista_tramites)
        col_e1, col_e2 = st.columns(2)
        filtro_tramite = col_e1.selectbox("🔵 Estado del TRÁMITE ⬇️", ["Todos"] + sorted(df_all["estado_tramite"].unique().tolist()))
        filtro_pago = col_e2.selectbox("🟢 Estado PAGO AL MÉDICO ⬇️", ["Todos", "Pendiente", "Pagado"])
        df = df_all.copy()
        if medico_sel != "Todos los médicos":
            df = df[df["medico"] == medico_sel]
        if tramite_sel != "Todos los trámites":
            df = df[df["tramite"].astype(str).str.strip() == tramite_sel]
        if buscar_tramite_texto:
            df = df[df["tramite"].astype(str).str.contains(buscar_tramite_texto.strip(), na=False)]
        if filtro_tramite != "Todos":
            df = df[df["estado_tramite"] == filtro_tramite]
        if filtro_pago != "Todos":
            df = df[df["estado_pago"] == filtro_pago]
        st.write(f"Resultado: {len(df)} trámites")
        if len(df) > 0:
            cols_mostrar = [c for c in ["id", "medico", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "estado_tramite", "estado_pago"] if c in df.columns]
            st.dataframe(df[cols_mostrar], use_container_width=True)

if menu == "Importar Archivos":
    st.subheader("📂 Importar Archivos - Sube y listo, actualiza solo")
    st.info("Solo sube el archivo. La app lee sola el Estado y actualiza. Tú solo te encargas de que el archivo venga con los estados claros.")
    df_existente = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    st.info(f"Ya tienes: {len(df_existente)} registros")
    archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls", "csv"], key="import1")
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
            # --- ACTUALIZA SOLO, SIN BOTÓN DE CARGAR ---
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
                    conn.execute("UPDATE honorarios SET estado_tramite=?, estado=? WHERE id=?", (row["estado_tramite"], row["estado_tramite"], int(existentes[clave])))
                    actualizados += 1
                else:
                    conn.execute("INSERT INTO honorarios (paciente, medico, fecha, codigo, descripcion, valor, seguro, tramite, mes_anio, valor_40, valor_50, valor_60, estado, estado_tramite, estado_pago, valor_pagado, es_paquete) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(row["paciente"]), str(row["medico"]), str(row["fecha"]), str(row["codigo"]), str(row["descripcion"]), float(row["valor"]), str(row["seguro"]), str(row["tramite"]), str(row["mes_anio"]), float(row["valor_40"]), float(row["valor_50"]), float(row["valor_60"]), str(row["estado_tramite"]), str(row["estado_tramite"]), "Pendiente", 0, 0))
                    nuevos += 1
            conn.commit()
            st.success(f"✅ ¡Listo! Automático. Nuevos: {nuevos} | Estados actualizados: {actualizados}")
            st.balloons()
            if c_estado:
                st.write("Estados que traía tu archivo:")
                st.dataframe(df_imp[c_estado].astype(str).value_counts().reset_index(), use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

# --- ACTUALIZAR ESTADOS POR EXCEL - SUBE Y LISTO, SIN MARCAR NADA ---
if menu == "Actualizar Estados por Excel":
    st.subheader("🔄 Actualizar Estados por Excel - Solo sube, no marques nada")
    st.success("Tú solo sube el archivo con los estados claros. La app actualiza sola. No tienes que elegir columna, ni hoja, ni darle a otro botón.")
    st.write("Tu archivo debe tener: Trámite, Paciente y Estado (Pagado, Liquidado, Despachado, Pendiente...)")
    archivo2 = st.file_uploader("Sube el Excel con los estados", type=["xlsx", "xls", "csv"], key="import_estados")
    if archivo2 is not None:
        try:
            df_imp = leer_excel_auto(archivo2)
            cols = list(df_imp.columns)
            c_estado2 = buscar_col(cols, ["ESTADO DEL TRAMITE", "ESTADO TRAMITE", "ESTADO", "SITUACION", "ESTATUS"])
            c_tramite2 = buscar_col(cols, ["N TRAMITE", "TRAMITE", "NUMERO TRAMITE"])
            c_paciente2 = buscar_col(cols, ["NOMBRES DEL PACIENTE", "PACIENTE"])
            c_codigo2 = buscar_col(cols, ["CODIGO PLANILLADO", "CODIGO"])
            if not c_estado2 or not c_tramite2:
                st.error("No encontré la columna ESTADO o TRÁMITE en tu archivo. Revisa que tu archivo tenga una columna que diga ESTADO y otra que diga TRÁMITE.")
                st.write("Columnas que tiene tu archivo:", cols)
            else:
                st.write(f"Leído: Estado = {c_estado2} | Trámite = {c_tramite2}")
                st.write("Estados que trae tu archivo:")
                st.dataframe(df_imp[c_estado2].astype(str).value_counts().reset_index(), use_container_width=True)
                # --- ACTUALIZA SOLO, SIN BOTÓN ---
                actualizados = 0
                no_encontrados = 0
                for _, row in df_imp.iterrows():
                    tram = str(row[c_tramite2]).strip()
                    pac = str(row[c_paciente2]).strip() if c_paciente2 else ""
                    cod = str(row[c_codigo2]).strip() if c_codigo2 else ""
                    estado_nuevo = limpiar_estado(row[c_estado2])
                    cur = None
                    if pac and tram and cod:
                        cur = conn.execute("SELECT id FROM honorarios WHERE paciente=? AND tramite=? AND codigo=?", (pac, tram, cod)).fetchone()
                    if not cur and tram != "":
                        cur = conn.execute("SELECT id FROM honorarios WHERE tramite=?", (tram,)).fetchone()
                    if not cur and pac and cod:
                        cur = conn.execute("SELECT id FROM honorarios WHERE paciente=? AND codigo=?", (pac, cod)).fetchone()
                    if cur:
                        conn.execute("UPDATE honorarios SET estado_tramite=?, estado=? WHERE id=?", (estado_nuevo, estado_nuevo, int(cur[0])))
                        actualizados += 1
                    else:
                        no_encontrados += 1
                conn.commit()
                st.success(f"✅ ¡Actualizado solo! Actualizados: {actualizados} | No encontrados: {no_encontrados}")
                st.balloons()
                if no_encontrados > 0:
                    st.warning("Los no encontrados es porque ese N° de Trámite aún no está cargado en la base.")
        except Exception as e:
            st.error(f"Error: {e}")

if menu == "Sin Médico Asignado":
    st.subheader("✏️ Sin Médico Asignado")
    df_sin = arreglar_df(pd.read_sql("SELECT * FROM honorarios WHERE medico='SIN ASIGNAR' OR medico='' OR medico IS NULL", conn))
    st.write(f"Líneas sin médico: {len(df_sin)}")
    st.dataframe(df_sin, use_container_width=True)

if menu == "Médicos":
    st.subheader("👨‍⚕️ Médicos - Manual o Cargar Archivo")
    df_medicos = pd.read_sql("SELECT * FROM medicos", conn)
    st.write(f"Médicos registrados: {len(df_medicos)}")
    st.dataframe(df_medicos, use_container_width=True)
    st.divider()
    st.write("### ✍️ FORMA 1: Agregar a mano")
    with st.form("nm"):
        n = st.text_input("Nombre *").upper()
        ced = st.text_input("Cédula")
        esp = st.text_input("Especialidad")
        sen = st.text_input("Registro Senescyt")
        if st.form_submit_button("➕ Agregar Médico Manual"):
            if n.strip() == "":
                st.warning("Escribe el nombre")
            else:
                conn.execute("INSERT OR REPLACE INTO medicos (nombre,cedula,especialidad,registro_senescyt) VALUES (?,?,?,?)", (n, ced, esp, sen))
                conn.commit()
                st.success(f"Médico {n} agregado")
                st.rerun()
    st.divider()
    st.write("### 📂 FORMA 2: Cargar archivo con médicos - Sube y listo")
    st.info("Sube tu Excel de médicos. La app lee sola la columna de Nombre. No tienes que marcar nada.")
    buf_plantilla = crear_excel_bien({"Medicos": pd.DataFrame([{"Nombre": "MARIO PEREZ", "Cedula": "0912345678", "Especialidad": "Cirugia", "Registro Senescyt": "12345"}])})
    st.download_button("📥 Descargar plantilla de médicos", data=buf_plantilla, file_name="Plantilla_Medicos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    archivo_medicos = st.file_uploader("Sube tu archivo Excel de médicos", type=["xlsx", "xls"], key="upload_medicos")
    if archivo_medicos is not None:
        try:
            df_m_imp = leer_excel_auto(archivo_medicos)
            cols_m = list(df_m_imp.columns)
            c_nombre_m = buscar_col(cols_m, ["NOMBRE DEL MEDICO", "NOMBRE", "MEDICO", "DOCTOR"])
            c_ced_m = buscar_col(cols_m, ["CEDULA", "CI", "IDENTIFICACION"])
            c_esp_m = buscar_col(cols_m, ["ESPECIALIDAD"])
            if not c_nombre_m:
                st.error("No encontré columna de Nombre en tu archivo de médicos.")
                st.write("Columnas:", cols_m)
            else:
                df_nuevos = pd.DataFrame()
                df_nuevos["nombre"] = df_m_imp[c_nombre_m].astype(str).str.strip().str.upper()
                df_nuevos["cedula"] = df_m_imp[c_ced_m].astype(str).str.strip() if c_ced_m else ""
                df_nuevos["especialidad"] = df_m_imp[c_esp_m].astype(str).str.strip() if c_esp_m else ""
                df_nuevos["registro_senescyt"] = ""
                df_nuevos = df_nuevos[df_nuevos["nombre"] != ""]
                df_nuevos = df_nuevos[~df_nuevos["nombre"].isin(["NAN", "NONE"])]
                df_nuevos = df_nuevos.drop_duplicates(subset=["nombre"])
                ya_existentes = set(df_medicos["nombre"].astype(str).str.strip().str.upper().tolist()) if len(df_medicos) > 0 else set()
                df_nuevos_f = df_nuevos[~df_nuevos["nombre"].isin(ya_existentes)]
                for _, r in df_nuevos_f.iterrows():
                    conn.execute("INSERT INTO medicos (nombre,cedula,especialidad,registro_senescyt) VALUES (?,?,?,?)", (r["nombre"], r["cedula"], r["especialidad"], r["registro_senescyt"]))
                conn.commit()
                st.success(f"✅ ¡Listo! Se cargaron {len(df_nuevos_f)} médicos nuevos, sin marcar nada.")
                st.balloons()
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    buf = crear_excel_bien({"Medicos": df_medicos})
    st.download_button("📥 Descargar médicos en Excel", data=buf, file_name="medicos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if menu == "Actualizar Estados":
    st.subheader("🔄 Actualizar Estados - Manual con flechitas")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df_all) == 0:
        st.info("Aún no hay datos.")
    else:
        buscar_t = st.text_input("🔍 Escribe el N° de Trámite aquí", placeholder="Ej: 12345", key="buscar_t_estados")
        col_m2, col_t2 = st.columns(2)
        lista_med2 = ["Todos los médicos"] + sorted([m for m in df_all["medico"].dropna().astype(str).unique() if m not in ["", "nan"]])
        f_medico = col_m2.selectbox("👨‍⚕️ Médico ⬇️", lista_med2, key="f_med_est")
        df_para_t2 = df_all.copy()
        if f_medico != "Todos los médicos":
            df_para_t2 = df_all[df_all["medico"] == f_medico]
        lista_tram2 = ["Todos los trámites"] + sorted([t for t in df_para_t2["tramite"].dropna().astype(str).unique() if t not in ["", "nan"]])
        f_tramite_num = col_t2.selectbox("📋 N° Trámite ⬇️", lista_tram2, key="f_tram_est")
        df_f = df_all.copy()
        if f_medico != "Todos los médicos":
            df_f = df_f[df_f["medico"] == f_medico]
        if f_tramite_num != "Todos los trámites":
            df_f = df_f[df_f["tramite"].astype(str) == f_tramite_num]
        if buscar_t:
            df_f = df_f[df_f["tramite"].astype(str).str.contains(buscar_t.strip(), na=False)]
        st.write(f"Mostrando {len(df_f)} trámites")
        df_editable = df_f[["id", "medico", "paciente", "codigo", "tramite", "valor_60", "estado_tramite", "estado_pago"]].copy()
        df_editado = st.data_editor(df_editable, use_container_width=True, hide_index=True, key="editor_estados2", column_config={"estado_tramite": st.column_config.SelectboxColumn("Estado Trámite ⬇️", options=["Pendiente", "Pagado", "Liquidado", "Despachado", "En Trámite", "Observado", "Rechazado"]), "estado_pago": st.column_config.SelectboxColumn("Pago al Médico ⬇️", options=["Pendiente", "Pagado"])}, disabled=["id", "medico", "paciente", "codigo", "tramite", "valor_60"])
        if st.button("💾 GUARDAR CAMBIOS", type="primary"):
            cambios = 0
            for _, row in df_editado.iterrows():
                orig = df_f[df_f["id"] == row["id"]]
                if len(orig) > 0 and (row["estado_tramite"] != orig.iloc[0]["estado_tramite"] or row["estado_pago"] != orig.iloc[0]["estado_pago"]):
                    conn.execute("UPDATE honorarios SET estado_tramite=?, estado_pago=?, estado=? WHERE id=?", (row["estado_tramite"], row["estado_pago"], row["estado_tramite"], int(row["id"])))
                    cambios += 1
            conn.commit()
            st.success(f"Se guardaron {cambios} cambios")
            st.rerun()