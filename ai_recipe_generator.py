import os
import json
import random
import re
import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from rich.console import Console

# Initialize OpenAI
import openai

# Initialize console for rich output
console = Console()

class AIRecipeGenerator:
    """Handles AI-based recipe generation using OpenAI's API."""
    
    def __init__(self):
        """Initialize the AI recipe generator."""
        # Set up OpenAI client if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            # Set the API key for OpenAI 0.28.0
            openai.api_key = api_key
            self.client = True  # Just a flag to indicate we have API access
        else:
            self.client = None
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
            
            # Construct the prompt for the AI
            system_prompt = f"""
            You are a creative meal planning assistant for a family of {members} {children_text}.
            Create a {meal_count}-day meal plan with meals that take around 30 minutes to cook.
            The meals should be healthy and include oily fish at least once per week.
            
            IMPORTANT GUIDELINES:
            1. Analyze the family's preferred meals and identify key ingredients, flavor profiles, and cooking techniques they enjoy.
            2. Create new, interesting dishes that remix these preferred meals using similar ingredients but with creative twists.
            3. Maintain familiarity while introducing variety - use ingredients they already like in new combinations.
            4. Consider the children's preferences while ensuring nutritional balance.
            5. Suggest meals that repurpose ingredients across multiple days to reduce waste and simplify shopping.
            """
            
            # Extract ingredients from liked foods to help with remixing
            liked_ingredients = self._extract_common_ingredients(liked_foods)
            
            user_prompt = f"""
            Please create a creative {meal_count}-day meal plan for my family that remixes our favorite meals with new twists.
            
            PREFERRED MEALS: {', '.join(liked_foods)}
            DISLIKED FOODS: {', '.join(disliked_foods)}
            RECENT MEALS (please avoid repeating): {', '.join(recent_meals)}
            
            KEY INGREDIENTS WE ENJOY: {', '.join(liked_ingredients)}
            
            IMPORTANT INSTRUCTIONS:
            1. Create exactly {meal_count} NEW meal ideas that remix our preferred meals listed above
            2. Use similar ingredients to what we enjoy, but with creative new combinations
            3. Each meal should feel familiar yet exciting - like a new twist on something we already like
            4. Include at least one meal with oily fish (salmon, mackerel, sardines, etc.)
            5. Try to reuse ingredients across multiple days to reduce waste
            6. ENSURE EACH MEAL IS UNIQUE - do not duplicate meals or create very similar variations
            
            For each day, provide:
            1. The name of the meal (make it appealing and descriptive)
            2. A brief description explaining how it relates to our preferred meals
            3. Whether it contains oily fish
            
            Format the response as a JSON object with this structure:
            {{
                "days": [
                    {{
                        "day": "Day 1",
                        "meal": "Meal name",
                        "description": "Brief description explaining how this remixes our preferred meals",
                        "contains_oily_fish": true/false
                    }},
                    ...
                ]
            }}
            
            IMPORTANT: Your response must be valid JSON and contain exactly {meal_count} unique meals.
            """
            
            response = openai.ChatCompletion.create(
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
            
            response = openai.ChatCompletion.create(
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
            
            response = openai.ChatCompletion.create(
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
