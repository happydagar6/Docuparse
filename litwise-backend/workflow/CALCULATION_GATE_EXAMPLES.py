"""
CALCULATION GATE SYSTEM - USAGE EXAMPLES
=========================================

This demonstrates how to use the deterministic calculation gate system
to ensure the LLM never decides calculation eligibility.

CORE PRINCIPLE:
- System checks inputs → decides if calculation can run
- LLM receives decision → can ONLY explain the result
- NO LLM override allowed
"""

from workflow.financial_rag_pipeline import FinancialRAGPipeline, CalculationGate


# ========================================
# EXAMPLE 1: MARGIN CALCULATION (SUCCESS)
# ========================================

def example_margin_calculation_success():
    """
    Scenario: All required inputs exist in extracted data
    Expected: Gate passes → calculation MUST run
    """
    pipeline = FinancialRAGPipeline()
    
    # Define what inputs are REQUIRED for margin calculation
    gate = CalculationGate(
        required_inputs=['numerator', 'denominator'], # If these inputs are missing the calculation cannot be performed
        calculation_type='margin' # Defines the calculation to be performed
    )
    
    # Extracted data from tables (all inputs present)
    extracted_data = {
        'numerator': 5640,      # UTOP from table
        'denominator': 25336,   # Sales from table
        'source_page': 20,
        'table_name': 'Note 3.1 Revenue and Results'
    }
    
    # Execute with gate
    result = pipeline.execute_gated_calculation(
        gate=gate,
        extracted_data=extracted_data, # Data extracted from the PDF
        metadata={
            'label': 'Zone NA UTOP Margin 2024', # LLM will see this text
            'source_page': 20,
            'source_table': 'Note 3.1'
        }
    )
    
    # ✅ EXPECTED RESULT:
    # {
    #     'status': 'success',
    #     'result': CalculationResult(result=0.2227, ...),
    #     'error': None,
    #     'gate_decision': {
    #         'can_proceed': True,
    #         'missing_inputs': [],
    #         'validated_inputs': ['numerator', 'denominator']
    #     },
    #     'llm_instruction': 'EXPLAIN this result. DO NOT recalculate.'
    # }
    
    print("✅ GATE PASSED - Calculation executed")
    print(f"Result: {result['result'].format_percentage(decimals=2)}")
    print(f"LLM Instruction: {result['llm_instruction']}")
    
    return result;


# ========================================
# EXAMPLE 2: MARGIN CALCULATION (BLOCKED)
# ========================================

def example_margin_calculation_blocked():
    """
    Scenario: Numerator is missing from extracted data
    Expected: Gate blocks → hard error MUST be returned
    """
    pipeline = FinancialRAGPipeline()
    
    gate = CalculationGate(
        required_inputs=['numerator', 'denominator'],
        calculation_type='margin'
    )
    
    # Extracted data MISSING numerator (e.g., not in PDF)
    extracted_data = {
        'denominator': 25336,   # Sales exists
        # 'numerator': ???     # UTOP missing - not in document
    }
    
    # Execute with gate
    result = pipeline.execute_gated_calculation(
        gate=gate,
        extracted_data=extracted_data,
        metadata={'label': 'Zone NA UTOP Margin 2024'}
    )
    
    # ✅ EXPECTED RESULT:
    # {
    #     'status': 'blocked',
    #     'result': None,
    #     'error': '❌ CALCULATION BLOCKED: margin\nMissing inputs: [numerator]',
    #     'gate_decision': {
    #         'can_proceed': False,
    #         'missing_inputs': ['numerator']
    #     },
    #     'llm_instruction': 'EXPLAIN why calculation was blocked. DO NOT approximate.'
    # }
    
    print("❌ GATE BLOCKED - Calculation cannot proceed")
    print(f"Error: {result['error']}")
    print(f"Missing: {result['gate_decision']['missing_inputs']}")
    print(f"LLM Instruction: {result['llm_instruction']}")
    
    return result;


# ========================================
# EXAMPLE 3: GROWTH RATE (SUCCESS)
# ========================================

def example_growth_rate_success():
    """
    Scenario: Multi-year data exists for growth calculation
    Expected: Gate passes → calculation MUST run
    """
    pipeline = FinancialRAGPipeline()
    
    gate = CalculationGate(
        required_inputs=['current_value', 'previous_value'],
        calculation_type='growth_rate'
    )
    
    # Extracted data from multi-year table
    extracted_data = {
        'current_value': 25336,   # 2024 sales
        'previous_value': 24102,  # 2023 sales
    }
    
    result = pipeline.execute_gated_calculation(
        gate=gate,
        extracted_data=extracted_data,
        metadata={
            'label': 'Zone NA Sales Growth (2024 vs 2023)',
            'source_page': 20
        }
    )
    
    print("✅ GROWTH RATE - Calculation executed")
    print(f"Result: {result['result'].format_percentage(decimals=2)}")
    
    return result;


