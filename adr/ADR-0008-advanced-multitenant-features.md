# ADR-0008: Características Avanzadas Multi-Tenant

## Estado
**PROPUESTO** - Basado en análisis profundo de requerimientos del usuario

## Contexto

### Situación Actual (Post Task #1 Completado)
- ✅ ChromaDB multi-tenant implementado con collections per-user
- ✅ Aislamiento básico de datos garantizado
- ✅ Interface ChromaManager con dependency injection
- ❌ **LIMITACIONES IDENTIFICADAS**: 6 características avanzadas solicitadas no implementadas

### Requerimientos del Usuario (6 Preguntas Críticas)
1. **Análisis Semántico**: "¿Se guarda absolutamente todo? ¿Mejor analizar interacción?"
2. **Memoria Local**: "¿Dónde se guarda en memoria local?"
3. **Deployment Cloud**: "¿Es mejor usar memoria en la nube?"
4. **Collections Globales**: "¿Cómo crear colección global?"
5. **Sistema de Roles**: "¿Cómo hacer usuario administrador?"
6. **Acceso Cross-Tenant**: "¿Cómo acceder a colecciones públicas?"

### Objetivo
Extender la arquitectura multi-tenant básica con características avanzadas que mantengan la simplicidad y filosofía del proyecto.

## Decisión

### **Decisión 1: Sistema de Roles y Permisos (Pregunta 5)**

**Implementación en ChromaManager:**
```python
from enum import Enum
from typing import Set

class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(Enum):
    READ_OWN = "read_own"
    WRITE_OWN = "write_own"
    READ_GLOBAL = "read_global"
    WRITE_GLOBAL = "write_global"
    MANAGE_USERS = "manage_users"

class RoleManager:
    ROLE_PERMISSIONS = {
        UserRole.USER: {Permission.READ_OWN, Permission.WRITE_OWN},
        UserRole.ADMIN: {Permission.READ_OWN, Permission.WRITE_OWN, Permission.READ_GLOBAL, Permission.WRITE_GLOBAL},
        UserRole.SUPER_ADMIN: {Permission.READ_OWN, Permission.WRITE_OWN, Permission.READ_GLOBAL, Permission.WRITE_GLOBAL, Permission.MANAGE_USERS}
    }

    async def check_permission(self, user_id: str, permission: Permission) -> bool
    async def grant_role(self, user_id: str, role: UserRole, granted_by: str) -> bool
```

**Justificación:**
- ✅ **Simple**: Solo 3 roles, fácil de entender
- ✅ **Extensible**: Permission enum permite futuras expansiones
- ✅ **Secure**: Default USER role, escalación controlada

### **Decisión 2: Collections Globales (Pregunta 4)**

**Extensión de ChromaManager:**
```python
class GlobalCollectionManager:
    """Gestiona collections globales compartidas entre usuarios."""

    RESERVED_COLLECTIONS = {
        "shared_knowledge": "Base de conocimiento compartida",
        "public_templates": "Plantillas públicas de documentos",
        "community_insights": "Insights comunitarios"
    }

    async def create_global_collection(self, name: str, created_by_admin: str, metadata: Dict) -> bool
    async def query_global_collection(self, user_id: str, collection_name: str, query: str) -> List[Result]
    async def contribute_to_global(self, user_id: str, collection: str, data: Dict, requires_approval: bool = True) -> bool
```

**Naming Convention:**
```python
# User collections (existente)
"user_{user_id}"          # ej: user_12345

# Global collections (nuevo)
"global_{collection_name}" # ej: global_shared_knowledge
```

**Justificación:**
- ✅ **Clear Separation**: Prefijo "global_" evita colisiones
- ✅ **Permission-Based**: Requiere permisos para acceso
- ✅ **Controlled**: Admin puede crear, users contribuir con approval

### **Decisión 3: Análisis Semántico de Contenido (Pregunta 1)**

**Smart Content Analyzer:**
```python
from typing import Optional, List, Dict
from dataclasses import dataclass

@dataclass
class ContentAnalysis:
    should_store: bool
    relevance_score: float
    extracted_entities: List[str]
    summary: Optional[str]
    categories: List[str]

class SmartContentAnalyzer:
    """Analiza contenido antes de almacenamiento para optimizar relevancia."""

    async def analyze_user_message(self, content: str, context: Dict) -> ContentAnalysis
    async def extract_key_information(self, message: str) -> List[str]
    async def should_store_interaction(self, content: str, user_history: Dict) -> bool

    # Filtros inteligentes
    SKIP_PATTERNS = ["testing", "hello", "thanks", "ok"]
    IMPORTANT_PATTERNS = ["remember", "save", "important", "document"]
```

