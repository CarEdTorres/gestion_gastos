import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# ========== CONFIGURACIÓN ==========
st.set_page_config(
    page_title="💰 Gestor de Gastos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== BASE DE DATOS ==========
def inicializar_db():
    """Crea las tablas necesarias"""
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        
        # Tabla de gastos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                persona TEXT NOT NULL,
                monto REAL NOT NULL
            )
        ''')
        
        # Tabla de personas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                orden INTEGER DEFAULT 0
            )
        ''')
        
        # Insertar personas por defecto
        cursor.execute("SELECT COUNT(*) FROM personas")
        if cursor.fetchone()[0] == 0:
            personas_default = ['Ana', 'Luis', 'Maria']
            for i, nombre in enumerate(personas_default):
                cursor.execute("INSERT INTO personas (nombre, orden) VALUES (?, ?)", (nombre, i))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error en base de datos: {e}")
        return False

def obtener_personas():
    """Obtiene lista de personas"""
    try:
        conn = sqlite3.connect('gastos.db')
        df = pd.read_sql_query("SELECT nombre FROM personas ORDER BY orden", conn)
        conn.close()
        return df['nombre'].tolist()
    except:
        return ['Ana', 'Luis', 'Maria']

def agregar_persona(nombre):
    """Agrega nueva persona"""
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
    """Elimina persona y sus gastos"""
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
    """Edita nombre de persona"""
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

