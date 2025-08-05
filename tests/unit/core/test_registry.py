# tests/unit/core/test_registry.py
import pytest

from src.core.interfaces.workflow import IWorkflow
from src.core.registry import WorkflowRegistry

# --- Fixtures de prueba ---


# Una clase de workflow falsa para usar en las pruebas
class MockWorkflow(IWorkflow):
    async def run(self, data):
        return {"status": "mocked"}


# Otra clase de workflow falsa
class AnotherMockWorkflow(IWorkflow):
    async def run(self, data):
        return {"status": "another"}


@pytest.fixture(autouse=True)
def clear_registry():
    """
    Fixture que se ejecuta antes de cada prueba para limpiar el registro.
    Esto asegura que las pruebas sean independientes entre sí.
    """
    # Obtenemos la instancia singleton
    registry_instance = WorkflowRegistry()
    # Limpiamos su diccionario interno
    registry_instance._registry.clear()
    yield
    # Opcional: limpiar de nuevo después de la prueba
    registry_instance._registry.clear()


# --- Casos de Prueba ---


def test_register_and_get_workflow():
    """
    Verifica que un workflow puede ser registrado y luego recuperado.
    """
    registry = WorkflowRegistry()
    registry.register("test_task")(MockWorkflow)

    workflow_class = registry.get_workflow("test_task")

    assert workflow_class is MockWorkflow


def test_get_non_existent_workflow_returns_none():
    """
    Verifica que get_workflow devuelve None si la tarea no existe.
    """
    registry = WorkflowRegistry()
    assert registry.get_workflow("non_existent_task") is None


def test_register_decorator_works():
    """
    Verifica que el decorador registra la clase correctamente.
    """
    registry = WorkflowRegistry()

    @registry.register("decorated_task")
    class DecoratedWorkflow(IWorkflow):
        async def run(self, data):
            return {}

    workflow_class = registry.get_workflow("decorated_task")
    assert workflow_class is DecoratedWorkflow


def test_register_raises_type_error_for_invalid_class():
    """
    Verifica que el registro falla si la clase no implementa IWorkflow.
    """
    registry = WorkflowRegistry()

    class NotAWorkflow:
        pass

    with pytest.raises(TypeError, match="must implement the IWorkflow interface"):
        # Esta es una forma de probar el decorador sin aplicarlo directamente
        registry.register("invalid_task")(NotAWorkflow)


def test_overriding_workflow_logs_warning(caplog):
    """
    Verifica que se emite un warning si se sobreescribe un workflow.
    """
    registry = WorkflowRegistry()
    registry.register("shared_task")(MockWorkflow)
    registry.register("shared_task")(AnotherMockWorkflow)

    assert "is being overridden" in caplog.text
    # Y verifica que el último registro es el que prevalece
    assert registry.get_workflow("shared_task") is AnotherMockWorkflow


def test_get_all_workflows():
    """
    Verifica que se puede obtener una copia de todos los workflows registrados.
    """
    registry = WorkflowRegistry()
    registry.register("task1")(MockWorkflow)
    registry.register("task2")(AnotherMockWorkflow)

    all_workflows = registry.get_all_workflows()

    assert len(all_workflows) == 2
    assert all_workflows["task1"] is MockWorkflow
    assert all_workflows["task2"] is AnotherMockWorkflow
    # Probar que es una copia
    all_workflows["new"] = None
    assert len(registry.get_all_workflows()) == 2
