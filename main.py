import customtkinter as ctk
import tkinter as tk
import math
import random

SCALE = 0.1

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class GeoLogisticsPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GeoLogistics Pro - Учет покрытия")
        self.geometry("1200x850")

        self.nodes = []
        self.adj = {}
        self.mode = "БАЗА"
        self.selected_start = None

        self.setup_ui()

    def setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=300)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="ИНСТРУМЕНТЫ", font=("Arial", 16, "bold")).pack(pady=10)
        self.btn_node = self.create_btn("📍 Поставить базу", lambda: self.set_mode("БАЗА"))
        self.btn_edge = self.create_btn("🛣 Проложить дорогу", lambda: self.set_mode("ДОРОГА"))

        # --- НОВЫЙ БЛОК: Выбор типа дороги ---
        ctk.CTkLabel(self.sidebar, text="ТИП ПОКРЫТИЯ:", font=("Arial", 12)).pack(pady=(15, 0))
        self.road_type_var = ctk.StringVar(value="Сухая дорога (x1.0)")
        self.road_menu = ctk.CTkOptionMenu(
            self.sidebar,
            variable=self.road_type_var,
            values=["Сухая дорога (x1.0)", "Грунтовка (x1.5)", "Грязь/Болото (x2.5)"],
            fg_color="#444"
        )
        self.road_menu.pack(pady=5, padx=10, fill="x")
        # -------------------------------------

        ctk.CTkLabel(self.sidebar, text="ВЫЧИСЛЕНИЯ", font=("Arial", 16, "bold")).pack(pady=(20, 5))
        self.btn_dijkstra = self.create_btn("🏁 Путь А -> Б (Дейкстра)", lambda: self.set_mode("ДЕЙКСТРА"))
        self.btn_aco = self.create_btn("🐜 Оптимизация (ACO)", self.run_aco_tour, "green")

        self.btn_clear_path = self.create_btn("🧹 Очистить маршрут", self.clear_visuals, "#444")
        self.btn_clear = self.create_btn("🗑 Сбросить всё", self.clear_all, "#7b1f1f")

        self.log_box = ctk.CTkTextbox(self.sidebar, height=250, font=("Consolas", 12))
        self.log_box.pack(pady=20, padx=10, fill="x")
        self.log("Готов к работе.\nВыберите тип покрытия перед прокладкой дороги.")

        self.canvas = tk.Canvas(self, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

    def create_btn(self, text, cmd, color=None):
        btn = ctk.CTkButton(self.sidebar, text=text, command=cmd, fg_color=color)
        btn.pack(pady=5, padx=10, fill="x")
        return btn

    def set_mode(self, mode):
        self.clear_visuals()
        self.mode = mode
        self.selected_start = None
        self.log(f"Режим: {mode}")

    def log(self, text):
        self.log_box.delete("0.0", "end")
        self.log_box.insert("0.0", text)

    def clear_visuals(self):
        self.canvas.delete("result_path")
        self.canvas.delete("nav")
        self.canvas.delete("temp_select")
        self.selected_start = None

    def clear_all(self):
        self.nodes, self.adj = [], {}
        self.canvas.delete("all")
        self.log("Все данные удалены.")

    def on_click(self, event):
        x, y = event.x, event.y
        if self.mode == "БАЗА":
            idx = len(self.nodes)
            self.nodes.append((x, y))
            self.adj[idx] = {}
            self.draw_node(x, y, idx)
        elif self.mode in ["ДОРОГА", "ДЕЙКСТРА"]:
            target = self.get_node_at(x, y)
            if target is not None:
                if self.selected_start is None:
                    self.selected_start = target
                    self.canvas.create_oval(self.nodes[target][0] - 15, self.nodes[target][1] - 15,
                                            self.nodes[target][0] + 15, self.nodes[target][1] + 15,
                                            outline="yellow", width=3, tags="temp_select")
                else:
                    if self.mode == "ДОРОГА":
                        self.ask_and_add_edge(self.selected_start, target)
                    else:
                        self.run_dijkstra(self.selected_start, target)
                    self.selected_start = None
                    self.canvas.delete("temp_select")

    def ask_and_add_edge(self, u, v):
        if u == v: return

        auto_dist = round(math.hypot(self.nodes[u][0] - self.nodes[v][0], self.nodes[u][1] - self.nodes[v][1]) * SCALE,
                          2)
        dialog = ctk.CTkInputDialog(text=f"Введите длину дороги между {u} и {v} (км):", title="Параметры участка")
        input_val = dialog.get_input()

        try:
            if input_val is None or input_val.strip() == "":
                base_dist = auto_dist
            else:
                base_dist = float(input_val.replace(',', '.'))

            # Логика коэффициентов покрытия
            road_choice = self.road_type_var.get()
            if "Сухая" in road_choice:
                coef, color, type_name = 1.0, "#888888", "Сухо"
            elif "Грунтовка" in road_choice:
                coef, color, type_name = 1.5, "#d97706", "Грунт"
            else:
                coef, color, type_name = 2.5, "#7c3aed", "Грязь"

            # Эффективная стоимость пути (которую видят алгоритмы)
            final_cost = round(base_dist * coef, 2)

            self.adj[u][v] = final_cost
            self.adj[v][u] = final_cost

            x1, y1 = self.nodes[u]
            x2, y2 = self.nodes[v]
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=3 if coef > 1 else 2, tags="bg_edge")

            # Подпись на холсте (показываем реальные КМ и тип покрытия)
            label_text = f"{base_dist}км ({type_name})"
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2 - 12, text=label_text, fill=color,
                                    font=("Arial", 9, "bold"))
            self.canvas.tag_lower("bg_edge")

            self.log(f"Добавлена дорога: \n{u} <-> {v}\nФактическая длина: \n{base_dist} км\nЭффективная длина: \n{final_cost} км")

        except ValueError:
            self.log("ОШИБКА: Введите числовое значение!")

    def draw_node(self, x, y, idx):
        self.canvas.create_oval(x - 12, y - 12, x + 12, y + 12, fill="#007acc", outline="white", tags=f"node_{idx}")
        self.canvas.create_text(x, y, text=str(idx), fill="white", font=("Arial", 10, "bold"))

    def get_node_at(self, x, y):
        for i, (nx, ny) in enumerate(self.nodes):
            if math.hypot(nx - x, ny - y) < 20: return i
        return None

    def run_dijkstra(self, start, end):
        self.clear_visuals()
        distances = {i: float('inf') for i in range(len(self.nodes))}
        previous = {i: None for i in range(len(self.nodes))}
        distances[start] = 0
        nodes_list = list(range(len(self.nodes)))

        while nodes_list:
            current = min(nodes_list, key=lambda n: distances[n])
            nodes_list.remove(current)
            if distances[current] == float('inf'): break

            for neighbor, weight_cost in self.adj[current].items():
                alt = distances[current] + weight_cost
                if alt < distances[neighbor]:
                    distances[neighbor] = alt
                    previous[neighbor] = current

        path = []
        curr = end
        while curr is not None:
            path.append(curr)
            curr = previous[curr]
        path.reverse()

        if path and path[0] == start:
            self.visualize_path(path, distances[end], "Кратчайший путь (Дейкстра)")
        else:
            self.log("ОШИБКА: Базы не связаны!")

    def run_aco_tour(self):
        self.clear_visuals()
        n = len(self.nodes)
        if n < 3:
            self.log("Нужно минимум 3 базы.")
            return

        for i in range(n):
            if not self.adj[i]:
                self.log(f"База {i} изолирована!")
                return

        best_path, min_dist = None, float('inf')

        for _ in range(200):
            path = [0]
            curr = 0
            visited = {0}
            total_d = 0
            while len(visited) < n:
                neighbors = [nb for nb in self.adj[curr].keys() if nb not in visited]
                if not neighbors: break
                nxt = random.choice(neighbors)
                total_d += self.adj[curr][nxt]
                path.append(nxt)
                visited.add(nxt)
                curr = nxt

            if len(path) == n and 0 in self.adj[path[-1]]:
                total_d += self.adj[path[-1]][0]
                path.append(0)
                if total_d < min_dist:
                    min_dist = total_d
                    best_path = path

        if best_path:
            self.visualize_path(best_path, min_dist, "ACO: Оптимальный обход")
        else:
            self.log("Маршрут не найден.")

    def visualize_path(self, path, dist, title):
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            x1, y1 = self.nodes[u]
            x2, y2 = self.nodes[v]
            self.canvas.create_line(x1, y1, x2, y2, fill="#22c55e", width=4, tags="result_path")
            self.canvas.create_text(x1 + 15, y1 + 15, text=f"[{i + 1}]", fill="#22c55e", font=("Arial", 12, "bold"),
                                    tags="nav")

        self.log(f"{title}\nЭффективная дистанция: \n{dist:.2f} км\nЦепочка: \n{' -> '.join(map(str, path))}")


if __name__ == "__main__":
    GeoLogisticsPro().mainloop()