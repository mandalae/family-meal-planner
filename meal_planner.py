import random
import datetime
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import click

# Load environment variables
load_dotenv()

# Initialize console for rich output
console = Console()

# Import after environment variables are loaded
from preferences import PreferenceManager
from recipe_fetcher import RecipeFetcher
from ai_recipe_generator import AIRecipeGenerator
from recipe_remixer import RecipeRemixer
from shopping_list import ShoppingListManager

class MealPlanner:
    """AI-powered meal planner that generates weekly meal plans."""
    
    def __init__(self):
        """Initialize the meal planner with necessary components."""
        self.preference_manager = PreferenceManager()
        self.recipe_fetcher = RecipeFetcher()
        self.ai_generator = AIRecipeGenerator()
        self.recipe_remixer = RecipeRemixer()
        self.shopping_list_manager = ShoppingListManager()
    
    def _generate_and_cache_shopping_list(self, meal_plan: Dict[str, Any]) -> None:
        """Generate and cache a shopping list for a meal plan."""
        try:
            # Generate the shopping list
            shopping_list = self.shopping_list_manager.generate_shopping_list(meal_plan)
            
            # Cache the shopping list
            self.preference_manager.store_shopping_list(meal_plan["id"], shopping_list)
            
            console.print(f"[green]Shopping list generated and cached for meal plan {meal_plan['id']}[/green]")
        except Exception as e:
            console.print(f"[red]Error generating shopping list: {str(e)}[/red]")
    
    def get_shopping_list(self, meal_plan_id: str) -> List[Dict[str, Any]]:
        """Get a shopping list for a specific meal plan, generating it if not cached."""
        # Check if the shopping list is cached
        if self.preference_manager.has_shopping_list(meal_plan_id):
            return self.preference_manager.get_shopping_list(meal_plan_id)
        
        # If not cached, find the meal plan and generate the shopping list
        meal_history = self.preference_manager.get_meal_history()
        for plan in meal_history:
            if plan.get("id") == meal_plan_id:
                shopping_list = self.shopping_list_manager.generate_shopping_list(plan)
                self.preference_manager.store_shopping_list(meal_plan_id, shopping_list)
                return shopping_list
        
        # If meal plan not found, return empty list
        return []
    
    def generate_meal_plan(self) -> Dict[str, Any]:
        """Generate a meal plan based on preferences and configured meal count."""
        liked_foods = self.preference_manager.get_liked_foods()
        disliked_foods = self.preference_manager.get_disliked_foods()
        meal_history = self.preference_manager.get_meal_history()
        meal_count = self.preference_manager.get_meal_count()  # Get the configured meal count
        
        # Extract recent meals to avoid repetition
        recent_meals = []
        if meal_history:
            for plan in meal_history[-2:]:  # Last 2 meal plans
                for day in plan["days"]:
                    recent_meals.append(day["meal"])
        
        # Try to generate with AI first
        plan_data = self._generate_with_ai(liked_foods, disliked_foods, recent_meals, meal_count)
        
        # Fall back to non-AI method if AI generation fails
        if not plan_data:
            plan_data = self._generate_fallback(liked_foods, disliked_foods, recent_meals, meal_count)
            
        # Add metadata
        plan_data["date_generated"] = datetime.datetime.now().isoformat()
        plan_data["week_starting"] = (datetime.datetime.now() + 
                                  datetime.timedelta(days=(7 - datetime.datetime.now().weekday()))).isoformat()
        
        # Generate a unique ID for the meal plan
        plan_data["id"] = str(uuid.uuid4())
        
        # Save to history
        self.preference_manager.add_meal_to_history(plan_data)
        
        # Generate and cache the shopping list
        self._generate_and_cache_shopping_list(plan_data)
        
        return plan_data
    
    def _generate_with_ai(self, liked_foods: List[str], disliked_foods: List[str], 
                          recent_meals: List[str], meal_count: int = 3) -> Dict[str, Any]:
        """Generate meal plan using OpenAI API via AIRecipeGenerator."""
        try:
            # Get family information from preferences
            family_info = self.preference_manager.data.get("family_info", {
                "members": 4,
                "children_ages": [6, 8]
            })
            
            # Use the AI generator to create the meal plan
            plan_data = self.ai_generator.generate_meal_plan(
                liked_foods, disliked_foods, recent_meals, meal_count, family_info
            )
            
            if not plan_data:
                return None
            
            # Add recipes to the plan
            for day in plan_data["days"]:
                if "preparation_instructions" in day and day["preparation_instructions"]:
                    # AI provided instructions, use them
                    day["recipe"] = {
                        "name": day["meal"],
                        "ingredients": day.get("ingredients", []),  # Use AI-provided ingredients, fallback to empty list
                        "instructions": day["preparation_instructions"],
                        "source": "AI Generated"
                    }
                else:
                    # Fallback to RecipeFetcher if AI didn't provide instructions
                    day["recipe"] = self.recipe_fetcher.fetch_recipe(day["meal"])
                    if day["recipe"]:
                        day["recipe"]["source"] = "RecipeFetcher"
                    else: # Handle case where RecipeFetcher also fails
                        day["recipe"] = {
                            "name": day["meal"],
                            "ingredients": [],
                            "instructions": ["No instructions available."],
                            "source": "None"
                        }
            
            return plan_data
            
        except Exception as e:
            console.print(f"[red]Error generating meal plan with AI: {str(e)}[/red]")
            return None
    
    def _extract_common_ingredients(self, meals: List[str]) -> List[str]:
        """Extract common ingredients from a list of meals using the AIRecipeGenerator."""
        return self.ai_generator._extract_common_ingredients(meals)
    
    def _generate_fallback(self, liked_foods: List[str], disliked_foods: List[str], 
                          recent_meals: List[str], meal_count: int = 3) -> Dict[str, Any]:
        """Generate a meal plan without using AI API."""
        # Filter out recently used meals
        available_meals = [meal for meal in liked_foods if meal not in recent_meals]
        
        # If we've used all meals recently, just use the full list
        if not available_meals:
            available_meals = liked_foods
        
        # Ensure we include oily fish
        oily_fish_included = False
        plan_data = {"days": []}
        
        # Select meals based on configured meal count
        selected_meals = random.sample(available_meals, min(meal_count, len(available_meals)))
        
        # Check if any of the selected meals contain oily fish
        for meal in selected_meals:
            if self.recipe_remixer.is_oily_fish_recipe(meal):
                oily_fish_included = True
                break
        
        # If no oily fish meal was selected, replace one meal with a fish option
        if not oily_fish_included:
            fish_options = [meal for meal in liked_foods 
                           if "fish" in meal.lower() or 
                           any(fish in meal.lower() for fish in self.recipe_remixer.oily_fish)]
            
            if fish_options:
                # Replace one random meal with a fish option
                selected_meals[random.randint(0, len(selected_meals) - 1)] = random.choice(fish_options)
        
        # Create remixed meal plans based on selected meals
        for i, meal in enumerate(selected_meals):
            # Get base meal and remix it
            base_meal = meal
            remixed_name, description, contains_oily_fish = self.recipe_remixer.create_remixed_meal(base_meal, liked_foods)
            
            day_plan = {
                "day": f"Day {i + 1}",
                "meal": remixed_name,
                "description": description,
                "contains_oily_fish": contains_oily_fish,
                "recipe": self.recipe_fetcher.fetch_recipe(remixed_name)
            }
            
            plan_data["days"].append(day_plan)
        
        return plan_data
    
    def _create_remixed_meal(self, base_meal: str, all_liked_meals: List[str]) -> Tuple[str, str]:
        """Create a remixed version of a meal with a creative twist using the AIRecipeGenerator."""
        # Get family information from preferences
        family_info = self.preference_manager.data.get("family_info", {
            "members": 4,
            "children_ages": [6, 8]
        })
        
        # Try to use AI-based remixing first
        remixed_name, description, contains_oily_fish = self.ai_generator.create_remixed_meal(
            base_meal, all_liked_meals, family_info
        )
        
        # Fall back to pattern-based remixing if AI fails
        if not remixed_name or not description:
            remixed_name, description, contains_oily_fish = self.recipe_remixer.create_remixed_meal(base_meal, all_liked_meals)
            
        return remixed_name, description
    
    # This method is now handled by the RecipeRemixer class
    
    def display_meal_plan(self, plan: Dict[str, Any]) -> None:
        """Display a meal plan in a formatted table."""
        table = Table(title="Weekly Meal Plan")
        
        table.add_column("Day", style="cyan")
        table.add_column("Meal", style="green")
        table.add_column("Description", style="yellow")
        table.add_column("Cooking Time", style="magenta")
        table.add_column("Contains Oily Fish", style="blue")
        
        for day in plan["days"]:
            cooking_time = f"{day['recipe']['cooking_time']} minutes"
            contains_fish = "✓" if day["contains_oily_fish"] else "✗"
            
            table.add_row(
                day["day"],
                day["meal"],
                day["description"],
                cooking_time,
                contains_fish
            )
        
        console.print(table)
        
        # Display week information
        week_starting = datetime.datetime.fromisoformat(plan["week_starting"]).strftime("%B %d, %Y")
        console.print(f"\nMeal plan for week starting: [bold]{week_starting}[/bold]\n")
    
    def display_recipe(self, day_index: int, plan: Dict[str, Any]) -> None:
        """Display a recipe for a specific day."""
        if day_index < 0 or day_index >= len(plan["days"]):
            console.print("[red]Invalid day index[/red]")
            return
        
        day = plan["days"][day_index]
        recipe = day["recipe"]
        
        console.print(f"\n[bold cyan]Recipe for {day['meal']}[/bold cyan]")
        console.print(f"[bold]Cooking Time:[/bold] {recipe['cooking_time']} minutes\n")
        
        console.print("[bold]Ingredients:[/bold]")
        for ingredient in recipe["ingredients"]:
            console.print(f"• {ingredient}")
        
        console.print("\n[bold]Instructions:[/bold]")
        for i, step in enumerate(recipe["instructions"], 1):
            console.print(f"{i}. {step}")
        
        if recipe["url"]:
            console.print(f"\n[bold]Source:[/bold] {recipe['source']}")
            console.print(f"[bold]URL:[/bold] {recipe['url']}")


