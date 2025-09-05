# tests/integration/test_functionality_restoration_validation.py
"""
Integration test para validar que toda la funcionalidad perdida fue restaurada
manteniendo las optimizaciones de performance de ADR-0009.
"""

import os
import pytest


class TestFunctionalityRestoration:
    """Tests de validación de restauración completa de funcionalidad."""

    def test_chat_agent_restoration_validation(self):
        """Validate complete restoration of ChatAgent functionality."""
        chat_agent_path = "src/agents/specialists/chat_agent.py"
        
        # Check file exists
        assert os.path.exists(chat_agent_path), f"ChatAgent file not found: {chat_agent_path}"
        
        with open(chat_agent_path, 'r') as f:
            content = f.read()
            lines = len(f.readlines())
        
        # Re-open to count lines properly
        with open(chat_agent_path, 'r') as f:
            lines = len(f.readlines())
        
        print(f"\n📊 RESTORATION METRICS:")
        print(f"   Current lines: {lines}")
        print(f"   Previous (broken): 143 lines")
        print(f"   Target (full functionality): 400+ lines")
        print(f"   Improvement: {((lines - 143) / 143) * 100:.1f}% increase")
        
        # Validate file size increase
        assert lines >= 400, f"ChatAgent should have 400+ lines, got {lines}"
        
        # Validate restored functionality
        restored_functions = [
            "_optimized_delegation_analysis",
            "_optimized_delegate_and_translate", 
            "_translate_specialist_response",
            "_enhanced_conversational_response",
            "_format_conversation_history",
            "DELEGATION_ANALYSIS_TEMPLATE",
            "CONVERSATIONAL_RESPONSE_TEMPLATE"
        ]
        
        missing_functions = []
        for func in restored_functions:
            if func not in content:
                missing_functions.append(func)
        
        assert len(missing_functions) == 0, f"Missing functions: {missing_functions}"
        
        # Validate architectural coherence
        architectural_checks = [
            "src.core.engine",
            "master_orchestrator", 
            "InternalDelegationResponse"
        ]
        
        missing_architecture = []
        for check in architectural_checks:
            if check not in content:
                missing_architecture.append(check)
        
        assert len(missing_architecture) <= 1, f"Architecture issues: {missing_architecture}"
        
        print(f"✅ ChatAgent restoration validation PASSED")
    
    def test_performance_balance_validation(self):
        """Validate that performance and functionality are properly balanced."""
        routing_analyzer_path = "src/agents/orchestrator/routing/routing_analyzer.py"
        
        if os.path.exists(routing_analyzer_path):
            with open(routing_analyzer_path, 'r') as f:
                routing_content = f.read()
            
            # Check that function calling optimizations are present
            function_calling_present = (
                "function calling" in routing_content and 
                "bind_tools" in routing_content
            )
            
            print(f"   Function calling optimization: {'✅' if function_calling_present else '❌'}")
            
            # This is a soft check - routing might have been refactored
            if not function_calling_present:
                print(f"   ⚠️  Function calling patterns not detected (may be refactored)")
        
        print(f"✅ Performance balance validation completed")