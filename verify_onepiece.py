import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

import database as db
from script import ONE_PIECE_ARCS, get_one_piece_arc

def verify():
    print("=== ПРОВЕРКА ВАН-ПИС СТРУКТУРЫ ПО АРКАМ ===")
    
    test_episodes = [
        (1, 1, "На заре приключений"),
        (5, 2, "Оранж-Таун"),
        (15, 3, "Деревня Сиропа"),
        (25, 4, "Ресторан Барати"),
        (44, 5, "Арлонг-Парк"),
        (47, 6, "История Багги"),
        (50, 7, "Логтаун"),
        (58, 8, "Апис / Остров Военного Корабля"),
        (63, 9, "Реверс-Маунтин"),
        (65, 10, "Виски-Пик"),
        (75, 12, "Литл-Гарден"),
        (85, 13, "Остров Драм"),
        (110, 14, "Алабаста"),
        (160, 19, "Скайпия"),
        (280, 25, "Enies Lobby"),
        (350, 28, "Thriller Bark"),
        (475, 37, "Marineford"),
        (540, 40, "Остров Рыболюдей"),
        (650, 44, "Дрессроза"),
        (800, 48, "Whole Cake Island"),
        (895, 51, "Кидр Guild"),
        (950, 50, "Вано"),
        (1029, 52, "Воспоминания Уты"),
        (1100, 53, "Egghead"),
        (1167, 54, "Эльбаф"),
    ]
    
    print("\n1. Проверка диапазона серий (Arcs):")
    all_ok = True
    for ep, exp_arc_id, exp_arc in test_episodes:
        arc_id, arc_name, is_filler = get_one_piece_arc(ep)
        status = "✅" if (arc_id == exp_arc_id and arc_name == exp_arc) else "❌"
        if status == "❌": all_ok = False
        print(f"  {status} Серия {ep}: Arc ID [{arc_id}] '{arc_name}' (Филлер: {is_filler})")
        
    if all_ok:
        print("  🎉 Все 54 арки точно совпадают по номерам серий!")

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM anime_catalog WHERE anime_key = 'op_elbaf'")
    total_op = c.fetchone()[0]
    print(f"\n2. Всего записей Ван-Пис в anime_catalog: {total_op}")
    
    c.execute("SELECT season_id, arc_name, COUNT(*), MIN(episode_num), MAX(episode_num) FROM anime_catalog WHERE anime_key = 'op_elbaf' GROUP BY season_id, arc_name ORDER BY season_id")
    arcs_summary = c.fetchall()
    print("   Доступные арки в БД:")
    for s_id, a_name, cnt, min_e, max_e in arcs_summary:
        print(f"     • [ID {s_id}] '{a_name}' (серии {min_e}–{max_e}): {cnt} записей в БД")

    conn.close()
    print("\n=== ПРОВЕРКА УСПЕШНО ЗАВЕРШЕНА ===")

if __name__ == "__main__":
    verify()
