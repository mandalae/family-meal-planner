import json
import os
from typing import List, Dict, Any

class PreferenceManager:
    """Manages family food preferences and meal history."""
    
    def __init__(self, data_file: str = "preferences.json"):
        """Initialize the preference manager with a data file."""
        self.data_file = data_file
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """Load preference data from file or create default structure."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._create_default_data()
        else:
            return self._create_default_data()
    
    def _create_default_data(self) -> Dict[str, Any]:
        """Create default data structure for preferences."""
        return {
            "family_info": {
                "members": 4,
                "children_ages": [6, 8]
            },
            "preferences": {
                "liked_foods": [
                    "Hotdogs",
                    "Burgers",
                    "Chicken nuggets and chips",
                    "Fish tacos",
                    "Fish and broccoli",
                    "Fajitas",
                    "Bolognese"
                ],
                "disliked_foods": [],
                "dietary_requirements": ["Include oily fish weekly"],
                "meal_count": 3  # Default number of meals to generate
            },
            "meal_history": [],
            "shopping_lists": {}  # Store shopping lists by meal plan ID
        }
    
    def save(self) -> None:
        """Save current preferences to file."""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def add_preference(self, food: str, liked: bool = True) -> None:
        """Add a food preference."""
        if liked:
            if food not in self.data["preferences"]["liked_foods"]:
                self.data["preferences"]["liked_foods"].append(food)
        else:
            if food not in self.data["preferences"]["disliked_foods"]:
                self.data["preferences"]["disliked_foods"].append(food)
        self.save()
    
    def remove_preference(self, food: str, liked: bool = True) -> bool:
        """Remove a food preference."""
        try:
            if liked:
                self.data["preferences"]["liked_foods"].remove(food)
            else:
                self.data["preferences"]["disliked_foods"].remove(food)
            self.save()
            return True
        except ValueError:
            return False
    
    def get_liked_foods(self) -> List[str]:
        """Get list of liked foods."""
        return self.data["preferences"]["liked_foods"]
    
    def get_disliked_foods(self) -> List[str]:
        """Get list of disliked foods."""
        return self.data["preferences"]["disliked_foods"]
    
    def add_meal_to_history(self, meal_plan: Dict[str, Any]) -> None:
        """Add a meal plan to history."""
        self.data["meal_history"].append(meal_plan)
        # Keep only the last 10 meal plans
        if len(self.data["meal_history"]) > 10:
            # Remove shopping lists for old meal plans
            for old_plan in self.data["meal_history"][:-10]:
                plan_id = old_plan.get("id")
                if plan_id and plan_id in self.data.get("shopping_lists", {}):
                    del self.data["shopping_lists"][plan_id]
            
            self.data["meal_history"] = self.data["meal_history"][-10:]
        self.save()
    
    def get_meal_history(self) -> List[Dict[str, Any]]:
        """Get meal history."""
        # Reload data from file to ensure we have the latest meal history
        self.data = self._load_data()
        return self.data["meal_history"]
        
    def reload(self) -> None:
        """Reload data from file."""
        self.data = self._load_data()
        
    def store_shopping_list(self, meal_plan_id: str, shopping_list: List[Dict[str, Any]]) -> None:
        """Store a shopping list for a specific meal plan."""
        if "shopping_lists" not in self.data:
            self.data["shopping_lists"] = {}
        
        self.data["shopping_lists"][meal_plan_id] = shopping_list
        self.save()
    
    def get_shopping_list(self, meal_plan_id: str) -> List[Dict[str, Any]]:
        """Get a shopping list for a specific meal plan."""
        return self.data.get("shopping_lists", {}).get(meal_plan_id, [])
    
    def has_shopping_list(self, meal_plan_id: str) -> bool:
        """Check if a shopping list exists for a specific meal plan."""
        return meal_plan_id in self.data.get("shopping_lists", {})
        
    def get_meal_count(self) -> int:
        """Get the number of meals to generate."""
        return self.data["preferences"].get("meal_count", 3)  # Default to 3 if not set
    
    def set_meal_count(self, count: int) -> None:
        """Set the number of meals to generate."""
        if count < 1:
            count = 1  # Minimum of 1 meal
        elif count > 7:
            count = 7  # Maximum of 7 meals
            
        self.data["preferences"]["meal_count"] = count
        self.save()
