"""
Modelos de dados para o Planejador de Refeições.
Define as entidades Meal e Ingredient com relacionamento 1:N.
"""
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class Ingredient(SQLModel, table=True):
    """Ingrediente de uma refeição."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Nome do ingrediente")
    quantity: str = Field(description="Quantidade (ex: '200g', '1 xícara')")
    meal_id: int = Field(foreign_key="meal.id", description="ID da refeição")
    
    # Relacionamento
    meal: Optional["Meal"] = Relationship(back_populates="ingredients")


class Meal(SQLModel, table=True):
    """Refeição com informações nutricionais."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Nome da refeição")
    description: str = Field(default="", description="Descrição da refeição")
    calories: float = Field(ge=0, description="Calorias totais")
    is_healthy: bool = Field(default=True, description="Refeição saudável?")
    
    # Relacionamento
    ingredients: List["Ingredient"] = Relationship(back_populates="meal")


# Modelos para criação (sem id)
class MealCreate(SQLModel):
    """Modelo para criar uma nova refeição."""
    name: str
    description: str = ""
    calories: float
    is_healthy: bool = True


class IngredientCreate(SQLModel):
    """Modelo para criar um novo ingrediente."""
    name: str
    quantity: str
    meal_id: int


# Modelos para resposta (com relacionamentos populados)
class MealRead(SQLModel):
    """Modelo para leitura de refeição (sem ingredientes)."""
    id: int
    name: str
    description: str
    calories: float
    is_healthy: bool


class IngredientRead(SQLModel):
    """Modelo para leitura de ingrediente."""
    id: int
    name: str
    quantity: str
    meal_id: int


class MealReadWithIngredients(MealRead):
    """Modelo para leitura de refeição com ingredientes."""
    ingredients: List[IngredientRead] = []
