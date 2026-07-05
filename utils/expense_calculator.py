class Calculator:
    @staticmethod
    def _to_float(value):
        """Coerce a numeric-looking value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if cleaned.startswith("$"):
                cleaned = cleaned[1:]
            return float(cleaned)
        raise TypeError(f"Expected a numeric value, got {type(value).__name__}")

    @classmethod
    def _flatten_numbers(cls, values):
        """Flatten nested sequences of numbers into a plain list of floats."""
        flattened = []
        for value in values:
            if isinstance(value, list):
                flattened.extend(cls._flatten_numbers(value))
            else:
                flattened.append(cls._to_float(value))
        return flattened

    @staticmethod
    def multiply(a: int, b: int) -> int:
        """
        Multiply two integers.

        Args:
            a (int): The first integer.
            b (int): The second integer.

        Returns:
            int: The product of a and b.
        """
        return Calculator._to_float(a) * Calculator._to_float(b)
    
    @staticmethod
    def calculate_total(x: list[float]) -> float:
        """
        Calculate sum of the given list of numbers

        Args:
            x (list): List of floating numbers

        Returns:
            float: The sum of numbers in the list x
        """
        return sum(Calculator._flatten_numbers(x))
    
    @staticmethod
    def calculate_daily_budget(total: float, days: int) -> float:
        """
        Calculate daily budget

        Args:
            total (float): Total cost.
            days (int): Total number of days

        Returns:
            float: Expense for a single day
        """
        total_value = Calculator._to_float(total)
        days_value = int(days)
        return total_value / days_value if days_value > 0 else 0
    
    