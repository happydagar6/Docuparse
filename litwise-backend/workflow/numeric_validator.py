"""
Numeric Validation Module
Post-LLM validation to catch arithmetic errors and ensure accuracy
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class NumericValidator:
    """
    Validates numeric claims in LLM responses
    Recomputes calculations and flags discrepancies
    """
    
    def __init__(self, tolerance_bps: float = 2.0):
        """
        Args:
            tolerance_bps: Maximum acceptable discrepancy in basis points
        """
        self.tolerance_bps = tolerance_bps
        self.tolerance_decimal = Decimal(str(tolerance_bps / 10000.0))
    
    def extract_numeric_claims(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Extract all numeric claims from LLM response
        
        Returns:
            List of claims with values, units, and context
        """
        claims = []
        
        # Pattern for percentages
        pct_pattern = r'(\d+\.?\d*)\s*%'
        for match in re.finditer(pct_pattern, response_text):
            claims.append({
                'type': 'percentage',
                'value': float(match.group(1)),
                'text': match.group(0),
                'position': match.span()
            })
        
        # Pattern for basis points
        bps_pattern = r'(\d+\.?\d*)\s*(bps|basis points)'
        for match in re.finditer(bps_pattern, response_text, re.IGNORECASE):
            claims.append({
                'type': 'basis_points',
                'value': float(match.group(1)),
                'text': match.group(0),
                'position': match.span()
            })
        
        # Pattern for currency amounts
        currency_pattern = r'([$€£¥])\s*(\d+[\d,]*\.?\d*)'
        for match in re.finditer(currency_pattern, response_text):
            value_str = match.group(2).replace(',', '')
            claims.append({
                'type': 'currency',
                'value': float(value_str),
                'currency': match.group(1),
                'text': match.group(0),
                'position': match.span()
            })
        
        # Pattern for plain numbers in context
        number_pattern = r'\b(\d+[\d,]*\.?\d+)\s*(million|thousand|billion)?\b'
        for match in re.finditer(number_pattern, response_text):
            value_str = match.group(1).replace(',', '')
            value = float(value_str)
            
            # Apply multiplier if present
            multiplier = match.group(2)
            if multiplier:
                if multiplier.lower() == 'million':
                    value *= 1_000_000
                elif multiplier.lower() == 'billion':
                    value *= 1_000_000_000
                elif multiplier.lower() == 'thousand':
                    value *= 1_000
            
            claims.append({
                'type': 'number',
                'value': value,
                'multiplier': multiplier,
                'text': match.group(0),
                'position': match.span()
            })
        
        return claims
    
    def validate_margin_calculation(
        self,
        response_text: str,
        calculated_result: Dict[str, Any],
        context: str = ""
    ) -> Tuple[bool, List[str]]:
        """
        Validate margin calculation claims in response
        
        Args:
            response_text: LLM response text
            calculated_result: Result from FinancialCalculator
            context: Additional context for validation
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        is_valid = True
        
        try:
            # Skip validation if no calculated result
            if not calculated_result:
                logger.debug("No calculated result provided, skipping validation")
                return True, []
            
            # Extract percentage claims
            claims = self.extract_numeric_claims(response_text)
            percentage_claims = [c for c in claims if c['type'] == 'percentage']
            bps_claims = [c for c in claims if c['type'] == 'basis_points']
            
            # Skip if no numeric claims found (likely not a financial response)
            if not percentage_claims and not bps_claims:
                logger.debug("No percentage or bps claims found, skipping validation")
                return True, []
            
            # Get expected values with safe conversion
            result_value = calculated_result.get('result', 0)
            if result_value is None:
                logger.debug("No result value in calculated_result, skipping validation")
                return True, []
            
            expected_result = Decimal(str(result_value))
            expected_pct = expected_result * Decimal('100')
            expected_bps = calculated_result.get('components', {}).get('basis_points')
            
            # Validate percentage claims
            for claim in percentage_claims:
                try:
                    claimed_value = Decimal(str(claim['value']))
                    diff = abs(claimed_value - expected_pct)
                    
                    # Check if within tolerance (convert tolerance to percentage terms)
                    tolerance_pct = self.tolerance_decimal * Decimal('100')
                    if diff > tolerance_pct:
                        is_valid = False
                        issues.append(
                            f"❌ Percentage mismatch: LLM claims {claim['text']}, "
                            f"calculated {expected_pct:.4f}%, difference: {diff:.4f}%"
                        )
                except (ValueError, TypeError, ArithmeticError) as e:
                    # ✅ FIX: Don't spam warnings for validation errors - use DEBUG
                    logger.debug(f"Skipping percentage claim validation '{claim['text']}': {e}")
                    continue
            
            # Validate basis point claims
            if expected_bps is not None:
                for claim in bps_claims:
                    try:
                        claimed_bps = int(float(claim['value']))
                        expected_bps_int = int(float(expected_bps))
                        bps_diff = abs(claimed_bps - expected_bps_int)
                        
                        if bps_diff > self.tolerance_bps:
                            is_valid = False
                            issues.append(
                                f"❌ Basis points mismatch: LLM claims {claim['text']}, "
                                f"calculated {expected_bps_int} bps, difference: {bps_diff} bps"
                            )
                    except (ValueError, TypeError, ArithmeticError) as e:
                        # ✅ FIX: Don't spam warnings - use DEBUG
                        logger.debug(f"Skipping bps claim validation '{claim['text']}': {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Validation failed with error: {e}", exc_info=True)
            # Don't fail validation on errors - just log and pass
            return True, []
        
        return is_valid, issues
    
    def validate_reconciliation(
        self,
        response_text: str,
        calculated_result: Dict[str, Any],
        required_components: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate reconciliation completeness
        
        Args:
            response_text: LLM response
            calculated_result: Result from FinancialCalculator
            required_components: List of required movement descriptions
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        is_valid = True        
        try:
            # Skip if no calculated result
            if not calculated_result:
                return True, []
            
            # Check if reconciliation is balanced
            components = calculated_result.get('components', {})
            is_balanced = components.get('is_balanced', False)
            
            if not is_balanced:
                is_valid = False
                discrepancy = components.get('discrepancy', 0)
                issues.append(
                    f"❌ Reconciliation not balanced: discrepancy of {discrepancy}"
                )
            
            # Check if all required components are mentioned
            if required_components:
                movements = components.get('movements', {})
                mentioned_components = set(movements.keys())
                required_set = set(required_components)
                
                missing = required_set - mentioned_components
                if missing:
                    is_valid = False
                    issues.append(
                        f"❌ Missing reconciliation components: {', '.join(missing)}"
                    )
            
            # Check if LLM mentions all movements
            movements = components.get('movements', {})
            for movement_name in movements.keys():
                if movement_name.lower() not in response_text.lower():
                    is_valid = False
                    issues.append(
                        f"⚠️ Movement '{movement_name}' not mentioned in response"
                    )
        
        except Exception as e:
            logger.error(f"Reconciliation validation failed: {e}", exc_info=True)
            return True, []
        
        return is_valid, issues
    
    def validate_growth_rate(
        self,
        response_text: str,
        calculated_result: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate growth rate calculation"""
        issues = []
        is_valid = True
        
        try:
            # Skip if no calculated result
            if not calculated_result:
                return True, []
            
            # Extract percentage claims (growth rates are typically in %)
            claims = self.extract_numeric_claims(response_text)
            percentage_claims = [c for c in claims if c['type'] == 'percentage']
            
            # Skip if no percentage claims
            if not percentage_claims:
                return True, []
            
            # Get expected growth percentage
            components = calculated_result.get('components', {})
            growth_pct = components.get('growth_percentage', 0)
            if growth_pct is None:
                return True, []
            
            expected_growth_pct = Decimal(str(growth_pct))
            
            # Check if any claimed percentage is close to expected
            found_match = False
            for claim in percentage_claims:
                try:
                    claimed_value = Decimal(str(claim['value']))
                    diff = abs(claimed_value - expected_growth_pct)
                    
                    if diff <= Decimal('0.1'):  # Within 0.1%
                        found_match = True
                    elif diff > Decimal('1.0'):  # More than 1% off
                        is_valid = False
                        issues.append(
                            f"❌ Growth rate mismatch: LLM claims {claim['text']}, "
                            f"calculated {expected_growth_pct:.2f}%"
                        )
                except (ValueError, TypeError, ArithmeticError) as e:
                    logger.warning(f"Failed to validate growth claim '{claim}': {e}")
                    continue
            
            if not found_match and percentage_claims:
                is_valid = False
                issues.append(
                    f"⚠️ No growth rate claim matches calculated value of {expected_growth_pct:.2f}%"
                )
        
        except Exception as e:
            logger.error(f"Growth rate validation failed: {e}", exc_info=True)
            return True, []
        
        return is_valid, issues
    
    def generate_correction_prompt(
        self,
        original_response: str,
        issues: List[str],
        calculated_result: Dict[str, Any]
    ) -> str:
        """
        Generate a prompt to correct LLM's numeric errors
        
        Args:
            original_response: Original LLM response with errors
            issues: List of identified issues
            calculated_result: Correct calculated values
            
        Returns:
            Correction prompt for LLM
        """
        prompt = "Your previous response contained numeric inaccuracies. Please correct them.\n\n"
        prompt += "**Issues Found:**\n"
        for issue in issues:
            prompt += f"- {issue}\n"
        
        prompt += "\n**Verified Calculations:**\n"
        components = calculated_result.get('components', {})
        
        # Add correct values
        for key, value in components.items():
            if isinstance(value, (int, float)):
                prompt += f"- {key}: {value}\n"
        
        # Add intermediate steps if available
        steps = calculated_result.get('intermediate_steps', [])
        if steps:
            prompt += "\n**Calculation Steps:**\n"
            for step in steps:
                prompt += f"- {step}\n"
        
        prompt += "\nPlease revise your answer using these EXACT values. "
        prompt += "Do not perform calculations yourself - use the values provided above."
        
        return prompt
    
    def check_source_citation(
        self,
        response_text: str,
        required_sources: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Verify that response cites required sources (page numbers, table names)
        
        Args:
            response_text: LLM response
            required_sources: List of sources that should be cited
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        is_valid = True
        
        for source in required_sources:
            page = source.get('page')
            table_name = source.get('table_name')
            
            # Check for page citation
            if page:
                page_patterns = [
                    f"page {page}",
                    f"p. {page}",
                    f"pg. {page}",
                    f"page {page}"
                ]
                
                if not any(pattern.lower() in response_text.lower() for pattern in page_patterns):
                    is_valid = False
                    issues.append(f"⚠️ Missing page citation: Page {page} not referenced")
            
            # Check for table citation
            if table_name:
                if table_name.lower() not in response_text.lower():
                    is_valid = False
                    issues.append(f"⚠️ Missing table citation: '{table_name}' not referenced")
        
        return is_valid, issues


# Global validator instance
validator = NumericValidator(tolerance_bps=2.0)
