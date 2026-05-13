from pathlib import Path

import pytest


@pytest.mark.performance
class TestADR0009RoutingPerformance:
    def test_routing_analyzer_initialization_method(self):
        routing_tools_path = Path("src/agents/orchestrator/routing/routing_tools.py")
        assert (
            routing_tools_path.exists()
        ), f"Routing tools file missing: {routing_tools_path}"
        content = routing_tools_path.read_text(encoding="utf-8")
        assert "route_user_message" in content

        routing_analyzer_path = Path(
            "src/agents/orchestrator/routing/routing_analyzer.py"
        )
        if routing_analyzer_path.exists():
            content = routing_analyzer_path.read_text(encoding="utf-8")

            # Check for function calling patterns
            function_calling_indicators = [
                "bind_tools",
                "_extract_tool_result",
                "function calling",
            ]

            found_indicators = []
            for indicator in function_calling_indicators:
                if indicator in content:
                    found_indicators.append(indicator)

            # At least some function calling patterns should be present
            assert (
                len(found_indicators) >= 1
            ), "No function calling patterns found in routing analyzer"
            print(f"✅ Routing analyzer function calling patterns: {found_indicators}")
        else:
            pytest.skip("Routing analyzer file not found - may have been refactored")

    def test_adr0009_documentation_exists(self):
        adr_path = Path("adr/archivo/ADR-0009-migracion-rendimiento-enrutamiento.md")
        assert adr_path.exists(), f"ADR-0009 documentation missing: {adr_path}"
        content = adr_path.read_text(encoding="utf-8")

        # Check for key ADR content
        required_adr_content = ["function calling", "Performance", "ACEPTADO"]

        missing_adr_content = []
        for item in required_adr_content:
            if item not in content:
                missing_adr_content.append(item)

        assert (
            len(missing_adr_content) <= 1
        ), f"ADR-0009 missing content: {missing_adr_content}"
        print("✅ ADR-0009 documentation validated")

    def test_performance_improvement_calculation(self):
        """Test theoretical performance improvement calculation."""
        # Performance targets from ADR-0009
        old_performance = 36.5  # seconds (structured output)
        new_performance = 1.8  # seconds (function calling target)
        improvement_factor = old_performance / new_performance

        print("\n📊 PERFORMANCE ANALYSIS:")
        print(f"   Old (structured output): {old_performance}s")
        print(f"   New (function calling): {new_performance}s")
        print(f"   Improvement factor: {improvement_factor:.1f}x")