**Integración con ChromaManager:**
```python
# Extender save_user_data existente
async def save_user_data_smart(self, user_id: str, data: Dict, data_type: str) -> None:
    # Análisis semántico antes de guardar
    analysis = await self.content_analyzer.analyze_user_message(
        data.get("content", ""),
        {"user_id": user_id, "session_context": data}
    )

    if analysis.should_store:
        # Enriquecer metadata con análisis
        enhanced_data = {
            **data,
            "entities": analysis.extracted_entities,
            "categories": analysis.categories,
            "relevance_score": analysis.relevance_score
        }
        await self.save_user_data(user_id, enhanced_data, data_type)
```

**Justificación:**
- ✅ **Storage Efficiency**: Reduce ruido y almacena solo relevante
- ✅ **Enhanced Search**: Entities y categories mejoran búsquedas
- ✅ **User Value**: Summary y relevance_score aportan contexto

### **Decisión 4: Memoria Híbrida Local/Cloud (Preguntas 2 + 3)**

**Hybrid Memory Strategy:**
```python
from enum import Enum

class StorageStrategy(Enum):
    LOCAL_ONLY = "local"           # Para dev/testing
    CLOUD_ONLY = "cloud"          # Para producción distribuida
    HYBRID = "hybrid"             # Local cache + cloud persistence
    AUTO = "auto"                 # Decide automáticamente

class HybridMemoryManager:
    """Gestiona estrategia híbrida de memoria local y cloud."""

    def __init__(self, strategy: StorageStrategy = StorageStrategy.AUTO):
        self.strategy = strategy
        self.local_cache = {}  # Simple dict para cache local
        self.chroma_manager = ChromaManager()

    async def store_with_strategy(self, user_id: str, data: Dict, priority: str = "normal") -> None:
        if self.strategy in [StorageStrategy.LOCAL_ONLY, StorageStrategy.HYBRID]:
            # Cache local para acceso rápido
            cache_key = f"{user_id}:recent"
            self.local_cache[cache_key] = data

        if self.strategy in [StorageStrategy.CLOUD_ONLY, StorageStrategy.HYBRID]:
            # Persistencia en ChromaDB
            await self.chroma_manager.save_user_data(user_id, data)

    async def query_hybrid(self, user_id: str, query: str, max_results: int = 5) -> List[Dict]:
        # Buscar primero en cache local
        local_results = self._query_local_cache(user_id, query)

        # Complementar con ChromaDB si no suficientes resultados
        if len(local_results) < max_results:
            cloud_results = await self.chroma_manager.query_user_data(user_id, query)
            return local_results + cloud_results[:max_results-len(local_results)]

        return local_results[:max_results]
```

**Configuración per Environment:**
```python
# settings.py
class BaseAppSettings:
    # Configuración memoria híbrida
    MEMORY_STRATEGY: StorageStrategy = StorageStrategy.AUTO
    LOCAL_CACHE_TTL: int = 300  # 5 minutos
    CLOUD_BATCH_SIZE: int = 50

    # Cloud deployment settings
    CHROMA_CLOUD_HOST: Optional[str] = None
    CHROMA_CLOUD_PORT: Optional[int] = None
    CHROMA_USE_CLOUD: bool = False
```

**Justificación:**
- ✅ **Performance**: Cache local para consultas frecuentes
- ✅ **Flexibility**: Configuración per environment
- ✅ **Resilience**: Fallback entre local y cloud
- ✅ **Cost Optimization**: Reduce llamadas cloud innecesarias

### **Decisión 5: Acceso Cross-Tenant Controlado (Pregunta 6)**

**Cross-Tenant Access Manager:**
```python
class CrossTenantAccess:
    """Gestiona acceso controlado a collections de otros usuarios."""

    async def grant_collection_access(
        self,
        owner_user_id: str,
        target_user_id: str,
        collection_type: str,
        permission_level: str = "read"
    ) -> bool:
        # Validar que owner puede otorgar permisos
        if not await self.role_manager.check_permission(owner_user_id, Permission.WRITE_OWN):
            return False

        # Crear registro de permiso cross-tenant
        permission_record = {
            "owner": owner_user_id,
            "accessor": target_user_id,
            "collection": f"user_{owner_user_id}",
            "level": permission_level,
            "granted_at": datetime.utcnow()
        }

        await self._store_permission(permission_record)
        return True

    async def query_with_cross_tenant_access(
        self,
        requester_id: str,
        query: str,
        include_accessible: bool = True
    ) -> List[Dict]:
        results = []

        # Buscar en propia collection
        own_results = await self.chroma_manager.query_user_data(requester_id, query)
        results.extend(own_results)

        if include_accessible:
            # Buscar en collections con permisos otorgados
            accessible_collections = await self._get_accessible_collections(requester_id)
            for collection in accessible_collections:
                cross_results = await self._query_cross_tenant(collection, query, requester_id)
                results.extend(cross_results)

        # Buscar en global collections si tiene permisos
        if await self.role_manager.check_permission(requester_id, Permission.READ_GLOBAL):
            global_results = await self._query_global_collections(query)
            results.extend(global_results)

        return results
```

