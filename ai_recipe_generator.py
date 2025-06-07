import os
import json
import random
import re
import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from rich.console import Console

# Initialize OpenAI
from openai import OpenAI

# Initialize console for rich output
console = Console()

class AIRecipeGenerator:
    """Handles AI-based recipe generation using OpenAI's API."""
    
    def __init__(self):
        """Initialize the AI recipe generator."""
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = None  # Initialize client to None
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key) # New client initialization
            except Exception as e:
                # self.client remains None if initialization fails
                console.print(f"[yellow]Warning: Failed to initialize OpenAI client: {e}. Using fallback methods.[/yellow]")
        else:
            # self.client is already None
            console.print("[yellow]Warning: No OpenAI API key found. Using fallback methods.[/yellow]")
    
    def generate_meal_plan(self, 
                          liked_foods: List[str], 
                          disliked_foods: List[str],
                          recent_meals: List[str],
                          meal_count: int = 3,
                          family_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a meal plan using OpenAI API."""
        if not self.client:
            return None
            
        try:
            # Use default family info if none provided
            if family_info is None:
                family_info = {
                    "members": 4,
                    "children_ages": [6, 8]
                }
            
            # Extract family details
            members = family_info.get("members", 4)
            children_ages = family_info.get("children_ages", [6, 8])
            children_text = ""
            
            if children_ages and len(children_ages) > 0:
                children_text = f"with {len(children_ages)} {'child' if len(children_ages) == 1 else 'children'} aged {', '.join(map(str, children_ages))}"
            
            # Sanitize inputs that will be part of f-strings to avoid issues with user-provided curly braces
            safe_liked_foods_str = ', '.join([str(food).replace('{', '{{').replace('}', '}}') for food in liked_foods])
            safe_disliked_foods_str = ', '.join([str(food).replace('{', '{{').replace('}', '}}') for food in disliked_foods])
            safe_recent_meals_str = ', '.join([str(food).replace('{', '{{').replace('}', '}}') for food in recent_meals])

            total_meals_for_ai = meal_count + 2 # Add 2 weekend meals

            # Construct the prompt for the AI
            system_prompt = f"""
            You are an expert meal planning assistant for a family of {members} {children_text}.
            Your goal is to create a {total_meals_for_ai}-day meal plan.
            - For {meal_count} of the days (weekday meals), suggest EXISTING, well-known meals that have similar flavor profiles or ingredients to the family's liked foods. These meals should be relatively common, easy to find recipes for, and take around 30 minutes to cook.
            - For 2 of the days (weekend meals), suggest meals that can take up to 60 minutes to cook. These can be a bit more involved or special.
            - For ONE of the total {total_meals_for_ai} days, create a NEW, interesting dish that REMIXES one or more of the family's preferred meals, using similar ingredients but with a creative twist. This remixed meal can be a weekday or a weekend meal.
            All meals should be healthy, and the plan should include oily fish at least once across the {total_meals_for_ai} days.

            IMPORTANT GUIDELINES:
            1. For existing meal suggestions: Analyze the family's preferred meals to understand their taste. Suggest existing dishes that align with this taste.
            2. For the remixed meal: Be creative but ensure it's appealing and uses ingredients the family likely enjoys.
            3. Meal Composition: Each meal MUST include a significant source of meat or fish protein. Each meal MUST also include at least three different types of vegetables (these can be part of the main dish or as sides). Suggest appropriate accompaniments like salads or bread where suitable.
            4. Maintain variety and nutritional balance. Consider children's preferences.
            5. Suggest meals that can repurpose ingredients to reduce waste.
            6. You MUST include at least one meal containing oily fish (e.g., salmon, mackerel, sardines, trout) in the {total_meals_for_ai}-day plan. Clearly flag this meal.
            7. For each meal, provide a detailed list of ingredients (including name, quantity, unit, and category).
            8. For each meal, provide clear, step-by-step preparation instructions, including estimated timings, suitable for a ~30-minute total cooking time for weekday meals and up to 60 minutes for weekend meals.
            """
            
            # Extract ingredients from liked foods to help with remixing
            # liked_ingredients = self._extract_common_ingredients(liked_foods) # Commented out for performance
            
            user_prompt = f"""
            Please create a {total_meals_for_ai}-day meal plan for my family.
            The first {meal_count} meals should be for weekdays and take approximately 30 minutes to prepare and cook.
            The following 2 meals should be for the weekend (e.g., Day {meal_count + 1}, Day {meal_count + 2}) and can take up to 60 minutes to prepare and cook.
            It is very important that the plan includes at least one meal with oily fish (e.g., salmon, mackerel, sardines, trout).

            PREFERRED MEALS (use these to understand our taste and for the remixed meal): {safe_liked_foods_str}
            DISLIKED FOODS: {safe_disliked_foods_str}
            RECENT MEALS (please avoid repeating): {safe_recent_meals_str}

            IMPORTANT INSTRUCTIONS:
            1. Generate a total of {total_meals_for_ai} meal ideas.
            2. If {total_meals_for_ai > 1}, {total_meals_for_ai - 1} of these meals should be EXISTING, well-known dishes. For these, select meals that you think we would enjoy based on our PREFERRED MEALS list.
            3. ONE meal (or the only meal if {total_meals_for_ai == 1}) should be a CREATIVE REMIX of one or more of our PREFERRED MEALS.
            4. Ensure at least one meal in the plan contains oily fish.
            5. All meals should be unique within this plan.
            6. Meal Composition: Every meal must contain a meat or fish protein and at least three different vegetables (these can be part of the main dish or as sides).
            7. Accompaniments: Please suggest suitable accompaniments like a side salad, bread, or other relevant side dishes when appropriate for the meal.

            For each day, provide:
            1. "day": The day number (e.g., "Day 1", "Day 2", ... "Day {total_meals_for_ai}").
            2. "meal": The name of the meal.
            3. "description": Explanation (existing or remixed), including any suggested accompaniments.
            4. "is_remixed": true/false.
            5. "contains_oily_fish": true/false.
            6. "ingredients": List of objects (name, quantity, unit, category), including all main components, vegetables, and key accompaniment ingredients.
            7. "preparation_instructions": List of strings (steps with timings appropriate for weekday ~30min or weekend ~60min).

            Format the response as a JSON object with this structure:
            {{  # Escaped curly braces for f-string
                "days": [
                    // ... (Example for a weekday meal, ~30 min) ...
                    {{
                        "day": "Day 1", 
                        "meal": "Quick Weekday Salmon with Roasted Veg & Salad", 
                        "description": "A fast and healthy salmon dish with roasted asparagus, broccoli, and cherry tomatoes, served with a side of mixed salad leaves. Similar to your liked grilled fish.",
                        "is_remixed": false, 
                        "contains_oily_fish": true,
                        "ingredients": [
                            {{"name": "Salmon Fillet", "quantity": "2", "unit": "pieces", "category": "Fish"}},
                            {{"name": "Broccoli", "quantity": "1", "unit": "small head", "category": "Produce"}},
                            {{"name": "Asparagus", "quantity": "1", "unit": "bunch", "category": "Produce"}},
                            {{"name": "Cherry Tomatoes", "quantity": "1", "unit": "punnet", "category": "Produce"}},
                            {{"name": "Mixed Salad Leaves", "quantity": "50", "unit": "grams", "category": "Produce"}},
                            {{"name": "Olive Oil", "quantity": "1", "unit": "tbsp", "category": "Pantry"}}
                        ],
                        "preparation_instructions": ["Step 1: Toss vegetables with olive oil, roast for 15 mins.", "Step 2: Pan-fry salmon for 10 mins.", "Step 3: Serve salmon with roasted vegetables and salad."]
                    }},
                    // ... (Example for a weekend meal, up to 60 min) ...
                    {{
                        "day": "Day {meal_count + 1}", 
                        "meal": "Weekend Special Roast Chicken with Root Vegetables",
                        "description": "A more involved roast chicken with potatoes, carrots, and onions, served with gravy. Perfect for a weekend.",
                        "is_remixed": false, 
                        "contains_oily_fish": false,
                        "ingredients": [
                            {{"name": "Whole Chicken", "quantity": "1", "unit": "kg", "category": "Poultry"}},
                            {{"name": "Potatoes", "quantity": "500", "unit": "grams", "category": "Produce"}},
                            {{"name": "Carrots", "quantity": "3", "unit": "medium", "category": "Produce"}},
                            {{"name": "Onion", "quantity": "1", "unit": "large", "category": "Produce"}},
                            {{"name": "Gravy Granules", "quantity": "2", "unit": "tbsp", "category": "Pantry"}}
                        ],
                        "preparation_instructions": ["Step 1: Prep chicken and vegetables (15 mins)...", "Step 2: Roast for 45-60 mins until cooked.", "Step 3: Make gravy and serve."]
                    }},
                     {{
                        "day": "Day {meal_count + 2}", 
                        "meal": "Hearty Weekend Beef Stew with Crusty Bread",
                        "description": "A slow-cooked beef stew with carrots, celery, onions, and peas. Great for a relaxing weekend, served with crusty bread.",
                        "is_remixed": false, 
                        "contains_oily_fish": false,
                        "ingredients": [
                            {{"name": "Beef Chuck", "quantity": "500", "unit": "grams", "category": "Meat"}},
                            {{"name": "Carrots", "quantity": "2", "unit": "large", "category": "Produce"}},
                            {{"name": "Celery Sticks", "quantity": "2", "unit": "stalks", "category": "Produce"}},
                            {{"name": "Onion", "quantity": "1", "unit": "medium", "category": "Produce"}},
                            {{"name": "Peas", "quantity": "100", "unit": "grams", "category": "Produce/Frozen"}},
                            {{"name": "Crusty Bread", "quantity": "1", "unit": "loaf", "category": "Bakery"}}
                        ],
                        "preparation_instructions": ["Step 1: Brown beef (10 mins)...", "Step 2: Sauté vegetables (5 mins)...", "Step 3: Simmer stew for 45-50 mins...", "Step 4: Serve with bread."]
                    }},
                     {{
                        "day": "Day X", 
                        "meal": "Creative Remixed Turkey Tacos with All The Fixings",
                        "description": "A fun remix of your favorite taco night, using ground turkey. Served with lettuce, tomatoes, bell peppers, and salsa.",
                        "is_remixed": true,
                        "contains_oily_fish": false,
                        "ingredients": [
                            {{"name": "Ground Turkey", "quantity": "250", "unit": "grams", "category": "Poultry"}},
                            {{"name": "Corn Tortillas", "quantity": "8", "unit": "pieces", "category": "Bakery"}},
                            {{"name": "Lettuce", "quantity": "1/2", "unit": "head", "category": "Produce"}},
                            {{"name": "Tomatoes", "quantity": "2", "unit": "medium", "category": "Produce"}},
                            {{"name": "Bell Pepper", "quantity": "1", "unit": "medium", "category": "Produce"}},
                            {{"name": "Salsa", "quantity": "1", "unit": "jar", "category": "Condiment"}},
                            {{"name": "Taco Seasoning", "quantity": "1", "unit": "packet", "category": "Pantry"}}
                        ],
                        "preparation_instructions": ["Step 1: Cook turkey with taco seasoning (15 mins)...", "Step 2: Warm tortillas and chop vegetables...", "Step 3: Assemble tacos with all the fixings."]
                    }}
                ]
            }}

            IMPORTANT: Your response must be valid JSON. Ensure exactly one meal has "is_remixed": true (unless {total_meals_for_ai == 0}, then none). The total number of meals must be {total_meals_for_ai}.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            console.print(f"[red]Error generating meal plan with AI: {str(e)}[/red]")
            return None
    
    def _extract_common_ingredients(self, meals: List[str]) -> List[str]:
        """Extract common ingredients from a list of meals using GPT."""
        if not meals or not self.client:
            # Fallback if no meals or no API access
            return ["chicken", "beef", "fish", "pasta", "rice", "potatoes", "vegetables"]
        
        try:
            # Construct prompt for ingredient extraction
            system_prompt = """
            You are a helpful assistant that identifies common ingredients in meals.
            Your task is to analyze meal names and extract the most likely key ingredients.
            Focus on main proteins, starches, and distinctive ingredients that define the dish.
            """
            
            user_prompt = f"""
            Please identify the most common ingredients likely found in these meals:
            {', '.join(meals)}
            
            Return ONLY a comma-separated list of ingredients, nothing else.
            Focus on the main ingredients that define these dishes.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract ingredients from response
            ingredients_text = response.choices[0].message.content.strip()
            ingredients = [ingredient.strip() for ingredient in ingredients_text.split(',')]
            
            return ingredients
            
        except Exception as e:
            console.print(f"[yellow]Error extracting ingredients with AI: {str(e)}. Using fallback.[/yellow]")
            # Fallback ingredients if API call fails
            return ["chicken", "beef", "fish", "pasta", "rice", "potatoes", "vegetables"]
            
    def create_remixed_meal(self, base_meal: str, all_liked_meals: List[str], family_info: Dict[str, Any] = None) -> Tuple[str, str, bool]:
        """Create a remixed version of a meal with a creative twist using GPT."""
        if not self.client:
            return None, None, False
            
        # Use default family info if none provided
        if family_info is None:
            family_info = {
                "members": 4,
                "children_ages": [6, 8]
            }
        
        try:
            # Get ingredients from base meal and other liked meals
            base_ingredients = self._extract_common_ingredients([base_meal])
            all_ingredients = self._extract_common_ingredients(all_liked_meals)
            
            # Extract family details
            members = family_info.get("members", 4)
            children_ages = family_info.get("children_ages", [6, 8])
            children_text = ""
            
            if children_ages and len(children_ages) > 0:
                children_text = f"that children aged {', '.join(map(str, children_ages))} would enjoy"
            else:
                children_text = "that the whole family would enjoy"
            
            # Construct prompt for meal remixing
            system_prompt = f"""
            You are a creative culinary expert specializing in remixing familiar dishes into exciting new variations.
            Your task is to create innovative meal ideas that maintain the essence of favorite dishes while introducing new elements.
            Focus on family-friendly meals {children_text}, with preparation time around 30 minutes.
            """
            
            # Sometimes create a fusion dish by combining two meals
            other_meals = [m for m in all_liked_meals if m != base_meal]
            fusion_meal = ""
            if other_meals and random.random() < 0.4:  # 40% chance of fusion
                fusion_meal = random.choice(other_meals)
            
            fusion_text = f"Consider combining elements of {base_meal} with {fusion_meal}." if fusion_meal else ""
            
            user_prompt = f"""
            Please create a remixed version of {base_meal} that would appeal to a family with young children.
            {fusion_text}
            
            Key ingredients in the original dish likely include: {', '.join(base_ingredients)}
            Other ingredients the family enjoys: {', '.join(all_ingredients[:10])}  # Limit to avoid overwhelming
            
            Return your response in this exact format:
            NAME: [creative name for the remixed dish]
            DESCRIPTION: [brief description explaining how this relates to the original dish and what makes it special]
            CONTAINS_OILY_FISH: [true/false]
            
            The name should be catchy and descriptive. The description should be 1-2 sentences explaining the connection to the original dish.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract name and description from response
            content = response.choices[0].message.content.strip()
            
            # Parse the response to extract name, description, and oily fish status
            name_match = re.search(r"NAME:\s*(.+)\n", content + "\n")
            desc_match = re.search(r"DESCRIPTION:\s*(.+)", content)
            fish_match = re.search(r"CONTAINS_OILY_FISH:\s*(true|false)", content.lower())
            
            if name_match and desc_match:
                remixed_name = name_match.group(1).strip()
                description = desc_match.group(1).strip()
                contains_oily_fish = fish_match and fish_match.group(1).lower() == "true"
                return remixed_name, description, contains_oily_fish
            else:
                # Fallback if parsing fails
                return f"Creative {base_meal} Remix", f"A new twist on {base_meal} using favorite ingredients in an exciting way.", False
            
        except Exception as e:
            console.print(f"[yellow]Error creating remixed meal with AI: {str(e)}. Using fallback.[/yellow]")
            return None, None, False
