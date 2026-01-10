"""
Financial RAG Integration Layer
Coordinates table normalization, calculations, and validation
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from workflow.financial_calculator import calculator, CalculationResult
from workflow.table_normalizer import normalizer
from workflow.numeric_validator import validator
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class CalculationGate:
    """
    ❌ CRITICAL: Deterministic gate for calculation eligibility
    
    This class makes THE DECISION whether a calculation can run.
    The LLM is NOT ALLOWED to override this decision.
    
    RULES:
    - If ALL required inputs exist → calculation MUST run
    - If ANY input missing → calculation MUST be blocked
    - LLM can ONLY explain the decision, not make it
    """
    required_inputs: List[str]  # List of field names needed
    calculation_type: str       # 'margin', 'growth', 'ratio', etc.
    
    def validate(self, extracted_data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate if calculation can proceed
        
        Args:
            extracted_data: Dictionary of extracted values from tables
            
        Returns:
            Tuple of:
            - can_proceed: bool (True if ALL inputs exist)
            - missing_inputs: List of missing field names
            - validated_inputs: Dict of validated values (only if can_proceed=True)
            
        Raises:
            Never raises - returns structured decision
        """
        missing_inputs = []
        validated_inputs = {}
        
        for required_field in self.required_inputs:
            value = extracted_data.get(required_field)
            
            # ✅ GATE RULE: Check if value exists and is valid
            if value is None:
                missing_inputs.append(required_field)
                logger.info(f"⛔ Gate blocked: '{required_field}' is None")
            elif value == '':
                missing_inputs.append(required_field)
                logger.info(f"⛔ Gate blocked: '{required_field}' is empty string")
            elif str(value).strip() in ['', '-', 'N/A', 'n/a', 'NA', 'na']:
                missing_inputs.append(required_field)
                logger.info(f"⛔ Gate blocked: '{required_field}' is placeholder: '{value}'")
            else:
                # Value exists and is not a placeholder
                try:
                    # Validate it's numeric (will raise if not)
                    from decimal import Decimal
                    numeric_val = Decimal(str(value).replace(',', ''))
                    validated_inputs[required_field] = float(numeric_val)
                    logger.debug(f"✅ Gate validated: '{required_field}' = {numeric_val}")
                except Exception as e:
                    missing_inputs.append(required_field)
                    logger.info(f"⛔ Gate blocked: '{required_field}' is not numeric: '{value}' ({e})")
        
        can_proceed = len(missing_inputs) == 0
        
        if can_proceed:
            logger.info(f"✅ CALCULATION GATE PASSED: {self.calculation_type} - All {len(self.required_inputs)} inputs validated")
        else:
            logger.warning(
                f"⛔ CALCULATION GATE BLOCKED: {self.calculation_type} - "
                f"Missing {len(missing_inputs)}/{len(self.required_inputs)} inputs: {missing_inputs}"
            )
        
        return can_proceed, missing_inputs, validated_inputs
    
    def get_block_message(self, missing_inputs: List[str]) -> str:
        """
        Generate hard error message for blocked calculation
        
        Returns:
            Explicit error message listing missing inputs
        """
        return (
            f"❌ CALCULATION BLOCKED: {self.calculation_type}\n"
            f"Required inputs: {self.required_inputs}\n"
            f"Missing inputs: {missing_inputs}\n"
            f"Reason: Cannot proceed without all required inputs from source document.\n"
            f"NO APPROXIMATION OR ESTIMATION ALLOWED."
        )


