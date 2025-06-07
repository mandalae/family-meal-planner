import os
import re
import json
import requests
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables
load_dotenv()

# Initialize console for rich output
console = Console()

class ShoppingListManager:
    """Manages shopping lists and integrates with online grocery services."""
    
    def __init__(self):
        """Initialize the shopping list manager."""
        self.tesco_api_key = os.getenv("TESCO_API_KEY")
        self.tesco_user_id = os.getenv("TESCO_USER_ID")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        # Initialize OpenAI client if API key is available
        if self.openai_api_key:
            try:
                self.client = OpenAI(api_key=self.openai_api_key)
                console.print("[green]OpenAI client initialized for ingredient normalization[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not initialize OpenAI client: {str(e)}[/yellow]")
                console.print("[yellow]Will use regex-based ingredient processing instead[/yellow]")
        
    def generate_shopping_list(self, meal_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a shopping list from a meal plan."""
        processed_ingredients_map = {}
        raw_ingredient_strings = []

        # Extract and segregate ingredients from the meal plan
        for day in meal_plan.get("days", []):
            recipe = day.get("recipe", {})
            ingredients = recipe.get("ingredients", [])
            for ing in ingredients:
                if isinstance(ing, dict) and all(k in ing for k in ["name", "quantity", "unit"]):
                    # This is a pre-structured ingredient (likely from AI)
                    name = ing["name"]
                    quantity = ing["quantity"]
                    unit = ing["unit"]
                    category = ing.get("category", self._determine_category(name)) # Use AI category or determine
                    original = ing.get("original", name)

                    # Attempt to convert quantity to float for aggregation
                    try:
                        quantity_val = float(quantity)
                    except ValueError:
                        # If quantity is not a number (e.g., "to taste"), handle as a unique item or skip aggregation
                        # For simplicity, we'll add it as is and rely on later steps or manual review
                        key = f"{name.lower()}_{unit.lower()}_{category.lower()}_non_numeric_{len(processed_ingredients_map)}"
                        processed_ingredients_map[key] = {
                            "name": name,
                            "quantity": quantity, # Keep original non-numeric quantity
                            "unit": unit,
                            "category": category,
                            "original": original
                        }
                        continue
                    
                    key = f"{name.lower()}_{unit.lower()}_{category.lower()}"
                    if key in processed_ingredients_map:
                        try:
                            processed_ingredients_map[key]["quantity"] += quantity_val
                        except TypeError: # if existing quantity was also non-numeric
                             pass # or handle error / log
                        processed_ingredients_map[key]["original"] += f", {original}"
                    else:
                        processed_ingredients_map[key] = {
                            "name": name,
                            "quantity": quantity_val,
                            "unit": unit,
                            "category": category,
                            "original": original
                        }
                elif isinstance(ing, str):
                    # This is a raw ingredient string
                    raw_ingredient_strings.append(ing)
                # Else: unknown ingredient format, skip or log

        # Process raw string ingredients if any
        normalized_raw_ingredients = []
        if raw_ingredient_strings:
            if self.client:
                normalized_raw_ingredients = self._normalize_ingredients_with_llm(raw_ingredient_strings)
            else:
                normalized_raw_ingredients = self._normalize_ingredients_with_regex(raw_ingredient_strings)
        
        # Combine normalized raw ingredients with already processed structured ingredients
        for item in normalized_raw_ingredients:
            name = item["name"]
            quantity = item["quantity"]
            unit = item["unit"]
            category = item.get("category", self._determine_category(name))
            original = item.get("original", name)
            
            try:
                quantity_val = float(quantity)
            except ValueError:
                key = f"{name.lower()}_{unit.lower()}_{category.lower()}_non_numeric_{len(processed_ingredients_map)}"
                processed_ingredients_map[key] = {
                    "name": name,
                    "quantity": quantity, 
                    "unit": unit,
                    "category": category,
                    "original": original
                }
                continue

            key = f"{name.lower()}_{unit.lower()}_{category.lower()}"
            if key in processed_ingredients_map:
                try:
                    processed_ingredients_map[key]["quantity"] += quantity_val
                except TypeError:
                    pass # if existing quantity was also non-numeric
                processed_ingredients_map[key]["original"] += f", {original}"
            else:
                processed_ingredients_map[key] = {
                    "name": name,
                    "quantity": quantity_val,
                    "unit": unit,
                    "category": category,
                    "original": original
                }

        # Convert map to list and filter pantry items
        final_shopping_list = []
        for item_data in processed_ingredients_map.values():
            if self._is_pantry_item(item_data["name"]):
                continue
            # Convert numeric quantities back to string if needed, or ensure consistency
            item_data["quantity"] = str(item_data["quantity"]) 
            final_shopping_list.append(item_data)
        
        # Sort by category
        final_shopping_list = self._categorize_and_sort(final_shopping_list)
        
        return final_shopping_list
    
    def _normalize_ingredients_with_llm(self, ingredients: List[str]) -> List[Dict[str, Any]]:
        """Use LLM to normalize and combine ingredients."""
        try:
            # Prepare the ingredients for the LLM
            ingredients_text = "\n".join(ingredients)
            
            # Create the prompt for the LLM
            prompt = f"""You are a helpful assistant that normalizes and combines ingredients for a shopping list.
            
            Here's a list of ingredients from various recipes:
            {ingredients_text}
            
            Please normalize these ingredients by:
            1. Identifying the same ingredients that appear multiple times and combining their quantities
            2. Converting all quantities to standard units where possible
            3. Standardizing ingredient names (e.g., 'tomato sauce' and 'pasta sauce' might be the same thing)
            4. Categorizing each ingredient (produce, meat, dairy, bakery, pantry, etc.)
            
            Return the results as a JSON array of objects with these properties:
            - name: The normalized ingredient name
            - quantity: The combined quantity as a number
            - unit: The standardized unit of measurement
            - category: The ingredient category
            - original: A comma-separated list of the original ingredient strings that were combined
            
            Example output format:
            [
              {{
                "name": "olive oil",
                "quantity": 5,
                "unit": "tablespoons",
                "category": "pantry",
                "original": "2 tbsp olive oil, 3 tablespoons olive oil"
              }},
              {{
                "name": "onion",
                "quantity": 2,
                "unit": "",
                "category": "produce",
                "original": "1 onion, diced, 1 onion"
              }}
            ]
            
            Only include the JSON array in your response, nothing else.
            """
            
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that normalizes and combines ingredients for a shopping list."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            # Extract the JSON response
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response to ensure it's valid JSON
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            # Parse the JSON
            normalized_ingredients = json.loads(result_text)
            
            console.print(f"[green]Successfully normalized {len(ingredients)} ingredients into {len(normalized_ingredients)} shopping items using LLM[/green]")
            return normalized_ingredients
            
        except Exception as e:
            console.print(f"[red]Error normalizing ingredients with LLM: {str(e)}[/red]")
            console.print("[yellow]Falling back to regex-based normalization[/yellow]")
            return self._normalize_ingredients_with_regex(ingredients)
    
    def _normalize_ingredients_with_regex(self, ingredients: List[str]) -> List[Dict[str, Any]]:
        """Use regex to normalize and combine ingredients (fallback method)."""
        ingredients_dict = {}  # To track and combine duplicate ingredients
        
        for ingredient in ingredients:
            # Process the ingredient to standardize it
            processed = self._process_ingredient(ingredient)
            
            # Skip if it's a common pantry item that most people have
            if self._is_pantry_item(processed["name"]):
                continue
            
            # Create a normalized key for better matching
            normalized_key = self._normalize_ingredient_name(processed["name"])
            
            # Combine quantities for the same ingredient
            if normalized_key in ingredients_dict:
                # If the units match, try to combine quantities
                if processed["unit"] == ingredients_dict[normalized_key]["unit"]:
                    ingredients_dict[normalized_key]["quantity"] += processed["quantity"]
                    ingredients_dict[normalized_key]["original"] += f", {ingredient}"
                else:
                    # If units don't match, keep as separate items
                    # Add a suffix to make the key unique
                    key = f"{normalized_key}_{processed['unit']}"
                    processed["original"] = ingredient
                    ingredients_dict[key] = processed
            else:
                processed["original"] = ingredient
                ingredients_dict[normalized_key] = processed
        
        # Assign categories to ingredients
        for key, item in ingredients_dict.items():
            item["category"] = self._determine_category(item["name"])
        
        return list(ingredients_dict.values())
    
    def _process_ingredient(self, ingredient: str) -> Dict[str, Any]:
        """Process an ingredient string to extract quantity, unit, and name."""
        # Default values
        result = {
            "name": ingredient,
            "quantity": 1,
            "unit": "",
            "original": ingredient
        }
        
        # Regular expression to match common quantity patterns
        # Examples: "500g flour", "2 tablespoons olive oil", "1/2 cup sugar"
        pattern = r'^([\d./]+)?\s*([a-zA-Z]*)\s+(.+)$'
        match = re.match(pattern, ingredient)
        
        if match:
            quantity_str, unit, name = match.groups()
            
            # Process quantity
            if quantity_str:
                try:
                    # Handle fractions like 1/2
                    if '/' in quantity_str:
                        num, denom = quantity_str.split('/')
                        quantity = float(num) / float(denom)
                    else:
                        quantity = float(quantity_str)
                    result["quantity"] = quantity
                except ValueError:
                    # If conversion fails, keep the default
                    pass
            
            # Process unit and name
            result["unit"] = unit.lower() if unit else ""
            result["name"] = name.strip().lower()
        
        return result
        
    def _normalize_ingredient_name(self, name: str) -> str:
        """Normalize ingredient name for better matching."""
        # Remove common words and descriptors
        words_to_remove = ["fresh", "frozen", "dried", "chopped", "diced", "sliced", "minced", 
                          "grated", "peeled", "cooked", "raw", "whole", "large", "small", "medium"]
        
        name = name.lower()
        
        for word in words_to_remove:
            name = re.sub(f"\\b{word}\\b", "", name)
        
        # Remove extra spaces and trim
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Handle common variations
        name_mapping = {
            "tomato sauce": "pasta sauce",
            "spaghetti sauce": "pasta sauce",
            "marinara": "pasta sauce",
            "bell pepper": "pepper",
            "capsicum": "pepper",
            "scallion": "green onion",
            "spring onion": "green onion"
        }
        
        for key, value in name_mapping.items():
            if key in name:
                name = name.replace(key, value)
        
        return name
        
    def _determine_category(self, ingredient: str) -> str:
        """Determine the category of an ingredient."""
        categories = {
            "produce": ["fruit", "vegetable", "tomato", "onion", "garlic", "potato", "carrot", "lettuce", "avocado", "lemon", "lime", "apple", "banana", "berry", "pepper", "cucumber", "zucchini", "squash", "broccoli", "cauliflower", "spinach", "kale", "herbs", "cilantro", "parsley", "basil", "mint"],
            "meat": ["beef", "chicken", "pork", "lamb", "turkey", "sausage", "bacon", "ham", "steak", "ground", "mince"],
            "seafood": ["fish", "salmon", "tuna", "cod", "shrimp", "prawn", "crab", "lobster", "mussel", "clam", "oyster", "scallop"],
            "dairy": ["milk", "cheese", "yogurt", "cream", "butter", "egg", "yoghurt", "sour cream", "buttermilk", "ice cream"],
            "bakery": ["bread", "bun", "roll", "tortilla", "wrap", "pita", "bagel", "croissant", "pastry", "cake", "cookie", "muffin"],
            "pantry": ["rice", "pasta", "noodle", "bean", "lentil", "chickpea", "flour", "sugar", "oil", "vinegar", "sauce", "spice", "herb", "cereal", "grain", "nut", "seed", "syrup", "honey", "jam", "peanut butter"],
            "frozen": ["frozen", "ice cream"],
            "canned": ["canned", "can of", "tin of", "tinned"],
            "beverages": ["water", "juice", "soda", "coffee", "tea", "wine", "beer", "alcohol", "drink"],
            "snacks": ["chip", "crisp", "pretzel", "popcorn", "cracker", "chocolate", "candy", "sweet"],
            "other": []
        }
        
        ingredient = ingredient.lower()
        
        for category, keywords in categories.items():
            if any(keyword in ingredient for keyword in keywords):
                return category
        
        return "other"
    
    def _is_pantry_item(self, ingredient: str) -> bool:
        """Check if an ingredient is a common pantry item."""
        pantry_items = [
            "salt", "pepper", "olive oil", "vegetable oil", "flour", "sugar",
            "baking powder", "baking soda", "vanilla extract", "garlic powder",
            "onion powder", "dried oregano", "dried basil", "dried thyme",
            "paprika", "cumin", "cinnamon", "nutmeg", "bay leaves"
        ]
        
        return any(item in ingredient.lower() for item in pantry_items)
    
    def _categorize_and_sort(self, shopping_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize and sort shopping list items."""
        # If items already have categories, just sort them
        if all("category" in item for item in shopping_list):
            return sorted(shopping_list, key=lambda x: (x["category"], x["name"]))
            
        # Otherwise, assign categories
        for item in shopping_list:
            if "category" not in item or not item["category"]:
                item["category"] = self._determine_category(item["name"])
        
        # Sort by category and then by name
        return sorted(shopping_list, key=lambda x: (x["category"], x["name"]))
    
    def add_to_tesco_cart(self, shopping_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add items from the shopping list to Tesco online shopping cart."""
        if not self.tesco_api_key or not self.tesco_user_id:
            return {
                "success": False,
                "message": "Tesco API credentials not configured. Please add TESCO_API_KEY and TESCO_USER_ID to your .env file."
            }
        
        try:
            # This is a mock implementation since we don't have actual Tesco API access
            # In a real implementation, you would make API calls to Tesco's services
            
            # Simulate API call to search for products
            products_found = []
            products_not_found = []
            
            for item in shopping_list:
                # Mock product search and add to cart
                product_result = self._mock_tesco_product_search(item["name"])
                
                if product_result["found"]:
                    products_found.append({
                        "name": item["name"],
                        "quantity": item["quantity"],
                        "unit": item["unit"],
                        "product_id": product_result["product_id"],
                        "product_name": product_result["product_name"],
                        "price": product_result["price"]
                    })
                else:
                    products_not_found.append(item["name"])
            
            # Mock adding products to cart
            cart_response = self._mock_tesco_add_to_cart(products_found)
            
            return {
                "success": True,
                "message": f"Added {len(products_found)} items to your Tesco cart.",
                "items_added": products_found,
                "items_not_found": products_not_found,
                "cart_url": "https://www.tesco.com/groceries/en-GB/trolley",
                "total_price": cart_response["total_price"]
            }
            
        except Exception as e:
            console.print(f"[red]Error adding items to Tesco cart: {str(e)}[/red]")
            return {
                "success": False,
                "message": f"Error adding items to Tesco cart: {str(e)}"
            }
    
    def _mock_tesco_product_search(self, item_name: str) -> Dict[str, Any]:
        """Mock Tesco product search API call."""
        # This is a simulation - in a real implementation, you would call Tesco's API
        # to search for products matching the item name
        
        # Simulate some common products
        common_products = {
            "chicken": {"found": True, "product_id": "12345", "product_name": "Tesco British Chicken Breast Fillets 650G", "price": 4.50},
            "beef": {"found": True, "product_id": "23456", "product_name": "Tesco Beef Mince 5% Fat 500G", "price": 3.25},
            "pasta": {"found": True, "product_id": "34567", "product_name": "Tesco Italian Spaghetti 500G", "price": 0.95},
            "rice": {"found": True, "product_id": "45678", "product_name": "Tesco Easy Cook Long Grain Rice 1Kg", "price": 1.75},
            "onion": {"found": True, "product_id": "56789", "product_name": "Tesco Brown Onions 1Kg", "price": 0.85},
            "garlic": {"found": True, "product_id": "67890", "product_name": "Tesco Garlic 4 Pack", "price": 0.79},
            "tomato": {"found": True, "product_id": "78901", "product_name": "Tesco Salad Tomatoes 6 Pack", "price": 0.90},
            "cheese": {"found": True, "product_id": "89012", "product_name": "Tesco British Mature Cheddar 460G", "price": 2.65},
            "broccoli": {"found": True, "product_id": "90123", "product_name": "Tesco Broccoli", "price": 0.65},
            "carrot": {"found": True, "product_id": "01234", "product_name": "Tesco Carrots 1Kg", "price": 0.45}
        }
        
        # Check if the item is in our mock database
        for key, product in common_products.items():
            if key in item_name.lower():
                return product
        
        # Simulate a 80% chance of finding a generic product for other items
        import random
        if random.random() < 0.8:
            return {
                "found": True,
                "product_id": f"generic_{hash(item_name) % 10000}",
                "product_name": f"Tesco {item_name.title()}",
                "price": round(random.uniform(0.5, 5.0), 2)
            }
        else:
            return {"found": False}
    
    def _mock_tesco_add_to_cart(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock adding products to Tesco cart."""
        # In a real implementation, you would call Tesco's API to add products to the cart
        
        # Calculate total price
        total_price = sum(product["price"] for product in products)
        
        return {
            "success": True,
            "total_price": round(total_price, 2),
            "items_count": len(products)
        }
