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

def detectar_columnas(df_imp):
    cols_norm = {}
    for c in df_imp.columns:
        c_norm = str(c).strip().upper().replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U").replace("Ñ","N")
        cols_norm[c_norm] = c
    def buscar(posibles):
        for p in posibles:
            p_norm = p.upper().replace("Á","A").replace("É","E")
            if p_norm in cols_norm:
                return cols_norm[p_norm]
            for cn, orig in cols_norm.items():
                if p_norm in cn:
                    return orig
        return None
    return {
        "paciente": buscar(["NOMBRES DEL PACIENTE", "PACIENTE"]),
        "medico": buscar(["NOMBRE DEL MEDICO", "MEDICO", "DOCTOR"]),
        "fecha": buscar(["FECHA"]),
        "codigo": buscar(["CODIGO PLANILLADO", "CODIGO"]),
        "descripcion": buscar(["DESCRIPCION", "DETALLE"]),
        "valor": buscar(["VALOR DE CODIGO", "VALOR"]),
        "seguro": buscar(["SEGURO"]),
        "tramite": buscar(["N TRAMITE", "TRAMITE", "NUMERO TRAMITE"]),
        "mes": buscar(["MES Y ANO", "MES"]),
        "estado_tramite": buscar(["ESTADO DEL TRAMITE", "ESTADO TRAMITE", "ESTADO", "SITUACION", "ESTATUS", "CONDICION"]),
    }

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

try:
    df_resumen = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    df_med = pd.read_sql("SELECT * FROM medicos", conn)
    todos_medicos = sorted(set(df_resumen["medico"].dropna().astype(str).str.strip().unique().tolist() + df_med["nombre"].dropna().astype(str).str.strip().unique().tolist()) - set(["", "SIN ASIGNAR", "nan"])) if len(df_resumen) > 0 else []
    st.success(f"📋 Total registros: {len(df_resumen)} | 👨‍⚕️ Médicos: {len(todos_medicos)}")
except:
    st.info("Aún no hay datos")

MEDICOS_DEFAULT = ["SIN ASIGNAR", "GARCIA LOPEZ", "PEREZ JUAN", "OTRO"]
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
        st.write("**Por Pago al Médico:**")
        st.dataframe(df.groupby("estado_pago")["valor_60"].agg(["count", "sum"]).reset_index(), use_container_width=True)
        st.dataframe(df, use_container_width=True)

