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
    # ESTADO TRAMITE separado de ESTADO PAGO
    if "estado_tramite" not in df.columns:
        # Si viene del archivo viejo, usamos la columna estado si existe
        if "estado" in df.columns:
            df["estado_tramite"] = df["estado"].fillna("Pendiente")
        else:
            df["estado_tramite"] = "Pendiente"
    df["estado_tramite"] = df["estado_tramite"].fillna("Pendiente").astype(str).str.strip()
    df.loc[(df["estado_tramite"] == "") | (df["estado_tramite"] == "nan"), "estado_tramite"] = "Pendiente"
    df.loc[(df["estado_pago"] == "") | (df["estado_pago"] == "nan"), "estado_pago"] = "Pendiente"
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
menu = st.sidebar.selectbox("Menú", ["Dashboard", "Buscador", "Importar Archivos", "Sin Médico Asignado", "Médicos"])

if menu == "Dashboard":
    st.subheader("Dashboard - Todo se paga al 60%")
    df = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    if len(df) == 0:
        st.info("Aún no hay datos. Ve a Importar Archivos y carga tu Excel.")
    else:
        total_general = df["valor"].sum()
        total_60 = df["valor_60"].sum()
        # PAGO AL MEDICO es lo que tú marcaste, no el estado del trámite
        pagado_60 = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
        pendiente_60 = total_60 - pagado_60
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total General Cargado", f"${total_general:,.2f}")
        c2.metric("Total a Pagar (60%)", f"${total_60:,.2f}")
        c3.metric("Pagado AL MEDICO (60%)", f"${pagado_60:,.2f}")
        c4.metric("Pendiente AL MEDICO (60%)", f"${pendiente_60:,.2f}")
        st.write("**Resumen por Estado del Trámite (lo que dice el archivo):**")
        st.dataframe(df.groupby("estado_tramite")["valor_60"].agg(["count", "sum"]).reset_index().rename(columns={"estado_tramite": "Estado Trámite", "count": "N° Trámites", "sum": "Total 60%"}), use_container_width=True)
        st.dataframe(df, use_container_width=True)
        buf = crear_excel_bien({"Honorarios": df})
        st.download_button("📥 Descargar en Excel bien", data=buf, file_name="honorarios.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- BUSCADOR CON 2 ESTADOS SEPARADOS ---
if menu == "Buscador":
    st.subheader("Buscador por Médico - 2 estados separados")
    st.info("🔵 **Estado Trámite** = lo que dice tu archivo (Pendiente, Pagado, Liquidado...).  🟢 **Estado Pago al Médico** = si TÚ ya le pagaste su 60% (Pendiente / Pagado). Son diferentes.")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    lista = sorted([m for m in df_all["medico"].dropna().astype(str).str.strip().unique() if m not in ["", "SIN ASIGNAR", "nan"]]) if len(df_all) > 0 else []
    if len(lista) == 0:
        st.info("Aún no hay médicos cargados. Ve a Importar Archivos.")
        st.dataframe(df_all, use_container_width=True)
    else:
        medico_sel = st.selectbox("Selecciona el médico", ["-- Elige un médico --"] + lista)
        buscar_texto = st.text_input("O escribe parte del nombre para filtrar (opcional)")
        if buscar_texto:
            lista_filtrada = [m for m in lista if buscar_texto.lower() in m.lower()]
            if len(lista_filtrada) > 0:
                medico_sel = st.selectbox("Médicos encontrados", lista_filtrada, key="filtro_medico")
        if medico_sel and medico_sel != "-- Elige un médico --":
            df_base = df_all[df_all["medico"] == medico_sel].copy()
            # --- FILTROS POR LOS 2 ESTADOS ---
            st.write("### 🔍 Filtros")
            col_f1, col_f2 = st.columns(2)
            estados_tramite = ["Todos"] + sorted(df_base["estado_tramite"].unique().tolist())
            filtro_tramite = col_f1.selectbox("Filtrar por Estado del TRÁMITE", estados_tramite)
            filtro_pago = col_f2.selectbox("Filtrar por Estado del PAGO AL MÉDICO", ["Todos", "Pendiente", "Pagado"])
            df = df_base.copy()
            if filtro_tramite != "Todos":
                df = df[df["estado_tramite"] == filtro_tramite]
            if filtro_pago != "Todos":
                df = df[df["estado_pago"] == filtro_pago]
            st.write(f"Mostrando: {len(df)} de {len(df_base)} trámites de {medico_sel} con esos filtros")
            if len(df) == 0:
                st.warning(f"No hay trámites de {medico_sel} con Estado Trámite={filtro_tramite} y Pago al Médico={filtro_pago}")
            else:
                total_general = df["valor"].sum()
                total_60 = df["valor_60"].sum()
                total_pagado_medico = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
                total_pendiente_medico = total_60 - total_pagado_medico
                st.write(f"### 👨‍⚕️ Médico: {medico_sel} | Filtro Trámite: {filtro_tramite} | Filtro Pago: {filtro_pago}")
                c1, c2 = st.columns(2)
                c1.metric("Total General (filtrado)", f"${total_general:,.2f}")
                c2.metric("Total a Pagar 60% (filtrado)", f"${total_60:,.2f}")
                c3, c4, c5 = st.columns(3)
                c3.metric("Pagado AL MEDICO", f"${total_pagado_medico:,.2f}")
                c4.metric("Pendiente AL MEDICO", f"${total_pendiente_medico:,.2f}")
                c5.metric("N° Trámites (filtrado)", len(df))
                st.write("**Desglose por Estado del Trámite:**")
                st.dataframe(df.groupby("estado_tramite")["valor_60"].agg(["count", "sum"]).reset_index().rename(columns={"estado_tramite": "Estado Trámite", "count": "N°", "sum": "Total 60%"}), use_container_width=True)
                porc = (total_pagado_medico / total_60 * 100) if total_60 > 0 else 0
                st.progress(porc / 100)
                st.write(f"Pago al Médico: {porc:.1f}% pagado - Falta {100-porc:.1f}%")
                if total_pagado_medico == 0:
                    estado_txt = "NO PAGADO AL MEDICO"
                    st.error("🔴 Pago al Médico: NO PAGADO")
                elif total_pendiente_medico == 0:
                    estado_txt = "PAGADO TOTAL AL MEDICO"
                    st.success("🟢 Pago al Médico: PAGADO TOTAL")
                else:
                    estado_txt = "PAGO PARCIAL AL MEDICO"
                    st.warning(f"🟡 Pago al Médico: PARCIAL - Ya le pagaste ${total_pagado_medico:,.2f} de ${total_60:,.2f}")
                st.divider()
                st.write(f"#### 📋 Todos los cargos de {medico_sel} - con los 2 estados")
                cols_mostrar = [c for c in ["id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "mes_anio", "estado_tramite", "estado_pago"] if c in df.columns]
                st.dataframe(df[cols_mostrar], use_container_width=True)
                st.divider()
                st.write("#### ✅ Marcar PAGO AL MÉDICO (esto NO cambia el Estado del Trámite)")
                st.write("Marca los que ya le pagaste al médico. El Estado del Trámite queda igual como vino en el archivo.")
                df["seleccionar"] = False
                cols_edit = [c for c in ["seleccionar", "id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "estado_tramite", "estado_pago"] if c in df.columns]
                df_edit = st.data_editor(df[cols_edit], use_container_width=True, hide_index=True, key="editor_pagos")
                ids_sel = sacar_seleccionados(df_edit)
                col1, col2 = st.columns(2)
                if col1.button(f"✅ Marcar {len(ids_sel)} como PAGADO AL MEDICO"):
                    for i in ids_sel:
                        conn.execute("UPDATE honorarios SET estado_pago='Pagado' WHERE id=?", (int(i),))
                    conn.commit()
                    st.success(f"Se marcaron {len(ids_sel)} como Pagado AL MEDICO. El Estado del Trámite no se tocó.")
                    st.rerun()
                if col2.button(f"↩️ Volver {len(ids_sel)} a PENDIENTE AL MEDICO"):
                    for i in ids_sel:
                        conn.execute("UPDATE honorarios SET estado_pago='Pendiente' WHERE id=?", (int(i),))
                    conn.commit()
                    st.success(f"Se volvieron {len(ids_sel)} a Pendiente AL MEDICO.")
                    st.rerun()
                st.divider()
                st.write(f"#### 📥 Descargar resumen de {medico_sel} con los 2 estados")
                resumen = pd.DataFrame([{
                    "Medico": medico_sel,
                    "Filtro Estado Tramite": filtro_tramite,
                    "Filtro Pago al Medico": filtro_pago,
                    "Total General": round(total_general, 2),
                    "Total a Pagar 60%": round(total_60, 2),
                    "Pagado al Medico": round(total_pagado_medico, 2),
                    "Pendiente al Medico": round(total_pendiente_medico, 2),
                    "N Tramites": len(df),
                    "Estado Pago al Medico": estado_txt
                }])
                buf = crear_excel_bien({"Resumen": resumen, "Detalle": df[cols_mostrar]})
                st.download_button(f"📥 Descargar resumen de {medico_sel} en Excel", data=buf, file_name=f"Resumen_{medico_sel.replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if menu == "Importar Archivos":
    st.subheader("📂 Importar Archivos - Se va alimentando, NO borra lo anterior")
    st.info("Ahora la app lee la columna de ESTADO del Trámite de tu Excel: Pagado, Pendiente, Liquidado, etc. Y deja el Pago al Médico en Pendiente hasta que tú lo marques.")
    df_existente = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    st.info(f"Ya tienes guardados: {len(df_existente)} registros - Total acumulado: ${df_existente['valor'].sum():,.2f}")
    archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"])
    if archivo is not None:
        try:
            xls = pd.ExcelFile(archivo)
            hoja = "FORMATO FINAL  " if "FORMATO FINAL  " in xls.sheet_names else xls.sheet_names[0]
            df_imp = pd.read_excel(archivo, sheet_name=hoja)
            df_imp.columns = [str(c).strip().upper() for c in df_imp.columns]
            st.write("Hoja leída:", hoja)
            st.write("Columnas que encontró en tu archivo:", list(df_imp.columns))
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
            # ESTO ES LO NUEVO: Busca la columna de Estado del Trámite
            c_estado_tramite = buscar_col(["ESTADO DEL TRAMITE", "ESTADO TRAMITE", "ESTADO"])
            c_estado_pago = buscar_col(["ESTADO DE PAGO", "ESTADO PAGO"])
            st.write(f"Columna Estado Trámite encontrada: {c_estado_tramite} | Columna Estado Pago encontrada: {c_estado_pago}")
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
            # ESTADO TRAMITE viene del archivo tal cual: Pagado, Liquidado, Pendiente, etc.
            if c_estado_tramite:
                df2["estado_tramite"] = df_imp[c_estado_tramite].fillna("Pendiente").astype(str).str.strip()
                df2.loc[df2["estado_tramite"] == "", "estado_tramite"] = "Pendiente"
            else:
                df2["estado_tramite"] = "Pendiente"
            df2["estado"] = df2["estado_tramite"]
            # PAGO AL MEDICO siempre empieza en Pendiente, hasta que tú lo marques
            if c_estado_pago:
                # Si tu archivo ya trae pago al médico, lo respeta
                df2["estado_pago"] = df_imp[c_estado_pago].fillna("Pendiente").astype(str).str.strip()
            else:
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
            st.success(f"Este archivo trae: {len(df2)} filas NUEVAS. Duplicados que ya estaban: {duplicados}")
            st.dataframe(df2.head(20))
            if st.button("💾 SUMAR y alimentar la página - NO borra lo anterior"):
                df2.to_sql("honorarios", conn, if_exists="append", index=False)
                conn.commit()
                total_nuevo = pd.read_sql("SELECT * FROM honorarios", conn)
                st.success(f"¡Sumado! Ahora tienes {len(total_nuevo)} registros.")
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

if menu == "Sin Médico Asignado":
    st.subheader("✏️ Pacientes / Líneas SIN Médico Asignado")
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
        st.success("🎉 No hay nada pendiente. Todo tiene médico asignado.")
    else:
        busqueda = st.text_input("🔍 Buscar por paciente, código, trámite o descripción")
        df_filtrado = df_sin.copy()
        if busqueda:
            df_filtrado = df_sin[df_sin.apply(lambda r: busqueda.lower() in str(r["paciente"]).lower() or busqueda.lower() in str(r["codigo"]).lower() or busqueda.lower() in str(r["tramite"]).lower() or busqueda.lower() in str(r["descripcion"]).lower(), axis=1)]
            st.write(f"Encontrados: {len(df_filtrado)}")
        st.write("#### ⚡ Selecciona varias y asígnalas a un médico")
        df_filtrado["seleccionar"] = False
        cols_sin = [c for c in ["seleccionar", "id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "mes_anio", "estado_tramite", "estado_pago"] if c in df_filtrado.columns]
        df_edit = st.data_editor(df_filtrado[cols_sin], use_container_width=True, hide_index=True, key="editor_sin_medico")
        medico_elegido = st.selectbox("¿A qué médico le asignas los seleccionados?", lista_medicos)
        ids_sel = sacar_seleccionados(df_edit)
        if st.button(f"✅ Asignar {len(ids_sel)} líneas a {medico_elegido}"):
            if len(ids_sel) == 0:
                st.warning("Marca primero con el cuadrito cuáles quieres asignar")
            else:
                for i in ids_sel:
                    conn.execute("UPDATE honorarios SET medico=? WHERE id=?", (medico_elegido, int(i)))
                conn.commit()
                st.success(f"Listo. Se asignaron {len(ids_sel)} líneas a {medico_elegido}")
                st.rerun()

if menu == "Médicos":
    st.subheader("👨‍⚕️ Médicos Registrados")
    df_medicos = pd.read_sql("SELECT * FROM medicos", conn)
    df_hon = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    medicos_con_carga = [m for m in df_hon["medico"].dropna().astype(str).str.strip().unique() if m not in ["", "SIN ASIGNAR", "nan"]] if len(df_hon) > 0 else []
    c1, c2 = st.columns(2)
    c1.metric("Médicos agregados a mano", len(df_medicos))
    c2.metric("Médicos con honorarios cargados", len(medicos_con_carga))
    st.divider()
    st.write("#### Lista de médicos agregados")
    st.dataframe(df_medicos, use_container_width=True)
    st.write("#### Lista de médicos que ya tienen honorarios cargados")
    if len(medicos_con_carga) > 0:
        resumen = []
        for m in sorted(medicos_con_carga):
            d = df_hon[df_hon["medico"] == m]
            resumen.append({"Médico": m, "N° Trámites": len(d), "Total General": round(d["valor"].sum(), 2), "Total a Pagar 60%": round(d["valor_60"].sum(), 2), "Pagado al Médico": round(d[d["estado_pago"] == "Pagado"]["valor_60"].sum(), 2)})
        st.dataframe(pd.DataFrame(resumen), use_container_width=True)
    else:
        st.info("Aún no hay médicos con honorarios cargados")
    st.divider()
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