def guardar_gasto(persona, monto):
    """Guarda un gasto"""
    try:
        conn = sqlite3.connect('gastos.db')
        cursor = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO gastos (fecha, persona, monto) VALUES (?, ?, ?)", 
                      (fecha, persona, float(monto)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

def eliminar_ultimo_gasto(persona=None):
    """Elimina el último gasto"""
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

def obtener_totales():
    """Obtiene totales por persona"""
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
    """Obtiene historial de gastos"""
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
    """Obtiene gastos agrupados por día"""
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

# ========== FUNCIONES DE INTERFAZ ==========
def mostrar_totales(df_totales):
    """Muestra tarjetas de totales"""
    if df_totales.empty:
        st.info("No hay gastos registrados aún")
        return
    
    cols = st.columns(min(len(df_totales), 4))
    for idx, row in df_totales.iterrows():
        with cols[idx % len(cols)]:
            st.metric(
                label=f"👤 {row['nombre']}",
                value=f"${row['total']:,.2f}",
                delta=None
            )

def mostrar_graficos(df_totales, df_diario):
    """Muestra gráficos interactivos"""
    tab1, tab2, tab3 = st.tabs(["📊 Barras", "🥧 Pastel", "📅 Evolución"])
    
    with tab1:
        if not df_totales.empty and df_totales['total'].sum() > 0:
            fig = px.bar(df_totales, x='nombre', y='total', 
                        title="Gastos por persona",
                        color='nombre',
                        color_discrete_sequence=px.colors.qualitative.Set2)
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

# ========== FUNCIÓN PRINCIPAL ==========
def main():
    # Inicializar DB
    if not inicializar_db():
        st.error("❌ Error al inicializar la base de datos")
        return
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        # Gestión de personas
        st.subheader("👥 Personas")
        personas = obtener_personas()
        
        # Agregar nueva persona
        with st.form(key="add_person_form"):
            nueva_persona = st.text_input("➕ Nueva persona", key="new_person_input")
            submit_add = st.form_submit_button("Agregar")
            if submit_add and nueva_persona and nueva_persona.strip():
                if agregar_persona(nueva_persona.strip()):
                    st.success(f"✅ {nueva_persona} agregada")
                    st.rerun()
                else:
                    st.error("❌ Ya existe o nombre inválido")
        
        # Editar/Eliminar personas
        if personas and len(personas) > 0:
            st.divider()
            st.write("✏️ Editar personas:")
            
            with st.form(key="edit_person_form"):
                persona_seleccionada = st.selectbox("Seleccionar", personas, key="edit_select")
                nuevo_nombre = st.text_input("Nuevo nombre", value=persona_seleccionada, key="edit_name_input")
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_edit = st.form_submit_button("💾 Editar")
                    if submit_edit and nuevo_nombre and nuevo_nombre != persona_seleccionada:
                        if editar_persona(persona_seleccionada, nuevo_nombre):
                            st.success("✅ Editado")
                            st.rerun()
                
                with col2:
                    submit_delete = st.form_submit_button("🗑️ Eliminar")
                    if submit_delete:
                        if len(personas) > 1:
                            if eliminar_persona(persona_seleccionada):
                                st.success("✅ Eliminado")
                                st.rerun()
                        else:
                            st.error("❌ Debe haber al menos una persona")
        
        st.divider()
        
        # Exportar datos
        st.subheader("📊 Exportar")
        df_export = obtener_historial(limite=1000)
        if not df_export.empty:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='Historial', index=False)
                obtener_totales().to_excel(writer, sheet_name='Totales', index=False)
            
            st.download_button(
                label="📥 Descargar Excel",
                data=output.getvalue(),
                file_name=f"gastos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel"
            )
        else:
            st.info("No hay datos para exportar")
    
    # ========== CONTENIDO PRINCIPAL ==========
    st.title("💰 Gestor de Gastos Compartidos")
    
    # ========== REGISTRO RÁPIDO ==========
    with st.container():
        st.subheader("📝 Registrar gasto")
        
        personas_actuales = obtener_personas()
        if not personas_actuales:
            st.warning("⚠️ Agrega al menos una persona en la barra lateral")
            return
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            with st.form(key="gasto_form"):
                persona = st.selectbox("Persona", personas_actuales, key="persona_select")
                monto = st.number_input("Monto ($)", min_value=0.01, step=10.0, format="%.2f", key="monto_input")
                submit_gasto = st.form_submit_button("💾 GUARDAR GASTO", type="primary", use_container_width=True)
                
                if submit_gasto and monto > 0:
                    if guardar_gasto(persona, monto):
                        st.success(f"✅ Gasto de ${monto:.2f} guardado para {persona}")
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar")
        
        with col2:
            st.subheader("↩️ Deshacer")
            with st.form(key="deshacer_form"):
                deshacer_tipo = st.radio("Tipo", ["Último global", "Solo esta persona"], key="deshacer_tipo")
                submit_deshacer = st.form_submit_button("🗑️ Deshacer", use_container_width=True)
                
                if submit_deshacer:
                    persona_filtro = persona if deshacer_tipo == "Solo esta persona" else None
                    if eliminar_ultimo_gasto(persona_filtro):
                        st.success("✅ Último gasto eliminado")
                        st.rerun()
                    else:
                        st.error("❌ No hay gastos para eliminar")
    
    # ========== TOTALES ==========
    st.divider()
    st.subheader("💰 Totales acumulados")
    
    df_totales = obtener_totales()
    mostrar_totales(df_totales)
    
    # ========== GRÁFICOS ==========
    st.divider()
    st.subheader("📈 Visualizaciones")
    
    df_diario = obtener_gastos_por_dia()
    mostrar_graficos(df_totales, df_diario)
    
    # ========== HISTORIAL ==========
    st.divider()
    st.subheader("📜 Historial de gastos")
    
    col_filtro1, col_filtro2 = st.columns([1, 2])
    with col_filtro1:
        filtro_persona = st.selectbox("Filtrar por persona", ["Todas"] + obtener_personas(), key="filtro_historial")
    
    with col_filtro2:
        limite = st.slider("Mostrar últimos", 5, 100, 20, key="limite_historial")
    
    # Mostrar historial
    if filtro_persona == "Todas":
        df_historial = obtener_historial(limite=limite)
    else:
        df_historial = obtener_historial(persona=filtro_persona, limite=limite)
    
    if not df_historial.empty:
        # Formatear para mostrar
        df_display = df_historial.copy()
        df_display['fecha'] = pd.to_datetime(df_display['fecha']).dt.strftime('%Y-%m-%d %H:%M')
        df_display['monto'] = df_display['monto'].apply(lambda x: f"${x:.2f}")
        df_display = df_display.rename(columns={'fecha': 'Fecha', 'persona': 'Persona', 'monto': 'Monto'})
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("📭 No hay gastos registrados aún")
    
    # ========== ESTADÍSTICAS ==========
    if filtro_persona != "Todas" and not df_historial.empty:
        st.divider()
        st.subheader(f"📊 Estadísticas de {filtro_persona}")
        
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            st.metric("Total gastado", f"${df_historial['monto'].sum():,.2f}")
        with col_e2:
            st.metric("Promedio por gasto", f"${df_historial['monto'].mean():.2f}")
        with col_e3:
            st.metric("Cantidad de gastos", len(df_historial))

if __name__ == "__main__":
    main()