"""
Script para inicializar o banco de dados e testar operações básicas.
"""
from src.database import create_db_and_tables, get_session_context
from src.models import MealCreate, IngredientCreate
from src.core import (
    create_meal,
    get_meals,
    create_ingredient,
    get_meal_with_ingredients,
    delete_meal,
    add_meal_calories_string,
    add_meal_calories_float,
    get_meal_stats,
    MealHasIngredientsError,
    InvalidQuantityError
)


def init_database():
    """Inicializa o banco de dados e cria tabelas."""
    print("🔧 Inicializando banco de dados...")
    create_db_and_tables()


def test_basic_operations():
    """Testa operações básicas do CRUD."""
    print("\n📝 Testando operações básicas...\n")
    
    with get_session_context() as session:
        # 1. Criar refeições
        print("1️⃣ Criando refeições...")
        meal1 = create_meal(session, MealCreate(
            name="Salada Caesar",
            description="Salada com frango grelhado",
            calories=350.0,
            is_healthy=True
        ))
        print(f"   ✓ Criada: {meal1.name} ({meal1.calories} cal)")
        
        meal2 = create_meal(session, MealCreate(
            name="Arroz com Feijão",
            description="Arroz integral com feijão preto",
            calories=450.0,
            is_healthy=True
        ))
        print(f"   ✓ Criada: {meal2.name} ({meal2.calories} cal)")
        
        meal3 = create_meal(session, MealCreate(
            name="Pizza Margherita",
            description="Pizza tradicional italiana",
            calories=800.0,
            is_healthy=False
        ))
        print(f"   ✓ Criada: {meal3.name} ({meal3.calories} cal)")
        
        # 2. Criar ingredientes
        print("\n2️⃣ Adicionando ingredientes...")
        ing1 = create_ingredient(session, IngredientCreate(
            name="Alface",
            quantity="100g",
            meal_id=meal1.id
        ))
        print(f"   ✓ Adicionado: {ing1.quantity} de {ing1.name}")
        
        ing2 = create_ingredient(session, IngredientCreate(
            name="Frango grelhado",
            quantity="150g",
            meal_id=meal1.id
        ))
        print(f"   ✓ Adicionado: {ing2.quantity} de {ing2.name}")
        
        ing3 = create_ingredient(session, IngredientCreate(
            name="Arroz integral",
            quantity="200g",
            meal_id=meal2.id
        ))
        print(f"   ✓ Adicionado: {ing3.quantity} de {ing3.name}")
        
        # 3. Listar refeições
        print("\n3️⃣ Listando refeições...")
        meals = get_meals(session)
        for meal in meals:
            print(f"   • {meal.name} - {meal.calories} cal - {'✓ Saudável' if meal.is_healthy else '✗ Não saudável'}")
        
        # 4. Buscar refeição com ingredientes
        print(f"\n4️⃣ Refeição '{meal1.name}' com ingredientes:")
        meal_full = get_meal_with_ingredients(session, meal1.id)
        if meal_full:
            for ing in meal_full.ingredients:
                print(f"   • {ing.quantity} de {ing.name}")
        
        # 5. Estatísticas
        print("\n5️⃣ Estatísticas do banco:")
        stats = get_meal_stats(session)
        print(f"   Total de refeições: {stats['total_meals']}")
        print(f"   Total de ingredientes: {stats['total_ingredients']}")
        print(f"   Refeições saudáveis: {stats['healthy_meals']}")
        print(f"   Refeições não saudáveis: {stats['unhealthy_meals']}")


def test_special_operations():
    """Testa os requisitos especiais do trabalho."""
    print("\n🔬 Testando requisitos especiais...\n")
    
    with get_session_context() as session:
        # REQUISITO 1: Operação que levanta exceção
        print("📌 REQUISITO 1: Tentar deletar meal com ingredients (deve lançar exceção)")
        try:
            delete_meal(session, 1)  # Meal 1 tem ingredients
            print("   ✗ ERRO: Deveria ter lançado exceção!")
        except MealHasIngredientsError as e:
            print(f"   ✓ Exceção capturada corretamente: {e}")
        
        # REQUISITO 2: Operação que retorna erro
        print("\n📌 REQUISITO 2: Criar ingredient com quantity inválida (deve retornar erro)")
        try:
            create_ingredient(session, IngredientCreate(
                name="Tomate",
                quantity="quantidade inválida",  # Formato errado
                meal_id=1
            ))
            print("   ✗ ERRO: Deveria ter lançado exceção!")
        except InvalidQuantityError as e:
            print(f"   ✓ Erro capturado corretamente: {e}")
        
        # REQUISITO 3: Operações similares com parâmetros diferentes
        print("\n📌 REQUISITO 3: Operações similares (string vs float)")
        
        # Buscar meal para pegar calorias antes
        from src.models import Meal
        meal_before = session.get(Meal, 1)
        calories_before = meal_before.calories
        print(f"   Calorias antes: {calories_before}")
        
        # Operação 1: string
        meal_updated = add_meal_calories_string(session, 1, "50.5")
        print(f"   ✓ add_meal_calories_string('50.5'): {meal_updated.calories} cal")
        
        # Operação 2: float
        meal_updated = add_meal_calories_float(session, 1, 25.0)
        print(f"   ✓ add_meal_calories_float(25.0): {meal_updated.calories} cal")
        
        print(f"   Total adicionado: {meal_updated.calories - calories_before} cal")


def main():
    """Função principal."""
    print("=" * 60)
    print("  🍽️  PLANEJADOR DE REFEIÇÕES - INICIALIZAÇÃO")
    print("=" * 60)
    
    # Inicializar banco
    init_database()
    
    # Testar operações básicas
    test_basic_operations()
    
    # Testar requisitos especiais
    test_special_operations()
    
    print("\n" + "=" * 60)
    print("  ✅ Inicialização e testes concluídos com sucesso!")
    print("=" * 60)


if __name__ == "__main__":
    main()
