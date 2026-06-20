import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# ========== CONFIGURACIÓN ==========
st.set_page_config(
    page_title="💰 Gestor de Gastos",
    page_icon="💰",
    layout="wide"
)

# ========== BASE DE DATOS ==========
def inicializar_db():
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                persona TEXT NOT NULL,
                monto REAL NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                orden INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM personas")
        if cursor.fetchone()[0] == 0:
            personas_default = ['Ana', 'Luis', 'Maria']
            for i, nombre in enumerate(personas_default):
                cursor.execute("INSERT INTO personas (nombre, orden) VALUES (?, ?)", (nombre, i))
        
        conn.commit()
        conn.close()
        return True
    except:
        return False

def obtener_personas():
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM personas ORDER BY orden")
        personas = [row[0] for row in cursor.fetchall()]
        conn.close()
        return personas
    except:
        return ['Ana', 'Luis', 'Maria']

def obtener_totales():
    try:
        conn = sqlite3.connect('gastos.db')
        query = '''
            SELECT p.nombre, COALESCE(SUM(g.monto), 0) as total
            FROM personas p
            LEFT JOIN gastos g ON p.nombre = g.persona
            GROUP BY p.nombre
            ORDER BY p.orden
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame(columns=['nombre', 'total'])

def obtener_historial(persona=None, limite=50):
    try:
        conn = sqlite3.connect('gastos.db')
        if persona:
            query = "SELECT fecha, persona, monto FROM gastos WHERE persona = ? ORDER BY fecha DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(persona, limite))
        else:
            query = "SELECT fecha, persona, monto FROM gastos ORDER BY fecha DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(limite,))
        conn.close()
        return df
    except:
        return pd.DataFrame(columns=['fecha', 'persona', 'monto'])

def obtener_gastos_por_dia():
    try:
        conn = sqlite3.connect('gastos.db')
        df = pd.read_sql_query("""
            SELECT date(fecha) as dia, persona, SUM(monto) as total
            FROM gastos
            GROUP BY date(fecha), persona
            ORDER BY dia DESC
        """, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame(columns=['dia', 'persona', 'total'])

def guardar_gasto(persona, monto):
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO gastos (fecha, persona, monto) VALUES (?, ?, ?)", 
                      (fecha, persona, float(monto)))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def eliminar_ultimo_gasto(persona=None):
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        if persona:
            cursor.execute("DELETE FROM gastos WHERE id = (SELECT id FROM gastos WHERE persona = ? ORDER BY fecha DESC LIMIT 1)", (persona,))
        else:
            cursor.execute("DELETE FROM gastos WHERE id = (SELECT id FROM gastos ORDER BY fecha DESC LIMIT 1)")
        conn.commit()
        conn.close()
        return True
    except:
        return False

def agregar_persona(nombre):
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO personas (nombre, orden) VALUES (?, (SELECT COALESCE(MAX(orden), -1) + 1 FROM personas))", (nombre,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def eliminar_persona(nombre):
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM personas WHERE nombre = ?", (nombre,))
        cursor.execute("DELETE FROM gastos WHERE persona = ?", (nombre,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def editar_persona(nombre_antiguo, nombre_nuevo):
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE personas SET nombre = ? WHERE nombre = ?", (nombre_nuevo, nombre_antiguo))
        cursor.execute("UPDATE gastos SET persona = ? WHERE persona = ?", (nombre_nuevo, nombre_antiguo))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# ========== INTERFAZ PRINCIPAL ==========
def main():
    # Inicializar DB
    if not inicializar_db():
        st.error("❌ Error al inicializar la base de datos")
        return
    
    # Verificar si hay que recargar
    if 'recargar' in st.session_state and st.session_state.recargar:
        st.session_state.recargar = False
        st.experimental_rerun()
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        # Personas
        st.subheader("👥 Personas")
        personas = obtener_personas()
        
        # Agregar persona
        with st.expander("➕ Agregar persona", expanded=False):
            nueva_persona = st.text_input("Nombre", key="new_person")
            if st.button("Agregar", key="add_person_btn"):
                if nueva_persona and nueva_persona.strip():
                    if agregar_persona(nueva_persona.strip()):
                        st.success(f"✅ {nueva_persona} agregada")
                        st.session_state.recargar = True
                        st.experimental_rerun()
                    else:
                        st.error("❌ Ya existe o nombre inválido")
        
        # Editar/Eliminar
        if personas and len(personas) > 0:
            with st.expander("✏️ Editar/Eliminar", expanded=False):
                persona_sel = st.selectbox("Seleccionar", personas, key="edit_select")
                
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_nom = st.text_input("Nuevo nombre", value=persona_sel, key="edit_name")
                    if st.button("💾 Editar", key="edit_btn"):
                        if nuevo_nom and nuevo_nom != persona_sel:
                            if editar_persona(persona_sel, nuevo_nom):
                                st.success("✅ Editado")
                                st.session_state.recargar = True
                                st.experimental_rerun()
                
                with col2:
                    if st.button("🗑️ Eliminar", key="delete_btn"):
                        if len(personas) > 1:
                            if eliminar_persona(persona_sel):
                                st.success("✅ Eliminado")
                                st.session_state.recargar = True
                                st.experimental_rerun()
                        else:
                            st.error("❌ Debe haber al menos una persona")
        
        st.divider()
        
        # Exportar
        st.subheader("📊 Exportar")
        df_exp = obtener_historial(limite=1000)
        if not df_exp.empty:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_exp.to_excel(writer, sheet_name='Historial', index=False)
                obtener_totales().to_excel(writer, sheet_name='Totales', index=False)
            
            st.download_button(
                label="📥 Descargar Excel",
                data=output.getvalue(),
                file_name=f"gastos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_btn"
            )
        else:
            st.info("No hay datos para exportar")
    
    # ========== CONTENIDO PRINCIPAL ==========
    st.title("💰 Gestor de Gastos Compartidos")
    
    # Obtener datos
    personas = obtener_personas()
    if not personas:
        st.warning("⚠️ Agrega personas en la barra lateral")
        return
    
    # ========== REGISTRO RÁPIDO ==========
    st.subheader("📝 Registrar gasto")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        persona = st.selectbox("Persona", personas, key="gasto_persona")
        monto = st.number_input("Monto ($)", min_value=0.01, step=10.0, format="%.2f", key="gasto_monto")
        
        if st.button("💾 GUARDAR GASTO", type="primary", use_container_width=True, key="guardar_btn"):
            if monto > 0:
                if guardar_gasto(persona, monto):
                    st.success(f"✅ Gasto de ${monto:.2f} guardado para {persona}")
                    st.session_state.recargar = True
                    st.experimental_rerun()
                else:
                    st.error("❌ Error al guardar")
            else:
                st.error("❌ Ingresa un monto válido")
    
    with col2:
        st.subheader("↩️ Deshacer")
        deshacer_tipo = st.radio("Tipo", ["Global", "Solo esta"], key="deshacer_tipo", horizontal=True)
        if st.button("🗑️ Deshacer último", use_container_width=True, key="deshacer_btn"):
            persona_filtro = persona if deshacer_tipo == "Solo esta" else None
            if eliminar_ultimo_gasto(persona_filtro):
                st.success("✅ Último gasto eliminado")
                st.session_state.recargar = True
                st.experimental_rerun()
            else:
                st.error("❌ No hay gastos para eliminar")
    
    # ========== TOTALES ==========
    st.divider()
    st.subheader("💰 Totales acumulados")
    
    df_totales = obtener_totales()
    if not df_totales.empty:
        cols = st.columns(min(len(df_totales), 4))
        for idx, row in df_totales.iterrows():
            with cols[idx % len(cols)]:
                st.metric(
                    label=f"👤 {row['nombre']}",
                    value=f"${row['total']:,.2f}",
                    delta=None
                )
    else:
        st.info("No hay gastos registrados")
    
    # ========== GRÁFICOS ==========
    st.divider()
    st.subheader("📈 Visualizaciones")
    
    df_diario = obtener_gastos_por_dia()
    
    tab1, tab2, tab3 = st.tabs(["📊 Barras", "🥧 Pastel", "📅 Evolución"])
    
    with tab1:
        if not df_totales.empty and df_totales['total'].sum() > 0:
            fig = px.bar(df_totales, x='nombre', y='total', 
                        title="Gastos por persona",
                        color='nombre')
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True, key="bar_chart")
        else:
            st.info("No hay datos para mostrar")
    
    with tab2:
        if not df_totales.empty and df_totales['total'].sum() > 0:
            fig = px.pie(df_totales, values='total', names='nombre',
                        title="Distribución de gastos",
                        hole=0.3)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True, key="pie_chart")
        else:
            st.info("No hay datos para mostrar")
    
    with tab3:
        if not df_diario.empty:
            fig = px.line(df_diario, x='dia', y='total', color='persona',
                         title="Evolución diaria de gastos",
                         markers=True)
            fig.update_layout(xaxis_title="Fecha", yaxis_title="Monto ($)", height=400)
            st.plotly_chart(fig, use_container_width=True, key="line_chart")
        else:
            st.info("No hay datos suficientes para la evolución")
    
    # ========== HISTORIAL ==========
    st.divider()
    st.subheader("📜 Historial de gastos")
    
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        filtro = st.selectbox("Filtrar", ["Todas"] + personas, key="filtro_historial")
    with col_f2:
        limite = st.slider("Mostrar", 5, 100, 20, key="limite_historial")
    
    if filtro == "Todas":
        df_hist = obtener_historial(limite=limite)
    else:
        df_hist = obtener_historial(persona=filtro, limite=limite)
    
    if not df_hist.empty:
        df_display = df_hist.copy()
        df_display['fecha'] = pd.to_datetime(df_display['fecha']).dt.strftime('%Y-%m-%d %H:%M')
        df_display['monto'] = df_display['monto'].apply(lambda x: f"${x:.2f}")
        df_display = df_display.rename(columns={'fecha': 'Fecha', 'persona': 'Persona', 'monto': 'Monto'})
        
        st.dataframe(df_display, use_container_width=True, hide_index=True, key="historial_df")
    else:
        st.info("📭 No hay gastos registrados")
    
    # ========== ESTADÍSTICAS ==========
    if filtro != "Todas" and not df_hist.empty:
        st.divider()
        st.subheader(f"📊 Estadísticas de {filtro}")
        
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            st.metric("Total", f"${df_hist['monto'].sum():,.2f}")
        with col_e2:
            st.metric("Promedio", f"${df_hist['monto'].mean():.2f}")
        with col_e3:
            st.metric("Cantidad", len(df_hist))

if __name__ == "__main__":
    main()