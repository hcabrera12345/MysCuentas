import flet as ft
import requests
import json

# --- SERVICES (Inline) ---
class ApiService:
    BASE_URL = "http://127.0.0.1:8000"
    def send_chat(self, text, user="Hernan"):
        try:
            res = requests.post(f"{self.BASE_URL}/chat/", json={"text": text, "user": user})
            return res.json() if res.status_code == 200 else {"response": "Error del servidor", "intent": "ERROR"}
        except Exception as e:
            return {"response": f"Error: {e}", "intent": "ERROR"}

api = ApiService()

# --- MAIN APP ---
def main(page: ft.Page):
    page.title = "The Bot Family"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    # -- UTILS --
    def go_home(e=None):
        page.clean()
        page.add(
            ft.AppBar(title=ft.Text("The Bot Family 🤖"), center_title=True, bgcolor="surface_variant"),
            ft.Column([
                ft.Container(height=20),
                bot_card("Finance Bot", "Gastos y Reportes", "attach_money", "green", go_finance),
                bot_card("Home Bot", "Compras y Tareas", "home", "orange", None, True),
                bot_card("Travel Bot", "Viajes", "airplanemode_active", "blue", None, True),
                bot_card("Memory Bot", "Fotos", "photo_camera", "purple", None, True),
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        )
        page.update()

    def go_finance(e=None):
        page.clean()
        chat_list = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        
        # Initial msg
        chat_list.controls.append(chat_bubble("Hola! Soy tu Finance Bot. ¿Qué gastaste hoy?", False))

        txt_input = ft.TextField(hint_text="Escribe un gasto...", expand=True, on_submit=lambda e: send_msg(e))
        
        def send_msg(e):
            text = txt_input.value
            if not text: return
            txt_input.value = ""
            
            # User msg
            chat_list.controls.append(chat_bubble(text, True))
            page.update()
            
            # API Call
            res = api.send_chat(text)
            resp = res.get("response", "Error")
            
            # Bot msg
            chat_list.controls.append(chat_bubble(resp, False))
            page.update()
            txt_input.focus()

        page.add(
            ft.AppBar(
                title=ft.Text("Finance Bot 💰"), 
                bgcolor="green_100", 
                leading=ft.IconButton("arrow_back", on_click=go_home)
            ),
            ft.Container(chat_list, expand=True, padding=10),
            ft.Container(
                content=ft.Row([txt_input, ft.IconButton("send", on_click=send_msg, icon_color="green")]),
                padding=10
            )
        )
        page.update()

    # -- COMPONENTS --
    def bot_card(title, sub, icon, color, on_click, disabled=False):
        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=40, color=color),
                    ft.Container(width=20),
                    ft.Column([ft.Text(title, weight="bold"), ft.Text(sub, size=12, color="grey")], expand=True),
                    ft.Icon("arrow_forward_ios", size=16, color="grey") if not disabled else ft.Container(content=ft.Text("Pronto", size=10), bgcolor="grey_300", padding=5, border_radius=5)
                ]),
                padding=20,
                on_click=on_click,
                ink=not disabled
            ),
            margin=ft.margin.only(bottom=15)
        )

    def chat_bubble(text, is_user):
        return ft.Row(
            [ft.Container(
                content=ft.Text(text, color="white" if is_user else "black"),
                bgcolor="blue" if is_user else "white",
                border_radius=20,
                padding=15
            )],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
        )

    # -- START --
    go_home()

if __name__ == "__main__":
    ft.app(main)
