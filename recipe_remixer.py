import random
from typing import List, Tuple, Dict, Any
from rich.console import Console

# Initialize console for rich output
console = Console()

class RecipeRemixer:
    """Handles remixing meals with creative variations."""
    
    def __init__(self):
        """Initialize the recipe remixer."""
        # Meal remix patterns
        self.remix_patterns = [
            # Format: (pattern, description template)
            ("Deconstructed {}", "A creative deconstructed version of {}, with all the flavors you love but presented in a new way."),
            ("{} Bowl", "Inspired by {}, but served as a convenient and customizable bowl with all ingredients arranged separately."),
            ("Loaded {} Platter", "A family-style platter based on {}, with extra toppings and sides for everyone to share."),
            ("{} Fusion", "A fusion twist on {}, incorporating flavors from another cuisine while keeping the core ingredients you enjoy."),
            ("One-Pan {}", "A simplified one-pan version of {}, with the same great taste but easier cleanup."),
            ("Crispy {}", "A crispier, more textured version of {} that adds a satisfying crunch to a family favorite."),
            ("Stuffed {}", "A creative stuffed version of {}, with delicious fillings that complement the original flavors."),
            ("{} Medley", "A medley inspired by {}, combining several favorite ingredients in a new and exciting way."),
            ("Inside-Out {}", "An inside-out version of {}, with traditional fillings on the outside and wrappings on the inside."),
            ("Grilled {}", "A grilled version of {}, adding smoky flavors to this family favorite."),
            ("Sheet Pan {}", "A convenient sheet pan version of {}, with all ingredients roasted together for maximum flavor."),
            ("Mini {}", "Fun, bite-sized versions of {}, perfect for little hands and customizable for each family member."),
            ("{} Skewers", "The flavors of {} threaded onto skewers for a fun, interactive meal experience."),
            ("{} Casserole", "A comforting casserole inspired by {}, combining all the flavors in a single baked dish."),
            ("{} Stir-Fry", "A quick stir-fry version of {}, maintaining the flavors while adding fresh vegetables."),
            ("Slow-Cooker {}", "A convenient slow-cooker adaptation of {}, letting the flavors develop throughout the day."),
            ("{} Pasta", "The flavors of {} incorporated into a family-friendly pasta dish."),
            ("{} Wrap", "All the delicious components of {} wrapped up for a handheld meal experience."),
            ("{} Salad", "A lighter salad version of {}, keeping the key flavors while adding fresh elements."),
            ("Homestyle {}", "A comforting homestyle version of {}, with a focus on simple, satisfying flavors.")
        ]
        
        # Oily fish options for ensuring nutritional balance
        self.oily_fish = ["salmon", "mackerel", "sardines", "trout", "herring", "anchovies"]
    
    def create_remixed_meal(self, base_meal: str, all_liked_meals: List[str]) -> Tuple[str, str, bool]:
        """Create a remixed version of a meal with a creative twist."""
        # Sometimes combine with another meal's ingredients for fusion
        other_meals = [m for m in all_liked_meals if m != base_meal]
        if other_meals and random.random() < 0.3:  # 30% chance of fusion
            other_meal = random.choice(other_meals)
            pattern, desc_template = (f"{{}}_{other_meal} Fusion", "A creative fusion combining elements of {} and {}, using similar ingredients in a new way.")
            remixed_name = pattern.format(base_meal)
            description = desc_template.format(base_meal, other_meal)
        else:
            # Choose a random remix pattern
            pattern, desc_template = random.choice(self.remix_patterns)
            remixed_name = pattern.format(base_meal)
            description = desc_template.format(base_meal)
        
        # Determine if this is an oily fish recipe
        contains_oily_fish = any(fish in base_meal.lower() for fish in self.oily_fish)
        
        return remixed_name, description, contains_oily_fish
    
    def is_oily_fish_recipe(self, meal_name: str) -> bool:
        """Check if a meal contains oily fish based on its name."""
        return any(fish in meal_name.lower() for fish in self.oily_fish)
    
    def generate_fallback_recipe(self, meal_name: str) -> Dict[str, Any]:
        """Generate a simple recipe structure for a given meal name."""
        # Simple generic recipe structure
        return {
            "ingredients": [
                "Main protein (chicken, beef, fish, etc.)",
                "Vegetables of choice",
                "Starch (rice, pasta, potatoes)",
                "Seasonings to taste",
                "Oil or butter for cooking"
            ],
            "instructions": [
                "Prepare all ingredients by washing and chopping as needed.",
                f"Cook the main components of the {meal_name} according to your preferred method.",
                "Combine all elements and season to taste.",
                "Serve hot and enjoy with your family!"
            ]
        }
