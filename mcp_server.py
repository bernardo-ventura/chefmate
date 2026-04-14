"""
MCP Server para Planejador de Refeições usando FastMCP.
Expõe: tools (operações CRUD), resources (documentação), prompts (templates).

Run with: python mcp_server.py
"""

from fastmcp import FastMCP
from src.database import get_session_context
from src.models import MealCreate, IngredientCreate
from src.core import (
    # Meal operations
    create_meal,
    get_meals,
    get_meal_with_ingredients,
    search_meals_by_name,
    search_meals_by_ingredient,
    delete_meal,
    get_meal_stats,
    # Ingredient operations
    create_ingredient,
    get_ingredients,
    delete_ingredient,
    # Special operations (requirements)
    add_meal_calories_string,
    add_meal_calories_float,
    # Exceptions
    MealHasIngredientsError,
    InvalidQuantityError,
)

# Initialize MCP server
mcp = FastMCP(name="MealPlannerServer")


# ============================================
# TOOLS - MEAL OPERATIONS
# ============================================

@mcp.tool()
def create_new_meal(name: str, description: str, calories: float, is_healthy: bool = True) -> str:
    """
    Create a new meal in the database.
    
    Args:
        name: Name of the meal (e.g., "Salada Caesar")
        description: Description of the meal
        calories: Total calories (must be >= 0)
        is_healthy: Whether the meal is considered healthy (default: true)
    
    Returns:
        Success message with meal ID
    """
    try:
        with get_session_context() as session:
            meal_data = MealCreate(
                name=name,
                description=description,
                calories=calories,
                is_healthy=is_healthy
            )
            meal = create_meal(session, meal_data)
            return f"✓ Meal created successfully! ID: {meal.id}, Name: {meal.name}, Calories: {meal.calories}"
    except Exception as e:
        return f"✗ Error creating meal: {str(e)}"


@mcp.tool()
def list_all_meals(is_healthy: bool = None, limit: int = 20) -> str:
    """
    List all meals in the database.
    
    Args:
        is_healthy: Filter by healthy status (true/false). If not provided, shows all meals.
        limit: Maximum number of meals to return (default: 20)
    
    Returns:
        Formatted list of meals with their details
    """
    try:
        with get_session_context() as session:
            meals = get_meals(session, limit=limit, is_healthy=is_healthy)
            
            if not meals:
                return "No meals found."
            
            result = []
            filter_text = f" (filtered: is_healthy={is_healthy})" if is_healthy is not None else ""
            result.append(f"📋 Found {len(meals)} meal(s){filter_text}:\n")
            
            for meal in meals:
                health_icon = "✓" if meal.is_healthy else "✗"
                result.append(
                    f"  {health_icon} ID {meal.id}: {meal.name}\n"
                    f"     Calories: {meal.calories} | Healthy: {meal.is_healthy}\n"
                    f"     Description: {meal.description or 'N/A'}\n"
                )
            
            return "".join(result)
    except Exception as e:
        return f"✗ Error listing meals: {str(e)}"


@mcp.tool()
def get_meal_details(meal_id: int) -> str:
    """
    Get detailed information about a specific meal, including its ingredients.
    
    Args:
        meal_id: The ID of the meal to retrieve
    
    Returns:
        Detailed meal information with ingredients list
    """
    try:
        with get_session_context() as session:
            meal = get_meal_with_ingredients(session, meal_id)
            
            if not meal:
                return f"✗ Meal with ID {meal_id} not found."
            
            result = [
                f"🍽️ Meal Details:\n",
                f"  ID: {meal.id}\n",
                f"  Name: {meal.name}\n",
                f"  Description: {meal.description or 'N/A'}\n",
                f"  Calories: {meal.calories}\n",
                f"  Healthy: {'Yes ✓' if meal.is_healthy else 'No ✗'}\n",
                f"\n  Ingredients ({len(meal.ingredients)}):\n"
            ]
            
            if meal.ingredients:
                for ing in meal.ingredients:
                    result.append(f"    • {ing.quantity} of {ing.name}\n")
            else:
                result.append("    (No ingredients yet)\n")
            
            return "".join(result)
    except Exception as e:
        return f"✗ Error getting meal details: {str(e)}"