# ========================================
# EXAMPLE 4: SCENARIO/SENSITIVITY (BLOCKED)
# ========================================

def example_scenario_analysis_blocked():
    """
    Scenario: User asks "what if revenue was 30,000?"
    Expected: Gate blocks because "30,000" is NOT in source document
    """
    pipeline = FinancialRAGPipeline()
    
    gate = CalculationGate(
        required_inputs=['scenario_revenue', 'margin_assumption'],
        calculation_type='scenario'
    )
    
    # User invented scenario (NOT from document)
    extracted_data = {
        # 'scenario_revenue': ???     # NOT IN DOCUMENT
        # 'margin_assumption': ???    # NOT IN DOCUMENT
    }
    
    result = pipeline.execute_gated_calculation(
        gate=gate,
        extracted_data=extracted_data,
        metadata={'label': 'Hypothetical Scenario'}
    )
    
    # ✅ EXPECTED: Gate blocks because inputs don't exist in source
    print("❌ SCENARIO BLOCKED - Inputs not in source document")
    print(f"Error: {result['error']}")
    print("LLM cannot invent or approximate - must explain block")
    
    return result


# ========================================
# EXAMPLE 5: PLACEHOLDER VALUES (BLOCKED)
# ========================================

def example_placeholder_blocked():
    """
    Scenario: Table has placeholder values (-, N/A, etc.)
    Expected: Gate blocks because placeholders are not valid inputs
    """
    pipeline = FinancialRAGPipeline()
    
    gate = CalculationGate(
        required_inputs=['numerator', 'denominator'],
        calculation_type='margin'
    )
    
    # Extracted data with placeholders
    extracted_data = {
        'numerator': '-',       # Placeholder in table
        'denominator': 25336,
    }
    
    result = pipeline.execute_gated_calculation(
        gate=gate,
        extracted_data=extracted_data
    )
    
    # ✅ EXPECTED: Gate detects placeholder and blocks
    print("❌ PLACEHOLDER DETECTED - Calculation blocked")
    print(f"Missing: {result['gate_decision']['missing_inputs']}")
    
    return result


# ========================================
# INTEGRATION EXAMPLE: FULL PIPELINE
# ========================================

def example_full_pipeline():
    """
    Complete example: Extract → Gate → Calculate → Format for LLM
    """
    pipeline = FinancialRAGPipeline()
    
    # Step 1: Extract data from tables (your existing extraction logic)
    extracted_data = {
        'numerator': 5640,
        'denominator': 25336,
    }
    
    # Step 2: Define gate for required calculation
    gate = CalculationGate(
        required_inputs=['numerator', 'denominator'],
        calculation_type='margin'
    )
    
    # Step 3: Execute with gate (deterministic decision)
    result = pipeline.execute_gated_calculation(
        gate=gate,
        extracted_data=extracted_data,
        metadata={'label': 'Zone NA Margin', 'source_page': 20}
    )
    
    # Step 4: Format for LLM context
    if result['status'] == 'success':
        context = f"""
        📊 CALCULATION: margin
        Gate Decision: ✅ PASSED
        Result: {result['result'].format_percentage(decimals=2)}
        
        🤖 YOUR INSTRUCTION: {result['llm_instruction']}
        
        EXPLANATION: The UTOP margin for Zone NA in 2024 was **22.27%**
        (calculated as 5,640 ÷ 25,336, Source: Page 20).
        """
    else:
        context = f"""
        📊 CALCULATION: margin
        Gate Decision: ❌ BLOCKED
        Missing Inputs: {result['gate_decision']['missing_inputs']}
        
        🤖 YOUR INSTRUCTION: {result['llm_instruction']}
        
        EXPLANATION: Cannot calculate margin because the following inputs
        are not available in the source document: {result['gate_decision']['missing_inputs']}.
        No approximation or estimation is allowed.
        """
    
    print(context)
    return result


# ========================================
# RUN EXAMPLES
# ========================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("CALCULATION GATE SYSTEM - EXAMPLES")
    print("="*80 + "\n")
    
    print("\n--- Example 1: Success ---")
    example_margin_calculation_success()
    
    print("\n--- Example 2: Blocked (Missing Input) ---")
    example_margin_calculation_blocked()
    
    print("\n--- Example 3: Growth Rate ---")
    example_growth_rate_success()
    
    print("\n--- Example 4: Scenario Blocked ---")
    example_scenario_analysis_blocked()
    
    print("\n--- Example 5: Placeholder Blocked ---")
    example_placeholder_blocked()
    
    print("\n--- Example 6: Full Pipeline ---")
    example_full_pipeline()
    
    print("\n" + "="*80)
    print("KEY TAKEAWAYS:")
    print("1. Gate decides calculation eligibility (NOT the LLM)")
    print("2. Gate passes → calculation MUST run")
    print("3. Gate blocks → hard error MUST be returned")
    print("4. LLM can ONLY explain decisions, not override them")
    print("5. NO approximation, estimation, or scenario invention")
    print("="*80 + "\n")