**Security Model:**
```python
# Metadata para cross-tenant access
cross_tenant_metadata = {
    "owner_id": "original_user_123",
    "accessor_id": "requester_456",
    "access_level": "read",  # read, write, admin
    "access_granted_by": "user_123",
    "access_expires": "2025-12-31T23:59:59Z",
    "source_collection": "user_123"
}
```

**Justificación:**
- ✅ **Security First**: Permisos explícitos requeridos
- ✅ **Traceability**: Metadata completo de acceso
- ✅ **Controlled**: Owner decide qué compartir
- ✅ **Expirable**: Accesos temporales posibles

## Implementación

### **Fase 1: Foundation Extensions (Semanas 1-2)**
1. Implementar `RoleManager` con UserRole enum
2. Crear `GlobalCollectionManager` con collections reservadas
3. Extender configuración con roles por defecto
4. Tests unitarios para roles y permisos básicos

### **Fase 2: Smart Analysis (Semanas 2-3)**
1. Implementar `SmartContentAnalyzer` con patterns básicos
2. Integrar análisis en `save_user_data_smart`
3. Configurar filtros y thresholds por environment
4. Tests de análisis semántico y filtrado

### **Fase 3: Hybrid Memory (Semanas 3-4)**
1. Crear `HybridMemoryManager` con strategies
2. Implementar cache local simple (dict-based inicialmente)
3. Configuración flexible local/cloud per environment
4. Performance testing y optimization

### **Fase 4: Cross-Tenant Access (Semanas 4-5)**
1. Implementar `CrossTenantAccess` con security model
2. Sistema de permisos y metadata tracking
3. UI/API endpoints para gestión de accesos
4. Security testing y validation exhaustiva

## Consecuencias

### **Positivas**
- ✅ **Enhanced User Experience**: Filtrado inteligente + acceso controlado
- ✅ **Performance**: Memoria híbrida optimiza speed + persistencia
- ✅ **Collaboration**: Collections globales + cross-tenant permiten trabajo colaborativo
- ✅ **Security**: Sistema de roles robusto mantiene aislamiento por defecto
- ✅ **Scalability**: Estrategias cloud-ready para deployment distribuido

### **Negativas**
- ❌ **Complexity**: Más componentes y configuración
- ❌ **Resource Usage**: Cache local + análisis semántico consume más memoria
- ❌ **Administration**: Sistema de roles requiere gestión manual inicial

### **Riesgos**
- 🔶 **Permission Sprawl**: Gestión de permisos cross-tenant puede volverse compleja
- 🔶 **Cache Coherency**: Mantener consistencia local/cloud requiere estrategia
- 🔶 **Performance**: Análisis semántico puede añadir latencia

## Acceptance Criteria

### **Foundation Extensions (Must-Have)**
```bash
# Sistema de roles funcional
role_manager.grant_role("user_123", UserRole.ADMIN, "super_admin_456")
assert await role_manager.check_permission("user_123", Permission.READ_GLOBAL) == True

# Collections globales operacionales
await global_manager.create_global_collection("shared_knowledge", "admin_123")
results = await global_manager.query_global_collection("user_456", "shared_knowledge", "query")
assert len(results) >= 0
```

### **Smart Analysis (Should-Have)**
```bash
# Análisis semántico funcionando
analysis = await content_analyzer.analyze_user_message("This is important information", context)
assert analysis.should_store == True
assert analysis.relevance_score > 0.7
```

### **Hybrid Memory (Should-Have)**
```bash
# Memoria híbrida operacional
await hybrid_manager.store_with_strategy("user_123", data, "high")
results = await hybrid_manager.query_hybrid("user_123", "query", max_results=5)
assert len(results) <= 5
```

### **Cross-Tenant Access (Could-Have)**
```bash
# Acceso cross-tenant controlado
await cross_tenant.grant_collection_access("owner_123", "accessor_456", "documents", "read")
results = await cross_tenant.query_with_cross_tenant_access("accessor_456", "query")
assert any(r["metadata"]["owner_id"] == "owner_123" for r in results)
```

## Validación

- [ ] **Architecture Review**: Consistency con ADR-0007 y filosofía proyecto
- [ ] **Security Review**: Validation roles, permisos y aislamiento
- [ ] **Performance Review**: Impacto de análisis semántico y memoria híbrida
- [ ] **User Experience Review**: Interfaces claras para características avanzadas

---

**Decision Date**: 2025-08-25
**Status**: PROPUESTO
**Dependent on**: ADR-0007 (Multi-Tenant Foundation)
**Next Review**: Post implementación Fase 1 (End Week 2)
