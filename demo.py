#!/usr/bin/env python3
"""
Demo script for the Family Meal Planner
This allows testing the basic functionality without an OpenAI API key
"""

from meal_planner import MealPlanner
from rich.console import Console
from preferences import PreferenceManager

console = Console()

def main():
    """Run a simple demo of the meal planner."""
    console.print("[bold cyan]Family Meal Planner Demo[/bold cyan]")
    console.print("This demo will generate a sample meal plan using the fallback method.\n")
    
    # Initialize the planner
    planner = MealPlanner()
    
    # Show current preferences
    pref_manager = PreferenceManager()
    liked_foods = pref_manager.get_liked_foods()
    
    console.print("[bold]Current food preferences:[/bold]")
    for food in liked_foods:
        console.print(f"• {food}")
    
    console.print("\n[bold]Generating a 3-day meal plan...[/bold]")
    meal_plan = planner.generate_meal_plan()
    
    # Display the meal plan
    planner.display_meal_plan(meal_plan)
    
    # Show a recipe example
    console.print("\n[bold]Sample Recipe:[/bold]")
    planner.display_recipe(0, meal_plan)
    
    console.print("\n[bold green]Demo completed![/bold green]")
    console.print("To use the full application with AI-powered meal planning:")
    console.print("1. Create a .env file with your OpenAI API key")
    console.print("2. Run 'python meal_planner.py plan' to generate a meal plan")
    console.print("3. Run 'python meal_planner.py add-preference \"New Food\"' to add preferences")
    console.print("4. Run 'python meal_planner.py list-preferences' to view all preferences")

if __name__ == "__main__":
    main()