@click.group()
def cli():
    """Family Meal Planner - AI-powered meal planning assistant."""
    pass


@cli.command()
def plan():
    """Generate a new 3-day meal plan."""
    planner = MealPlanner()
    meal_plan = planner.generate_meal_plan()
    planner.display_meal_plan(meal_plan)
    
    # Ask if user wants to see recipes
    for i, day in enumerate(meal_plan["days"]):
        if click.confirm(f"\nWould you like to see the recipe for {day['meal']}?", default=True):
            planner.display_recipe(i, meal_plan)


@cli.command()
@click.argument("food")
@click.option("--dislike", is_flag=True, help="Mark as disliked food instead of liked")
def add_preference(food, dislike):
    """Add a food preference."""
    manager = PreferenceManager()
    manager.add_preference(food, not dislike)
    
    if dislike:
        console.print(f"[green]Added [bold]{food}[/bold] to disliked foods[/green]")
    else:
        console.print(f"[green]Added [bold]{food}[/bold] to liked foods[/green]")


@cli.command()
def list_preferences():
    """List all food preferences."""
    manager = PreferenceManager()
    
    liked = manager.get_liked_foods()
    disliked = manager.get_disliked_foods()
    
    table = Table(title="Food Preferences")
    table.add_column("Liked Foods", style="green")
    table.add_column("Disliked Foods", style="red")
    
    # Determine the maximum number of rows needed
    max_rows = max(len(liked), len(disliked))
    
    # Add rows to the table
    for i in range(max_rows):
        liked_food = liked[i] if i < len(liked) else ""
        disliked_food = disliked[i] if i < len(disliked) else ""
        table.add_row(liked_food, disliked_food)
    
    console.print(table)


@cli.command()
def history():
    """View meal planning history."""
    manager = PreferenceManager()
    history = manager.get_meal_history()
    
    if not history:
        console.print("[yellow]No meal planning history found[/yellow]")
        return
    
    for i, plan in enumerate(history, 1):
        week_starting = datetime.datetime.fromisoformat(plan["week_starting"]).strftime("%B %d, %Y")
        console.print(f"\n[bold]Week {i} (starting {week_starting}):[/bold]")
        
        for day in plan["days"]:
            fish_emoji = "🐟 " if day["contains_oily_fish"] else ""
            console.print(f"  • {day['day']}: {fish_emoji}{day['meal']}")


if __name__ == "__main__":
    cli()
