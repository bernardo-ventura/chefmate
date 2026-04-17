"""
Funções CRUD core compartilhadas entre REST API e MCP Server.
Implementa requisitos especiais do trabalho:
- Exceção ao deletar meal com ingredients
- Erro ao criar ingredient com quantity inválida
- Operações similares com parâmetros diferentes (calories)
"""
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from src.models import (
    Meal, MealCreate, MealRead, MealReadWithIngredients,
    Ingredient, IngredientCreate, IngredientRead
)
import re


# ============================================
# EXCEÇÕES PERSONALIZADAS
# ============================================

class MealHasIngredientsError(Exception):
    """Exceção lançada quando tenta deletar meal com ingredients."""
    pass


class InvalidQuantityError(Exception):
    """Exceção para quantity inválida em ingredient."""
    pass


# ============================================
# CRUD - MEAL
# ============================================

def create_meal(session: Session, meal: MealCreate) -> Meal:
    """Cria uma nova refeição."""
    db_meal = Meal.model_validate(meal)
    session.add(db_meal)
    session.commit()
    session.refresh(db_meal)
    return db_meal


def get_meal(session: Session, meal_id: int) -> Optional[Meal]:
    """Busca uma refeição por ID."""
    return session.get(Meal, meal_id)


def get_meals(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    is_healthy: Optional[bool] = None
) -> List[Meal]:
    """Lista refeições com filtros opcionais."""
    statement = select(Meal)
    
    if is_healthy is not None:
        statement = statement.where(Meal.is_healthy == is_healthy)
    
    statement = statement.offset(skip).limit(limit)
    results = session.exec(statement)
    return list(results.all())


def search_meals_by_name(session: Session, name_query: str) -> List[Meal]:
    """Busca refeições por nome (case-insensitive)."""
    statement = select(Meal).where(Meal.name.ilike(f"%{name_query}%"))
    results = session.exec(statement)
    return list(results.all())


def search_meals_by_ingredient(session: Session, ingredient_name: str) -> List[Meal]:
    """Busca refeições que contêm determinado ingrediente."""
    statement = (
        select(Meal)
        .join(Ingredient)
        .where(Ingredient.name.ilike(f"%{ingredient_name}%"))
        .distinct()
    )
    results = session.exec(statement)
    return list(results.all())


def update_meal(session: Session, meal_id: int, meal_data: Dict[str, Any]) -> Optional[Meal]:
    """Atualiza uma refeição existente."""
    db_meal = session.get(Meal, meal_id)
    if not db_meal:
        return None
    
    for key, value in meal_data.items():
        if hasattr(db_meal, key):
            setattr(db_meal, key, value)
    
    session.add(db_meal)
    session.commit()
    session.refresh(db_meal)
    return db_meal


def delete_meal(session: Session, meal_id: int) -> bool:
    """
    Deleta uma refeição.
    
    REQUISITO ESPECIAL: Levanta exceção se a refeição tem ingredientes.
    """
    db_meal = session.get(Meal, meal_id)
    if not db_meal:
        return False
    
    # Verificar se tem ingredientes (REQUISITO: EXCEÇÃO)
    if db_meal.ingredients:
        raise MealHasIngredientsError(
            f"Cannot delete meal '{db_meal.name}' (id={meal_id}): "
            f"it has {len(db_meal.ingredients)} ingredient(s). "
            f"Delete ingredients first."
        )
    
    session.delete(db_meal)
    session.commit()
    return True


# ============================================
# CRUD - INGREDIENT
# ============================================

def validate_quantity(quantity: str) -> bool:
    """
    Valida o formato da quantidade.
    Deve ser número seguido de unidade (ex: '200g', '1 xícara').
    """
    # Aceita formatos: "200g", "1.5 kg", "2 xícaras", etc.
    pattern = r'^[\d.]+\s*[a-zA-Zçãõáéíóú]+$'
    return bool(re.match(pattern, quantity.strip()))


def create_ingredient(session: Session, ingredient: IngredientCreate) -> Ingredient:
    """
    Cria um novo ingrediente.
    
    REQUISITO ESPECIAL: Retorna erro se quantity é inválida.
    """
    if not validate_quantity(ingredient.quantity):
        raise InvalidQuantityError(
            f"Invalid quantity format: '{ingredient.quantity}'. "
            f"Expected format: number + unit (e.g., '200g', '1 xícara')."
        )
    
    # Verificar se meal existe
    meal = session.get(Meal, ingredient.meal_id)
    if not meal:
        raise ValueError(f"Meal with id={ingredient.meal_id} not found")
    
    db_ingredient = Ingredient.model_validate(ingredient)
    session.add(db_ingredient)
    session.commit()
    session.refresh(db_ingredient)
    return db_ingredient