@mcp.tool()
def search_meals(query: str, search_by: str = "name") -> str:
    """
    Search for meals by name or ingredient.
    
    Args:
        query: The search term (e.g., "salad", "chicken")
        search_by: Search type - "name" or "ingredient" (default: "name")
    
    Returns:
        List of matching meals
    """
    try:
        with get_session_context() as session:
            if search_by == "ingredient":
                meals = search_meals_by_ingredient(session, query)
                search_desc = f"containing ingredient '{query}'"
            else:
                meals = search_meals_by_name(session, query)
                search_desc = f"with name matching '{query}'"
            
            if not meals:
                return f"No meals found {search_desc}."
            
            result = [f"🔍 Found {len(meals)} meal(s) {search_desc}:\n\n"]
            
            for meal in meals:
                health_icon = "✓" if meal.is_healthy else "✗"
                result.append(
                    f"  {health_icon} {meal.name} (ID: {meal.id})\n"
                    f"     {meal.calories} calories | {meal.description or 'No description'}\n"
                )
            
            return "".join(result)
    except Exception as e:
        return f"✗ Error searching meals: {str(e)}"


@mcp.tool()
def remove_meal(meal_id: int) -> str:
    """
    Delete a meal from the database.
    
    ⚠️ SPECIAL REQUIREMENT: Raises exception if meal has ingredients.
    You must delete all ingredients first before deleting the meal.
    
    Args:
        meal_id: The ID of the meal to delete
    
    Returns:
        Success or error message
    """
    try:
        with get_session_context() as session:
            success = delete_meal(session, meal_id)
            
            if success:
                return f"✓ Meal ID {meal_id} deleted successfully!"
            else:
                return f"✗ Meal with ID {meal_id} not found."
    
    except MealHasIngredientsError as e:
        return f"✗ Cannot delete meal: {str(e)}\n\nPlease delete the ingredients first using remove_ingredient."


# ============================================
# TOOLS - INGREDIENT OPERATIONS
# ============================================

@mcp.tool()
def add_ingredient(name: str, quantity: str, meal_id: int) -> str:
    """
    Add an ingredient to a meal.
    
    ⚠️ SPECIAL REQUIREMENT: Returns error if quantity format is invalid.
    Quantity must be in format: "number + unit" (e.g., "200g", "1 xícara").
    
    Args:
        name: Ingredient name (e.g., "Chicken breast", "Rice")
        quantity: Amount with unit (e.g., "200g", "1.5 kg", "2 cups")
        meal_id: ID of the meal to add ingredient to
    
    Returns:
        Success or error message
    """
    try:
        with get_session_context() as session:
            ingredient_data = IngredientCreate(
                name=name,
                quantity=quantity,
                meal_id=meal_id
            )
            ingredient = create_ingredient(session, ingredient_data)
            return f"✓ Ingredient added! ID: {ingredient.id}, {ingredient.quantity} of {ingredient.name} added to meal {meal_id}"
    
    except InvalidQuantityError as e:
        return f"✗ Invalid quantity format: {str(e)}\n\nValid examples: '200g', '1.5 kg', '2 xícaras'"
    
    except ValueError as e:
        return f"✗ Error: {str(e)}"
    
    except Exception as e:
        return f"✗ Unexpected error: {str(e)}"


