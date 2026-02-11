-- src/memory/schema.sql
-- Habilitar soporte para llaves foráneas
PRAGMA foreign_keys = ON;

-- Tabla principal de memorias (texto + metadatos)
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    namespace TEXT NOT NULL DEFAULT 'user', -- 'global' | 'user_{id}'
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,       -- SHA-256 para deduplicación
    memory_type TEXT NOT NULL,               -- 'fact', 'preference', 'conversation', 'document'
    metadata TEXT DEFAULT '{}',              -- JSON almacenado como texto
    source_type TEXT NOT NULL DEFAULT 'explicit'
        CHECK(source_type IN ('explicit', 'observed', 'inferred')),
    confidence REAL NOT NULL DEFAULT 1.0
        CHECK(confidence >= 0.0 AND confidence <= 1.0),
    sensitivity TEXT NOT NULL DEFAULT 'low'
        CHECK(sensitivity IN ('low', 'medium', 'high')),
    evidence TEXT,
    confirmed_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice FTS5 para búsqueda rápida por palabras clave exactas
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    content='memories',
    content_rowid='id'
);

-- Triggers para mantener FTS sincronizado automáticamente
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
END;

-- Tabla vectorial (sqlite-vec)
-- Dimensión 768 para text-embedding-004 de Google
CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
    embedding FLOAT[768]
);

-- Mapeo entre el vector (rowid) y la memoria (id)
CREATE TABLE IF NOT EXISTS vector_memory_map (
    vector_id INTEGER PRIMARY KEY, -- Coincide con el rowid de memory_vectors
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE
);

-- Cache de embeddings para optimizar costos de API
CREATE TABLE IF NOT EXISTS embedding_cache (
    content_hash TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,         -- Vector serializado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Perfiles de Usuario (Local-First)
CREATE TABLE IF NOT EXISTS profiles (
    chat_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,              -- JSON del perfil
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger de limpieza automática: borra el vector físico cuando se elimina su referencia
-- Esto completa la cascada de limpieza: memories → vector_memory_map → memory_vectors
CREATE TRIGGER IF NOT EXISTS cleanup_vector_on_map_delete
AFTER DELETE ON vector_memory_map
BEGIN
    DELETE FROM memory_vectors WHERE rowid = OLD.vector_id;
END;
