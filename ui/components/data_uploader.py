import streamlit as st
import pandas as pd
import sys
import subprocess

def render_global_uploader(key, context_name):
    st.info(f"**Inteligencia de Datos Central:** Carga la sábana consolidada de {context_name}. El sistema extraerá las partes correspondientes e inyectará los KPIs automáticamente hacia cada campus.")
    uploaded_file = st.file_uploader(f"Cargar Base Maestra CSV/Excel", type=["csv", "xlsx", "xls"], key=f"up_global_{key}")
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_custom = pd.read_csv(uploaded_file, header=0)
            else:
                try:
                    df_custom = pd.read_excel(uploaded_file, header=0)
                except ImportError:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--user"])
                    st.error("Reiniciando motor de excel. Presiona Ctrl+C y vuelve a correr Streamlit.")
                    st.stop()
            
            # Auto-limpieza básica
            df_custom = df_custom.dropna(how='all').dropna(axis=1, how='all')
            
            # Motor de re-estructuración (Molding Tool para reportes sucios)
            campus_keywords = ["misiones", "san agustin", "nuevo sur", "nuevo_sur", "san_agustin"]
            
            # Verificar si las columnas actuales ya son el header correcto (caso header=0 limpio)
            cols_str = " ".join([str(x).lower() for x in df_custom.columns])
            if sum([1 for c in campus_keywords if c in cols_str]) < 2:
                for idx, row in df_custom.iterrows():
                    row_str = " ".join([str(x).lower() for x in row.values])
                    # Si la fila tiene los nombres de los campus, asumimos que es el verdadero header
                    if sum([1 for c in campus_keywords if c in row_str]) >= 2:
                        df_custom.columns = row.values
                        df_custom = df_custom.loc[idx+1:]
                        break
                    
            # Limpieza y renombramiento de columnas caóticas
            new_cols = []
            for i, col in enumerate(df_custom.columns):
                # Si es nulo o equivalente
                if pd.isna(col) or str(col).strip() == "" or str(col).startswith("Unnamed"):
                    if i == 0:
                        new_cols.append("Nivel / Segmento")
                    else:
                        new_cols.append(f"Sin_Titulo_{i}")
                else:
                    new_cols.append(str(col))
                    
            df_custom.columns = new_cols
            df_custom = df_custom.reset_index(drop=True)
            
            st.session_state[f"dynamic_df_{key}"] = df_custom
            
            st.success(f"Master File detectado y limpio. Estructuras dinámicas listas para distribución.")
        except Exception as e:
            st.error(f"Error interpretando tu archivo base central: {str(e)}")
            
    if f"dynamic_df_{key}" in st.session_state:
        df_custom = st.session_state[f"dynamic_df_{key}"]
        st.success(f"Master File detectado y limpio. Estructuras dinámicas listas para distribución.")
        st.markdown("**Vista Integradora Global de Sábana de Datos**")
        st.dataframe(df_custom, hide_index=True, use_container_width=True)
        return True
        
    return False

def render_campus_dynamic_view(key, campus_name):
    if f"dynamic_df_{key}" in st.session_state:
        df_master = st.session_state[f"dynamic_df_{key}"]
        
        # 1. Búsqueda Vertical Clásica (columna llamada Campus/Sede)
        campus_col = None
        for col in df_master.columns:
            if str(col).lower() in ["campus", "sede", "colegio", "escuela", "institucion", "plantel", "school"]:
                campus_col = col
                break
                
        if campus_col:
            df_campus = df_master[df_master[campus_col].astype(str).str.contains(campus_name, case=False, na=False)]
            if not df_campus.empty:
                st.success(f"Datos Inyectados desde Central (Mapeo Vertical) para {campus_name}.")
                st.dataframe(df_campus, hide_index=True, use_container_width=True)
                return True

        # 2. Búsqueda Pivot Inteligente Profunda (Buscando tanto en headers como en celdas para sub-tablas)
        cols_to_keep = [df_master.columns[0]] # Siempre anclar la primera columna (índices o labels)
        found_campus_col = None
        
        for col in df_master.columns:
            # Match directo en el header
            if campus_name.lower() in str(col).lower():
                found_campus_col = col
                break
            # Match profundo en las celdas de la columna (típico cuando el excel trae sub-títulos)
            elif df_master[col].astype(str).str.contains(campus_name, case=False, na=False).any():
                found_campus_col = col
                break
                
        if found_campus_col:
            cols_to_keep.append(found_campus_col)
            # Evitar repetición si la primera columna es la misma
            cols_to_keep = list(dict.fromkeys(cols_to_keep))
            
            # Limpiamos filas donde la columna de anclaje Y la del campus estén vacías en el subset
            df_sliced = df_master[cols_to_keep].dropna(how='all')
            
            st.success(f"Metadatos Extraídos Precisamente desde Central para {campus_name}.")
            st.dataframe(df_sliced, hide_index=True, use_container_width=True)
            return True
        
        # 3. Failsafe: Mostrar crudo
        st.info(f"Visualizando sábana cruda global (imposible aislar una segmentación directa para {campus_name}).")
        st.dataframe(df_master, hide_index=True, use_container_width=True)
        return True
        
    return False
