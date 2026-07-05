from utils.expense_calculator import Calculator
from typing import List
from langchain.tools import tool

class CalculatorTool:
    def __init__(self):
        self.calculator = Calculator()
        self.calculator_tool_list = self._setup_tools()

    @staticmethod
    def _to_float(value):
        """Convert tool inputs coming from the LLM into numeric values safely."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, list):
            raise TypeError("Expected a numeric value, got a list")
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if cleaned.startswith("$"):
                cleaned = cleaned[1:]
            return float(cleaned)
        raise TypeError(f"Expected a numeric value, got {type(value).__name__}")

    @classmethod
    def _flatten_costs(cls, costs):
        """Flatten nested cost values and coerce each item to float."""
        flattened = []
        for cost in costs:
            if isinstance(cost, list):
                flattened.extend(cls._flatten_costs(cost))
            else:
                flattened.append(cls._to_float(cost))
        return flattened

    def _setup_tools(self) -> List:
        """Setup all tools for the calculator tool"""
        @tool
        def estimate_total_hotel_cost(price_per_night: str, total_days: float) -> float:
            """Calculate total hotel cost"""
            nightly_rate = self._to_float(price_per_night)
            nights = self._to_float(total_days)
            return self.calculator.multiply(nightly_rate, nights)
        
        @tool
        def calculate_total_expense(costs: list[float]) -> float:
            """Calculate total expense of the trip from a list of costs"""
            numeric_costs = self._flatten_costs(costs)
            return self.calculator.calculate_total(numeric_costs)
        
        @tool
        def calculate_daily_expense_budget(total_cost: float, days: int) -> float:
            """Calculate daily expense"""
            return self.calculator.calculate_daily_budget(self._to_float(total_cost), int(days))
        
        return [estimate_total_hotel_cost, calculate_total_expense, calculate_daily_expense_budget]