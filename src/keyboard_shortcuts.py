"""
Keyboard Shortcuts für die Streamlit GUI

Unterstützt:
- Ctrl+O: Audio öffnen
- Ctrl+R: Render starten
- Ctrl+S: Projekt speichern
- Ctrl+Z: Undo
- Ctrl+Y: Redo
- ESC: Vorschau schließen
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional
from enum import Enum
import streamlit as st


class ShortcutKey(Enum):
    """Verfügbare Keyboard Shortcuts."""

    OPEN = "ctrl+o"
    SAVE = "ctrl+s"
    RENDER = "ctrl+r"
    PREVIEW = "ctrl+p"
    UNDO = "ctrl+z"
    REDO = "ctrl+y"
    ESCAPE = "escape"
    FULLSCREEN = "f11"


@dataclass
class ShortcutAction:
    """Eine Keyboard Shortcut Aktion."""

    key: str
    description: str
    callback: Optional[Callable] = None
    prevent_default: bool = True


class KeyboardShortcutManager:
    """
    Verwaltet Keyboard Shortcuts für die Streamlit GUI.

    Usage:
        manager = KeyboardShortcutManager()
        manager.register(ShortcutKey.OPEN, "Audio öffnen", on_open)
        manager.render_component()  # Rendert das JS für Shortcuts
    """

    def __init__(self):
        self.shortcuts: Dict[ShortcutKey, ShortcutAction] = {}
        self._init_session_state()

    def _init_session_state(self):
        """Initialisiert Session State für Shortcuts."""
        if "keyboard_shortcuts" not in st.session_state:
            st.session_state.keyboard_shortcuts = {}
        if "shortcut_history" not in st.session_state:
            st.session_state.shortcut_history = []

    def register(
        self,
        key: ShortcutKey,
        description: str,
        callback: Optional[Callable] = None,
        prevent_default: bool = True,
    ):
        """Registriert einen neuen Shortcut."""
        self.shortcuts[key] = ShortcutAction(
            key=key.value,
            description=description,
            callback=callback,
            prevent_default=prevent_default,
        )

    def unregister(self, key: ShortcutKey):
        """Entfernt einen Shortcut."""
        if key in self.shortcuts:
            del self.shortcuts[key]

    def get_js_component(self) -> str:
        """Generiert das JavaScript für Keyboard Shortcuts."""
        shortcuts_js = []
        for key, action in self.shortcuts.items():
            shortcuts_js.append(
                {
                    "key": action.key,
                    "action": key.name,
                    "preventDefault": action.prevent_default,
                }
            )

        import json

        shortcuts_json = json.dumps(shortcuts_js)

        return f"""
        <script>
        // Keyboard Shortcuts für Audio Visualizer Pro
        (function() {{
            const shortcuts = {shortcuts_json};
            
            document.addEventListener('keydown', function(e) {{
                const keyCombo = [];
                if (e.ctrlKey) keyCombo.push('ctrl');
                if (e.altKey) keyCombo.push('alt');
                if (e.shiftKey) keyCombo.push('shift');
                keyCombo.push(e.key.toLowerCase());
                
                const pressedKey = keyCombo.join('+');
                
                shortcuts.forEach(function(shortcut) {{
                    if (pressedKey === shortcut.key) {{
                        if (shortcut.preventDefault) {{
                            e.preventDefault();
                        }}
                        
                        // Sende Event an Streamlit
                        const event = new CustomEvent('shortcutTriggered', {{
                            detail: {{ action: shortcut.action }}
                        }});
                        document.dispatchEvent(event);
                        
                        // Speichere in sessionStorage für Streamlit-Polling
                        sessionStorage.setItem('lastShortcut', JSON.stringify({{
                            action: shortcut.action,
                            timestamp: Date.now()
                        }}));
                    }}
                }});
            }});
            
            console.log('🎹 Keyboard Shortcuts aktiviert:', shortcuts.map(s => s.key).join(', '));
        }})();
        </script>
        """

    def render_component(self):
        """Rendert das Shortcut-JS in Streamlit."""
        st.components.v1.html(self.get_js_component(), height=0)

    def check_shortcuts(self) -> Optional[str]:
        """Prüft ob ein Shortcut ausgelöst wurde (Polling)."""
        import streamlit.components.v1 as components

        # HTML Komponente die sessionStorage ausliest
        result = components.html(
            """
        <script>
        const lastShortcut = sessionStorage.getItem('lastShortcut');
        if (lastShortcut) {
            const data = JSON.parse(lastShortcut);
            // Nur wenn weniger als 500ms alt
            if (Date.now() - data.timestamp < 500) {
                sessionStorage.removeItem('lastShortcut');
                document.write(data.action);
            } else {
                document.write('');
            }
        }
        </script>
        """,
            height=0,
        )

        return result if result else None

    def get_help_text(self) -> str:
        """Generiert Hilfe-Text für alle Shortcuts."""
        lines = ["### ⌨️ Keyboard Shortcuts\n"]
        for key, action in self.shortcuts.items():
            key_display = action.key.replace("+", "+").upper()
            lines.append(f"**`{key_display}`** - {action.description}")
        return "\n".join(lines)


class UndoRedoManager:
    """
    Einfaches Undo/Redo System für Config-Änderungen.

    Usage:
        undo_manager = UndoRedoManager(max_history=10)
        undo_manager.push_state(config)

        # Bei Undo:
        config = undo_manager.undo()
    """

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self._init_session_state()

    def _init_session_state(self):
        """Initialisiert Session State für Undo/Redo."""
        if "undo_stack" not in st.session_state:
            st.session_state.undo_stack = []
        if "redo_stack" not in st.session_state:
            st.session_state.redo_stack = []

    def push_state(self, state: dict):
        """Speichert einen neuen Zustand."""
        # Konvertiere zu JSON für Deep Copy
        import json

        state_copy = json.loads(json.dumps(state, default=str))

        st.session_state.undo_stack.append(state_copy)

        # Limit Stack-Größe
        if len(st.session_state.undo_stack) > self.max_history:
            st.session_state.undo_stack.pop(0)

        # Clear redo stack auf neue Änderung
        st.session_state.redo_stack = []

    def can_undo(self) -> bool:
        """Prüft ob Undo möglich ist."""
        return len(st.session_state.undo_stack) > 1

    def can_redo(self) -> bool:
        """Prüft ob Redo möglich ist."""
        return len(st.session_state.redo_stack) > 0

    def undo(self) -> Optional[dict]:
        """Macht die letzte Änderung rückgängig."""
        if not self.can_undo():
            return None

        # Aktueller Zustand auf Redo-Stack
        current = st.session_state.undo_stack.pop()
        st.session_state.redo_stack.append(current)

        # Vorheriger Zustand zurückgeben
        if st.session_state.undo_stack:
            return st.session_state.undo_stack[-1]
        return None

    def redo(self) -> Optional[dict]:
        """Wiederholt die letzte rückgängig gemachte Änderung."""
        if not self.can_redo():
            return None

        state = st.session_state.redo_stack.pop()
        st.session_state.undo_stack.append(state)
        return state

    def clear(self):
        """Löscht die gesamte History."""
        st.session_state.undo_stack = []
        st.session_state.redo_stack = []


# Hilfsfunktionen für GUI-Integration
def show_shortcut_help():
    """Zeigt Keyboard-Shortcut Hilfe an."""
    manager = KeyboardShortcutManager()

    # Standard-Shortcuts registrieren
    manager.register(ShortcutKey.OPEN, "Audio-Datei öffnen")
    manager.register(ShortcutKey.SAVE, "Projekt speichern")
    manager.register(ShortcutKey.RENDER, "Video rendern")
    manager.register(ShortcutKey.PREVIEW, "Vorschau starten")
    manager.register(ShortcutKey.UNDO, "Rückgängig")
    manager.register(ShortcutKey.REDO, "Wiederholen")
    manager.register(ShortcutKey.ESCAPE, "Vorschau schließen")

    with st.expander("⌨️ Keyboard Shortcuts"):
        st.markdown(manager.get_help_text())


def init_keyboard_support():
    """Initialisiert Keyboard-Support für die GUI."""
    if "keyboard_manager" not in st.session_state:
        st.session_state.keyboard_manager = KeyboardShortcutManager()

    if "undo_manager" not in st.session_state:
        st.session_state.undo_manager = UndoRedoManager()

    return st.session_state.keyboard_manager, st.session_state.undo_manager
