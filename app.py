import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# ========== CONFIGURACIÓN DE PÁGINA ==========
st.set_page_config(
    page_title="💰 Gestor de Gastos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== BASE DE DATOS ==========
def inicializar_db():
    """Crea las tablas necesarias"""
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

def obtener_personas():
    """Obtiene lista de personas"""
    conn = sqlite3.connect('gastos.db')
    df = pd.read_sql_query("SELECT nombre FROM personas ORDER BY orden", conn)
    conn.close()
    return df['nombre'].tolist()

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
    conn = sqlite3.connect('gastos.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM personas WHERE nombre = ?", (nombre,))
    cursor.execute("DELETE FROM gastos WHERE persona = ?", (nombre,))
    conn.commit()
    conn.close()

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
    except:
        return False

def eliminar_ultimo_gasto(persona=None):
    """Elimina el último gasto"""
    conn = sqlite3.connect('gastos.db')
    cursor = conn.cursor()
    if persona:
        cursor.execute("DELETE FROM gastos WHERE id = (SELECT id FROM gastos WHERE persona = ? ORDER BY fecha DESC LIMIT 1)", (persona,))
    else:
        cursor.execute("DELETE FROM gastos WHERE id = (SELECT id FROM gastos ORDER BY fecha DESC LIMIT 1)")
    conn.commit()
    conn.close()

def obtener_totales():
    """Obtiene totales por persona"""
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

def obtener_historial(persona=None, limite=50):
    """Obtiene historial de gastos"""
    conn = sqlite3.connect('gastos.db')
    if persona:
        query = "SELECT fecha, persona, monto FROM gastos WHERE persona = ? ORDER BY fecha DESC LIMIT ?"
        df = pd.read_sql_query(query, conn, params=(persona, limite))
    else:
        query = "SELECT fecha, persona, monto FROM gastos ORDER BY fecha DESC LIMIT ?"
        df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df

def obtener_gastos_por_dia():
    """Obtiene gastos agrupados por día"""
    conn = sqlite3.connect('gastos.db')
    df = pd.read_sql_query("""
        SELECT date(fecha) as dia, persona, SUM(monto) as total
        FROM gastos
        GROUP BY date(fecha), persona
        ORDER BY dia DESC
    """, conn)
    conn.close()
    return df

# ========== INTERFAZ WEB ==========
def main():
    # Inicializar DB
    inicializar_db()
    
    # Sidebar - Configuración
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        # Gestión de personas
        st.subheader("👥 Personas")
        
        # Mostrar personas actuales
        personas = obtener_personas()
        
        # Agregar nueva persona
        nueva_persona = st.text_input("➕ Nueva persona")
        if st.button("Agregar", use_container_width=True):
            if nueva_persona and nueva_persona.strip():
                if agregar_persona(nueva_persona.strip()):
                    st.success(f"✅ {nueva_persona} agregada")
                    st.rerun()
                else:
                    st.error("❌ Ya existe o nombre inválido")
        
        # Editar/Eliminar personas
        if personas:
            st.divider()
            st.write("✏️ Editar personas:")
            persona_seleccionada = st.selectbox("Seleccionar", personas)
            
            col1, col2 = st.columns(2)
            with col1:
                nuevo_nombre = st.text_input("Nuevo nombre", value=persona_seleccionada, key="edit_name")
                if st.button("💾 Editar", use_container_width=True):
                    if nuevo_nombre and nuevo_nombre != persona_seleccionada:
                        if editar_persona(persona_seleccionada, nuevo_nombre):
                            st.success("✅ Editado")
                            st.rerun()
            
            with col2:
                if st.button("🗑️ Eliminar", use_container_width=True):
                    if len(personas) > 1:
                        if eliminar_persona(persona_seleccionada):
                            st.success("✅ Eliminado")
                            st.rerun()
                    else:
                        st.error("❌ Debe haber al menos una persona")
        
        st.divider()
        
        # Exportar datos
        st.subheader("📊 Exportar")
        if st.button("📥 Descargar Excel", use_container_width=True):
            # Crear Excel en memoria
            from io import BytesIO
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                obtener_historial(limite=1000).to_excel(writer, sheet_name='Historial', index=False)
                obtener_totales().to_excel(writer, sheet_name='Totales', index=False)
            
            st.download_button(
                label="📥 Descargar",
                data=output.getvalue(),
                file_name=f"gastos_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # ========== CONTENIDO PRINCIPAL ==========
    st.title("💰 Gestor de Gastos Compartidos")
    
    # Columnas para registro rápido
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader("📝 Registrar gasto")
        
        # Selector de persona
        personas_actuales = obtener_personas()
        if not personas_actuales:
            st.warning("Agrega al menos una persona en la barra lateral")
            return
        
        persona = st.selectbox("Persona", personas_actuales, key="persona_gasto")
        monto = st.number_input("Monto ($)", min_value=0.01, step=10.0, format="%.2f", key="monto_gasto")
        
        if st.button("💾 GUARDAR GASTO", type="primary", use_container_width=True):
            if monto > 0:
                if guardar_gasto(persona, monto):
                    st.success(f"✅ Gasto de ${monto:.2f} guardado para {persona}")
                    st.rerun()
            else:
                st.error("❌ Ingresa un monto válido")
    
    with col2:
        st.subheader("↩️ Deshacer")
        ultimo_tipo = st.radio("Tipo", ["Último global", "Solo esta persona"], key="deshacer_tipo")
        if st.button("🗑️ Deshacer último", use_container_width=True):
            persona_filtro = persona if ultimo_tipo == "Solo esta persona" else None
            eliminar_ultimo_gasto(persona_filtro)
            st.success("✅ Último gasto eliminado")
            st.rerun()
    
    # Mostrar totales
    st.divider()
    st.subheader("💰 Totales acumulados")
    
    df_totales = obtener_totales()
    
    if not df_totales.empty:
        # Tarjetas de totales
        cols = st.columns(len(df_totales))
        for idx, row in df_totales.iterrows():
            with cols[idx]:
                st.metric(
                    label=f"👤 {row['nombre']}",
                    value=f"${row['total']:,.2f}",
                    delta=None
                )
    
    # Gráficos
    st.divider()
    st.subheader("📈 Visualizaciones")
    
    tab1, tab2, tab3 = st.tabs(["📊 Barras", "🥧 Pastel", "📅 Evolución"])
    
    with tab1:
        if not df_totales.empty and df_totales['total'].sum() > 0:
            fig = px.bar(df_totales, x='nombre', y='total', 
                        title="Gastos por persona",
                        color='nombre',
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para mostrar")
    
    with tab2:
        if not df_totales.empty and df_totales['total'].sum() > 0:
            fig = px.pie(df_totales, values='total', names='nombre',
                        title="Distribución de gastos",
                        hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para mostrar")
    
    with tab3:
        df_diario = obtener_gastos_por_dia()
        if not df_diario.empty:
            fig = px.line(df_diario, x='dia', y='total', color='persona',
                         title="Evolución diaria de gastos",
                         markers=True)
            fig.update_layout(xaxis_title="Fecha", yaxis_title="Monto ($)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para la evolución")
    
    # Historial
    st.divider()
    st.subheader("📜 Historial de gastos")
    
    # Filtro de historial
    col_filtro1, col_filtro2 = st.columns([1, 2])
    with col_filtro1:
        filtro_persona = st.selectbox("Filtrar por persona", ["Todas"] + obtener_personas())
    
    with col_filtro2:
        limite = st.slider("Mostrar últimos", 10, 100, 20)
    
    # Mostrar historial
    if filtro_persona == "Todas":
        df_historial = obtener_historial(limite=limite)
    else:
        df_historial = obtener_historial(persona=filtro_persona, limite=limite)
    
    if not df_historial.empty:
        # Formatear para mostrar
        df_historial['fecha'] = pd.to_datetime(df_historial['fecha']).dt.strftime('%Y-%m-%d %H:%M')
        df_historial['monto'] = df_historial['monto'].apply(lambda x: f"${x:.2f}")
        df_historial = df_historial.rename(columns={'fecha': 'Fecha', 'persona': 'Persona', 'monto': 'Monto'})
        
        st.dataframe(df_historial, use_container_width=True, hide_index=True)
    else:
        st.info("No hay gastos registrados aún")
    
    # Estadísticas rápidas
    if not df_historial.empty and filtro_persona != "Todas":
        st.divider()
        st.subheader(f"📊 Estadísticas de {filtro_persona}")
        
        df_stats = obtener_historial(persona=filtro_persona, limite=1000)
        if not df_stats.empty:
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                st.metric("Total gastado", f"${df_stats['monto'].sum():,.2f}")
            with col_e2:
                st.metric("Promedio por gasto", f"${df_stats['monto'].mean():.2f}")
            with col_e3:
                st.metric("Cantidad de gastos", len(df_stats))

if __name__ == "__main__":
    main()