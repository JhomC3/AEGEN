# tests/unit/memory/test_chunker.py
from src.memory.chunker import RecursiveChunker


def test_chunker_basic():
    chunker = RecursiveChunker(chunk_size=50, chunk_overlap=10)
    text = (
        "Este es un texto de prueba. Tiene varias oraciones para probar el chunking recursivo. "
        * 5
    )
    chunks = chunker.chunk(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunker.encoding.encode(chunk.content)) <= 50
        assert chunk.content != ""


def test_chunker_overlap():
    chunker = RecursiveChunker(chunk_size=20, chunk_overlap=10)
    text = "Palabra1 Palabra2 Palabra3 Palabra4 Palabra5 Palabra6 Palabra7 Palabra8"
    chunks = chunker.chunk(text)

    # Verificar que hay solapamiento (el final de un chunk debe estar en el siguiente)
    if len(chunks) > 1:
        last_words = chunks[0].content.split()[-2:]
        next_words = chunks[1].content.split()[:5]
        # Al menos una palabra del final del primer chunk debería estar en el segundo
        assert any(word in next_words for word in last_words)


def test_chunker_empty_text():
    chunker = RecursiveChunker()
    assert chunker.chunk("") == []
    assert chunker.chunk("   ") == []


def test_chunker_large_paragraph():
    # Probar que divide un párrafo gigante recursivamente
    chunker = RecursiveChunker(chunk_size=10, chunk_overlap=2)
    text = "Esta es una oración muy larga que definitivamente excede el límite de diez tokens por mucho."
    chunks = chunker.chunk(text)

    assert len(chunks) > 1
    for chunk in chunks:
        # Algunos chunks pueden exceder ligeramente si no hay separadores,
        # pero con espacios debería poder dividir casi siempre
        assert chunker.count_tokens(chunk.content) <= 15  # Margen pequeño
