import requests
import os
import random
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import openai
from rich.console import Console

# Load environment variables
load_dotenv()

# Initialize console for rich output
console = Console()

class RecipeFetcher:
    """Fetches recipes from online sources or generates them using AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the recipe fetcher with optional API key."""
        self.api_key = api_key
        # List of oily fish for reference
        self.oily_fish = [
            "salmon", "mackerel", "sardines", "trout", "herring", 
            "tuna", "anchovies", "pilchards"
        ]
        
        # Set up OpenAI client if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            # Set the API key for OpenAI
            openai.api_key = api_key
            self.client = True  # Just a flag to indicate we have API access
        else:
            self.client = None
            console.print("[yellow]Warning: No OpenAI API key found. Using fallback recipe generation.[/yellow]")
    
    def is_oily_fish_recipe(self, recipe_name: str) -> bool:
        """Check if a recipe contains oily fish."""
        recipe_name_lower = recipe_name.lower()
        return any(fish in recipe_name_lower for fish in self.oily_fish)
    
    def fetch_recipe(self, meal_name: str) -> Dict[str, Any]:
        """Fetch or generate a recipe for the given meal name."""
        # Try to generate a detailed recipe using AI first
        if self.client:
            try:
                ai_recipe = self._generate_ai_recipe(meal_name)
                if ai_recipe:
                    return ai_recipe
            except Exception as e:
                console.print(f"[yellow]Error generating recipe with AI: {str(e)}. Using fallback.[/yellow]")
        
        # Fallback to mock recipe if AI generation fails or is unavailable
        cooking_time = random.randint(25, 35)  # Around 30 minutes
        
        # Simple mock recipe structure
        recipe = {
            "name": meal_name,
            "cooking_time": cooking_time,
            "ingredients": self._generate_mock_ingredients(meal_name),
            "instructions": self._generate_mock_instructions(meal_name),
            "source": "Generated recipe",
            "url": None
        }
        
        return recipe
    
    def _generate_ai_recipe(self, meal_name: str) -> Dict[str, Any]:
        """Generate a detailed recipe using AI."""
        try:
            # Construct system prompt for recipe generation
            system_prompt = """
            You are a professional chef specializing in family-friendly recipes that are easy to follow.
            Your task is to create detailed, practical recipes with specific ingredients and clear instructions.
            Focus on recipes that take around 30 minutes to prepare and cook.
            Use common ingredients that are easy to find in most supermarkets.
            Provide exact measurements and cooking times for a reliable result.
            """
            
            user_prompt = f"""
            Please create a detailed recipe for: {meal_name}
            
            The recipe should include:
            1. A list of specific ingredients with exact quantities (e.g., "2 tablespoons olive oil" not just "olive oil")
            2. Step-by-step cooking instructions that are clear and easy to follow
            3. Approximate cooking time
            
            Format your response as a JSON object with this structure:
            {{"ingredients": ["ingredient 1", "ingredient 2", ...], "instructions": ["step 1", "step 2", ...], "cooking_time": minutes}}
            
            IMPORTANT: 
            - Be very specific with ingredients - no generic terms like "carbohydrates" or "protein component"
            - Each ingredient should be something you can actually buy or measure
            - Instructions should be detailed enough that a novice cook could follow them
            - The JSON must be valid with no additional text
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract recipe data from response
            import json
            recipe_data = json.loads(response.choices[0].message.content)
            
            # Create complete recipe object
            recipe = {
                "name": meal_name,
                "cooking_time": recipe_data.get("cooking_time", 30),
                "ingredients": recipe_data.get("ingredients", []),
                "instructions": recipe_data.get("instructions", []),
                "source": "AI-generated recipe",
                "url": None
            }
            
            return recipe
            
        except Exception as e:
            console.print(f"[yellow]Error in AI recipe generation: {str(e)}[/yellow]")
            return None
    
    def _generate_mock_ingredients(self, meal_name: str) -> List[str]:
        """Generate mock ingredients based on meal name."""
        # This is a fallback method when AI generation fails
        base_ingredients = ["2 tablespoons olive oil", "1 teaspoon salt", "1/2 teaspoon black pepper"]
        
        if "burger" in meal_name.lower():
            return base_ingredients + [
                "500g lean ground beef",
                "4 burger buns",
                "1 large onion, thinly sliced",
                "4 slices cheddar cheese",
                "4 large lettuce leaves",
                "2 ripe tomatoes, sliced",
                "4 tablespoons mayonnaise",
                "2 tablespoons ketchup",
                "1 tablespoon mustard"
            ]
        elif "hotdog" in meal_name.lower():
            return base_ingredients + [
                "8 good quality hotdog sausages",
                "8 soft hotdog buns",
                "1 medium onion, finely diced",
                "4 tablespoons ketchup",
                "2 tablespoons yellow mustard",
                "4 tablespoons sweet relish",
                "1/4 cup pickled jalapeños (optional)"
            ]
        elif "chicken nugget" in meal_name.lower():
            return base_ingredients + [
                "500g chicken breast, cut into 2cm chunks",
                "100g panko breadcrumbs",
                "50g plain flour",
                "2 large eggs, beaten",
                "1 teaspoon garlic powder",
                "1 teaspoon paprika",
                "500g russet potatoes, cut into chips",
                "2 cups vegetable oil for frying",
                "100ml honey mustard sauce for dipping"
            ]
        elif "fish taco" in meal_name.lower():
            return base_ingredients + [
                "500g firm white fish fillets (cod or haddock)",
                "8 small corn tortillas",
                "1 ripe avocado, sliced",
                "1 lime, cut into wedges",
                "200g red cabbage, finely shredded",
                "100g carrot, grated",
                "4 tablespoons sour cream",
                "Fresh cilantro, chopped",
                "1 tablespoon cumin",
                "1 teaspoon chili powder"
            ]
        elif "fish and broccoli" in meal_name.lower():
            return base_ingredients + [
                "4 salmon or cod fillets (150g each)",
                "400g broccoli florets",
                "2 lemons (1 juiced, 1 cut into wedges)",
                "3 cloves garlic, minced",
                "50g butter",
                "1 tablespoon fresh dill, chopped",
                "200g new potatoes, halved",
                "2 tablespoons capers (optional)"
            ]
        elif "fajita" in meal_name.lower():
            return base_ingredients + [
                "500g chicken breast, sliced into strips",
                "2 bell peppers (1 red, 1 yellow), sliced",
                "1 large onion, sliced",
                "2 tablespoons fajita seasoning",
                "8 flour tortillas",
                "100g sour cream",
                "100g grated cheddar cheese",
                "100g fresh salsa",
                "1 lime, cut into wedges",
                "Fresh cilantro for garnish"
            ]
        elif "bolognese" in meal_name.lower():
            return base_ingredients + [
                "500g lean ground beef",
                "1 large onion, finely diced",
                "3 cloves garlic, minced",
                "1 large carrot, finely diced",
                "2 celery stalks, finely diced",
                "400g can crushed tomatoes",
                "2 tablespoons tomato paste",
                "1 beef stock cube dissolved in 200ml hot water",
                "1 teaspoon dried oregano",
                "1 teaspoon dried basil",
                "1 bay leaf",
                "350g spaghetti",
                "50g grated parmesan cheese"
            ]
        else:
            # For unknown recipes, provide a more detailed generic template
            return [
                "2 tablespoons olive oil",
                "1 teaspoon salt",
                "1/2 teaspoon black pepper",
                "500g protein of choice (chicken, beef, fish, or tofu)",
                "1 large onion, diced",
                "2 cloves garlic, minced",
                "2 cups mixed vegetables (bell peppers, carrots, broccoli)",
                "1 cup rice, pasta, or potatoes",
                "2 tablespoons fresh herbs (parsley, basil, or cilantro)",
                "1 lemon or lime, juiced",
                "1 tablespoon butter or cream (optional)",
                "1 cup stock or broth appropriate for your protein"
            ]
    
    def _generate_mock_instructions(self, meal_name: str) -> List[str]:
        """Generate mock instructions based on meal name."""
        # This is a fallback method when AI generation fails
        if "burger" in meal_name.lower():
            return [
                "In a large bowl, season the ground beef with salt and pepper. Mix gently and form into 4 equal-sized patties about 1cm thick.",
                "Heat 1 tablespoon of olive oil in a large pan over medium-high heat.",
                "Cook the patties for 4-5 minutes on each side for medium doneness, or adjust to your preference.",
                "Place a slice of cheese on each patty during the last minute of cooking and cover to melt.",
                "Meanwhile, lightly toast the burger buns in another pan or under the broiler.",
                "Spread mayonnaise on the bottom buns, then layer with lettuce, tomato slices, and the cooked patties with melted cheese.",
                "Add sliced onion on top of the patties, then drizzle with ketchup and mustard.",
                "Place the top buns on and serve immediately while hot."
            ]
        elif "hotdog" in meal_name.lower():
            return [
                "Fill a large pot halfway with water and bring to a simmer over medium heat (not a rolling boil).",
                "Gently add the hotdog sausages to the simmering water and cook for 5-7 minutes until heated through.",
                "While the sausages are cooking, lightly toast the hotdog buns in a dry pan or under the broiler until golden.",
                "Drain the sausages well and pat dry with paper towels if needed.",
                "Place each sausage in a toasted bun.",
                "Top with diced onion, then add ketchup, mustard, and relish according to preference.",
                "For extra flavor, you can add pickled jalapeños or sauerkraut if desired.",
                "Serve immediately while the sausages are still hot."
            ]
        elif "chicken nugget" in meal_name.lower():
            return [
                "Set up a breading station: put flour in one bowl, beaten eggs in a second bowl, and mix breadcrumbs with garlic powder and paprika in a third bowl.",
                "Season the chicken pieces with salt and pepper.",
                "Dredge each piece of chicken in flour, then dip in beaten egg, and finally coat in the seasoned breadcrumbs.",
                "Heat oil in a large, deep pan to 350°F (175°C).",
                "Fry the chicken pieces in batches for 3-4 minutes until golden brown and cooked through (internal temperature of 165°F/74°C).",
                "Remove with a slotted spoon and drain on paper towels.",
                "For the chips, heat oil to 350°F (175°C) and fry potato pieces for 4-5 minutes until golden and crisp.",
                "Season the chips with salt while still hot and serve alongside the nuggets with dipping sauce."
            ]
        elif "fish taco" in meal_name.lower():
            return [
                "In a small bowl, mix salt, pepper, cumin, and chili powder. Season the fish fillets on both sides.",
                "Heat 1 tablespoon of olive oil in a large non-stick pan over medium-high heat.",
                "Cook the fish for 3-4 minutes per side until opaque and flakes easily with a fork.",
                "While the fish cooks, warm the tortillas in a dry pan or microwave for 20 seconds.",
                "In a bowl, toss the shredded cabbage and grated carrot with a squeeze of lime juice and a pinch of salt.",
                "Break the cooked fish into chunks with a fork.",
                "Assemble the tacos: place some slaw on each tortilla, top with fish pieces, sliced avocado, a dollop of sour cream, and fresh cilantro.",
                "Serve with lime wedges on the side for squeezing over the tacos."
            ]
        else:
            # More detailed generic instructions
            return [
                "Prepare all ingredients according to the list: chop vegetables, measure spices, and prepare the protein.",
                "Heat a large pan or pot over medium heat and add the olive oil.",
                "If using meat or fish, season with salt and pepper, then cook until properly done (chicken and pork to 165°F/74°C, beef to desired doneness, fish until it flakes easily).",
                "Remove the protein and set aside. In the same pan, sauté the onions and garlic until fragrant, about 2-3 minutes.",
                "Add any vegetables and cook until tender but still crisp, about 5-7 minutes depending on the type.",
                "If using rice, pasta, or potatoes, cook according to package instructions in a separate pot.",
                "Return the protein to the pan with the vegetables, add any sauces or liquids, and simmer for 5 minutes to combine flavors.",
                "Stir in fresh herbs and a squeeze of citrus juice just before serving.",
                "Taste and adjust seasoning with additional salt and pepper if needed.",
                "Serve hot, garnished with any remaining fresh herbs."
            ]
            
    def search_recipe_online(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for a recipe online using an API."""
        # In a real implementation, this would call an actual recipe API
        # For now, we'll return None to fall back to the mock generator
        return None
