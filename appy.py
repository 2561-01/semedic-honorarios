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
    df.loc[(df["valor_60"] == 0) & (df["valor"] != 0), "valor_60"] = (df["valor"] * 0.60).round(2)
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

try:
    df_resumen = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    df_med = pd.read_sql("SELECT * FROM medicos", conn)
    medicos_honorarios = df_resumen["medico"].dropna().astype(str).str.strip().unique().tolist() if len(df_resumen) > 0 else []
    medicos_registrados = df_med["nombre"].dropna().astype(str).str.strip().unique().tolist() if len(df_med) > 0 else []
    todos_medicos = sorted(set(medicos_honorarios + medicos_registrados) - set(["", "SIN ASIGNAR", "nan"]))
    total_medicos = len(todos_medicos)
    if len(df_resumen) > 0:
        meses = df_resumen["mes_anio"].dropna().astype(str).str.strip() if "mes_anio" in df_resumen.columns else pd.Series([])
        meses = meses[meses != ""]
        if len(meses) > 0:
            texto_rango = f"Honorarios actualizados desde: {sorted(meses.unique())[0]}  hasta: {sorted(meses.unique())[-1]}"
        else:
            fechas = pd.to_datetime(df_resumen["fecha"], errors="coerce").dropna() if "fecha" in df_resumen.columns else pd.Series([])
            texto_rango = f"Honorarios actualizados desde: {fechas.min().strftime('%B %Y')}  hasta: {fechas.max().strftime('%B %Y')}" if len(fechas) > 0 else "Sin datos aún"
    else:
        texto_rango = "Honorarios actualizados: Aún no has cargado ningún archivo"
    st.success(f"📅 {texto_rango}   |   👨‍⚕️ Médicos registrados: {total_medicos}   |   📋 Total registros: {len(df_resumen)}")
except Exception as e:
    st.info("Aún no hay datos cargados")

MEDICOS_DEFAULT = ["SIN ASIGNAR", "GARCIA LOPEZ", "PEREZ JUAN", "OTRO"]
# --- AHORA SON 6 PESTAÑAS, LA NUEVA ES ACTUALIZAR ESTADOS ---
menu = st.sidebar.selectbox("Menú", ["Dashboard", "Buscador", "Importar Archivos", "Sin Médico Asignado", "Médicos", "Actualizar Estados"])

