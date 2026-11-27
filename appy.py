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
for col, tipo in [("estado_pago","TEXT DEFAULT 'Pendiente'"), ("valor_pagado","REAL DEFAULT 0"), ("es_paquete","INTEGER DEFAULT 0"), ("valor_40","REAL DEFAULT 0"), ("valor_50","REAL DEFAULT 0"), ("valor_60","REAL DEFAULT 0")]:
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
    if "valor" not in df.columns:
        df["valor"] = 0
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    if "valor_60" not in df.columns or df["valor_60"].isna().all():
        df["valor_60"] = (df["valor"] * 0.60).round(2)
    if "valor_40" not in df.columns:
        df["valor_40"] = (df["valor"] * 0.40).round(2)
    if "valor_50" not in df.columns:
        df["valor_50"] = (df["valor"] * 0.50).round(2)
    if "estado_pago" not in df.columns:
        df["estado_pago"] = "Pendiente"
    df["estado_pago"] = df["estado_pago"].fillna("Pendiente")
    df.loc[(df["valor_60"] == 0) & (df["valor"] != 0), "valor_60"] = (df["valor"] * 0.60).round(2)
    try:
        conn.execute("UPDATE honorarios SET valor_60 = valor * 0.60 WHERE valor_60 IS NULL OR valor_60 = 0")
        conn.commit()
    except:
        pass
    return df

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
        pagado_60 = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
        pendiente_60 = total_60 - pagado_60
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total General Cargado", f"${total_general:,.2f}")
        c2.metric("Total a Pagar (60%)", f"${total_60:,.2f}")
        c3.metric("Total Pagado (del 60%)", f"${pagado_60:,.2f}")
        c4.metric("Total Pendiente (del 60%)", f"${pendiente_60:,.2f}")
        st.dataframe(df, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Honorarios")
        buffer.seek(0)
        st.download_button("📥 Descargar en Excel bien", data=buffer, file_name="honorarios.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- BUSCADOR: SELECCIONAR MEDICO Y DESCARGAR RESUMEN ---
if menu == "Buscador":
    st.subheader("Buscador por Médico - Selecciona y descarga su resumen")
    df_all = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    # Lista de médicos para seleccionar, no hay que escribir
    lista = sorted([m for m in df_all["medico"].dropna().astype(str).str.strip().unique() if m not in ["", "SIN ASIGNAR", "nan"]]) if len(df_all) > 0 else []
    if len(lista) == 0:
        st.info("Aún no hay médicos cargados. Ve a Importar Archivos.")
        st.dataframe(df_all, use_container_width=True)
    else:
        st.write("1️⃣ Selecciona el médico de la lista:")
        medico_sel = st.selectbox("Selecciona el médico", ["-- Elige un médico --"] + lista)
        # También puedes escribir si quieres buscar rápido
        buscar_texto = st.text_input("O escribe parte del nombre para filtrar (opcional)")
        if buscar_texto:
            lista_filtrada = [m for m in lista if buscar_texto.lower() in m.lower()]
            if len(lista_filtrada) > 0:
                medico_sel = st.selectbox("Médicos encontrados", lista_filtrada, key="filtro_medico")
        if medico_sel and medico_sel != "-- Elige un médico --":
            df = df_all[df_all["medico"] == medico_sel].copy()
            if len(df) == 0:
                st.warning("No se encontró ese médico")
            else:
                total_general = df["valor"].sum()
                total_60 = df["valor_60"].sum()
                total_pagado = df[df["estado_pago"] == "Pagado"]["valor_60"].sum()
                total_pendiente = total_60 - total_pagado
                n_pagados = len(df[df["estado_pago"] == "Pagado"])
                n_pendientes = len(df) - n_pagados
                st.write(f"### 👨‍⚕️ Médico seleccionado: {medico_sel}")
                c1, c2 = st.columns(2)
                c1.metric("Total General Cargado", f"${total_general:,.2f}")
                c2.metric("Total a Pagar - Solo 60%", f"${total_60:,.2f}")
                c3, c4, c5 = st.columns(3)
                c3.metric("Total Pagado (del 60%)", f"${total_pagado:,.2f}")
                c4.metric("Total Pendiente (del 60%)", f"${total_pendiente:,.2f}")
                c5.metric("N° Trámites", len(df))
                st.info(f"Al médico se le paga solo el 60%: de ${total_general:,.2f} cargados, se le deben pagar ${total_60:,.2f} | Pagados: {n_pagados} trámites | Pendientes: {n_pendientes} trámites")
                porc = (total_pagado / total_60 * 100) if total_60 > 0 else 0
                st.progress(porc / 100)
                st.write(f"Progreso del 60%: {porc:.1f}% pagado - Falta {100-porc:.1f}%")
                if total_pagado == 0:
                    estado_txt = "NO PAGADO"
                    st.error("🔴 Estado: NO PAGADO")
                elif total_pendiente == 0:
                    estado_txt = "PAGADO TOTAL"
                    st.success("🟢 Estado: PAGADO TOTAL")
                else:
                    estado_txt = "PAGO PARCIAL"
                    st.warning(f"🟡 Estado: PAGO PARCIAL - Ya se le pagó ${total_pagado:,.2f} de ${total_60:,.2f}")
                st.divider()
                st.write(f"#### 📋 Todos los cargos de {medico_sel} - Despliega todo")
                st.write("Aquí están todos los gastos / cargos que tiene este médico:")
                cols_mostrar = [c for c in ["id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "mes_anio", "estado_pago"] if c in df.columns]
                st.dataframe(df[cols_mostrar], use_container_width=True)
                st.divider()
                st.write("#### ✅ Marcar qué se le ha pagado al médico")
                df["seleccionar"] = False
                cols_edit = [c for c in ["seleccionar", "id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "estado_pago"] if c in df.columns]
                df_edit = st.data_editor(df[cols_edit], use_container_width=True, hide_index=True, key="editor_pagos")
                col1, col2 = st.columns(2)
                ids_sel = df_edit[df_edit["seleccionar"] == True]["id"].tolist() if "seleccionar" in df_edit.columns else []
                if col1.button(f"✅ Marcar {len(ids_sel)} como PAGADO"):
                    for i in ids_sel:
                        conn.execute("UPDATE honorarios SET estado_pago='Pagado', estado_tramite='Pagado' WHERE id=?", (int(i),))
                    conn.commit()
                    st.success(f"Se marcaron {len(ids_sel)} trámites como Pagado")
                    st.rerun()
                if col2.button(f"↩️ Volver {len(ids_sel)} a PENDIENTE"):
                    for i in ids_sel:
                        conn.execute("UPDATE honorarios SET estado_pago='Pendiente', estado_tramite='Pendiente' WHERE id=?", (int(i),))
                    conn.commit()
                    st.success(f"Se volvieron {len(ids_sel)} trámites a Pendiente")
                    st.rerun()
                st.divider()
                # --- DESCARGAR RESUMEN POR MEDICO ---
                st.write(f"#### 📥 Descargar resumen completo de {medico_sel}")
                st.write("El Excel trae 2 hojas: Resumen + Detalle con todos sus gastos.")
                if st.button(f"📥 Generar Excel de {medico_sel}"):
                    buffer = io.BytesIO()
                    resumen = pd.DataFrame([{
                        "Médico": medico_sel,
                        "Total General Cargado": round(total_general, 2),
                        "Total a Pagar 60%": round(total_60, 2),
                        "Total Pagado del 60%": round(total_pagado, 2),
                        "Total Pendiente del 60%": round(total_pendiente, 2),
                        "N° Trámites Total": len(df),
                        "N° Trámites Pagados": n_pagados,
                        "N° Trámites Pendientes": n_pendientes,
                        "Porcentaje Pagado": f"{porc:.1f}%",
                        "Estado del Pago": estado_txt
                    }])
                    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                        resumen.to_excel(writer, index=False, sheet_name="Resumen")
                        df[cols_mostrar].to_excel(writer, index=False, sheet_name="Detalle")
                    buffer.seek(0)
                    st.download_button(
                        f"📥 Descargar resumen de {medico_sel} en Excel",
                        data=buffer,
                        file_name=f"Resumen_{medico_sel.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success(f"Listo. Descarga el resumen de {medico_sel}")

if menu == "Importar Archivos":
    st.subheader("📂 Importar Archivos - Se va alimentando, NO borra lo anterior")
    df_existente = arreglar_df(pd.read_sql("SELECT * FROM honorarios", conn))
    st.info(f"Ya tienes guardados: {len(df_existente)} registros - Total acumulado: ${df_existente['valor'].sum():,.2f} si ya cargaste antes")
    archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"])
    if archivo is not None:
        try:
            xls = pd.ExcelFile(archivo)
            hoja = "FORMATO FINAL  " if "FORMATO FINAL  " in xls.sheet_names else xls.sheet_names[0]
            df_imp = pd.read_excel(archivo, sheet_name=hoja)
            df_imp.columns = [str(c).strip().upper() for c in df_imp.columns]
            st.write("Hoja leída:", hoja)
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
            df2["valor_40"] = (df2["valor"] * 0.40).round(2)
            df2["valor_50"] = (df2["valor"] * 0.50).round(2)
            df2["valor_60"] = (df2["valor"] * 0.60).round(2)
            df2["estado"] = "Pendiente"
            df2["estado_tramite"] = "Pendiente"
            df2["estado_pago"] = "Pendiente"
            df2["valor_pagado"] = 0
            df2["es_paquete"] = 0
            if len(df_existente) > 0:
                claves_exist = set(zip(df_existente["paciente"].astype(str), df_existente["tramite"].astype(str), df_existente["codigo"].astype(str), df_existente["valor"].astype(str)))
                df2["clave"] = list(zip(df2["paciente"].astype(str), df2["tramite"].astype(str), df2["codigo"].astype(str), df2["valor"].astype(str)))
                antes = len(df2)
                df2 = df2[~df2["clave"].isin(claves_exist)]
                df2 = df2.drop(columns=["clave"])
                duplicados = antes - len(df2)
            else:
                duplicados = 0
            st.success(f"Este archivo trae: {len(df2)} filas NUEVAS para sumar. Duplicados que ya estaban: {duplicados}")
            st.dataframe(df2.head(20))
            if st.button("💾 SUMAR y alimentar la página - NO borra lo anterior"):
                df2.to_sql("honorarios", conn, if_exists="append", index=False)
                conn.commit()
                total_nuevo = pd.read_sql("SELECT * FROM honorarios", conn)
                st.success(f"¡Sumado! Antes tenías {len(df_existente)} registros, ahora tienes {len(total_nuevo)} registros. Total acumulado: ${total_nuevo['valor'].sum():,.2f}")
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

if menu == "Sin Médico Asignado":
    st.subheader("✏️ Pacientes / Líneas SIN Médico Asignado - Aquí los editas")
    df_sin = arreglar_df(pd.read_sql("SELECT * FROM honorarios WHERE medico='SIN ASIGNAR' OR medico='' OR medico IS NULL", conn))
    df_med_all = pd.read_sql("SELECT * FROM medicos", conn)
    df_hon_all = pd.read_sql("SELECT medico FROM honorarios", conn)
    lista_medicos = sorted(set(df_med_all["nombre"].dropna().astype(str).tolist() + df_hon_all["medico"].dropna().astype(str).tolist()) - set(["", "SIN ASIGNAR", "nan"]))
    if len(lista_medicos) == 0:
        lista_medicos = MEDICOS_DEFAULT
    c1, c2 = st.columns(2)
    c1.metric("Líneas sin médico", len(df_sin))
    c2.metric("Total sin asignar (valor)", f"${df_sin['valor'].sum():,.2f}" if len(df_sin) > 0 else "$0.00")
    if len(df_sin) == 0:
        st.success("🎉 No hay nada pendiente. Todo tiene médico asignado.")
    else:
        busqueda = st.text_input("🔍 Buscar por paciente, código, trámite o descripción")
        df_filtrado = df_sin.copy()
        if busqueda:
            df_filtrado = df_sin[df_sin.apply(lambda r: busqueda.lower() in str(r["paciente"]).lower() or busqueda.lower() in str(r["codigo"]).lower() or busqueda.lower() in str(r["tramite"]).lower() or busqueda.lower() in str(r["descripcion"]).lower(), axis=1)]
            st.write(f"Encontrados: {len(df_filtrado)}")
        st.write("#### ⚡ Forma rápida: Selecciona varias líneas y asígnalas a un médico")
        df_filtrado["seleccionar"] = False
        cols_sin = [c for c in ["seleccionar", "id", "paciente", "fecha", "codigo", "descripcion", "valor", "valor_60", "seguro", "tramite", "mes_anio"] if c in df_filtrado.columns]
        df_edit = st.data_editor(df_filtrado[cols_sin], use_container_width=True, hide_index=True, key="editor_sin_medico")
        medico_elegido = st.selectbox("¿A qué médico le asignas los seleccionados?", lista_medicos)
        ids_sel = df_edit[df_edit["seleccionar"] == True]["id"].tolist() if "seleccionar" in df_edit.columns else []
        if st.button(f"✅ Asignar {len(ids_sel)} líneas a {medico_elegido}"):
            if len(ids_sel) == 0:
                st.warning("Marca primero con el cuadrito cuáles quieres asignar")
            else:
                for i in ids_sel:
                    conn.execute("UPDATE honorarios SET medico=? WHERE id=?", (medico_elegido, int(i)))
                conn.commit()
                st.success(f"Listo. Se asignaron {len(ids_sel)} líneas a {medico_elegido}")
                st.rerun()
        st.divider()
        st.write("#### ✏️ Forma uno por uno: Editar por código")
        for _, fila in df_filtrado.head(30).iterrows():
            id_val = fila["id"]
            col_a, col_b, col_c = st.columns([3, 2, 1])
            col_a.write(f"**{fila['paciente']}** - Código: {fila['codigo']} - Trámite: {fila['tramite']} - Valor: ${fila['valor']:,.2f} - 60%: ${fila['valor_60']:,.2f}")
            nm = col_b.selectbox(f"Médico para {id_val}", lista_medicos, key=f"m_{id_val}", label_visibility="collapsed")
            if col_c.button("Guardar", key=f"b_{id_val}"):
                conn.execute("UPDATE honorarios SET medico=? WHERE id=?", (nm, id_val))
                conn.commit()
                st.success(f"Asignado a {nm}")
                st.rerun()

if menu == "Médicos":
    st.subheader("👨‍⚕️ Médicos Registrados - Solo para ver médicos")
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
            resumen.append({"Médico": m, "N° Trámites": len(d), "Total General": round(d["valor"].sum(), 2), "Total a Pagar 60%": round(d["valor_60"].sum(), 2)})
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
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_medicos.to_excel(writer, index=False, sheet_name="Medicos")
    buffer.seek(0)
    st.download_button("📥 Descargar Médicos en Excel", data=buffer, file_name="medicos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")