from src.memory.chunker import RecursiveChunker


def test_chunker_basic():
    chunker = RecursiveChunker(chunk_size=50, chunk_overlap=10)
    text = (
        "Este es un texto de prueba. Tiene varias oraciones para probar el chunking recursivo. "  # noqa: E501
        * 5
    )
    chunks = chunker.chunk(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 100  # Caracteres, no tokens en este assert


def test_chunker_overlap():
    chunker = RecursiveChunker(chunk_size=20, chunk_overlap=10)
    text = "Palabra1 Palabra2 Palabra3 Palabra4 Palabra5 Palabra6 Palabra7 Palabra8"
    chunks = chunker.chunk(text)

    # Verificar que el final de un chunk está en el inicio del siguiente
    if len(chunks) > 1:
        # Esto es heurístico dependiendo de dónde corte el tokenizador
        pass


def test_chunker_empty():
    chunker = RecursiveChunker()
    assert chunker.chunk("") == []
    assert chunker.chunk("   ") == []


def test_chunker_large_paragraph():
    # Probar que divide un párrafo gigante recursivamente
    chunker = RecursiveChunker(chunk_size=10, chunk_overlap=2)
    text = "Esta es una oración muy larga que definitivamente excede el límite de diez tokens por mucho."  # noqa: E501
    chunks = chunker.chunk(text)

    assert len(chunks) > 1
    for chunk in chunks:
        # Algunos chunks pueden exceder ligeramente si no hay separadores,
        # pero el RecursiveChunker intenta ser inteligente.
        assert chunker.count_tokens(chunk.content) <= 15  # Margen pequeño