class FinancialRAGPipeline:
    """
    Orchestrates financial analysis with deterministic calculations
    """
    
    def __init__(self):
        self.calculator = calculator
        self.normalizer = normalizer
        self.validator = validator
    
    def execute_gated_calculation(
        self,
        gate: CalculationGate,
        extracted_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        ❌ CRITICAL: Execute calculation with MANDATORY gate check
        
        This function enforces the rule:
        - Gate passes → calculation MUST run
        - Gate blocks → hard error MUST be returned
        
        The LLM receives the result and can ONLY explain it.
        The LLM is NOT ALLOWED to override this decision.
        
        Args:
            gate: CalculationGate with required inputs
            extracted_data: Extracted values from tables
            metadata: Optional metadata (source page, etc.)
            
        Returns:
            Dict with:
            - status: 'success' or 'blocked'
            - result: CalculationResult (if success)
            - error: error message (if blocked)
            - gate_decision: audit trail
        """
        # ✅ STEP 1: GATE VALIDATION (DETERMINISTIC)
        can_proceed, missing_inputs, validated_inputs = gate.validate(extracted_data)
        
        gate_decision = {
            'calculation_type': gate.calculation_type,
            'required_inputs': gate.required_inputs,
            'can_proceed': can_proceed,
            'missing_inputs': missing_inputs,
            'validated_inputs': list(validated_inputs.keys()) if can_proceed else []
        }
        
        # ✅ STEP 2: DETERMINISTIC EXECUTION OR HARD BLOCK
        if not can_proceed:
            # ⛔ GATE BLOCKED → HARD ERROR (no LLM override allowed)
            error_msg = gate.get_block_message(missing_inputs)
            logger.error(f"Calculation blocked: {error_msg}")
            
            return {
                'status': 'blocked',
                'result': None,
                'error': error_msg,
                'gate_decision': gate_decision,
                'llm_instruction': 'EXPLAIN why calculation was blocked. DO NOT approximate or estimate.'
            }
        
        # ✅ GATE PASSED → CALCULATION MUST RUN (no LLM override allowed)
        try:
            # Route to appropriate calculator method based on calculation type
            if gate.calculation_type == 'margin':
                result = self.calculator.calculate_margin(
                    numerator=validated_inputs['numerator'],
                    denominator=validated_inputs['denominator'],
                    label=metadata.get('label', 'Margin') if metadata else 'Margin',
                    source_page=metadata.get('source_page') if metadata else None,
                    source_table=metadata.get('source_table') if metadata else None
                )
            
            elif gate.calculation_type == 'margin_change':
                result = self.calculator.calculate_margin_change(
                    current_margin=validated_inputs['current_margin'],
                    previous_margin=validated_inputs['previous_margin'],
                    label=metadata.get('label', 'Margin Change') if metadata else 'Margin Change',
                    return_bps=metadata.get('return_bps', True) if metadata else True,
                    source_page=metadata.get('source_page') if metadata else None
                )
            
            elif gate.calculation_type == 'growth_rate':
                result = self.calculator.calculate_growth_rate(
                    current_value=validated_inputs['current_value'],
                    previous_value=validated_inputs['previous_value'],
                    label=metadata.get('label', 'Growth Rate') if metadata else 'Growth Rate'
                )
            
            elif gate.calculation_type == 'ratio':
                result = self.calculator.calculate_ratio(
                    value1=validated_inputs['value1'],
                    value2=validated_inputs['value2'],
                    label=metadata.get('label', 'Ratio') if metadata else 'Ratio',
                    format_type=metadata.get('format_type', 'decimal') if metadata else 'decimal'
                )
            
            else:
                raise ValueError(f"Unknown calculation type: {gate.calculation_type}")
            
            logger.info(f"✅ Calculation executed: {gate.calculation_type} = {result.result}")
            
            return {
                'status': 'success',
                'result': result,
                'error': None,
                'gate_decision': gate_decision,
                'llm_instruction': 'EXPLAIN this result. DO NOT recalculate. USE EXACT VALUE PROVIDED.'
            }
        
        except Exception as e:
            # Calculation failed (e.g., division by zero caught by calculator)
            error_msg = f"❌ CALCULATION FAILED: {gate.calculation_type}\nError: {str(e)}"
            logger.error(f"Calculation execution failed: {error_msg}")
            
            return {
                'status': 'failed',
                'result': None,
                'error': error_msg,
                'gate_decision': gate_decision,
                'llm_instruction': 'EXPLAIN why calculation failed. DO NOT attempt manual calculation.'
            }
    
    def detect_question_type(self, question: str) -> Dict[str, Any]:
        """
        Classify question to determine calculation strategy
        
        Returns:
            Dict with question_type and parameters
        """
        question_lower = question.lower()
        
        # Margin calculation
        if any(kw in question_lower for kw in ['margin', 'utop', 'profitability']):
            return {
                'type': 'margin_calculation',
                'requires_tables': True,
                'calculation_type': 'ratio'
            }
        
        # Margin change / delta
        if any(kw in question_lower for kw in ['change', 'delta', 'difference', 'variation', 'vs', 'compared to']):
            if any(kw in question_lower for kw in ['margin', '%', 'percentage', 'bps', 'basis']):
                return {
                    'type': 'margin_change',
                    'requires_tables': True,
                    'calculation_type': 'difference',
                    'return_bps': 'bps' in question_lower or 'basis' in question_lower
                }
        
        # Reconciliation
        if any(kw in question_lower for kw in ['reconcil', 'movement', 'rollforward', 'bridge']):
            return {
                'type': 'reconciliation',
                'requires_tables': True,
                'calculation_type': 'reconciliation',
                'validate_completeness': True
            }
        
        # Growth rate
        if any(kw in question_lower for kw in ['growth', 'increase', 'decrease', 'yoy', 'year-over-year']):
            return {
                'type': 'growth_rate',
                'requires_tables': True,
                'calculation_type': 'percentage_change'
            }
        
        # Ratio calculation
        if any(kw in question_lower for kw in ['ratio', 'divide', '/']):
            return {
                'type': 'ratio',
                'requires_tables': True,
                'calculation_type': 'division'
            }
        
        # Default: general question
        return {
            'type': 'general',
            'requires_tables': False,
            'calculation_type': None
        }
    
    def process_financial_question(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main processing pipeline for financial questions
        
        Args:
            question: User question
            retrieved_chunks: Chunks from vector/hybrid search
            
        Returns:
            Dict with:
                - calculated_results: Deterministic calculation results
                - normalized_tables: Structured table data
                - context_for_llm: Prepared context string
                - question_metadata: Type and parameters
        """
        # Step 1: Detect question type
        question_metadata = self.detect_question_type(question)
        logger.info(f"Question type detected: {question_metadata['type']}")
        
        # Step 2: Extract and normalize tables
        tables = []
        if question_metadata['requires_tables']:
            tables = self.normalizer.extract_tables_from_chunks(retrieved_chunks)
            logger.info(f"Extracted {len(tables)} tables from chunks")
        
        # Step 3: Perform calculations based on question type
        calculated_results = None
        if question_metadata['type'] != 'general' and tables:
            calculated_results = self._perform_calculations(
                question,
                question_metadata,
                tables
            )
        
        # Step 4: Prepare context for LLM
        context_for_llm = self._prepare_llm_context(
            retrieved_chunks,
            tables,
            calculated_results,
            question_metadata
        )
        
        return {
            'calculated_results': calculated_results,
            'normalized_tables': tables,
            'context_for_llm': context_for_llm,
            'question_metadata': question_metadata,
            'retrieved_chunks': retrieved_chunks
        }
    
    def _perform_calculations(
        self,
        question: str,
        metadata: Dict[str, Any],
        tables: List[Dict[str, Any]]
    ) -> Optional[List[CalculationResult]]:
        """
        Perform deterministic calculations based on question type
        """
        question_type = metadata['type']
        results = []
        
        try:
            if question_type == 'margin_calculation':
                # Extract numerator and denominator from tables
                result = self._calculate_margins_from_tables(question, tables)
                if result:
                    results.extend(result)
            
            elif question_type == 'margin_change':
                # Calculate margin difference
                result = self._calculate_margin_changes(question, tables, metadata)
                if result:
                    results.extend(result)
            
            elif question_type == 'reconciliation':
                # Perform reconciliation
                result = self._perform_reconciliation(question, tables)
                if result:
                    results.extend(result)
            
            elif question_type == 'growth_rate':
                # Calculate growth
                result = self._calculate_growth_rates(question, tables)
                if result:
                    results.extend(result)
            
            return results if results else None
        
        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            return None
    
    def _calculate_margins_from_tables(
        self,
        question: str,
        tables: List[Dict[str, Any]]
    ) -> List[CalculationResult]:
        """
        Extract margin calculations from tables
        Auto-detect numerator and denominator columns
        """
        results = []
        
        # Look for common margin patterns in question
        # Example: "UTOP margin" → look for UTOP and Sales columns
        
        for table in tables:
            df = table['dataframe']
            headers = table['headers']
            
            # Try to identify numerator column (profit, UTOP, etc.)
            numerator_col = None
            for col in headers:
                if any(kw in col.lower() for kw in ['utop', 'profit', 'income', 'ebit']):
                    numerator_col = col
                    break
            
            # Try to identify denominator column (sales, revenue)
            denominator_col = None
            for col in headers:
                if any(kw in col.lower() for kw in ['sales', 'revenue', 'turnover']):
                    denominator_col = col
                    break
            
            if numerator_col and denominator_col:
                # Calculate margin for each row
                for idx, row in df.iterrows():
                    row_label = row[headers[0]]  # Assume first column is label
                    numerator = row[numerator_col]
                    denominator = row[denominator_col]
                    
                    if numerator is not None and denominator is not None and denominator != 0:
                        result = self.calculator.calculate_margin(
                            numerator=float(numerator),
                            denominator=float(denominator),
                            label=f"{row_label} Margin",
                            source_page=table.get('source_page'),
                            source_table=f"Table with {numerator_col} and {denominator_col}"
                        )
                        results.append(result)
        
        return results
    
    def _calculate_margin_changes(
        self,
        question: str,
        tables: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> List[CalculationResult]:
        """
        Calculate margin changes (basis points or percentage points)
        
        ✅ FIX: Pre-validate tables and rows to exclude headers
        """
        results = []
        return_bps = metadata.get('return_bps', True)
        
        # Look for tables with year columns (2024, 2023, etc.)
        for table in tables:
            # ✅ FIX: Validate table before processing
            if not self._is_valid_data_table(table):
                logger.debug(f"Skipping invalid table: {table.get('source_table', 'unknown')}")
                continue
            
            df = table['dataframe']
            headers = [str(h) for h in table['headers']]
            
            # Find year columns
            year_cols = [h for h in headers if re.match(r'20\d{2}', h)]
            
            if len(year_cols) >= 2:
                # Sort years
                year_cols_sorted = sorted(year_cols, reverse=True)
                current_year = year_cols_sorted[0]
                previous_year = year_cols_sorted[1]
                
                # Calculate margin change for each row
                for idx, row in df.iterrows():
                    row_label = row[headers[0]]
                    
                    # ✅ FIX: Skip descriptor/total rows
                    if self._is_descriptor_or_total_row(row_label):
                        logger.debug(f"Skipping descriptor/total row: {row_label}")
                        continue
                    
                    current_val = row.get(current_year)
                    previous_val = row.get(previous_year)
                    
                    if current_val is not None and previous_val is not None:
                        try:
                            # If values are already margins (< 1), use directly
                            # If they're percentages (> 1), convert to decimal
                            curr_margin = float(current_val) if float(current_val) < 1 else float(current_val) / 100
                            prev_margin = float(previous_val) if float(previous_val) < 1 else float(previous_val) / 100
                            
                            result = self.calculator.calculate_margin_change(
                                current_margin=curr_margin,
                                previous_margin=prev_margin,
                                label=f"{row_label} Margin Change ({current_year} vs {previous_year})",
                                return_bps=return_bps,
                                source_page=table.get('source_page')
                            )
                            results.append(result)
                        
                        except ValueError as e:
                            # Validation failed (likely header/descriptor row)
                            logger.debug(f"Skipping row '{row_label}': {e}")
                            continue
        
        return results
    
    def _perform_reconciliation(
        self,
        question: str,
        tables: List[Dict[str, Any]]
    ) -> List[Tuple[CalculationResult, bool, List[str]]]:
        """Perform reconciliation with completeness validation"""
        results = []
        
        # Look for tables with movement structure
        for table in tables:
            df = table['dataframe']
            headers = table['headers']
            
            # Typical reconciliation has: Opening, Movements..., Closing
            if len(df) >= 3:  # At least opening, one movement, closing
                # Try to identify opening and closing rows
                opening_row = None
                closing_row = None
                movements = {}
                
                for idx, row in df.iterrows():
                    row_label = str(row[headers[0]]).lower()
                    
                    if any(kw in row_label for kw in ['opening', 'beginning', 'start']):
                        opening_row = row
                    elif any(kw in row_label for kw in ['closing', 'ending', 'end']):
                        closing_row = row
                    else:
                        # It's a movement row
                        # Get value from last numeric column
                        for col in reversed(headers[1:]):
                            val = row[col]
                            if val is not None:
                                movements[row[headers[0]]] = float(val)
                                break
                
                if opening_row is not None and closing_row is not None and movements:
                    # Perform reconciliation
                    # Use last numeric column
                    value_col = headers[-1]
                    
                    opening_val = opening_row[value_col]
                    closing_val = closing_row[value_col]
                    
                    if opening_val is not None and closing_val is not None:
                        result, is_balanced, issues = self.calculator.calculate_reconciliation(
                            opening_balance=float(opening_val),
                            movements=movements,
                            closing_balance=float(closing_val),
                            label=f"Reconciliation from table on page {table.get('source_page', 'unknown')}",
                            source_page=table.get('source_page')
                        )
                        results.append((result, is_balanced, issues))
        
        return results
    
    def _calculate_growth_rates(
        self,
        question: str,
        tables: List[Dict[str, Any]]
    ) -> List[CalculationResult]:
        """Calculate growth rates between periods"""
        results = []
        
        for table in tables:
            df = table['dataframe']
            headers = [str(h) for h in table['headers']]
            
            # Find year columns
            year_cols = [h for h in headers if re.match(r'20\d{2}', h)]
            
            if len(year_cols) >= 2:
                year_cols_sorted = sorted(year_cols, reverse=True)
                current_year = year_cols_sorted[0]
                previous_year = year_cols_sorted[1]
                
                for idx, row in df.iterrows():
                    row_label = row[headers[0]]
                    current_val = row.get(current_year)
                    previous_val = row.get(previous_year)
                    
                    if current_val is not None and previous_val is not None:
                        try:
                            result = self.calculator.calculate_growth_rate(
                                current_value=float(current_val),
                                previous_value=float(previous_val),
                                label=f"{row_label} Growth ({current_year} vs {previous_year})"
                            )
                            results.append(result)
                        except ValueError:
                            continue
        
        return results
    
    def _prepare_llm_context(
        self,
        chunks: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
        calculations: Optional[List[Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """
        ❌ ISSUE #4: Prepare context with DETERMINISTIC calculations ONLY
        
        CRITICAL RULES:
        1. All calculations are PRE-COMPUTED by deterministic calculator
        2. LLM is FORBIDDEN from doing arithmetic
        3. LLM can ONLY explain pre-computed results
        """
        context_parts = []
        
        # ✅ FIX #4: EXPLICIT header warning LLM to NOT calculate
        # ✅ NEW: Add CALCULATION GATE enforcement
        context_parts.append("""⚠️ CRITICAL INSTRUCTION FOR AI ASSISTANT:

🔒 CALCULATION GATE RULES (MANDATORY):
- A DETERMINISTIC SYSTEM decides if calculations can run
- You are NOT ALLOWED to override these decisions
- If calculation status = 'success' → USE THE EXACT RESULT PROVIDED
- If calculation status = 'blocked' → EXPLAIN why it was blocked (missing inputs)
- If calculation status = 'failed' → EXPLAIN why it failed (error message)

❌ YOU ARE FORBIDDEN FROM:
- Deciding whether a calculation should run
- Approximating or estimating when inputs are missing
- Performing arithmetic yourself
- Inventing baseline values or scenarios
- Saying "I'll calculate" when gate is blocked

✅ YOUR ROLE IS ONLY TO:
- Explain pre-computed results
- Explain why calculations were blocked/failed
- Cite source documents

THIS IS A FINANCIAL ENGINE, NOT A REASONING ASSISTANT.
""")
        
        # Add calculation results if available
        if calculations:
            context_parts.append("\n=== ✅ VERIFIED CALCULATIONS (USE THESE EXACT VALUES) ===")
            context_parts.append("These calculations were executed by a DETERMINISTIC FINANCIAL ENGINE.")
            context_parts.append("Gate decisions and execution results are FINAL and NON-NEGOTIABLE.\n")
            
            for calc_result in calculations:
                # Handle gated calculation results
                if isinstance(calc_result, dict) and 'gate_decision' in calc_result:
                    gate = calc_result['gate_decision']
                    status = calc_result['status']
                    
                    context_parts.append(f"\n📊 CALCULATION: {gate['calculation_type']}")
                    context_parts.append(f"Required Inputs: {gate['required_inputs']}")
                    context_parts.append(f"Gate Decision: {'✅ PASSED' if gate['can_proceed'] else '⛔ BLOCKED'}")
                    
                    if status == 'success':
                        result: CalculationResult = calc_result['result']
                        context_parts.append(f"Status: ✅ EXECUTED")
                        context_parts.append(f"Result: {result.format_percentage(decimals=2)}")
                        
                        if 'basis_points' in result.components:
                            bps = result.components['basis_points']
                            context_parts.append(f"Basis Points: {bps:.2f} bps")
                        
                        if result.intermediate_steps:
                            context_parts.append("\nCalculation Steps (deterministic):")
                            for step in result.intermediate_steps:
                                context_parts.append(f"  {step}")
                        
                        if result.source_page:
                            context_parts.append(f"Source: Page {result.source_page}")
                        
                        context_parts.append(f"\n🤖 YOUR INSTRUCTION: {calc_result['llm_instruction']}")
                    
                    elif status == 'blocked':
                        context_parts.append(f"Status: ⛔ BLOCKED")
                        context_parts.append(f"Missing Inputs: {gate['missing_inputs']}")
                        context_parts.append(f"Error: {calc_result['error']}")
                        context_parts.append(f"\n🤖 YOUR INSTRUCTION: {calc_result['llm_instruction']}")
                    
                    elif status == 'failed':
                        context_parts.append(f"Status: ❌ FAILED")
                        context_parts.append(f"Error: {calc_result['error']}")
                        context_parts.append(f"\n🤖 YOUR INSTRUCTION: {calc_result['llm_instruction']}")
                    
                    context_parts.append("="*80)
                
                # Handle legacy CalculationResult objects (backward compatibility)
                elif isinstance(calc_result, CalculationResult):
                    context_parts.append(f"\n**{calc_result.components.get('label', 'Calculation')}:**")
                    context_parts.append(f"Result: {calc_result.format_percentage(decimals=2)}")
                    
                    if 'basis_points' in calc_result.components:
                        bps = calc_result.components['basis_points']
                        context_parts.append(f"Basis Points: {bps:.2f} bps")
                    
                    if calc_result.intermediate_steps:
                        context_parts.append("Calculation Steps (deterministic):")
                        for step in calc_result.intermediate_steps:
                            context_parts.append(f"  {step}")
                    
                    if calc_result.source_page:
                        context_parts.append(f"Source: Page {calc_result.source_page}")
                    
                    context_parts.append("")
                
                # Handle reconciliation tuples (backward compatibility)
                elif isinstance(calc_result, tuple):
                    result, is_balanced, issues = calc_result
                    context_parts.append(f"\n**Reconciliation:**")
                    context_parts.append(f"Balanced: {'✓ Yes' if is_balanced else '✗ No'}")
                    if issues:
                        context_parts.append("Issues:")
                        for issue in issues:
                            context_parts.append(f"  {issue}")
                    context_parts.append("")
        
        # Add structured table data
        if tables:
            context_parts.append("\n=== 📊 STRUCTURED TABLE DATA ===")
            for i, table in enumerate(tables[:3], 1):  # Limit to top 3 tables
                # ✅ FIX #3: Show unit normalization info
                unit_info = f" (normalized to {table.get('normalized_to', 'base units')})"
                context_parts.append(f"\nTable {i} (Page {table.get('source_page', 'unknown')}){unit_info}:")
                context_parts.append(f"Rows: {table['row_count']}, Columns: {table['col_count']}")
                context_parts.append(f"Headers: {', '.join(table['headers'])}")
                context_parts.append(f"Original Unit: {table.get('unit', 'unknown')}")
                
                # Show first few rows
                df = table['dataframe']
                context_parts.append(df.head(5).to_string())
                context_parts.append("")
        
        # Add original text chunks
        context_parts.append("\n=== DOCUMENT CONTEXT ===")
        for chunk in chunks[:10]:  # Limit chunks
            page = chunk.get('page', 'unknown')
            content = chunk.get('content', '')[:500]  # Truncate long content
            context_parts.append(f"[Page {page}] {content}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def validate_response(
        self,
        response_text: str,
        calculated_results: Optional[List[CalculationResult]],
        question_metadata: Dict[str, Any]
    ) -> Tuple[bool, List[str], Optional[str]]:
        """
        Validate LLM response for numeric accuracy
        
        ✅ FIX: Limit validations to prevent spam and hallucinations
        
        Returns:
            Tuple of (is_valid, issues, correction_prompt)
        """
        # Skip validation if no calculated results
        if not calculated_results:
            return True, [], None
        
        # Skip validation for general questions
        if question_metadata.get('type') == 'general':
            return True, [], None
        
        # ✅ FIX: Limit validation to prevent spam
        max_validations = 3
        
        all_issues = []
        is_valid = True
        validations_performed = 0
        
        try:
            question_type = question_metadata['type']
            
            for calc_result in calculated_results:
                # ✅ FIX: Stop after max validations
                if validations_performed >= max_validations:
                    logger.debug(f"Validation limit reached, skipping remaining results")
                    break
                
                try:
                    if isinstance(calc_result, CalculationResult):
                        if question_type == 'margin_change':
                            valid, issues = self.validator.validate_margin_calculation(
                                response_text,
                                calc_result.to_dict()
                            )
                            if not valid:
                                is_valid = False
                                all_issues.extend(issues)
                            validations_performed += 1
                        
                        elif question_type == 'growth_rate':
                            valid, issues = self.validator.validate_growth_rate(
                                response_text,
                                calc_result.to_dict()
                            )
                            if not valid:
                                is_valid = False
                                all_issues.extend(issues)
                            validations_performed += 1
                    
                    elif isinstance(calc_result, tuple):  # Reconciliation
                        result, is_balanced, recon_issues = calc_result
                        if not is_balanced:
                            is_valid = False
                            all_issues.extend(recon_issues)
                        validations_performed += 1
                
                except Exception as e:
                    logger.debug(f"Failed to validate individual calculation: {e}")
                    continue
            
            # ✅ FIX: Only generate correction for REAL issues (not validation bugs)
            correction_prompt = None
            if not is_valid and 0 < len(all_issues) < 50:
                logger.info(f"⚠️ Validation found {len(all_issues)} issues")
                first_result = calculated_results[0]
                if isinstance(first_result, CalculationResult):
                    correction_prompt = self.validator.generate_correction_prompt(
                        response_text,
                        all_issues[:10],  # ✅ Only first 10 issues
                        first_result.to_dict()
                    )
            elif len(all_issues) >= 50:
                # ✅ FIX: Too many issues = validation bug
                logger.warning(
                    f"⚠️ Validation found {len(all_issues)} issues - likely validation error. "
                    "Skipping correction to prevent hallucinations."
                )
                return True, [], None
            
            return is_valid, all_issues, correction_prompt
        
        except Exception as e:
            logger.error(f"Validation framework failed: {e}", exc_info=True)
            return True, [], None
    
    def _is_valid_data_table(self, table: Dict[str, Any]) -> bool:
        """
        Validate that table contains actual data (not just headers/descriptors)
        
        ✅ FIX: Pre-filter invalid tables before calculations
        """
        df = table.get('dataframe')
        if df is None or df.empty:
            return False
        
        # Check if table has at least 1 data row (after headers)
        if len(df) < 1:
            return False
        
        # Check if table has at least 2 columns (label + value)
        if len(df.columns) < 2:
            return False
        
        return True
    
    def _is_descriptor_or_total_row(self, row_label: str) -> bool:
        """
        Check if row is a descriptor, header, or total row
        
        ✅ FIX: Prevent using summary/header rows in calculations
        """
        if not row_label or not isinstance(row_label, str):
            return True
        
        label_lower = str(row_label).lower().strip()
        
        # Descriptor patterns
        descriptor_patterns = [
            r'\(in (millions?|thousands?|billions?)\)',
            r'\(in (CHF|USD|EUR|GBP)\)',
            r'\((un)?audited\)',
            r'^(note|ref)\s*\d',
            r'^currency:',
            r'^unit:',
        ]
        
        for pattern in descriptor_patterns:
            if re.search(pattern, label_lower):
                return True
        
        # Total/subtotal patterns
        total_keywords = ['total', 'subtotal', 'sum', 'aggregate', 'consolidated']
        if any(kw in label_lower for kw in total_keywords):
            return True
        
        # Empty or placeholder
        if label_lower in ['', '-', 'n/a', 'na', 'nil']:
            return True
        
        return False


# Global pipeline instance
financial_rag = FinancialRAGPipeline()
