import sqlite3
import argparse
import re

data = {"meals": ("breakfast", "brunch", "lunch", "supper"),
        "ingredients": ("milk", "cacao", "strawberry", "blue", "black", "sugar"),
        "measures": ("ml", "g", "l", "cup", "tbsp", "tsp", "dsp", "")}

set_ingredients, set_measures = "|".join(data["ingredients"]), "|".join(data["measures"])
pattern = re.compile(f"(?P<quantity>[0-9]+)\s+((?P<measure>{set_measures})\s+)?(?P<ingredient>{set_ingredients})")


create_meals = "CREATE TABLE IF NOT EXISTS meals (meal_id INTEGER PRIMARY KEY, " \
               "meal_name VARCHAR(30) NOT NULL UNIQUE);"

create_ingredients = "CREATE TABLE IF NOT EXISTS ingredients (ingredient_id INTEGER PRIMARY KEY, " \
                     "ingredient_name VARCHAR(30) NOT NULL UNIQUE);"

create_measures = "CREATE TABLE IF NOT EXISTS measures (measure_id INTEGER PRIMARY KEY, " \
                  "measure_name VARCHAR(30) UNIQUE);"

create_recipes = "CREATE TABLE IF NOT EXISTS recipes (recipe_id INTEGER PRIMARY KEY, " \
                 "recipe_name VARCHAR(30) NOT NULL, recipe_description VARCHAR(30));"

create_serve = "CREATE TABLE IF NOT EXISTS serve (serve_id INT PRIMARY KEY, " \
               "recipe_id INTEGER NOT NULL, " \
               "meal_id INTEGER NOT NULL, " \
               "FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id), " \
               "FOREIGN KEY (meal_id) REFERENCES meals(meal_id));"

create_quantity = "CREATE TABLE IF NOT EXISTS quantity (quantity_id INT PRIMARY KEY, " \
                  "measure_id INTEGER NOT NULL, " \
                  "ingredient_id INT NOT NULL, " \
                  "quantity INTEGER NOT NULL, " \
                  "recipe_id INTEGER NOT NULL," \
                  "FOREIGN KEY (measure_id) REFERENCES measures(measure_id)," \
                  "FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)," \
                  "FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id));"

tables = [create_meals, create_ingredients, create_measures, create_recipes, create_serve, create_quantity]


def set_args():
    parser = argparse.ArgumentParser(description="This program prints recipes "
                                                 "that can be made from the ingredients you provide.")
    parser.add_argument("db_name")
    parser.add_argument("--ingredients")
    parser.add_argument("--meals")
    return parser.parse_args()


def check_args():
    if not args.ingredients and not args.meals:
        print("Pass the empty recipe name to exit.")
        populate_tables()
        populate_recipe_serve()
        return None

    elif args.ingredients and not args.meals:
        ingredients = args.ingredients.split(",")
        recipes = recipe_by_single_arg(ingredients, "ingredients")
        print("Recipes selected for you:", recipes)

    elif args.meals and not args.ingredients:
        meal_times = args.meals.split(",")
        recipes = recipe_by_single_arg(meal_times, "meals")
        print("Recipes selected for you:", recipes)

    else:
        ingredients = args.ingredients.split(",")
        meals = args.meals.split(",")
        recipes = recipes_by_both(ingredients, meals)
        if recipes:
            print("Recipes selected for you:", recipes)
        else:
            print("no such recipes")

    connection.commit()


def create_tables():
    cur.execute("PRAGMA foreign_keys = ON;")
    for table in tables:
        cur.execute(table)
        connection.commit()


def populate_tables():
    for key in data:
        for count, elem in enumerate(data[key], start=1):
            cur.execute(f"INSERT INTO {key} VALUES (?, ?);", (count, elem))
    connection.commit()


def populate_recipe_serve():
    while True:
        recipe_name = input("Recipe name: ")
        if recipe_name == "":
            break

        recipe_description = input("Recipe description: ")
        meal_index = input("1) breakfast 2) brunch 3) lunch 4) supper\nWhen the dish can be served: ")
        recipe_id = cur.execute("INSERT INTO recipes (recipe_name, recipe_description) "
                                "VALUES (?, ?);", (recipe_name, recipe_description)).lastrowid

        for meal_id in meal_index.split():
            cur.execute("INSERT INTO serve (recipe_id, meal_id) "
                        "VALUES (?, ?);", (recipe_id, meal_id))

        populate_quantity(recipe_id)
        connection.commit()


def populate_quantity(recipe_id):
    while True:
        quantity_measure_ingredient = input("Input quantity of ingredient <press enter to stop>: ")
        if quantity_measure_ingredient == "":
            break

        match = re.search(pattern, quantity_measure_ingredient)

        if match is None:
            print("Quantity or measure is inconclusive!")
            continue

        quantity = match.group("quantity")
        ingredient = match.group("ingredient")
        measures = match.group("measure") if match.group("measure") else ""

        measure_id = data["measures"].index(measures) + 1
        ingredient_id = data["ingredients"].index(ingredient) + 1
        cur.execute("INSERT INTO quantity (measure_id, ingredient_id, quantity, recipe_id) "
                    "VALUES (?, ?, ?, ?);", (measure_id, ingredient_id, quantity, recipe_id))


def recipe_by_single_arg(arg_list, dict_key):
    count_items = len(arg_list)
    item_ids = [str(data[dict_key].index(item) + 1) for item in arg_list]
    item_ids = f"({','.join(item_ids)})"

    if dict_key == "meals":
        response = cur.execute(f"SELECT recipe_name FROM recipes "
                               f"WHERE recipe_id IN (SELECT recipe_id FROM serve WHERE meal_id IN {item_ids}"
                               f"GROUP BY recipe_id HAVING COUNT(*) = {count_items});")
        recipe_list = recipe_output(response)
        return recipe_list
    else:
        response = cur.execute(f"SELECT recipe_name FROM recipes "
                               f"WHERE recipe_id IN (SELECT recipe_id FROM quantity WHERE ingredient_id IN {item_ids}"
                               f"GROUP BY recipe_id HAVING COUNT(*) = {count_items});")
        recipe_list = recipe_output(response)
        return recipe_list


def recipes_by_both(ingredients_args, meals_args):
    count_ingredients = len(ingredients_args)
    count_meals = len(meals_args)

    ingredients_ids = []
    for name in ingredients_args:
        ing_id = cur.execute(f"SELECT ingredient_id FROM ingredients "
                             f"WHERE ingredient_name = '{name}';").fetchone()
        if ing_id:
            ingredients_ids.extend(str(ing_id[0]))

    ing_ids = f"({','.join(ingredients_ids)})"

    meal_ids = [str(data["meals"].index(item) + 1) for item in meals_args]
    meal_ids = f"({','.join(meal_ids)})"

    response = cur.execute(f"SELECT recipe_name FROM recipes "
                           f"JOIN serve ON serve.meal_id IN {meal_ids}"
                           f"WHERE recipes.recipe_id IN (SELECT quantity.recipe_id FROM quantity WHERE ingredient_id IN {ing_ids}"
                           f"GROUP BY recipe_id HAVING COUNT(*) = {count_ingredients})"
                           f"GROUP BY recipes.recipe_id;")

    recipe_list = recipe_output(response)
    return recipe_list


def recipe_output(sql_response):
    recipes = ["".join(string) for string in sql_response.fetchall()]
    return ", ".join(recipes)


if __name__ == "__main__":
    args = set_args()
    connection = sqlite3.connect(args.db_name)
    cur = connection.cursor()

    create_tables()
    check_args()
    connection.close()
