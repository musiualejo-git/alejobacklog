# ==============================================================================
# 🎮 ALEJO'S BACKLOG MANAGER (v1.0.1 - LocalStorage Edition)
# Developer: Alejandro Perdomo (built with Gemini 3.6 Flash assistance)
# Purpose: Streamlit application to manage personal game backlogs, queues,
#          and library exports using browser localStorage for device isolation.
# ==============================================================================

import streamlit as st
import pandas as pd
import json
import os
import logging
from streamlit_local_storage import LocalStorage

# ---------------- LOGGING SETUP ----------------
LOG_FILE = "app.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_event(message, level="info"):
    """Helper function to log messages to file and console."""
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)

# Initial launch log
if "app_initialized" not in st.session_state:
    log_event("Application v1.0.1 initialized successfully by Alejandro Perdomo (assisted by Gemini 3.6 Flash).")
    st.session_state.app_initialized = True

st.set_page_config(
    page_title="Alejo's Backlog Manager v1.0", 
    page_icon="🎮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

LOCAL_STORAGE_KEY = "alejo_backlog_data_v1"
CHUNK_SIZE = 18  # Number of games to load per batch in card view

# Initialize LocalStorage component
@st.cache_resource
def get_local_storage():
    return LocalStorage()

localStorage = get_local_storage()

# ---------------- TOAST NOTIFICATION HELPER ----------------
if "pending_toast" in st.session_state and st.session_state.pending_toast:
    msg, icon = st.session_state.pending_toast
    st.toast(msg, icon=icon)
    st.session_state.pending_toast = None

def trigger_toast(message, icon="ℹ️"):
    st.session_state.pending_toast = (message, icon)

# ---------------- LOCALSTORAGE DATA HANDLERS ----------------
def load_json_data():
    """Loads full library records from browser localStorage into a pandas DataFrame."""
    default_cols = ["Nombre", "Desarrolladores", "Editores", "Instalado", "Plataformas", 
                    "Fuentes", "Played", "Completed", "In_Queue", "Currently_Playing"]
    
    # Retrieve raw payload from browser local storage via component
    raw_storage = localStorage.getItem(LOCAL_STORAGE_KEY)
    
    games_data = []
    if raw_storage:
        try:
            # If raw_storage is returned as a string, parse it
            payload = json.loads(raw_storage) if isinstance(raw_storage, str) else raw_storage
            if isinstance(payload, dict):
                games_data = payload.get("games", [])
            elif isinstance(payload, list):
                games_data = payload
            log_event(f"Loaded localStorage payload containing {len(games_data)} items.")
            df = pd.DataFrame(games_data)
        except Exception as e:
            log_event(f"Error parsing localStorage payload ({e}). Returning empty structure.", level="error")
            df = pd.DataFrame(columns=default_cols)
    else:
        df = pd.DataFrame(columns=default_cols)
        log_event("No existing localStorage item found. Initialized empty library.")

    # Guarantee required schema columns
    for col in default_cols:
        if col not in df.columns:
            if col in ["Instalado", "Played", "Completed", "In_Queue", "Currently_Playing"]:
                df[col] = False
            else:
                df[col] = ""
        else:
            if col in ["Instalado", "Played", "Completed", "In_Queue", "Currently_Playing"]:
                df[col] = df[col].fillna(False).astype(bool)
            else:
                df[col] = df[col].fillna("").astype(str)

    return df

def save_json_data(explicit=False):
    """Saves DataFrame as clean structured records into browser localStorage."""
    autosave_enabled = st.session_state.get("autosave_enabled", True)
    
    if autosave_enabled or explicit:
        with st.spinner("💾 Saving changes to browser storage..."):
            status_cols = ["Instalado", "Played", "Completed", "In_Queue", "Currently_Playing"]
            for col in status_cols:
                if col in st.session_state.df.columns:
                    st.session_state.df[col] = st.session_state.df[col].fillna(False).astype(bool)

            games_records = st.session_state.df.to_dict(orient="records")
            
            payload = {
                "version": "1.0.1",
                "developer": "Alejandro Perdomo",
                "games": games_records
            }
            
            # Serialize and store into browser local storage
            localStorage.setItem(LOCAL_STORAGE_KEY, json.dumps(payload, ensure_ascii=False))
            
            st.session_state.unsaved_changes = False
            st.session_state.original_df = st.session_state.df.copy()
            log_event(f"Successfully saved {len(games_records)} records into browser localStorage.")
        
        trigger_toast("💾 Changes saved to browser storage!", icon="💾")

# ---------------- STATE INITIALIZATION ----------------
if "df" not in st.session_state:
    st.session_state.df = load_json_data()

if "history" not in st.session_state:
    st.session_state.history = []

if "original_df" not in st.session_state:
    st.session_state.original_df = st.session_state.df.copy()

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📚 Full Library"

if "visible_limit_library" not in st.session_state:
    st.session_state.visible_limit_library = CHUNK_SIZE

if "visible_limit_queue" not in st.session_state:
    st.session_state.visible_limit_queue = CHUNK_SIZE

tab_options = ["📚 Full Library", "🎯 Up Next / Queue", "➕ Add Game", "📁 Data & Backups"]

# ---------------- ACTION HELPERS ----------------
def push_history():
    st.session_state.history.append(st.session_state.df.copy())
    if len(st.session_state.history) > 20:
        st.session_state.history.pop(0)

def undo_last_action():
    if st.session_state.history:
        st.session_state.df = st.session_state.history.pop()
        st.session_state.unsaved_changes = True
        save_json_data()
        log_event("User triggered 'Undo Last Action'.")
        trigger_toast("↩️ Reverted last change!", icon="↩️")
        st.rerun()

def revert_all_changes():
    st.session_state.df = st.session_state.original_df.copy()
    st.session_state.history.clear()
    st.session_state.unsaved_changes = False
    log_event("User reverted all unsaved changes to original storage state.")
    trigger_toast("↩️ Restored to original state!", icon="↩️")
    st.rerun()

def mark_changed():
    st.session_state.unsaved_changes = True

def delete_grouped_game(game_name):
    push_history()
    st.session_state.df = st.session_state.df[st.session_state.df["Nombre"] != game_name].reset_index(drop=True)
    mark_changed()
    save_json_data()
    log_event(f"Deleted all instances of game: '{game_name}'")
    trigger_toast(f"🗑️ Deleted '{game_name}' from storage!", icon="🗑️")
    st.rerun()

def sync_main_tab():
    if "main_tab_selector" in st.session_state:
        st.session_state.active_tab = st.session_state.main_tab_selector
    st.session_state.visible_limit_library = CHUNK_SIZE
    st.session_state.visible_limit_queue = CHUNK_SIZE

# ---------------- SIDEBAR NAVIGATION & ACTIONS ----------------
st.sidebar.header("🛠️ Quick Actions")

has_history = len(st.session_state.get("history", [])) > 0
has_unsaved = st.session_state.get("unsaved_changes", False)
autosave_current = st.session_state.get("autosave_enabled", True)

if st.sidebar.button("↩️ Undo Last Action", disabled=not has_history, use_container_width=True, key="sidebar_undo_btn"):
    undo_last_action()

if not autosave_current:
    btn_label = "💾 Save Changes (*Unsaved*)" if has_unsaved else "💾 Save Changes"
    btn_type = "primary" if has_unsaved else "secondary"
    
    if st.sidebar.button(btn_label, type=btn_type, use_container_width=True, key="sidebar_manual_save_btn"):
        save_json_data(explicit=True)
        st.rerun()

    if st.sidebar.button("↩️ Revert All Changes", disabled=not has_unsaved, type="secondary", use_container_width=True, key="sidebar_revert_all_btn"):
        revert_all_changes()

st.sidebar.markdown("---")
st.sidebar.header("📌 Navigation Shortcuts")

for tab_name in tab_options:
    is_selected = (st.session_state.active_tab == tab_name)
    btn_type = "primary" if is_selected else "secondary"
    if st.sidebar.button(tab_name, type=btn_type, use_container_width=True, key=f"nav_shortcut_{tab_name}"):
        st.session_state.active_tab = tab_name
        if tab_name in tab_options:
            st.session_state.main_tab_selector = tab_name
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ View & App Settings")
mobile_mode = st.sidebar.toggle("📱 Mobile Card Layout", value=True)
autosave_enabled = st.sidebar.toggle("🔄 Autosave Changes", value=True, key="autosave_enabled")

# --- SYSTEM & INFO PAGES IN SIDEBAR ---
st.sidebar.markdown("---")
st.sidebar.header("ℹ️ System & Info")

is_about_active = (st.session_state.active_tab == "ℹ️ About")
about_btn_type = "primary" if is_about_active else "secondary"

if st.sidebar.button("ℹ️ About", type=about_btn_type, use_container_width=True, key="nav_shortcut_about"):
    st.session_state.active_tab = "ℹ️ About"
    st.rerun()

is_logs_active = (st.session_state.active_tab == "📊 Logs & Diagnostics")
logs_btn_type = "primary" if is_logs_active else "secondary"

if st.sidebar.button("📊 Logs & Diagnostics", type=logs_btn_type, use_container_width=True, key="nav_shortcut_logs"):
    st.session_state.active_tab = "📊 Logs & Diagnostics"
    st.rerun()

# ---------------- MAIN APP CONTENT ----------------
st.title("🎮 Alejo's Backlog Manager")

existing_sources = sorted([s for s in st.session_state.df["Fuentes"].dropna().unique() if s]) if not st.session_state.df.empty else []
existing_platforms = sorted([p for p in st.session_state.df["Plataformas"].dropna().unique() if p]) if not st.session_state.df.empty else []

if st.session_state.active_tab in tab_options:
    st.radio(
        "Select Tab",
        options=tab_options,
        index=tab_options.index(st.session_state.active_tab),
        key="main_tab_selector",
        on_change=sync_main_tab,
        horizontal=True,
        label_visibility="collapsed"
    )

st.markdown("---")

# ---------------- SHARED RENDERER FOR CARDS ----------------
def render_game_cards(view_df, is_queue_context=False):
    """Renders Detailed Expanders or Compact Grid Cards."""
    card_sub_view = st.radio(
        "Card Style", 
        options=["Detailed Expanders", "Compact Cards"], 
        index=0,
        horizontal=True, 
        key=f"card_sub_view_{'queue' if is_queue_context else 'lib'}"
    )
    
    limit_key = "visible_limit_queue" if is_queue_context else "visible_limit_library"
    current_limit = st.session_state[limit_key]
    
    paged_df = view_df.iloc[:current_limit]
    st.caption(f"Showing **{len(paged_df)}** of **{len(view_df)}** games")

    st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .card-title {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        font-weight: 700;
        font-size: 1.1em;
        line-height: 1.25em;
        margin-bottom: 6px;
        min-height: 2.5em;
    }
    .card-footer-meta {
        text-align: right;
        color: #888;
        font-size: 0.8em;
        font-weight: 600;
        margin-top: auto;
        padding-top: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    if card_sub_view == "Detailed Expanders":
        for idx, row in paged_df.iterrows():
            game_title = row["Nombre"]
            prefix = "🔥 " if row["Currently_Playing"] else ""
            
            with st.expander(f"**{prefix}{game_title}** *({row['Fuentes']})*"):
                if is_queue_context:
                    c_q = st.checkbox("In Queue", value=bool(row["In_Queue"]), key=f"q_q_{game_title}")
                    c_curr = st.checkbox("🔥 Currently Playing", value=bool(row["Currently_Playing"]), key=f"q_curr_{game_title}")
                    
                    if c_q != row["In_Queue"] or c_curr != row["Currently_Playing"]:
                        push_history()
                        mask = st.session_state.df["Nombre"] == game_title
                        st.session_state.df.loc[mask, ["In_Queue", "Currently_Playing"]] = [c_q or c_curr, c_curr]
                        mark_changed()
                        save_json_data()
                        st.rerun()
                else:
                    m_inst = st.checkbox("Installed", value=bool(row["Instalado"]), key=f"m_inst_{game_title}")
                    m_play = st.checkbox("Played", value=bool(row["Played"]), key=f"m_play_{game_title}")
                    m_comp = st.checkbox("Completed", value=bool(row["Completed"]), key=f"m_comp_{game_title}")
                    m_q = st.checkbox("In Queue", value=bool(row["In_Queue"]), key=f"m_q_{game_title}")
                    m_curr = st.checkbox("🔥 Currently Playing", value=bool(row["Currently_Playing"]), key=f"m_curr_{game_title}")

                    st.markdown("---")
                    if st.button(f"🗑️ Delete {game_title}", key=f"del_mob_{game_title}", use_container_width=True):
                        delete_grouped_game(game_title)

                    if (m_inst != row["Instalado"] or m_play != row["Played"] or 
                        m_comp != row["Completed"] or m_q != row["In_Queue"] or m_curr != row["Currently_Playing"]):
                        push_history()
                        mask = st.session_state.df["Nombre"] == game_title
                        st.session_state.df.loc[mask, ["Instalado", "Played", "Completed", "In_Queue", "Currently_Playing"]] = [
                            m_inst, m_play, m_comp, m_q or m_curr, m_curr
                        ]
                        mark_changed()
                        save_json_data()
                        st.rerun()

    else:
        cols_per_row = 3
        grid_cols = st.columns(cols_per_row)
        
        for idx, row in paged_df.reset_index(drop=True).iterrows():
            game_title = row["Nombre"]
            platform_info = row.get("Plataformas") or "PC"
            source_info = row.get("Fuentes") or "Unknown"
            col_target = grid_cols[idx % cols_per_row]
            
            with col_target:
                with st.container(border=True):
                    st.markdown(f"<div class='card-title' title='{game_title}'>{game_title}</div>", unsafe_allow_html=True)
                    
                    badges = []
                    if row["Currently_Playing"]:
                        badges.append("🔥 Playing")
                    elif row["In_Queue"]:
                        badges.append("🎯 Queued")
                    if row.get("Instalado"):
                        badges.append("💾 Installed")
                    if row.get("Played"):
                        badges.append("✅ Played")
                    if row.get("Completed"):
                        badges.append("🏆 Completed")
                    
                    badge_str = " • ".join(badges) if badges else "⏳ Backlog"
                    st.caption(f"`{badge_str}`")

                    st.markdown(
                        f"<div class='card-footer-meta'>🎮 {platform_info} • 🏪 {source_info}</div>", 
                        unsafe_allow_html=True
                    )

                    with st.expander("⚙️ Edit Status"):
                        if is_queue_context:
                            c_q = st.checkbox("In Queue", value=bool(row["In_Queue"]), key=f"qc_q_{game_title}")
                            c_curr = st.checkbox("🔥 Currently Playing", value=bool(row["Currently_Playing"]), key=f"qc_curr_{game_title}")
                            
                            if c_q != row["In_Queue"] or c_curr != row["Currently_Playing"]:
                                push_history()
                                mask = st.session_state.df["Nombre"] == game_title
                                st.session_state.df.loc[mask, ["In_Queue", "Currently_Playing"]] = [c_q or c_curr, c_curr]
                                mark_changed()
                                save_json_data()
                                st.rerun()
                        else:
                            c_inst = st.checkbox("Installed", value=bool(row["Instalado"]), key=f"cc_inst_{game_title}")
                            c_play = st.checkbox("Played", value=bool(row["Played"]), key=f"cc_play_{game_title}")
                            c_comp = st.checkbox("Completed", value=bool(row["Completed"]), key=f"cc_comp_{game_title}")
                            c_q = st.checkbox("In Queue", value=bool(row["In_Queue"]), key=f"cc_q_{game_title}")
                            c_curr = st.checkbox("🔥 Currently Playing", value=bool(row["Currently_Playing"]), key=f"cc_curr_{game_title}")
                            
                            st.markdown("---")
                            if st.button("🗑️ Delete Game", key=f"del_card_{game_title}", use_container_width=True):
                                delete_grouped_game(game_title)

                            if (c_inst != row["Instalado"] or c_play != row["Played"] or 
                                c_comp != row["Completed"] or c_q != row["In_Queue"] or c_curr != row["Currently_Playing"]):
                                push_history()
                                mask = st.session_state.df["Nombre"] == game_title
                                st.session_state.df.loc[mask, ["Instalado", "Played", "Completed", "In_Queue", "Currently_Playing"]] = [
                                    c_inst, c_play, c_comp, c_q or c_curr, c_curr
                                ]
                                mark_changed()
                                save_json_data()
                                st.rerun()

    if len(view_df) > current_limit:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬇️ Load More Games", use_container_width=True, key=f"load_more_{'queue' if is_queue_context else 'lib'}"):
            st.session_state[limit_key] += CHUNK_SIZE
            st.rerun()

# ---------------- TAB 1: FULL LIBRARY ----------------
if st.session_state.active_tab == "📚 Full Library":
    st.subheader("📚 Your Full Library")
    
    if st.session_state.df.empty:
        st.info("Your library is empty. Use '➕ Add Game' or import JSON/CSV in '📁 Data & Backups'!")
    else:
        col1, col2, col3, col4 = st.columns([2, 1.5, 1, 1])
        with col1:
            search_query = st.text_input("🔍 Search title", "", key="lib_search")
        with col2:
            source_filter = st.multiselect("Filter Source", options=existing_sources, key="lib_source_filter")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            only_installed = st.toggle("Only Installed", value=False, key="lib_installed_toggle")
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            group_dupes = st.toggle("Group Duplicates", value=True, key="lib_group_toggle")

        filtered_df = st.session_state.df.copy()
        if only_installed:
            filtered_df = filtered_df[filtered_df["Instalado"] == True]
        if search_query:
            filtered_df = filtered_df[filtered_df["Nombre"].str.contains(search_query, case=False, na=False)]
        if source_filter:
            filtered_df = filtered_df[filtered_df["Fuentes"].isin(source_filter)]

        if group_dupes and not filtered_df.empty:
            view_df = filtered_df.groupby("Nombre", as_index=False).agg({
                "Fuentes": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                "Plataformas": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                "Instalado": "any",
                "Played": "any",
                "Completed": "any",
                "In_Queue": "any",
                "Currently_Playing": "any"
            })
        else:
            view_df = filtered_df

        if mobile_mode:
            render_game_cards(view_df, is_queue_context=False)
        else:
            st.caption("⚡ Direct Table Edits")
            desktop_df = view_df[["Nombre", "Fuentes", "Instalado", "Played", "Completed", "In_Queue", "Currently_Playing"]].copy()
            desktop_df["Delete"] = False

            edited_data = st.data_editor(
                desktop_df,
                column_config={
                    "Nombre": st.column_config.TextColumn("Game Title", disabled=True),
                    "Fuentes": st.column_config.TextColumn("Source(s)", disabled=True),
                    "Instalado": st.column_config.CheckboxColumn("Installed?"),
                    "Played": st.column_config.CheckboxColumn("Played?"),
                    "Completed": st.column_config.CheckboxColumn("Completed?"),
                    "In_Queue": st.column_config.CheckboxColumn("In Queue?"),
                    "Currently_Playing": st.column_config.CheckboxColumn("Currently Playing?"),
                    "Delete": st.column_config.CheckboxColumn("🗑️ Delete?"),
                },
                use_container_width=True,
                hide_index=True,
                key="library_editor"
            )

            if "library_editor" in st.session_state and "edited_rows" in st.session_state.library_editor:
                edited_rows = st.session_state.library_editor["edited_rows"]
                if edited_rows:
                    push_history()
                    for row_pos, changes in edited_rows.items():
                        target_name = view_df.iloc[row_pos]["Nombre"]
                        if changes.get("Delete") is True:
                            delete_grouped_game(target_name)
                            break
                        else:
                            mask = st.session_state.df["Nombre"] == target_name
                            for col, new_val in changes.items():
                                if col != "Delete":
                                    st.session_state.df.loc[mask, col] = new_val
                                    if col == "Currently_Playing" and new_val is True:
                                        st.session_state.df.loc[mask, "In_Queue"] = True
                    mark_changed()
                    save_json_data()
                    st.rerun()

# ---------------- TAB 2: QUEUE ----------------
elif st.session_state.active_tab == "🎯 Up Next / Queue":
    st.subheader("🎯 Playing Next Queue")
    
    queue_items = st.session_state.df[st.session_state.df["In_Queue"] == True].copy() if not st.session_state.df.empty else pd.DataFrame()
    
    if queue_items.empty:
        st.info("Your queue is currently empty! Check 'In Queue' or 'Currently Playing' on any game in your library to add it.")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            q_search = st.text_input("🔍 Search Queue", "", key="queue_search")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            only_curr = st.toggle("Only 🔥 Currently Playing", value=False, key="queue_curr_toggle")

        filtered_q = queue_items.copy()
        if only_curr:
            filtered_q = filtered_q[filtered_q["Currently_Playing"] == True]
        if q_search:
            filtered_q = filtered_q[filtered_q["Nombre"].str.contains(q_search, case=False, na=False)]

        queue_view = filtered_q.groupby("Nombre", as_index=False).agg({
            "Fuentes": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
            "Plataformas": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
            "In_Queue": "any",
            "Currently_Playing": "any"
        }).sort_values(by="Currently_Playing", ascending=False)

        if mobile_mode:
            render_game_cards(queue_view, is_queue_context=True)
        else:
            st.caption("⚡ Direct Table Edits")
            desktop_q = queue_view[["Nombre", "Fuentes", "In_Queue", "Currently_Playing"]].copy()

            edited_q = st.data_editor(
                desktop_q,
                column_config={
                    "Nombre": st.column_config.TextColumn("Game Title", disabled=True),
                    "Fuentes": st.column_config.TextColumn("Source(s)", disabled=True),
                    "In_Queue": st.column_config.CheckboxColumn("In Queue?"),
                    "Currently_Playing": st.column_config.CheckboxColumn("🔥 Currently Playing?"),
                },
                use_container_width=True,
                hide_index=True,
                key="queue_editor"
            )

            if "queue_editor" in st.session_state and "edited_rows" in st.session_state.queue_editor:
                edited_rows = st.session_state.queue_editor["edited_rows"]
                if edited_rows:
                    push_history()
                    for row_pos, changes in edited_rows.items():
                        target_name = queue_view.iloc[row_pos]["Nombre"]
                        mask = st.session_state.df["Nombre"] == target_name
                        for col, new_val in changes.items():
                            st.session_state.df.loc[mask, col] = new_val
                            if col == "Currently_Playing" and new_val is True:
                                st.session_state.df.loc[mask, "In_Queue"] = True
                    mark_changed()
                    save_json_data()
                    st.rerun()

# ---------------- TAB 3: ADD NEW GAME ----------------
elif st.session_state.active_tab == "➕ Add Game":
    st.subheader("➕ Add a New Game to Your Library")
    
    with st.form("add_game_tab_form", clear_on_submit=True):
        name = st.text_input("Game Name")
        
        col_src, col_plat = st.columns(2)
        with col_src:
            source_choice = st.selectbox("Source / Store", options=existing_sources + ["+ Add Custom Source..."], key="add_source_choice")
            is_custom_source = (source_choice == "+ Add Custom Source...")
            source_input = st.text_input(
                "Custom Source Name", 
                value="Steam" if is_custom_source else "", 
                disabled=not is_custom_source,
                key="add_custom_source_input"
            )
            source = source_input if is_custom_source else source_choice

        with col_plat:
            platform_choice = st.selectbox("Platform", options=existing_platforms + ["+ Add Custom Platform..."], key="add_platform_choice")
            is_custom_platform = (platform_choice == "+ Add Custom Platform...")
            platform_input = st.text_input(
                "Custom Platform Name", 
                value="PC (Windows)" if is_custom_platform else "", 
                disabled=not is_custom_platform,
                key="add_custom_platform_input"
            )
            platform = platform_input if is_custom_platform else platform_choice

        st.markdown("##### Options & Initial Status")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            installed = st.checkbox("Installed")
        with c2:
            played = st.checkbox("Have Played")
        with c3:
            completed = st.checkbox("Have Completed")
        with c4:
            add_to_q = st.checkbox("Add to Queue")
        with c5:
            currently_playing = st.checkbox("🔥 Currently Playing")

        submitted = st.form_submit_button("➕ Add Game to Library", type="primary", use_container_width=True)
        if submitted:
            if name.strip() == "":
                st.error("Please enter a game name.")
            else:
                push_history()
                new_row = {
                    "Nombre": name.strip(),
                    "Desarrolladores": "",
                    "Editores": "",
                    "Instalado": installed,
                    "Plataformas": platform,
                    "Fuentes": source,
                    "Played": played,
                    "Completed": completed,
                    "In_Queue": add_to_q or currently_playing,
                    "Currently_Playing": currently_playing
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                mark_changed()
                save_json_data()
                log_event(f"Manually added game: '{name.strip()}'")
                trigger_toast(f"✅ Added '{name}' to your library!", icon="🎮")
                st.rerun()

# ---------------- TAB 4: DATA & BACKUPS ----------------
elif st.session_state.active_tab == "📁 Data & Backups":
    st.subheader("📁 Data Management & Backups")
    
    col_imp, col_exp = st.columns(2)
    
    with col_imp:
        st.markdown("### 📥 Import Data")
        uploaded_file = st.file_uploader("Choose JSON or CSV file", type=["json", "csv"], key="data_tab_uploader")
        
        if uploaded_file is not None:
            if st.button("Process & Merge Data File", type="primary", use_container_width=True):
                try:
                    push_history()
                    filename = uploaded_file.name.lower()
                    
                    if filename.endswith(".json"):
                        imported_payload = json.load(uploaded_file)
                        raw_records = imported_payload.get("games", []) if isinstance(imported_payload, dict) else imported_payload
                        imported_df = pd.DataFrame(raw_records)
                    else:
                        imported_df = pd.read_csv(uploaded_file)

                    col_aliases = {
                        "Name": "Nombre", "Installed": "Instalado", "IsInstalled": "Instalado",
                        "Platforms": "Plataformas", "Platform": "Plataformas",
                        "Source": "Fuentes", "Sources": "Fuentes"
                    }
                    imported_df = imported_df.rename(columns=col_aliases)

                    for col in ["Nombre", "Desarrolladores", "Editores", "Instalado", "Plataformas", "Fuentes"]:
                        if col not in imported_df.columns:
                            imported_df[col] = "" if col != "Instalado" else False

                    status_cols = ["Instalado", "Played", "Completed", "In_Queue", "Currently_Playing"]
                    for col in status_cols:
                        if col in imported_df.columns:
                            imported_df[col] = imported_df[col].fillna(False).astype(bool)
                        else:
                            imported_df[col] = False

                    existing_df = st.session_state.df.copy()
                    if existing_df.empty:
                        st.session_state.df = imported_df
                        added_count = len(imported_df)
                    else:
                        imported_df["_key"] = imported_df["Nombre"].str.lower().fillna("") + "||" + imported_df["Fuentes"].str.lower().fillna("")
                        existing_df["_key"] = existing_df["Nombre"].str.lower().fillna("") + "||" + existing_df["Fuentes"].str.lower().fillna("")
                        
                        existing_keys = set(existing_df["_key"])
                        new_mask = ~imported_df["_key"].isin(existing_keys)
                        new_games = imported_df[new_mask].drop(columns=["_key"])
                        
                        existing_df = existing_df.drop(columns=["_key"])
                        st.session_state.df = pd.concat([existing_df, new_games], ignore_index=True)
                        added_count = len(new_games)

                    mark_changed()
                    save_json_data()
                    log_event(f"Imported data file: {added_count} new entries merged.")
                    trigger_toast(f"✅ Import complete! Added {added_count} new entries.", icon="🎉")
                    st.rerun()

                except Exception as e:
                    log_event(f"Error processing import: {e}", level="error")
                    trigger_toast(f"❌ Failed to import file: {e}", icon="🚨")

    with col_exp:
        st.markdown("### 💾 Export & Download Backups")
        
        try:
            full_records = st.session_state.df.to_dict(orient="records")
            full_export_payload = {
                "version": "1.0.1",
                "developer": "Alejandro Perdomo",
                "games": full_records
            }
            json_bytes = json.dumps(full_export_payload, indent=2, ensure_ascii=False).encode('utf-8')
            
            st.download_button(
                "📥 Download Full JSON Backup", 
                data=json_bytes, 
                file_name="backlog_backup.json", 
                mime="application/json", 
                use_container_width=True
            )
        except Exception as e:
            log_event(f"Export JSON error: {e}", level="error")
            trigger_toast(f"❌ JSON Export failed: {e}", icon="🚨")

        st.markdown("<br>", unsafe_allow_html=True)
        
        try:
            csv_bytes = st.session_state.df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Full Library CSV", 
                data=csv_bytes, 
                file_name="full_library_backup.csv", 
                mime="text/csv", 
                use_container_width=True
            )
        except Exception as e:
            log_event(f"Export CSV error: {e}", level="error")
            trigger_toast(f"❌ CSV Export failed: {e}", icon="🚨")

    st.markdown("---")
    st.markdown("### 🚨 Danger Zone")
    confirm_clear = st.checkbox("I understand this will permanently erase my backlog and queue from browser storage", key="confirm_wipe_checkbox")
    
    if st.button("🔥 Clear All Data", type="primary", disabled=not confirm_clear, use_container_width=True):
        try:
            push_history()
            default_cols = ["Nombre", "Desarrolladores", "Editores", "Instalado", "Plataformas", 
                            "Fuentes", "Played", "Completed", "In_Queue", "Currently_Playing"]
            st.session_state.df = pd.DataFrame(columns=default_cols)
            save_json_data(explicit=True)
            log_event("User cleared all browser storage library data.", level="warning")
            trigger_toast("🔥 All data erased!", icon="🗑️")
            st.rerun()
        except Exception as e:
            log_event(f"Error clearing data: {e}", level="error")
            trigger_toast(f"❌ Failed to clear data: {e}", icon="🚨")

# ---------------- EXCLUSIVE PAGE: ABOUT ----------------
elif st.session_state.active_tab == "ℹ️ About":
    st.subheader("ℹ️ About Alejo's Backlog Manager")
    
    st.markdown("""
    ### 🎮 Welcome to Version 1.0.1 (LocalStorage Edition)
    **Alejo's Backlog Manager** is a lightweight, self-contained application built specifically to track, organize, and prioritize video game backlogs and play queues.

    ---

    #### 🚀 Key Features
    * **Browser Local Storage:** Persistent client-side architecture ensuring data is completely exclusive and isolated per browser/device.
    * **Play Queue & Up Next:** Prioritize titles, track what you're currently playing, and move games seamlessly between backlogs and active queues.
    * **Mobile & Desktop Responsive:** Switch on the fly between touch-friendly card expanders and high-density data tables.
    * **Full Undo & Data Control:** Complete historical state tracking with single-click action undo and comprehensive backup options.
    * **Diagnostics & Event Logging:** Real-time application logging for operational visibility and maintenance.

    ---

    **Credits & Acknowledgments:**
    * **[Playnite](https://playnite.link/)** — For the open-source video game library manager.
    * **[Library Exporter Advance](https://playnite.link/addons.html#LibraryExporter_54bf64c6-c453-4cbc-92f8-4960b56f930e)** — Addon used as the foundation for exporting game library data into this application.

    ---

    **🐙 Github repository:**
    * **[Alejo's Backlog Manager source code on Github](https://github.com/musiualejo-git/alejobacklog)** — For anyone interested to make their own or improve it.

    ---

    #### 📌 System Details
    | Property | Detail |
    | :--- | :--- |
    | **Application Version** | `1.0.1` (LocalStorage Release) |
    | **Developer** | Alejandro Perdomo |
    | **AI Assistance** | Gemini 3.6 Flash |
    | **Framework** | Streamlit & Python |
    | **Storage Model** | Browser Local Storage |
    """)

# ---------------- EXCLUSIVE PAGE: LOGS & DIAGNOSTICS ----------------
elif st.session_state.active_tab == "📊 Logs & Diagnostics":
    st.subheader("📊 Application Logs & Diagnostics")
    st.caption("Inspect runtime events or export `app.log` for troubleshooting.")

    col_log_actions, col_log_dl = st.columns([2, 1])

    log_contents = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            log_contents = f.read()

    with col_log_dl:
        if log_contents:
            st.download_button(
                "📥 Export Log File (app.log)",
                data=log_contents,
                file_name="app.log",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("Log file is currently empty.")

        if st.button("🗑️ Clear Log History", use_container_width=True):
            with open(LOG_FILE, "w") as f:
                f.write("")
            log_event("Log file cleared by user.")
            st.rerun()

    with col_log_actions:
        filter_level = st.selectbox("Filter Log Level", ["ALL", "INFO", "WARNING", "ERROR"])

    st.markdown("### 📜 Event Viewer")
    if log_contents:
        log_lines = log_contents.strip().split("\n")
        if filter_level != "ALL":
            log_lines = [line for line in log_lines if f"[{filter_level}]" in line]
        
        st.code("\n".join(log_lines[-200:]), language="log")
    else:
        st.code("No log records found.", language="log")
