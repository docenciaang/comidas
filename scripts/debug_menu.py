from app.models.db import get_session
from app.core.menu_manager import MenuManager

s = get_session()
m = MenuManager(s)
ws = m.get_current_week_start()
print("WEEK_START:", ws)
print('\nlist_week_menu:')
for e in m.list_week_menu(ws):
    print({"id": e.id, "day": e.day, "recipe_name": e.recipe_name, "meal_type": e.meal_type})
print('\nas_week_table:')
wt = m.as_week_table(ws)
for k in wt:
    print(k, [(e.recipe_name, e.meal_type, type(e.meal_type)) for e in wt[k]])

s.close()
