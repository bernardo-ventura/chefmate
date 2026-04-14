"""
REST API para o Planejador de Refeições.
Expõe operações CRUD para Meal e Ingredient via HTTP.

Run with: uvicorn src.rest_api:app --reload --port 8001
API Docs: http://localhost:8001/docs
"""
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import List, Optional

from src.database import create_db_and_tables, get_session
from src.models import (
    Meal, MealCreate, MealRead, MealReadWithIngredients,
    Ingredient, IngredientCreate, IngredientRead
)
from src.core import (
    # Meal operations
    create_meal,
    get_meal,
    get_meals,
    search_meals_by_name,
    search_meals_by_ingredient,
    update_meal,
    delete_meal,
    get_meal_with_ingredients,
    get_meal_stats,
    # Ingredient operations
    create_ingredient,
    get_ingredient,
    get_ingredients,
    update_ingredient,
    delete_ingredient,
    # Special operations
    add_meal_calories_string,
    add_meal_calories_float,
    # Exceptions
    MealHasIngredientsError,
    InvalidQuantityError,
)

# ============================================
# APP SETUP
# ============================================

app = FastAPI(
    title="Meal Planner API",
    description="REST API for managing meals and ingredients with nutritional information",
    version="1.0.0",
)

# CORS - permite acesso de outras origens
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar database
create_db_and_tables()


# ============================================
# MEAL ENDPOINTS
# ============================================

@app.post("/meals", response_model=MealRead, status_code=201, tags=["Meals"])
def create_meal_endpoint(
    meal: MealCreate,
    session: Session = Depends(get_session)
):
    """Create a new meal."""
    db_meal = create_meal(session, meal)
    return db_meal


@app.get("/meals", response_model=List[MealRead], tags=["Meals"])
def list_meals_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_healthy: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    """
    List meals with optional filters.
    - skip: Number of meals to skip (pagination)
    - limit: Maximum number of meals to return
    - is_healthy: Filter by healthy status (true/false)
    """
    meals = get_meals(session, skip=skip, limit=limit, is_healthy=is_healthy)
    return meals


@app.get("/meals/{meal_id}", response_model=MealReadWithIngredients, tags=["Meals"])
def get_meal_endpoint(
    meal_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific meal by ID, including its ingredients."""
    meal = get_meal_with_ingredients(session, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail=f"Meal with id={meal_id} not found")
    return meal


@app.get("/meals/search/by-name", response_model=List[MealRead], tags=["Meals"])
def search_meals_by_name_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    session: Session = Depends(get_session)
):
    """Search meals by name (case-insensitive)."""
    meals = search_meals_by_name(session, q)
    return meals


@app.get("/meals/search/by-ingredient", response_model=List[MealRead], tags=["Meals"])
def search_meals_by_ingredient_endpoint(
    ingredient: str = Query(..., min_length=1),
    session: Session = Depends(get_session)
):
    """Search meals that contain a specific ingredient."""
    meals = search_meals_by_ingredient(session, ingredient)
    return meals


@app.put("/meals/{meal_id}", response_model=MealRead, tags=["Meals"])
def update_meal_endpoint(
    meal_id: int,
    meal_data: MealCreate,
    session: Session = Depends(get_session)
):
    """Update an existing meal."""
    updated_meal = update_meal(session, meal_id, meal_data.model_dump())
    if not updated_meal:
        raise HTTPException(status_code=404, detail=f"Meal with id={meal_id} not found")
    return updated_meal


@app.delete("/meals/{meal_id}", status_code=204, tags=["Meals"])
def delete_meal_endpoint(
    meal_id: int,
    session: Session = Depends(get_session)
):
    """
    Delete a meal.
    
    ⚠️ SPECIAL REQUIREMENT: Raises exception if meal has ingredients.
    """
    try:
        success = delete_meal(session, meal_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Meal with id={meal_id} not found")
    except MealHasIngredientsError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# INGREDIENT ENDPOINTS
# ============================================

@app.post("/ingredients", response_model=IngredientRead, status_code=201, tags=["Ingredients"])
def create_ingredient_endpoint(
    ingredient: IngredientCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new ingredient.
    
    ⚠️ SPECIAL REQUIREMENT: Returns error if quantity format is invalid.
    """
    try:
        db_ingredient = create_ingredient(session, ingredient)
        return db_ingredient
    except InvalidQuantityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/ingredients", response_model=List[IngredientRead], tags=["Ingredients"])
def list_ingredients_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    meal_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """
    List ingredients with optional filters.
    - meal_id: Filter by meal ID
    """
    ingredients = get_ingredients(session, skip=skip, limit=limit, meal_id=meal_id)
    return ingredients


@app.get("/ingredients/{ingredient_id}", response_model=IngredientRead, tags=["Ingredients"])
def get_ingredient_endpoint(
    ingredient_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific ingredient by ID."""
    ingredient = get_ingredient(session, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient with id={ingredient_id} not found"
        )
    return ingredient


@app.put("/ingredients/{ingredient_id}", response_model=IngredientRead, tags=["Ingredients"])
def update_ingredient_endpoint(
    ingredient_id: int,
    ingredient_data: IngredientCreate,
    session: Session = Depends(get_session)
):
    """Update an existing ingredient."""
    try:
        updated_ingredient = update_ingredient(
            session, ingredient_id, ingredient_data.model_dump()
        )
        if not updated_ingredient:
            raise HTTPException(
                status_code=404,
                detail=f"Ingredient with id={ingredient_id} not found"
            )
        return updated_ingredient
    except InvalidQuantityError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/ingredients/{ingredient_id}", status_code=204, tags=["Ingredients"])
def delete_ingredient_endpoint(
    ingredient_id: int,
    session: Session = Depends(get_session)
):
    """Delete an ingredient."""
    success = delete_ingredient(session, ingredient_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient with id={ingredient_id} not found"
        )


# ============================================
# SPECIAL OPERATIONS (Requirements)
# ============================================

@app.post("/meals/{meal_id}/add-calories-string", response_model=MealRead, tags=["Special Operations"])
def add_calories_string_endpoint(
    meal_id: int,
    calories: str = Query(..., description="Calories as string (e.g., '50.5')"),
    session: Session = Depends(get_session)
):
    """
    Add calories to a meal (accepts calories as STRING).
    
    ⚠️ SPECIAL REQUIREMENT: Similar operation #1 - accepts string parameter.
    """
    try:
        updated_meal = add_meal_calories_string(session, meal_id, calories)
        return updated_meal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/meals/{meal_id}/add-calories-float", response_model=MealRead, tags=["Special Operations"])
def add_calories_float_endpoint(
    meal_id: int,
    calories: float = Query(..., description="Calories as float"),
    session: Session = Depends(get_session)
):
    """
    Add calories to a meal (accepts calories as FLOAT).
    
    ⚠️ SPECIAL REQUIREMENT: Similar operation #2 - accepts float parameter.
    """
    try:
        updated_meal = add_meal_calories_float(session, meal_id, calories)
        return updated_meal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# UTILITY ENDPOINTS
# ============================================

@app.get("/stats", tags=["Utilities"])
def get_stats_endpoint(session: Session = Depends(get_session)):
    """Get database statistics."""
    return get_meal_stats(session)


@app.get("/health", tags=["Utilities"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Meal Planner API"}


@app.get("/", tags=["Utilities"])
def root():
    """Root endpoint - redirects to docs."""
    return {
        "message": "Welcome to Meal Planner API",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