@mcp.tool()
def list_ingredients(meal_id: int = None) -> str:
    """
    List all ingredients, optionally filtered by meal.
    
    Args:
        meal_id: Optional meal ID to filter ingredients (default: shows all)
    
    Returns:
        List of ingredients
    """
    try:
        with get_session_context() as session:
            ingredients = get_ingredients(session, meal_id=meal_id)
            
            if not ingredients:
                filter_text = f" for meal ID {meal_id}" if meal_id else ""
                return f"No ingredients found{filter_text}."
            
            result = []
            filter_text = f" for meal ID {meal_id}" if meal_id else ""
            result.append(f"📦 Found {len(ingredients)} ingredient(s){filter_text}:\n\n")
            
            for ing in ingredients:
                result.append(
                    f"  • {ing.name}\n"
                    f"    Quantity: {ing.quantity}\n"
                    f"    Meal ID: {ing.meal_id} | Ingredient ID: {ing.id}\n"
                )
            
            return "".join(result)
    except Exception as e:
        return f"✗ Error listing ingredients: {str(e)}"


@mcp.tool()
def remove_ingredient(ingredient_id: int) -> str:
    """
    Remove an ingredient from a meal.
    
    Args:
        ingredient_id: The ID of the ingredient to remove
    
    Returns:
        Success or error message
    """
    try:
        with get_session_context() as session:
            success = delete_ingredient(session, ingredient_id)
            
            if success:
                return f"✓ Ingredient ID {ingredient_id} removed successfully!"
            else:
                return f"✗ Ingredient with ID {ingredient_id} not found."
    except Exception as e:
        return f"✗ Error removing ingredient: {str(e)}"


# ============================================
# TOOLS - SPECIAL OPERATIONS (Requirements)
# ============================================

@mcp.tool()
def add_calories_as_string(meal_id: int, calories_to_add: str) -> str:
    """
    Add calories to a meal (accepts calories as STRING).
    
    ⚠️ SPECIAL REQUIREMENT: Similar operation #1 - parameter is a string.
    
    Args:
        meal_id: The meal ID
        calories_to_add: Calories to add as STRING (e.g., "50.5", "100")
    
    Returns:
        Updated meal information
    """
    try:
        with get_session_context() as session:
            meal = add_meal_calories_string(session, meal_id, calories_to_add)
            return f"✓ Added {calories_to_add} calories (as string) to meal '{meal.name}'. New total: {meal.calories} calories"
    except ValueError as e:
        return f"✗ Error: {str(e)}"
    except Exception as e:
        return f"✗ Unexpected error: {str(e)}"


@mcp.tool()
def add_calories_as_float(meal_id: int, calories_to_add: float) -> str:
    """
    Add calories to a meal (accepts calories as FLOAT/NUMBER).
    
    ⚠️ SPECIAL REQUIREMENT: Similar operation #2 - parameter is a float.
    
    Args:
        meal_id: The meal ID
        calories_to_add: Calories to add as NUMBER (e.g., 50.5, 100)
    
    Returns:
        Updated meal information
    """
    try:
        with get_session_context() as session:
            meal = add_meal_calories_float(session, meal_id, calories_to_add)
            return f"✓ Added {calories_to_add} calories (as float) to meal '{meal.name}'. New total: {meal.calories} calories"
    except ValueError as e:
        return f"✗ Error: {str(e)}"
    except Exception as e:
        return f"✗ Unexpected error: {str(e)}"


# ============================================
# TOOLS - UTILITY
# ============================================

@mcp.tool()
def get_database_statistics() -> str:
    """
    Get statistics about the meal database.
    
    Returns:
        Summary of database contents
    """
    try:
        with get_session_context() as session:
            stats = get_meal_stats(session)
            
            return (
                f"📊 Database Statistics:\n\n"
                f"  Total Meals: {stats['total_meals']}\n"
                f"  Total Ingredients: {stats['total_ingredients']}\n"
                f"  Healthy Meals: {stats['healthy_meals']}\n"
                f"  Unhealthy Meals: {stats['unhealthy_meals']}\n"
            )
    except Exception as e:
        return f"✗ Error getting stats: {str(e)}"


#============================================
# RESOURCES
# ============================================

