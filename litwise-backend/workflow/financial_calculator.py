"""
Deterministic Financial Calculation Engine
Handles all numeric computations with full precision and audit trails
"""

from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import re
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CalculationResult:
    """Structured result with full audit trail"""
    result: Decimal
    formula: str
    components: Dict[str, Any]
    precision_level: str  # 'exact', 'rounded', 'estimated'
    source_page: Optional[int] = None
    source_table: Optional[str] = None
    intermediate_steps: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """❌ ISSUE #2: Guard against NaN/infinity in output"""
        result_dict = asdict(self)
        
        # ✅ FIX: Validate result before converting
        if self.result.is_nan() or self.result.is_infinite():
            raise ValueError(f"CALCULATION ERROR: Result is {self.result} (NaN or Infinity not allowed)")
        
        result_dict['result'] = float(self.result)
        return result_dict
    
    def format_bps(self) -> int:
        """Convert result to basis points (rounded)"""
        # ✅ FIX #2: NaN guard
        if self.result.is_nan() or self.result.is_infinite():
            raise ValueError(f"Cannot format NaN/Infinity as basis points")
        return int((self.result * Decimal('10000')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    
    def format_percentage(self, decimals: int = 2) -> str:
        """❌ ISSUE #5: Format with SANE financial precision (default 2 decimals, not 4)"""
        # ✅ FIX #2: NaN guard
        if self.result.is_nan() or self.result.is_infinite():
            raise ValueError(f"Cannot format NaN/Infinity as percentage")
        
        # ✅ FIX #5: Financial precision - use 2 decimals by default
        pct = (self.result * Decimal('100')).quantize(
            Decimal(f'0.{"0" * decimals}'), 
            rounding=ROUND_HALF_UP
        )
        return f"{pct}%"


class FinancialCalculator:
    """
    Deterministic calculation engine for financial metrics.
    All computations use Decimal for precision.
    """
    
    def __init__(self):
        self.calculation_history: List[CalculationResult] = []
        
    def calculate_margin(
        self,
        numerator: float,
        denominator: float,
        label: str = "Margin",
        source_page: Optional[int] = None,
        source_table: Optional[str] = None
    ) -> CalculationResult:
        """
        ❌ ISSUE #2 & #6: Calculate margin with HARD GUARDS against NaN and zero division
        
        Args:
            numerator: UTOP, profit, or other metric
            denominator: Sales, revenue, or base
            label: Description of margin
            
        Returns:
            CalculationResult with exact ratio
            
        Raises:
            ValueError: If inputs are invalid (headers, non-numeric, NaN, zero denominator)
        """
        # [LITWISE FINANCIAL LOGIC]: Strict Input Validation
        # Why we do this: LLMs are terrible at math. We don't let the LLM do the math. 
        # We only let the LLM extract the numbers, and then THIS Python function does the math.
        
        # 1. Validate both the numerator and denominator to ensure they are actual numbers
        # The _validate_and_convert method will throw a hard error if the LLM hallucinated the number.
        num = self._validate_and_convert(numerator, "numerator", label)
        denom = self._validate_and_convert(denominator, "denominator", label)
        
        # 2. Hard guard against ZeroDivisionError. 
        # If the denominator is 0, the calculation is mathematically impossible.
        if denom == 0:
            raise ValueError(
                f"❌ HARD FAILURE: Cannot calculate {label} - denominator is ZERO. "
                f"Value not available in source document."
            )
        
        # 3. Hard guard against NaN (Not a Number) inputs.
        # Python's Decimal library allows 'NaN', but financial reports do not!
        if num.is_nan() or denom.is_nan():
            raise ValueError(
                f"❌ HARD FAILURE: Cannot calculate {label} - input is NaN (numerator={num}, denominator={denom})"
            )
        
        result = num / denom
        
        # ✅ FIX #2: Validate result
        if result.is_nan() or result.is_infinite():
            raise ValueError(
                f"❌ HARD FAILURE: {label} calculation produced {result} (NaN/Infinity not allowed)"
            )
        
        return CalculationResult(
            result=result,
            formula=f"{numerator} / {denominator}",
            components={
                "numerator": float(num),
                "denominator": float(denom),
                "label": label
            },
            precision_level='exact',
            source_page=source_page,
            source_table=source_table,
            intermediate_steps=[
                f"Step 1: {label} = {numerator} / {denominator}",
                f"Step 2: Result = {result}"
            ]
        )
    
    def _validate_and_convert(self, value: Any, field_name: str, context: str = "") -> Decimal:
        """
        ❌ ISSUE #1 & #6: HARD VALIDATION - Reject ANY fabricated/hypothetical values
        """
        # [LITWISE FINANCIAL LOGIC]: The Gatekeeper Function
        # Why we do this: PDFs are messy. Sometimes the LLM extracts "(in millions)" instead of "1.5".
        # This function catches bad extractions and enforces strict Decimal types to prevent floating-point errors.
        
        # 1. Check for empty or missing values immediately.
        # If it's empty, it means the LLM couldn't find the number in the PDF.
        if value is None or value == '' or str(value).strip() == '':
            raise ValueError(
                f"❌ HARD FAILURE: {field_name} is missing/empty. "
                f"Value not available in source document (context: {context}). "
                f"CANNOT PROCEED - no fabricated values allowed."
            )
        
        # 2. If the value is already a standard Python number type (int, float, Decimal)
        if isinstance(value, (int, float, Decimal)):
            # Convert it strictly to a Decimal. 
            # (In finance, never use 'float' because 0.1 + 0.2 = 0.30000000000000004 in floats!)
            result = Decimal(str(value))
            
            # 3. Double check that the Decimal isn't technically "NaN"
            if result.is_nan():
                raise ValueError(
                    f"❌ HARD FAILURE: {field_name} is NaN (context: {context}). "
                    f"Value not available in source document."
                )
            if result.is_infinite():
                raise ValueError(
                    f"❌ HARD FAILURE: {field_name} is Infinity (context: {context}). "
                    f"Invalid value in source document."
                )
            return result
        
        # 4. If the value is a String, we need to make sure it's actually a number
        # and not a table header that the LLM accidentally extracted.
        value_str = str(value).strip()
        
        # 5. Define Regex patterns for common PDF table headers and placeholders
        descriptor_patterns = [
            r'\(in (millions?|thousands?|billions?)\)', # e.g., "(in millions)"
            r'\(in (CHF|USD|EUR|GBP|JPY)\)',            # e.g., "(in USD)"
            r'\((un)?audited\)',                        # e.g., "(unaudited)"
            r'(20\d{2})',                               # e.g., "2024" (We don't want to use years as financial values)
            r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Months
            r'(millions?|thousands?|billions?) of',
            r'^total$',
            r'^subtotal$',
            r'^note \d+',                               # e.g., "Note 4"
            r'^n/?a$',                                  # e.g., "N/A"
            r'^-$',                                     # e.g., "-" (Common in financial tables for zero)
            r'^\.\.\.$',  
            r'not applicable',
            r'not available',
            r'not disclosed',
        ]
        
        # 6. Loop through all the Regex patterns to see if the extracted string matches any of them
        value_lower = value_str.lower()
        for pattern in descriptor_patterns:
            if re.search(pattern, value_lower):
                # 7. If it matches a header, THROW AN ERROR! Do not allow the calculation to proceed.
                raise ValueError(
                    f"❌ HARD FAILURE: {field_name} appears to be a header/descriptor/placeholder, not a numeric value. "
                    f"Value: '{value_str}' (context: {context}). "
                    f"Value not available in source document."
                )
        
        # 8. Try to convert the remaining strings to a Decimal format.
        try:
            # Remove characters commonly used in financial formatting
            cleaned = value_str.replace(',', '').replace(' ', '').replace('$', '').replace('€', '')
            
            # Handle parentheses (negative numbers)
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            
            result = Decimal(cleaned)
            
            # ✅ FIX #2: Validate result
            if result.is_nan():
                raise ValueError(f"Result is NaN")
            if result.is_infinite():
                raise ValueError(f"Result is Infinity")
            
            return result
        
        except Exception as e:
            raise ValueError(
                f"❌ HARD FAILURE: Cannot convert {field_name} to number. "
                f"Value: '{value_str}' (context: {context}). "
                f"Error: {e}. Value not available in source document."
            )
    
    def calculate_margin_change(
        self,
        current_margin: float,
        previous_margin: float,
        label: str = "Margin Change",
        return_bps: bool = True,
        source_page: Optional[int] = None
    ) -> CalculationResult:
        """
        ❌ ISSUE #2 & #5: Calculate margin change with NaN guards and sane precision
        
        Args:
            current_margin: Current period margin (as decimal, e.g., 0.2227 for 22.27%)
            previous_margin: Previous period margin
            return_bps: If True, return basis points; else percentage points
            
        Returns:
            CalculationResult with precise difference
            
        Raises:
            ValueError: If inputs are invalid or missing
        """
        # ✅ FIX #1 & #6: Hard validation - no fabrication
        curr = self._validate_and_convert(current_margin, "current_margin", label)
        prev = self._validate_and_convert(previous_margin, "previous_margin", label)
        
        diff = curr - prev
        
        # ✅ FIX #2: Validate result
        if diff.is_nan() or diff.is_infinite():
            raise ValueError(
                f"❌ HARD FAILURE: {label} calculation produced {diff} (NaN/Infinity not allowed)"
            )
        
        # ✅ FIX #5: Calculate with SANE financial precision
        if return_bps:
            # Round to 2 decimals for basis points (e.g., 7.70 bps)
            bps = (diff * Decimal('10000')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            result_desc = f"{bps} bps"
        else:
            # Round to 2 decimals for percentage points (e.g., 0.08%)
            pct_points = (diff * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            result_desc = f"{pct_points} percentage points"
        
        return CalculationResult(
            result=diff,
            formula=f"{current_margin} - {previous_margin}",
            components={
                "current_margin": float(curr),
                "previous_margin": float(prev),
                "difference": float(diff),
                "basis_points": int((diff * Decimal('10000')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) if return_bps else None,
                "percentage_points": float(diff * Decimal('100')) if not return_bps else None
            },
            precision_level='exact',
            source_page=source_page,
            intermediate_steps=[
                f"Step 1: Current margin = {curr} ({curr * 100}%)",
                f"Step 2: Previous margin = {prev} ({prev * 100}%)",
                f"Step 3: Difference = {curr} - {prev} = {diff}",
                f"Step 4: {result_desc}"
            ]
        )
    
    def calculate_reconciliation(
        self,
        opening_balance: float,
        movements: Dict[str, float],
        closing_balance: float,
        label: str = "Reconciliation",
        source_page: Optional[int] = None
    ) -> Tuple[CalculationResult, bool, List[str]]:
        """
        Perform reconciliation with validation
        
        Args:
            opening_balance: Starting value
            movements: Dict of movement descriptions and amounts
            closing_balance: Expected ending value
            
        Returns:
            Tuple of (CalculationResult, is_balanced, discrepancy_messages)
        """
        opening = Decimal(str(opening_balance))
        closing = Decimal(str(closing_balance))
        
        # Sum all movements
        total_movements = sum(Decimal(str(v)) for v in movements.values())
        
        # Calculate expected closing
        expected_closing = opening + total_movements
        
        # Check if balanced
        discrepancy = expected_closing - closing
        is_balanced = abs(discrepancy) < Decimal('0.01')  # Allow 1 cent tolerance
        
        discrepancy_messages = []
        if not is_balanced:
            discrepancy_messages.append(
                f"⚠️ Reconciliation mismatch: Expected {expected_closing}, Got {closing}, "
                f"Discrepancy: {discrepancy}"
            )
            discrepancy_messages.append(
                "Possible causes: Missing movements, incorrect signs, or data entry errors"
            )
        
        intermediate_steps = [
            f"Opening Balance: {opening}",
            "Movements:"
        ]
        for desc, amount in movements.items():
            intermediate_steps.append(f"  {desc}: {amount}")
        intermediate_steps.extend([
            f"Sum of Movements: {total_movements}",
            f"Expected Closing: {opening} + {total_movements} = {expected_closing}",
            f"Actual Closing: {closing}",
            f"Balanced: {'✓' if is_balanced else '✗'}"
        ])
        
        result = CalculationResult(
            result=expected_closing,
            formula=f"{opening_balance} + sum(movements)",
            components={
                "opening_balance": float(opening),
                "movements": {k: float(Decimal(str(v))) for k, v in movements.items()},
                "total_movements": float(total_movements),
                "expected_closing": float(expected_closing),
                "actual_closing": float(closing),
                "discrepancy": float(discrepancy),
                "is_balanced": is_balanced
            },
            precision_level='exact',
            source_page=source_page,
            source_table=label,
            intermediate_steps=intermediate_steps
        )
        
        return result, is_balanced, discrepancy_messages
    
    def calculate_ratio(
        self,
        value1: float,
        value2: float,
        label: str = "Ratio",
        format_type: str = "decimal"  # 'decimal', 'percentage', 'x_to_1'
    ) -> CalculationResult:
        """
        Calculate ratio between two values
        
        Args:
            value1: First value
            value2: Second value
            format_type: How to format result
            
        Returns:
            CalculationResult
        """
        v1 = Decimal(str(value1))
        v2 = Decimal(str(value2))
        
        if v2 == 0:
            raise ValueError(f"Cannot calculate {label}: divisor is zero")
        
        ratio = v1 / v2
        
        formatted_result = ratio
        if format_type == "percentage":
            formatted_result = ratio * Decimal('100')
        elif format_type == "x_to_1":
            formatted_result = ratio
        
        return CalculationResult(
            result=ratio,
            formula=f"{value1} / {value2}",
            components={
                "value1": float(v1),
                "value2": float(v2),
                "ratio": float(ratio),
                "format_type": format_type
            },
            precision_level='exact',
            intermediate_steps=[
                f"{label} = {v1} / {v2} = {ratio}"
            ]
        )
    
    def calculate_growth_rate(
        self,
        current_value: float,
        previous_value: float,
        label: str = "Growth Rate"
    ) -> CalculationResult:
        """
        ❌ ISSUE #2 & #6: Calculate growth rate with HARD GUARDS
        
        Args:
            current_value: Current period value
            previous_value: Previous period value
            
        Returns:
            CalculationResult with growth rate
            
        Raises:
            ValueError: If values missing or previous value is zero
        """
        # ✅ FIX #1 & #6: Hard validation
        curr = self._validate_and_convert(current_value, "current_value", label)
        prev = self._validate_and_convert(previous_value, "previous_value", label)
        
        # ✅ FIX #2: Hard guard - zero denominator
        if prev == 0:
            raise ValueError(
                f"❌ HARD FAILURE: Cannot calculate {label} - previous value is ZERO. "
                f"Growth rate undefined. Value not available in source."
            )
        
        growth_rate = (curr - prev) / prev
        
        # ✅ FIX #2: Validate result
        if growth_rate.is_nan() or growth_rate.is_infinite():
            raise ValueError(
                f"❌ HARD FAILURE: {label} calculation produced {growth_rate} (NaN/Infinity not allowed)"
            )
        
        return CalculationResult(
            result=growth_rate,
            formula=f"({current_value} - {previous_value}) / {previous_value}",
            components={
                "current_value": float(curr),
                "previous_value": float(prev),
                "absolute_change": float(curr - prev),
                "growth_rate": float(growth_rate),
                "growth_percentage": float(growth_rate * Decimal('100'))
            },
            precision_level='exact',
            intermediate_steps=[
                f"Absolute Change = {curr} - {prev} = {curr - prev}",
                f"Growth Rate = ({curr - prev}) / {prev} = {growth_rate}",
                f"Growth Percentage = {growth_rate * 100}%"
            ]
        )
    
    def validate_sum(
        self,
        values: List[float],
        expected_total: float,
        tolerance: float = 0.01,
        label: str = "Sum Validation"
    ) -> Tuple[bool, Decimal, str]:
        """
        Validate that sum of values matches expected total
        
        Returns:
            Tuple of (is_valid, actual_sum, message)
        """
        actual_sum = sum(Decimal(str(v)) for v in values)
        expected = Decimal(str(expected_total))
        tol = Decimal(str(tolerance))
        
        diff = abs(actual_sum - expected)
        is_valid = diff <= tol
        
        if is_valid:
            message = f"✓ {label}: Sum validated ({actual_sum} ≈ {expected})"
        else:
            message = f"✗ {label}: Sum mismatch (actual: {actual_sum}, expected: {expected}, diff: {diff})"
        
        return is_valid, actual_sum, message


# Global calculator instance
calculator = FinancialCalculator()
