import os
import sqlite3
from datetime import datetime, date, time as dtime

os.environ["KIVY_LOG_LEVEL"] = "warning"

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.audio import SoundLoader

from kivymd.app import MDApp
from kivymd.uix.list import MDListItem, MDListItemHeadlineText

# Date picker залишаємо (він у тебе працює)
from kivymd.uix.pickers import MDModalDatePicker

try:
    from plyer import notification
except Exception:
    notification = None


KV = """
#:import dp kivy.metrics.dp

MDScreen:
    md_bg_color: app.theme_cls.backgroundColor

    BoxLayout:
        orientation: "vertical"

        BoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: dp(12)
            spacing: dp(12)

            MDLabel:
                text: "Planner"
                bold: True
                valign: "middle"

            Widget:

            MDLabel:
                text: "Dark"
                size_hint_x: None
                width: dp(48)
                halign: "right"
                valign: "middle"

            MDSwitch:
                id: theme_switch
                active: True
                on_active: app.toggle_theme(self.active)

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            padding: dp(12)
            spacing: dp(12)

            Button:
                text: "Todo"
                on_release: app.switch_tab("todo")

            Button:
                text: "Calendar"
                on_release: app.switch_tab("calendar")

        ScreenManager:
            id: sm

            Screen:
                name: "todo"

                BoxLayout:
                    orientation: "vertical"
                    padding: dp(12)
                    spacing: dp(12)

                    MDTextField:
                        id: task_input
                        hint_text: "New task"
                        mode: "outlined"
                        size_hint_y: None
                        height: dp(48)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(12)

                        Button:
                            text: "Add"
                            on_release: app.add_task()

                        Button:
                            text: "Clear done"
                            on_release: app.clear_done()

                    ScrollView:
                        MDList:
                            id: task_list

            Screen:
                name: "calendar"

                BoxLayout:
                    orientation: "vertical"
                    padding: dp(12)
                    spacing: dp(12)

                    MDLabel:
                        id: selected_dt_label
                        text: "Pick date and set time"
                        size_hint_y: None
                        height: dp(32)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(12)

                        Button:
                            text: "Pick date"
                            on_release: app.open_date_picker()

                    # Time input (instead of MDTimePicker)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(56)
                        spacing: dp(12)

                        MDTextField:
                            id: hour_input
                            hint_text: "HH"
                            input_filter: "int"
                            text: "09"
                            mode: "outlined"
                            size_hint_x: None
                            width: dp(90)

                        MDTextField:
                            id: minute_input
                            hint_text: "MM"
                            input_filter: "int"
                            text: "00"
                            mode: "outlined"
                            size_hint_x: None
                            width: dp(90)

                        Button:
                            text: "Set time"
                            on_release: app.set_time_from_inputs()

                    MDTextField:
                        id: event_title
                        hint_text: "Event title"
                        mode: "outlined"
                        size_hint_y: None
                        height: dp(48)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(12)

                        Button:
                            text: "Save event"
                            on_release: app.save_event()

                        Button:
                            text: "Delete selected"
                            on_release: app.delete_selected_event()

                    ScrollView:
                        MDList:
                            id: event_list
"""


class PlannerApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.root = Builder.load_string(KV)

        self.conn = sqlite3.connect("planner.db")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, text TEXT, done INTEGER DEFAULT 0)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, title TEXT, dt_iso TEXT)"
        )
        self.conn.commit()

        self.selected_date = date.today()
        self.selected_time = dtime(9, 0)
        self.selected_event_id = None

        self.load_tasks()
        self.load_events()
        self.update_selected_dt_label()

        Clock.schedule_interval(self.check_alarms, 1.0)

        # Optional alarm sound: place alarm.wav near this file
        self.alarm_sound = SoundLoader.load("alarm.wav")

        return self.root

    # Tabs
    def switch_tab(self, name: str):
        self.root.ids.sm.current = name

    # Theme
    def toggle_theme(self, dark: bool):
        self.theme_cls.theme_style = "Dark" if dark else "Light"

    # Todo
    def load_tasks(self):
        task_list = self.root.ids.task_list
        task_list.clear_widgets()
        for task_id, text, done in self.conn.execute(
            "SELECT id, text, done FROM tasks ORDER BY id DESC"
        ):
            label = ("✅ " if done else "⬜ ") + text
            item = MDListItem(MDListItemHeadlineText(text=label))
            item.on_release = lambda tid=task_id: self.toggle_done(tid)
            task_list.add_widget(item)

    def add_task(self):
        text = self.root.ids.task_input.text.strip()
        if not text:
            return
        self.conn.execute("INSERT INTO tasks(text, done) VALUES(?, 0)", (text,))
        self.conn.commit()
        self.root.ids.task_input.text = ""
        self.load_tasks()

    def toggle_done(self, task_id: int):
        row = self.conn.execute("SELECT done FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            return
        new_done = 0 if row[0] else 1
        self.conn.execute("UPDATE tasks SET done=? WHERE id=?", (new_done, task_id))
        self.conn.commit()
        self.load_tasks()

    def clear_done(self):
        self.conn.execute("DELETE FROM tasks WHERE done=1")
        self.conn.commit()
        self.load_tasks()

    # Calendar / date picker
    def update_selected_dt_label(self):
        dt = datetime.combine(self.selected_date, self.selected_time)
        self.root.ids.selected_dt_label.text = f"Selected: {dt.strftime('%Y-%m-%d %H:%M')}"

    def open_date_picker(self):
        picker = MDModalDatePicker()
        picker.bind(on_ok=self.on_date_ok, on_cancel=lambda *_: picker.dismiss())
        picker.open()

    def on_date_ok(self, instance_picker, selected_date: date, *_):
        instance_picker.dismiss()
        self.selected_date = selected_date
        self.update_selected_dt_label()

    # Time via inputs
    def set_time_from_inputs(self):
        h_txt = (self.root.ids.hour_input.text or "").strip()
        m_txt = (self.root.ids.minute_input.text or "").strip()

        try:
            h = int(h_txt)
            m = int(m_txt)
        except ValueError:
            return

        if not (0 <= h <= 23 and 0 <= m <= 59):
            return

        self.selected_time = dtime(h, m)
        self.update_selected_dt_label()

    # Events
    def save_event(self):
        title = self.root.ids.event_title.text.strip() or "Event"
        dt = datetime.combine(self.selected_date, self.selected_time)

        self.conn.execute("INSERT INTO events(title, dt_iso) VALUES(?, ?)", (title, dt.isoformat()))
        self.conn.commit()

        self.root.ids.event_title.text = ""
        self.load_events()

    def load_events(self):
        event_list = self.root.ids.event_list
        event_list.clear_widgets()
        self.selected_event_id = None

        for event_id, title, dt_iso in self.conn.execute(
            "SELECT id, title, dt_iso FROM events ORDER BY dt_iso ASC"
        ):
            dt = datetime.fromisoformat(dt_iso)
            label = f"⏰ {dt.strftime('%Y-%m-%d %H:%M')} — {title}"
            item = MDListItem(MDListItemHeadlineText(text=label))
            item.on_release = lambda eid=event_id: self.select_event(eid)
            event_list.add_widget(item)

    def select_event(self, event_id: int):
        self.selected_event_id = event_id

    def delete_selected_event(self):
        if not self.selected_event_id:
            return
        self.conn.execute("DELETE FROM events WHERE id=?", (self.selected_event_id,))
        self.conn.commit()
        self.selected_event_id = None
        self.load_events()

    # Alarm (in-app)
    def check_alarms(self, _dt):
        now = datetime.now()
        rows = list(self.conn.execute("SELECT id, title, dt_iso FROM events ORDER BY dt_iso ASC"))
        for event_id, title, dt_iso in rows:
            event_dt = datetime.fromisoformat(dt_iso)
            if event_dt <= now:
                self.trigger_alarm(title, event_dt)
                self.conn.execute("DELETE FROM events WHERE id=?", (event_id,))
                self.conn.commit()
                self.load_events()
                break

    def trigger_alarm(self, title: str, event_dt: datetime):
        msg = f"{event_dt.strftime('%Y-%m-%d %H:%M')} — {title}"

        if self.alarm_sound:
            self.alarm_sound.stop()
            self.alarm_sound.play()

        if notification:
            try:
                notification.notify(title="Planner alarm", message=msg, timeout=10)
            except Exception:
                pass

        print("[ALARM]", msg)

    def on_stop(self):
        try:
            self.conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    PlannerApp().run()