@mcp.resource("meal://db-schema")
def get_database_schema() -> str:
    """Returns the database schema documentation."""
    with open("resources/db_schema.txt", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("meal://nutrition-guide")
def get_nutrition_guide() -> str:
    """Returns the nutrition guide with meal planning tips."""
    with open("resources/nutrition_guide.txt", "r", encoding="utf-8") as f:
        return f.read()


# ============================================
# PROMPTS
# ============================================

@mcp.prompt()
def meal_planner_assistant(user_name: str = "User") -> str:
    """A system prompt that turns the LLM into a meal planning and nutrition assistant."""
    return (
        f"You are an expert meal planning and nutrition assistant helping {user_name}. "
        f"You have access to a comprehensive meal database with nutritional information.\n\n"
        
        f"Your capabilities:\n"
        f"• Create and manage meals with calorie tracking\n"
        f"• Add ingredients to meals with precise quantities\n"
        f"• Search meals by name or ingredient\n"
        f"• Provide nutrition guidance based on the nutrition guide\n"
        f"• Track calories and suggest healthy alternatives\n\n"
        
        f"Important rules:\n"
        f"• A healthy meal should be between 300-600 calories\n"
        f"• Always validate quantity format (e.g., '200g', '1 xícara')\n"
        f"• Cannot delete meals that have ingredients (must remove ingredients first)\n"
        f"• Be encouraging and supportive about healthy eating habits\n\n"
        
        f"When helping users:\n"
        f"1. Ask about their dietary goals and preferences\n"
        f"2. Suggest balanced meals with protein, carbs, and vegetables\n"
        f"3. Calculate total calories for meal plans\n"
        f"4. Provide alternatives for unhealthy choices\n"
        f"5. Use the nutrition guide for accurate calorie information\n\n"
        
        f"Remember: Your advice is informational only and not a substitute for "
        f"professional medical or nutritional guidance. Always encourage users to "
        f"consult with healthcare professionals for personalized advice."
    )


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    print("🍽️  Starting Meal Planner MCP Server...")
    print("📡 Running on: http://127.0.0.1:8002/sse")
    print("🔧 Tools: 13 meal & ingredient operations")
    print("📚 Resources: 2 (db-schema, nutrition-guide)")
    print("💡 Prompts: 1 (meal_planner_assistant)")
    print("\nPress Ctrl+C to stop\n")
    
    mcp.run(transport="sse", host="127.0.0.1", port=8002)
"""
MCP Server using FastMCP
Exposes: one tool, one resource, one prompt
Run with: python mcp_server.py
"""

from fastmcp import FastMCP

mcp = FastMCP(name="SimpleAssistantServer")


# ─── TOOL ────────────────────────────────────────────────────────────────────
@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> str:
    """Calculate the Body Mass Index (BMI) given weight in kg and height in meters."""
    if height_m <= 0:
        return "Error: height must be greater than 0."
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal weight"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    return f"BMI: {bmi:.2f} — Category: {category}"


# ─── RESOURCE ────────────────────────────────────────────────────────────────
@mcp.resource("info://app")
def get_app_info() -> str:
    """Returns general information about this MCP server / app."""
    return (
        "SimpleAssistantServer v1.0\n"
        "Purpose: Demo MCP server with a tool, resource, and prompt.\n"
        "Available tool: calculate_bmi\n"
        "Built with: FastMCP + Python\n"
    )


# ─── PROMPT ──────────────────────────────────────────────────────────────────
@mcp.prompt()
def health_advisor_prompt(user_name: str = "User") -> str:
    """A system prompt that turns the LLM into a friendly health advisor."""
    return (
        f"You are a friendly and knowledgeable health advisor. "
        f"You are currently helping {user_name}. "
        "You can calculate BMI using the `calculate_bmi` tool. "
        "Always remind users that your advice is informational only and not a substitute "
        "for professional medical guidance. Keep your tone warm and encouraging."
    )


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8002)