def get_ingredient(session: Session, ingredient_id: int) -> Optional[Ingredient]:
    """Busca um ingrediente por ID."""
    return session.get(Ingredient, ingredient_id)


def get_ingredients(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    meal_id: Optional[int] = None
) -> List[Ingredient]:
    """Lista ingredientes, opcionalmente filtrando por meal."""
    statement = select(Ingredient)
    
    if meal_id is not None:
        statement = statement.where(Ingredient.meal_id == meal_id)
    
    statement = statement.offset(skip).limit(limit)
    results = session.exec(statement)
    return list(results.all())


def update_ingredient(
    session: Session,
    ingredient_id: int,
    ingredient_data: Dict[str, Any]
) -> Optional[Ingredient]:
    """Atualiza um ingrediente existente."""
    db_ingredient = session.get(Ingredient, ingredient_id)
    if not db_ingredient:
        return None
    
    # Validar quantity se estiver sendo atualizada
    if "quantity" in ingredient_data:
        if not validate_quantity(ingredient_data["quantity"]):
            raise InvalidQuantityError(
                f"Invalid quantity format: '{ingredient_data['quantity']}'"
            )
    
    for key, value in ingredient_data.items():
        if hasattr(db_ingredient, key):
            setattr(db_ingredient, key, value)
    
    session.add(db_ingredient)
    session.commit()
    session.refresh(db_ingredient)
    return db_ingredient


def delete_ingredient(session: Session, ingredient_id: int) -> bool:
    """Deleta um ingrediente."""
    db_ingredient = session.get(Ingredient, ingredient_id)
    if not db_ingredient:
        return False
    
    session.delete(db_ingredient)
    session.commit()
    return True


# ============================================
# REQUISITO ESPECIAL: OPERAÇÕES SIMILARES
# ============================================

def add_meal_calories_string(session: Session, meal_id: int, calories: str) -> Meal:
    """
    Adiciona calorias a uma refeição (recebe como STRING).
    
    REQUISITO ESPECIAL: Operação similar #1 - aceita string.
    """
    db_meal = session.get(Meal, meal_id)
    if not db_meal:
        raise ValueError(f"Meal with id={meal_id} not found")
    
    # Converter string para float
    try:
        calories_float = float(calories)
    except ValueError:
        raise ValueError(f"Cannot convert '{calories}' to number")
    
    db_meal.calories += calories_float
    session.add(db_meal)
    session.commit()
    session.refresh(db_meal)
    return db_meal


def add_meal_calories_float(session: Session, meal_id: int, calories: float) -> Meal:
    """
    Adiciona calorias a uma refeição (recebe como FLOAT).
    
    REQUISITO ESPECIAL: Operação similar #2 - aceita float.
    """
    db_meal = session.get(Meal, meal_id)
    if not db_meal:
        raise ValueError(f"Meal with id={meal_id} not found")
    
    db_meal.calories += calories
    session.add(db_meal)
    session.commit()
    session.refresh(db_meal)
    return db_meal


# ============================================
# HELPERS
# ============================================

def get_meal_with_ingredients(session: Session, meal_id: int) -> Optional[MealReadWithIngredients]:
    """Retorna uma refeição com seus ingredientes."""
    meal = session.get(Meal, meal_id)
    if not meal:
        return None
    
    return MealReadWithIngredients(
        id=meal.id,
        name=meal.name,
        description=meal.description,
        calories=meal.calories,
        is_healthy=meal.is_healthy,
        ingredients=[
            IngredientRead(
                id=ing.id,
                name=ing.name,
                quantity=ing.quantity,
                meal_id=ing.meal_id
            )
            for ing in meal.ingredients
        ]
    )


def get_meal_stats(session: Session) -> Dict[str, Any]:
    """Retorna estatísticas do banco de dados."""
    total_meals = len(session.exec(select(Meal)).all())
    total_ingredients = len(session.exec(select(Ingredient)).all())
    healthy_meals = len(session.exec(select(Meal).where(Meal.is_healthy == True)).all())
    
    return {
        "total_meals": total_meals,
        "total_ingredients": total_ingredients,
        "healthy_meals": healthy_meals,
        "unhealthy_meals": total_meals - healthy_meals
    }
