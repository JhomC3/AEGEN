# tests/unit/test_schemas.py
# VERSIÓN DE PRODUCCIÓN: FUSIÓN DE COBERTURA EXHAUSTIVA Y ARQUITECTURA ROBUSTA
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.core.schemas import (
    AnalysisDetails,
    AnalysisFinding,
    AnalysisPlan,
    AnalysisStatus,
    AnalyzeQuery,
    AnalyzeResponse,
    HealthCheckResponse,
    PlanStep,
    ReportFormat,
    ServiceHealth,
    StatusResponse,
)

# --- Fixtures permanecen igual, son una excelente práctica ---


@pytest.fixture
def valid_uuid() -> UUID:
    """Proporciona un UUID único para cada prueba que lo utilice."""
    return uuid4()


# --- Clases de Pruebas: Organización y Escalabilidad ---


class TestAnalyzeQuery:
    """Agrupa todas las pruebas para el esquema AnalyzeQuery."""

    def test_creation_valid_minimal(self):
        """Prueba la creación con solo el campo 'query' requerido."""
        query_obj = AnalyzeQuery(query="Analyse this valid query please.")
        assert query_obj.query == "Analyse this valid query please."
        assert query_obj.user_id is None
        assert query_obj.session_id is None

    def test_creation_valid_with_all_fields(self, valid_uuid: UUID):
        """Prueba la creación proporcionando todos los campos opcionales."""
        query_obj = AnalyzeQuery(
            query="Analyse this with all fields.",
            user_id="test-user",
            session_id=valid_uuid,
        )
        assert query_obj.user_id == "test-user"
        assert query_obj.session_id == valid_uuid

    def test_edge_case_lengths(self):
        """Prueba los valores límite para la longitud de la consulta."""
        assert AnalyzeQuery(query="a" * 5).query == "a" * 5
        assert AnalyzeQuery(query="a" * 1000).query == "a" * 1000

    @pytest.mark.parametrize(
        "invalid_data, error_type, loc",
        [
            ({"user_id": "test"}, "missing", ("query",)),
            ({"query": "Hi"}, "string_too_short", ("query",)),
            ({"query": "a" * 1001}, "string_too_long", ("query",)),
            (
                {"query": "Valid query", "session_id": "not-a-uuid"},
                "uuid_parsing",
                ("session_id",),
            ),
        ],
        ids=["missing_query", "query_too_short", "query_too_long", "invalid_uuid"],
    )
    def test_validation_failures(self, invalid_data: dict, error_type: str, loc: tuple):
        """Prueba varios fallos de validación de forma parametrizada."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeQuery(**invalid_data)  # type: ignore
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == error_type
        assert errors[0]["loc"] == loc


class TestStatusAndHealth:
    """Agrupa pruebas para StatusResponse, ServiceHealth y HealthCheckResponse."""

    def test_status_response_valid(self):
        """Prueba StatusResponse con todos los campos."""
        resp = StatusResponse(status="API is UP", environment="test", version="1.0")
        assert resp.status == "API is UP"
        assert resp.environment == "test"
        assert resp.version == "1.0"

    def test_service_health_valid(self):
        """Prueba ServiceHealth con y sin el campo opcional 'details'."""
        service_with_details = ServiceHealth(
            name="db", status="ok", details="Connected"
        )
        service_without_details = ServiceHealth(name="api", status="degraded")
        assert service_with_details.details == "Connected"
        assert service_without_details.details is None

    def test_health_check_response_valid(self):
        """Prueba HealthCheckResponse con una lista de servicios."""
        services = [ServiceHealth(name="db", status="ok", details="Connected")]
        resp = HealthCheckResponse(overall_status="healthy", services=services)
        assert resp.overall_status == "healthy"
        assert len(resp.services) == 1
        assert resp.services[0].name == "db"


class TestAnalysisFindingAndDetails:
    """Agrupa pruebas para AnalysisFinding y AnalysisDetails."""

    def test_analysis_finding_creation_valid(self):
        """Prueba la creación de AnalysisFinding con y sin campos opcionales."""
        minimal_finding = AnalysisFinding(description="A finding.")
        assert minimal_finding.severity is None
        assert minimal_finding.confidence is None

        full_finding = AnalysisFinding(
            description="Full finding",
            severity="high",
            confidence=0.95,
            source_ids=["src1"],
            metadata={"tag": "critical"},
        )
        assert full_finding.severity == "high"
        assert full_finding.metadata == {"tag": "critical"}

    @pytest.mark.parametrize(
        "invalid_data, error_type",
        [
            ({"description": "Test", "confidence": -0.1}, "greater_than_equal"),
            ({"description": "Test", "confidence": 1.1}, "less_than_equal"),
            ({"description": ""}, "string_too_short"),
            ({"severity": "low"}, "missing"),
        ],
        ids=["conf_too_low", "conf_too_high", "desc_too_short", "missing_desc"],
    )
    def test_analysis_finding_validation_failures(
        self, invalid_data: dict, error_type: str
    ):
        """Prueba varios fallos de validación para AnalysisFinding."""
        with pytest.raises(ValidationError) as exc_info:
            AnalysisFinding(**invalid_data)  # type: ignore
        assert exc_info.value.errors()[0]["type"] == error_type

    def test_analysis_details_creation(self):
        """Prueba la creación de AnalysisDetails, con y sin valores por defecto."""
        default_details = AnalysisDetails()
        assert default_details.summary == "No summary available."
        assert default_details.key_findings == []

        finding = AnalysisFinding(description="A finding.")
        full_details = AnalysisDetails(
            summary="Custom summary",
            key_findings=[finding],
            data_sources_used=["source1"],
        )
        assert full_details.summary == "Custom summary"
        assert len(full_details.key_findings) == 1


class TestAnalyzeResponse:
    """Agrupa todas las pruebas para el esquema AnalyzeResponse."""

    def test_creation_valid(self, valid_uuid: UUID):
        """Prueba la creación válida de AnalyzeResponse."""
        details = AnalysisDetails(summary="Test Details")
        now_iso = datetime.now().isoformat()
        resp = AnalyzeResponse(
            request_id=valid_uuid,
            status=AnalysisStatus.PROCESSING,
            query_received="Original query",
            report_generated_at=now_iso,
            report_content="Report content.",
            details=details,
        )
        assert resp.request_id == valid_uuid
        assert resp.status == AnalysisStatus.PROCESSING
        assert resp.query_received == "Original query"

    @pytest.mark.parametrize("status", list(AnalysisStatus))
    def test_all_statuses(self, status: AnalysisStatus):
        """Prueba que todos los valores del enum AnalysisStatus son aceptados."""
        resp = AnalyzeResponse(
            query_received="Query",
            report_generated_at=datetime.now().isoformat(),
            report_content="Content",
            details=AnalysisDetails(),
            status=status,
        )
        assert resp.status == status

    def test_missing_required_fields_raises_error(self):
        """Verifica que ValidationError se levanta si faltan campos requeridos."""
        with pytest.raises(ValidationError):
            AnalyzeResponse()  # type: ignore[call-arg]


class TestAnalysisPlan:
    """Agrupa todas las pruebas para PlanStep y AnalysisPlan."""

    def test_plan_step_creation(self):
        """Prueba la creación de PlanStep, con y sin campos de herramientas."""
        step_with_tools = PlanStep(
            step_id=1,
            action="Fetch data",
            tool_to_use="api_tool",
            tool_parameters={"endpoint": "/data"},
            expected_output_description="JSON data",
        )
        assert step_with_tools.tool_to_use == "api_tool"

        step_without_tools = PlanStep(
            step_id=2, action="Summarize", expected_output_description="Text summary"
        )
        assert step_without_tools.tool_to_use is None

    def test_analysis_plan_creation(self):
        """Prueba la creación de AnalysisPlan con una lista de pasos."""
        steps = [
            PlanStep(step_id=1, action="Step 1", expected_output_description="Out 1")
        ]
        plan = AnalysisPlan(original_query="Test plan", steps=steps)
        assert isinstance(plan.plan_id, UUID)
        assert len(plan.steps) == 1
        assert plan.original_query == "Test plan"


class TestEnumsAndSerialization:
    """Agrupa pruebas misceláneas para enums y serialización."""

    def test_enum_values(self):
        """Verifica los valores literales de los enums."""
        assert AnalysisStatus.COMPLETED.value == "completed"
        assert ReportFormat.JSON_DETAILED.value == "json_detailed"

    def test_json_serialization(self, valid_uuid: UUID):
        """Prueba la serialización a JSON con model_dump."""
        query_obj = AnalyzeQuery(
            query="Test query", user_id="user1", session_id=valid_uuid
        )
        json_data = query_obj.model_dump(mode="json")
        assert json_data["query"] == "Test query"
        assert json_data["user_id"] == "user1"
        assert json_data["session_id"] == str(valid_uuid)