if menu == "Dashboard":
    st.subheader("Dashboard - Todo se paga al 60%")
    df = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df) == 0:
        st.info("Aún no hay datos. Ve a Importar Archivos y carga tu Excel.")
    else:
        total_general = df["valor"].sum()
        total_60 = df["valor_60"].sum()
        pagado_60 = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
        pendiente_60 = total_60 - pagado_60
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total General Cargado", f"${total_general:,.2f}")
        c2.metric("Total a Pagar (60%)", f"${total_60:,.2f}")
        c3.metric("Pagado AL MEDICO (60%)", f"${pagado_60:,.2f}")
        c4.metric("Pendiente AL MEDICO (60%)", f"${pendiente_60:,.2f}")
        st.write("**Resumen por Estado del Trámite:**")
        st.dataframe(df.groupby("estado_tramite")["valor_60"].agg(["count", "sum"]).reset_index().rename(columns={"estado_tramite": "Estado Trámite", "count": "N° Trámites", "sum": "Total 60%"}), use_container_width=True)
        st.write("**Resumen por Estado Pago al Médico:**")
        st.dataframe(df.groupby("estado_pago")["valor_60"].agg(["count", "sum"]).reset_index().rename(columns={"estado_pago": "Estado Pago al Médico", "count": "N° Trámites", "sum": "Total 60%"}), use_container_width=True)
        st.dataframe(df, use_container_width=True)
        buf = crear_excel_bien({"Honorarios": df})
        st.download_button("📥 Descargar en Excel bien", data=buf, file_name="honorarios.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if menu == "Buscador":
    st.subheader("Buscador por Médico - 2 estados separados")
    st.info("🔵 Estado Trámite = lo que dice tu archivo. 🟢 Estado Pago al Médico = si TÚ ya le pagaste su 60%.")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    lista = sorted([m for m in df_all["medico"].dropna().astype(str).str.strip().unique() if m not in ["", "SIN ASIGNAR", "nan"]]) if len(df_all) > 0 else []
    if len(lista) == 0:
        st.info("Aún no hay médicos cargados.")
        st.dataframe(df_all, use_container_width=True)
    else:
        medico_sel = st.selectbox("Selecciona el médico", ["-- Elige un médico --"] + lista)
        if medico_sel and medico_sel != "-- Elige un médico --":
            df_base = df_all[df_all["medico"] == medico_sel].copy()
            col_f1, col_f2 = st.columns(2)
            estados_tramite = ["Todos"] + sorted(df_base["estado_tramite"].unique().tolist())
            filtro_tramite = col_f1.selectbox("Filtrar por Estado del TRÁMITE", estados_tramite)
            filtro_pago = col_f2.selectbox("Filtrar por Estado del PAGO AL MÉDICO", ["Todos", "Pendiente", "Pagado"])
            df = df_base.copy()
            if filtro_tramite != "Todos":
                df = df[df["estado_tramite"] == filtro_tramite]
            if filtro_pago != "Todos":
                df = df[df["estado_pago"] == filtro_pago]
            st.write(f"Mostrando: {len(df)} de {len(df_base)} trámites")
            if len(df) > 0:
                total_general = df["valor"].sum()
                total_60 = df["valor_60"].sum()
                total_pagado_medico = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
                total_pendiente_medico = total_60 - total_pagado_medico
                st.write(f"### 👨‍⚕️ {medico_sel}")
                c1, c2 = st.columns(2)
                c1.metric("Total General", f"${total_general:,.2f}")
                c2.metric("Total 60%", f"${total_60:,.2f}")
                c3, c4, c5 = st.columns(3)
                c3.metric("Pagado AL MEDICO", f"${total_pagado_medico:,.2f}")
                c4.metric("Pendiente AL MEDICO", f"${total_pendiente_medico:,.2f}")
                c5.metric("N° Trámites", len(df))
                cols_mostrar = [c for c in ["id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "mes_anio", "estado_tramite", "estado_pago"] if c in df.columns]
                st.dataframe(df[cols_mostrar], use_container_width=True)
                resumen = pd.DataFrame([{"Medico": medico_sel, "Total General": round(total_general, 2), "Total 60%": round(total_60, 2), "Pagado al Medico": round(total_pagado_medico, 2), "Pendiente al Medico": round(total_pendiente_medico, 2), "N Tramites": len(df)}])
                buf = crear_excel_bien({"Resumen": resumen, "Detalle": df[cols_mostrar]})
                st.download_button(f"📥 Descargar resumen de {medico_sel}", data=buf, file_name=f"Resumen_{medico_sel.replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if menu == "Importar Archivos":
    st.subheader("📂 Importar Archivos - Se va alimentando, NO borra lo anterior")
    st.info("Aquí cargas el archivo y la app lee sola la columna ESTADO del Trámite: Pagado, Pendiente, Liquidado, etc.")
    df_existente = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    st.info(f"Ya tienes guardados: {len(df_existente)} registros")
    archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"])
    if archivo is not None:
        try:
            xls = pd.ExcelFile(archivo)
            hoja = "FORMATO FINAL  " if "FORMATO FINAL  " in xls.sheet_names else xls.sheet_names[0]
            df_imp = pd.read_excel(archivo, sheet_name=hoja)
            df_imp.columns = [str(c).strip().upper() for c in df_imp.columns]
            st.write("Hoja leída:", hoja)
            st.write("Columnas que encontró:", list(df_imp.columns))
            def buscar_col(posibles):
                for p in posibles:
                    for c in df_imp.columns:
                        if p in c:
                            return c
                return None
            c_paciente = buscar_col(["NOMBRES DEL PACIENTE", "PACIENTE"])
            c_medico = buscar_col(["NOMBRE DEL MEDICO", "MEDICO"])
            c_fecha = buscar_col(["FECHA"])
            c_codigo = buscar_col(["CODIGO PLANILLADO", "CODIGO"])
            c_desc = buscar_col(["DESCRIPCION"])
            c_valor = buscar_col(["VALOR DE CODIGO", "VALOR"])
            c_seguro = buscar_col(["SEGURO"])
            c_tramite = buscar_col(["N TRAMITE", "TRAMITE"])
            c_mes = buscar_col(["MES Y AÑO", "MES"])
            c_estado_tramite = buscar_col(["ESTADO DEL TRAMITE", "ESTADO TRAMITE", "ESTADO"])
            st.write(f"Columna Estado Trámite encontrada: {c_estado_tramite}")
            df2 = pd.DataFrame()
            df2["paciente"] = df_imp[c_paciente] if c_paciente else ""
            df2["medico"] = df_imp[c_medico] if c_medico else ""
            df2["fecha"] = df_imp[c_fecha] if c_fecha else ""
            df2["codigo"] = df_imp[c_codigo] if c_codigo else ""
            df2["descripcion"] = df_imp[c_desc] if c_desc else ""
            df2["valor"] = pd.to_numeric(df_imp[c_valor], errors="coerce").fillna(0) if c_valor else 0
            df2["seguro"] = df_imp[c_seguro] if c_seguro else ""
            df2["tramite"] = df_imp[c_tramite] if c_tramite else ""
            df2["mes_anio"] = df_imp[c_mes] if c_mes else ""
            df2 = df2[df2["paciente"].astype(str).str.strip() != ""]
            df2 = df2[~df2["paciente"].astype(str).str.contains("Suma|Total|Etiquetas", na=False)]
            df2["medico"] = df2["medico"].fillna("").astype(str).str.strip()
            df2.loc[df2["medico"] == "", "medico"] = "SIN ASIGNAR"
            if c_estado_tramite:
                df2["estado_tramite"] = df_imp[c_estado_tramite].fillna("Pendiente").astype(str).str.strip()
            else:
                df2["estado_tramite"] = "Pendiente"
            df2["estado"] = df2["estado_tramite"]
            df2["estado_pago"] = "Pendiente"
            df2["valor_40"] = (df2["valor"] * 0.40).round(2)
            df2["valor_50"] = (df2["valor"] * 0.50).round(2)
            df2["valor_60"] = (df2["valor"] * 0.60).round(2)
            df2["valor_pagado"] = 0
            df2["es_paquete"] = 0
            st.write("Ejemplo de estados que vienen en tu archivo:")
            st.dataframe(df2[["paciente", "estado_tramite", "estado_pago"]].head(10))
            if len(df_existente) > 0:
                claves_exist = set(zip(df_existente["paciente"].astype(str), df_existente["tramite"].astype(str), df_existente["codigo"].astype(str), df_existente["valor"].astype(str)))
                df2["clave"] = list(zip(df2["paciente"].astype(str), df2["tramite"].astype(str), df2["codigo"].astype(str), df2["valor"].astype(str)))
                antes = len(df2)
                df2 = df2[~df2["clave"].isin(claves_exist)]
                df2 = df2.drop(columns=["clave"])
                duplicados = antes - len(df2)
            else:
                duplicados = 0
            st.success(f"Este archivo trae: {len(df2)} filas NUEVAS. Duplicados: {duplicados}")
            st.dataframe(df2.head(20))
            if st.button("💾 SUMAR y alimentar la página"):
                df2.to_sql("honorarios", conn, if_exists="append", index=False)
                conn.commit()
                st.success("¡Sumado!")
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

if menu == "Sin Médico Asignado":
    st.subheader("✏️ Pacientes SIN Médico Asignado")
    df_sin = arreglar_df(pd.read_sql("SELECT * FROM honorarios WHERE medico='SIN ASIGNAR' OR medico='' OR medico IS NULL", conn))
    df_med_all = pd.read_sql("SELECT * FROM medicos", conn)
    df_hon_all = pd.read_sql("SELECT medico FROM honorarios", conn)
    lista_medicos = sorted(set(df_med_all["nombre"].dropna().astype(str).tolist() + df_hon_all["medico"].dropna().astype(str).tolist()) - set(["", "SIN ASIGNAR", "nan"]))
    if len(lista_medicos) == 0:
        lista_medicos = MEDICOS_DEFAULT
    c1, c2 = st.columns(2)
    c1.metric("Líneas sin médico", len(df_sin))
    c2.metric("Total sin asignar", f"${df_sin['valor'].sum():,.2f}" if len(df_sin) > 0 else "$0.00")
    if len(df_sin) == 0:
        st.success("🎉 Todo tiene médico asignado.")
    else:
        busqueda = st.text_input("🔍 Buscar por paciente, código, trámite")
        df_filtrado = df_sin.copy()
        if busqueda:
            df_filtrado = df_sin[df_sin.apply(lambda r: busqueda.lower() in str(r["paciente"]).lower() or busqueda.lower() in str(r["codigo"]).lower() or busqueda.lower() in str(r["tramite"]).lower(), axis=1)]
        df_filtrado["seleccionar"] = False
        cols_sin = [c for c in ["seleccionar", "id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "mes_anio", "estado_tramite", "estado_pago"] if c in df_filtrado.columns]
        df_edit = st.data_editor(df_filtrado[cols_sin], use_container_width=True, hide_index=True, key="editor_sin_medico")
        medico_elegido = st.selectbox("¿A qué médico le asignas los seleccionados?", lista_medicos)
        ids_sel = sacar_seleccionados(df_edit)
        if st.button(f"✅ Asignar {len(ids_sel)} líneas a {medico_elegido}"):
            if len(ids_sel) == 0:
                st.warning("Marca primero con el cuadrito")
            else:
                for i in ids_sel:
                    conn.execute("UPDATE honorarios SET medico=? WHERE id=?", (medico_elegido, int(i)))
                conn.commit()
                st.success(f"Se asignaron {len(ids_sel)} líneas a {medico_elegido}")
                st.rerun()

if menu == "Médicos":
    st.subheader("👨‍⚕️ Médicos Registrados")
    df_medicos = pd.read_sql("SELECT * FROM medicos", conn)
    df_hon = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    medicos_con_carga = [m for m in df_hon["medico"].dropna().astype(str).str.strip().unique() if m not in ["", "SIN ASIGNAR", "nan"]] if len(df_hon) > 0 else []
    c1, c2 = st.columns(2)
    c1.metric("Médicos agregados a mano", len(df_medicos))
    c2.metric("Médicos con honorarios cargados", len(medicos_con_carga))
    st.dataframe(df_medicos, use_container_width=True)
    if len(medicos_con_carga) > 0:
        resumen = []
        for m in sorted(medicos_con_carga):
            d = df_hon[df_hon["medico"] == m]
            resumen.append({"Médico": m, "N° Trámites": len(d), "Total General": round(d["valor"].sum(), 2), "Total 60%": round(d["valor_60"].sum(), 2), "Pagado al Médico": round(d[d["estado_pago"] == "Pagado"]["valor_60"].sum(), 2)})
        st.dataframe(pd.DataFrame(resumen), use_container_width=True)
    st.write("#### Agregar nuevo médico")
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
    buf = crear_excel_bien({"Medicos": df_medicos})
    st.download_button("📥 Descargar Médicos en Excel", data=buf, file_name="medicos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- NUEVA PESTAÑA: ACTUALIZAR ESTADOS - BIEN VISIBLE ---
if menu == "Actualizar Estados":
    st.subheader("🔄 Actualizar Estados - Aquí cambias los 2 estados")
    st.info("Aquí NO cargas archivo. Aquí editas lo que ya está cargado.\n\n🔵 **Estado del Trámite** = Pendiente, Pagado, Liquidado, En Trámite, Observado\n🟢 **Estado del Pago al Médico** = Pendiente, Pagado")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df_all) == 0:
        st.info("Aún no hay datos. Ve primero a Importar Archivos.")
    else:
        # Filtros para encontrar rápido
        col1, col2, col3 = st.columns(3)
        lista_med = ["Todos"] + sorted([m for m in df_all["medico"].dropna().astype(str).unique() if m not in ["", "nan"]])
        f_medico = col1.selectbox("Filtrar por Médico", lista_med)
        estados_t = ["Todos"] + sorted(df_all["estado_tramite"].unique().tolist())
        f_tramite = col2.selectbox("Filtrar por Estado del TRÁMITE", estados_t)
        f_pago = col3.selectbox("Filtrar por Estado del PAGO AL MÉDICO", ["Todos", "Pendiente", "Pagado"])
        df_f = df_all.copy()
        if f_medico != "Todos":
            df_f = df_f[df_f["medico"] == f_medico]
        if f_tramite != "Todos":
            df_f = df_f[df_f["estado_tramite"] == f_tramite]
        if f_pago != "Todos":
            df_f = df_f[df_f["estado_pago"] == f_pago]
        buscar = st.text_input("🔍 Buscar por paciente, código o trámite")
        if buscar:
            df_f = df_f[df_f.apply(lambda r: buscar.lower() in str(r["paciente"]).lower() or buscar.lower() in str(r["codigo"]).lower() or buscar.lower() in str(r["tramite"]).lower(), axis=1)]
        st.write(f"Mostrando {len(df_f)} trámites. Edita los estados directo en la tabla y luego dale GUARDAR.")
        # Resumen rápido
        c1, c2 = st.columns(2)
        c1.write("**Por Estado Trámite:**")
        c1.dataframe(df_f.groupby("estado_tramite")["valor_60"].agg(["count", "sum"]).reset_index(), use_container_width=True)
        c2.write("**Por Pago al Médico:**")
        c2.dataframe(df_f.groupby("estado_pago")["valor_60"].agg(["count", "sum"]).reset_index(), use_container_width=True)
        st.divider()
        st.write("#### ✏️ FORMA 1: Edita directo en la tabla")
        st.write("Haz clic en la columna Estado Trámite o Estado Pago y elige el nuevo. Luego dale GUARDAR CAMBIOS.")
        df_editable = df_f[["id", "medico", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "tramite", "estado_tramite", "estado_pago"]].copy()
        # Listas para los desplegables
        lista_estados_tramite = ["Pendiente", "Pagado", "Liquidado", "En Trámite", "Observado", "Rechazado"]
        lista_estados_pago = ["Pendiente", "Pagado"]
        df_editado = st.data_editor(
            df_editable,
            use_container_width=True,
            hide_index=True,
            key="editor_estados",
            column_config={
                "estado_tramite": st.column_config.SelectboxColumn("Estado del Trámite", options=lista_estados_tramite, required=True),
                "estado_pago": st.column_config.SelectboxColumn("Estado Pago al Médico", options=lista_estados_pago, required=True),
            },
            disabled=["id", "medico", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "tramite"]
        )
        if st.button("💾 GUARDAR CAMBIOS DE ESTADOS", type="primary"):
            cambios = 0
            for _, row in df_editado.iterrows():
                # Buscamos el original para ver si cambió
                orig = df_f[df_f["id"] == row["id"]]
                if len(orig) > 0:
                    o_tram = orig.iloc[0]["estado_tramite"]
                    o_pago = orig.iloc[0]["estado_pago"]
                    if row["estado_tramite"] != o_tram or row["estado_pago"] != o_pago:
                        conn.execute("UPDATE honorarios SET estado_tramite=?, estado_pago=?, estado=? WHERE id=?", (row["estado_tramite"], row["estado_pago"], row["estado_tramite"], int(row["id"])))
                        cambios += 1
            conn.commit()
            st.success(f"✅ Se guardaron {cambios} cambios de estados.")
            st.rerun()
        st.divider()
        st.write("#### ⚡ FORMA 2: Cambiar muchos a la vez - Masivo")
        st.write("Selecciona varios y cámbiales el estado a todos juntos.")
        df_f["seleccionar"] = False
        cols_masivo = [c for c in ["seleccionar", "id", "medico", "paciente", "codigo", "tramite", "valor_60", "estado_tramite", "estado_pago"] if c in df_f.columns]
        df_masivo = st.data_editor(df_f[cols_masivo], use_container_width=True, hide_index=True, key="editor_masivo")
        ids_masivo = sacar_seleccionados(df_masivo)
        col_a, col_b = st.columns(2)
        nuevo_tramite = col_a.selectbox("Nuevo Estado del TRÁMITE para los seleccionados", ["-- No cambiar --"] + lista_estados_tramite)
        nuevo_pago = col_b.selectbox("Nuevo Estado del PAGO AL MÉDICO para los seleccionados", ["-- No cambiar --"] + lista_estados_pago)
        if st.button(f"✅ Aplicar a {len(ids_masivo)} seleccionados"):
            if len(ids_masivo) == 0:
                st.warning("Marca primero con el cuadrito cuáles quieres cambiar")
            elif nuevo_tramite == "-- No cambiar --" and nuevo_pago == "-- No cambiar --":
                st.warning("Elige al menos un nuevo estado arriba")
            else:
                for i in ids_masivo:
                    if nuevo_tramite != "-- No cambiar --":
                        conn.execute("UPDATE honorarios SET estado_tramite=?, estado=? WHERE id=?", (nuevo_tramite, nuevo_tramite, int(i)))
                    if nuevo_pago != "-- No cambiar --":
                        conn.execute("UPDATE honorarios SET estado_pago=? WHERE id=?", (nuevo_pago, int(i)))
                conn.commit()
                st.success(f"Se actualizaron {len(ids_masivo)} trámites: Trámite={nuevo_tramite}, Pago al Médico={nuevo_pago}")
                st.rerun()