# --- BUSCADOR CON FLECHITAS ---
if menu == "Buscador":
    st.subheader("🔍 Buscador - Todo con flechita")
    st.info("1️⃣ Elige el médico con la flechita  2️⃣ Elige el trámite con la flechita  3️⃣ O escribe el N° de trámite arriba y te filtra solo")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df_all) == 0:
        st.info("Aún no hay datos. Ve a Importar Archivos.")
    else:
        # LÍNEA DE ARRIBA: Buscar por N° Trámite escribiendo
        st.write("### ✍️ Buscar rápido por N° de Trámite")
        buscar_tramite_texto = st.text_input("🔍 Escribe el N° de Trámite aquí arriba (ej: 12345)", placeholder="Escribe el número de trámite y dale Enter")
        st.divider()
        st.write("### ⬇️ Filtros con flechita - Desplegables")
        # Fila 1: Médico + Trámite desplegables
        col_m, col_t = st.columns(2)
        lista_medicos = ["Todos los médicos"] + sorted([m for m in df_all["medico"].dropna().astype(str).str.strip().unique() if m not in ["", "nan"]])
        medico_sel = col_m.selectbox("👨‍⚕️ Selecciona el Médico ⬇️", lista_medicos, help="Dale clic a la flechita y te salen todos los médicos")
        # Lista de trámites depende del médico elegido
        df_para_tramites = df_all.copy()
        if medico_sel != "Todos los médicos":
            df_para_tramites = df_all[df_all["medico"] == medico_sel]
        lista_tramites = ["Todos los trámites"] + sorted([t for t in df_para_tramites["tramite"].dropna().astype(str).str.strip().unique() if t not in ["", "nan"]])
        tramite_sel = col_t.selectbox("📋 Selecciona el N° de Trámite ⬇️", lista_tramites, help="Dale clic a la flechita y te salen todos los números de trámite de ese médico")
        # Fila 2: Estado Trámite + Estado Pago
        col_e1, col_e2 = st.columns(2)
        filtro_tramite = col_e1.selectbox("🔵 Filtrar por Estado del TRÁMITE ⬇️", ["Todos"] + sorted(df_all["estado_tramite"].unique().tolist()))
        filtro_pago = col_e2.selectbox("🟢 Filtrar por Estado PAGO AL MÉDICO ⬇️", ["Todos", "Pendiente", "Pagado"])
        # Aplicamos filtros
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
        st.divider()
        st.write(f"### 📋 Resultado: {len(df)} trámites encontrados")
        if medico_sel != "Todos los médicos":
            st.write(f"**Médico:** {medico_sel}")
        if tramite_sel != "Todos los trámites":
            st.write(f"**Trámite seleccionado:** {tramite_sel}")
        if buscar_tramite_texto:
            st.write(f"**Buscando trámite que contenga:** {buscar_tramite_texto}")
        if len(df) == 0:
            st.warning("No hay nada con esos filtros. Cambia el médico o el trámite con la flechita.")
        else:
            total_general = df["valor"].sum()
            total_60 = df["valor_60"].sum()
            total_pagado_medico = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
            total_pendiente_medico = total_60 - total_pagado_medico
            c1, c2 = st.columns(2)
            c1.metric("Total General (filtrado)", f"${total_general:,.2f}")
            c2.metric("Total 60% (filtrado)", f"${total_60:,.2f}")
            c3, c4, c5 = st.columns(3)
            c3.metric("Pagado AL MEDICO", f"${total_pagado_medico:,.2f}")
            c4.metric("Pendiente AL MEDICO", f"${total_pendiente_medico:,.2f}")
            c5.metric("N° Trámites", len(df))
            cols_mostrar = [c for c in ["id", "medico", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "mes_anio", "estado_tramite", "estado_pago"] if c in df.columns]
            st.dataframe(df[cols_mostrar], use_container_width=True)
            # Marcar pago al médico
            st.write("#### ✅ Marcar PAGO AL MÉDICO")
            df["seleccionar"] = False
            cols_edit = [c for c in ["seleccionar", "id", "medico", "paciente", "codigo", "tramite", "valor", "valor_60", "estado_tramite", "estado_pago"] if c in df.columns]
            df_edit = st.data_editor(df[cols_edit], use_container_width=True, hide_index=True, key="editor_pagos_bus")
            ids_sel = sacar_seleccionados(df_edit)
            col1, col2 = st.columns(2)
            if col1.button(f"✅ Marcar {len(ids_sel)} como PAGADO AL MEDICO"):
                for i in ids_sel:
                    conn.execute("UPDATE honorarios SET estado_pago='Pagado' WHERE id=?", (int(i),))
                conn.commit()
                st.success("Marcado como Pagado al Médico")
                st.rerun()
            if col2.button(f"↩️ Volver {len(ids_sel)} a PENDIENTE AL MEDICO"):
                for i in ids_sel:
                    conn.execute("UPDATE honorarios SET estado_pago='Pendiente' WHERE id=?", (int(i),))
                conn.commit()
                st.success("Vuelto a Pendiente")
                st.rerun()
            st.divider()
            resumen = pd.DataFrame([{"Medico": medico_sel, "Tramite": tramite_sel, "Total General": round(total_general, 2), "Total 60%": round(total_60, 2), "Pagado al Medico": round(total_pagado_medico, 2), "Pendiente al Medico": round(total_pendiente_medico, 2), "N Tramites": len(df)}])
            buf = crear_excel_bien({"Resumen": resumen, "Detalle": df[cols_mostrar]})
            st.download_button("📥 Descargar resumen filtrado en Excel", data=buf, file_name="Resumen_filtrado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if menu == "Importar Archivos":
    st.subheader("📂 Importar Archivos - ACTUALIZA estados automáticamente")
    st.success("Si vuelves a cargar el mismo archivo con estados nuevos, YA NO lo salta. Lo ACTUALIZA.")
    df_existente = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    st.info(f"Ya tienes: {len(df_existente)} registros")
    archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"], key="import1")
    if archivo is not None:
        try:
            xls = pd.ExcelFile(archivo)
            hoja = "FORMATO FINAL  " if "FORMATO FINAL  " in xls.sheet_names else xls.sheet_names[0]
            df_imp = pd.read_excel(archivo, sheet_name=hoja)
            df_imp.columns = [str(c).strip() for c in df_imp.columns]
            st.write("Hoja:", hoja, "| Columnas:", list(df_imp.columns))
            cols = detectar_columnas(df_imp)
            st.write(f"Columna Estado detectada: **{cols['estado_tramite']}**")
            if cols["estado_tramite"]:
                st.write("Estados que trae tu Excel:")
                st.dataframe(df_imp[cols["estado_tramite"]].astype(str).value_counts().reset_index(), use_container_width=True)
            df2 = pd.DataFrame()
            df2["paciente"] = df_imp[cols["paciente"]] if cols["paciente"] else ""
            df2["medico"] = df_imp[cols["medico"]] if cols["medico"] else ""
            df2["fecha"] = df_imp[cols["fecha"]] if cols["fecha"] else ""
            df2["codigo"] = df_imp[cols["codigo"]] if cols["codigo"] else ""
            df2["descripcion"] = df_imp[cols["descripcion"]] if cols["descripcion"] else ""
            df2["valor"] = pd.to_numeric(df_imp[cols["valor"]], errors="coerce").fillna(0) if cols["valor"] else 0
            df2["seguro"] = df_imp[cols["seguro"]] if cols["seguro"] else ""
            df2["tramite"] = df_imp[cols["tramite"]] if cols["tramite"] else ""
            df2["mes_anio"] = df_imp[cols["mes"]] if cols["mes"] else ""
            df2 = df2[df2["paciente"].astype(str).str.strip() != ""]
            df2 = df2[~df2["paciente"].astype(str).str.contains("Suma|Total|Etiquetas", na=False)]
            df2["medico"] = df2["medico"].fillna("").astype(str).str.strip()
            df2.loc[df2["medico"] == "", "medico"] = "SIN ASIGNAR"
            df2["estado_tramite"] = df_imp[cols["estado_tramite"]].apply(limpiar_estado) if cols["estado_tramite"] else "Pendiente"
            df2["estado"] = df2["estado_tramite"]
            df2["estado_pago"] = "Pendiente"
            df2["valor_40"] = (df2["valor"] * 0.40).round(2)
            df2["valor_50"] = (df2["valor"] * 0.50).round(2)
            df2["valor_60"] = (df2["valor"] * 0.60).round(2)
            df2["valor_pagado"] = 0
            df2["es_paquete"] = 0
            st.dataframe(df2[["paciente", "tramite", "codigo", "estado_tramite"]].head(20))
            if st.button("💾 CARGAR / ACTUALIZAR"):
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
                st.success(f"✅ Nuevos: {nuevos} | Estados actualizados: {actualizados}")
                st.balloons()
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

if menu == "Actualizar Estados por Excel":
    st.subheader("🔄 Actualizar Estados por Excel - Automático")
    st.info("Carga el Excel con estados nuevos y se actualiza solo. No toca el Pago al Médico.")
    archivo2 = st.file_uploader("Sube el Excel con estados actualizados", type=["xlsx", "xls"], key="import_estados")
    if archivo2 is not None:
        try:
            xls = pd.ExcelFile(archivo2)
            hoja = "FORMATO FINAL  " if "FORMATO FINAL  " in xls.sheet_names else xls.sheet_names[0]
            df_imp = pd.read_excel(archivo2, sheet_name=hoja)
            df_imp.columns = [str(c).strip() for c in df_imp.columns]
            cols = detectar_columnas(df_imp)
            st.write(f"Columna Estado: {cols['estado_tramite']}")
            if cols["estado_tramite"]:
                st.dataframe(df_imp[cols["estado_tramite"]].astype(str).value_counts().reset_index(), use_container_width=True)
                df_upd = pd.DataFrame()
                df_upd["paciente"] = df_imp[cols["paciente"]] if cols["paciente"] else ""
                df_upd["tramite"] = df_imp[cols["tramite"]] if cols["tramite"] else ""
                df_upd["codigo"] = df_imp[cols["codigo"]] if cols["codigo"] else ""
                df_upd["estado_nuevo"] = df_imp[cols["estado_tramite"]].apply(limpiar_estado)
                st.dataframe(df_upd.head(20))
                if st.button("🔄 ACTUALIZAR ESTADOS AHORA"):
                    actualizados = 0
                    no_encontrados = 0
                    for _, row in df_upd.iterrows():
                        pac = str(row["paciente"]).strip()
                        tram = str(row["tramite"]).strip()
                        cod = str(row["codigo"]).strip()
                        cur = conn.execute("SELECT id FROM honorarios WHERE paciente=? AND tramite=? AND codigo=?", (pac, tram, cod)).fetchone()
                        if not cur and tram != "":
                            cur = conn.execute("SELECT id FROM honorarios WHERE tramite=?", (tram,)).fetchone()
                        if cur:
                            conn.execute("UPDATE honorarios SET estado_tramite=?, estado=? WHERE id=?", (row["estado_nuevo"], row["estado_nuevo"], int(cur[0])))
                            actualizados += 1
                        else:
                            no_encontrados += 1
                    conn.commit()
                    st.success(f"✅ Actualizados: {actualizados} | No encontrados: {no_encontrados}")
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

if menu == "Sin Médico Asignado":
    st.subheader("✏️ Sin Médico Asignado")
    df_sin = arreglar_df(pd.read_sql("SELECT * FROM honorarios WHERE medico='SIN ASIGNAR' OR medico='' OR medico IS NULL", conn))
    st.write(f"Líneas sin médico: {len(df_sin)}")
    st.dataframe(df_sin, use_container_width=True)

if menu == "Médicos":
    st.subheader("👨‍⚕️ Médicos")
    df_medicos = pd.read_sql("SELECT * FROM medicos", conn)
    st.dataframe(df_medicos, use_container_width=True)
    with st.form("nm"):
        n = st.text_input("Nombre *").upper()
        ced = st.text_input("Cédula")
        esp = st.text_input("Especialidad")
        sen = st.text_input("Registro Senescyt")
        if st.form_submit_button("Agregar Médico"):
            conn.execute("INSERT OR REPLACE INTO medicos (nombre,cedula,especialidad,registro_senescyt) VALUES (?,?,?,?)", (n, ced, esp, sen))
            conn.commit()
            st.success("Médico agregado")
            st.rerun()

if menu == "Actualizar Estados":
    st.subheader("🔄 Actualizar Estados - Manual con flechitas")
    st.info("Aquí también con flechitas: elige médico, elige trámite, y edita los estados.")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df_all) == 0:
        st.info("Aún no hay datos.")
    else:
        st.write("### ✍️ Buscar por N° de Trámite")
        buscar_t = st.text_input("🔍 Escribe el N° de Trámite aquí", placeholder="Ej: 12345", key="buscar_t_estados")
        st.write("### ⬇️ Filtros con flechita")
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