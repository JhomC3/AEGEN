"""Catálogo de las 36 preguntas del ejercicio Dan Koe (spec 020).

Textos fieles al chat del ejercicio. `corta` para el chip, `completa` para el
popup. El orden de la lista es el orden de anterior/siguiente.
"""

PREGUNTAS: list[dict] = [
    # Excavación psicológica (ex01–ex14).
    {
        "id": "ex01",
        "grupo": "Excavación",
        "corta": "Insatisfacción tolerada",
        "completa": "¿Cuál es esa insatisfacción sorda y persistente con la que has "
        "aprendido a convivir? No hablo del sufrimiento profundo, sino de aquello "
        "que has aprendido a tolerar. (Si no lo odias, lo tolerarás.)",
    },
    {
        "id": "ex02",
        "grupo": "Excavación",
        "corta": "Quejas repetidas",
        "completa": "¿De qué te quejas repetidamente, pero nunca cambias realmente? "
        "Escribe las tres quejas que más has repetido durante el último año.",
    },
    {
        "id": "ex03",
        "grupo": "Excavación",
        "corta": "Qué diría un observador",
        "completa": "Para cada una de esas quejas, ¿qué concluiría alguien que observara "
        "tu comportamiento —no tus palabras— que realmente quieres?",
    },
    {
        "id": "ex04",
        "grupo": "Excavación",
        "corta": "Verdad insoportable",
        "completa": "¿Qué verdad sobre tu vida actual sería insoportable admitirle a "
        "alguien a quien respetas profundamente?",
    },
    {
        "id": "ex05",
        "grupo": "Excavación",
        "corta": "Martes en 5 años",
        "completa": "Si absolutamente nada cambia durante los próximos cinco años, "
        "describe un martes cualquiera. ¿Dónde te despiertas? ¿Qué siente tu cuerpo? "
        "¿Cuál es el primer pensamiento que tienes? ¿Quién está a tu alrededor? "
        "¿Qué haces entre las 9:00 a. m. y las 6:00 p. m.? ¿Cómo te sientes a las 10:00 p. m.?",
    },
    {
        "id": "ex06",
        "grupo": "Excavación",
        "corta": "A 10 años",
        "completa": "Ahora hazlo, pero a diez años. ¿Qué has perdido? ¿Qué oportunidades "
        "se cerraron? ¿Quién se rindió contigo? ¿Qué dice la gente sobre ti cuando no "
        "estás en la habitación?",
    },
    {
        "id": "ex07",
        "grupo": "Excavación",
        "corta": "Final de la vida segura",
        "completa": "Estás al final de tu vida. Viviste la versión segura de tu vida. "
        "Nunca rompiste el patrón. ¿Cuál fue el costo? ¿Qué nunca te permitiste sentir, "
        "intentar o llegar a ser?",
    },
    {
        "id": "ex08",
        "grupo": "Excavación",
        "corta": "Quién ya vive ese futuro",
        "completa": "¿Quién en tu vida ya está viviendo el futuro que acabas de describir? "
        "Alguien que esté cinco, diez o veinte años por delante de ti en esa misma "
        "trayectoria. ¿Qué sientes cuando piensas en convertirte en esa persona?",
    },
    {
        "id": "ex09",
        "grupo": "Excavación",
        "corta": "Identidad a abandonar",
        "completa": "¿Qué identidad tendrías que abandonar para cambiar de verdad? "
        "Completa: «Soy el tipo de persona que…». Y después: ¿qué te costaría "
        "socialmente dejar de ser esa persona?",
    },
    {
        "id": "ex10",
        "grupo": "Excavación",
        "corta": "Razón más vergonzosa",
        "completa": "¿Cuál es la razón más vergonzosa por la que no has cambiado? La que "
        "te hace sonar débil, asustado o perezoso, en lugar de razonable. No busques "
        "una explicación inteligente. Busca la respuesta que más te cueste admitir.",
    },
    {
        "id": "ex11",
        "grupo": "Excavación",
        "corta": "Qué proteges y a qué costo",
        "completa": "Si tu comportamiento actual es una forma de autoprotección, ¿qué "
        "estás protegiendo exactamente? Y, sobre todo: ¿qué te está costando esa protección?",
    },
    {
        "id": "ex12",
        "grupo": "Excavación",
        "corta": "Vida soñada en 3 años",
        "completa": "Olvida la practicidad por un momento. Si pudieras chasquear los dedos "
        "y estar viviendo una vida diferente dentro de tres años —no lo que sea "
        "realista, sino lo que realmente quieres—: ¿qué quieres? Describe un martes "
        "cualquiera de esa vida con el mismo nivel de detalle.",
    },
    {
        "id": "ex13",
        "grupo": "Excavación",
        "corta": "Qué creer (identidad)",
        "completa": "¿Qué tendrías que creer sobre ti mismo para que esa vida se sintiera "
        "natural, en lugar de forzada? Escribe la frase de identidad: «Soy el tipo de "
        "persona que…»",
    },
    {
        "id": "ex14",
        "grupo": "Excavación",
        "corta": "Una cosa esta semana",
        "completa": "¿Cuál es una cosa que harías esta semana si ya fueras esa persona?",
    },
    # Piloto automático (pa01–pa09).
    {
        "id": "pa01",
        "grupo": "Piloto automático",
        "corta": "Qué evito ahora mismo",
        "completa": "¿Qué estoy evitando ahora mismo al hacer lo que estoy haciendo?",
    },
    {
        "id": "pa02",
        "grupo": "Piloto automático",
        "corta": "Últimas 2 horas grabadas",
        "completa": "Si alguien hubiera grabado las últimas dos horas, ¿qué concluiría "
        "que realmente quieres de tu vida?",
    },
    {
        "id": "pa03",
        "grupo": "Piloto automático",
        "corta": "Hacia qué vida me muevo",
        "completa": "¿Me estoy moviendo hacia la vida que odio o hacia la vida que quiero?",
    },
    {
        "id": "pa04",
        "grupo": "Piloto automático",
        "corta": "Qué finjo que no importa",
        "completa": "¿Cuál es la cosa más importante que estoy fingiendo que no es importante?",
    },
    {
        "id": "pa05",
        "grupo": "Piloto automático",
        "corta": "Proteger identidad hoy",
        "completa": "¿Qué hice hoy por proteger mi identidad, en lugar de hacerlo por deseo genuino?",
    },
    {
        "id": "pa06",
        "grupo": "Piloto automático",
        "corta": "Más vivo / más muerto",
        "completa": "¿Cuándo te sentiste más vivo hoy? ¿Cuándo te sentiste más muerto?",
    },
    {
        "id": "pa07",
        "grupo": "Piloto automático",
        "corta": "Sin necesitar ser visto",
        "completa": "¿Qué cambiaría si dejaras de necesitar que las personas te vieran "
        "como la identidad que escribiste antes?",
    },
    {
        "id": "pa08",
        "grupo": "Piloto automático",
        "corta": "Vivo a cambio de seguro",
        "completa": "¿En qué parte de tu vida estás intercambiando estar vivo por estar seguro?",
    },
    {
        "id": "pa09",
        "grupo": "Piloto automático",
        "corta": "Versión más pequeña mañana",
        "completa": "¿Cuál es la versión más pequeña de la persona en la que quieres "
        "convertirte que podrías ser mañana?",
    },
    # Síntesis y lentes (si01–si07).
    {
        "id": "si01",
        "grupo": "Síntesis",
        "corta": "Por qué estancado",
        "completa": "Después de mirar honestamente todo lo que has escrito hoy, ¿cuál "
        "crees que es la verdadera razón por la que sigues atrapado en este ciclo? "
        "No «no tengo trabajo» o «me falta disciplina». ¿Qué hay debajo de todo eso?",
    },
    {
        "id": "si02",
        "grupo": "Síntesis",
        "corta": "Enemigo real",
        "completa": "¿Cuál es el enemigo real? Nómbralo con claridad. No son las "
        "circunstancias. No son otras personas. ¿Cuál es el patrón interno o la "
        "creencia que ha estado dirigiendo todo esto?",
    },
    {
        "id": "si03",
        "grupo": "Síntesis",
        "corta": "Anti-visión (1 frase)",
        "completa": "Escribe una sola frase que capture aquello en lo que te niegas a "
        "permitir que tu vida se convierta. Esta es tu anti-visión comprimida.",
    },
    {
        "id": "si04",
        "grupo": "Síntesis",
        "corta": "Visión MVP (1 frase)",
        "completa": "Escribe una sola frase que capture aquello hacia lo que estás "
        "construyendo, sabiendo que irá evolucionando. Esta es tu visión MVP.",
    },
    {
        "id": "si05",
        "grupo": "Síntesis",
        "corta": "Lente 1 año",
        "completa": "¿Qué tendría que ser verdad dentro de un año para que supieras que "
        "rompiste el patrón? Una sola cosa concreta.",
    },
    {
        "id": "si06",
        "grupo": "Síntesis",
        "corta": "Lente 1 mes",
        "completa": "¿Qué tendría que ser verdad dentro de un mes para que el objetivo "
        "de un año siguiera siendo posible? Una sola cosa concreta.",
    },
    {
        "id": "si07",
        "grupo": "Síntesis",
        "corta": "Lente diario",
        "completa": "¿Cuáles son 2–3 acciones que puedes poner mañana en bloques de tiempo "
        "y que la persona en la que te estás convirtiendo simplemente haría?",
    },
    # Videojuego (ju01–ju06).
    {
        "id": "ju01",
        "grupo": "Videojuego",
        "corta": "Cómo gano",
        "completa": "Si tu vida fuera un videojuego, ¿cómo sabes que estás ganando? "
        "Define qué significa ganar para ti en términos de la vida que estás construyendo.",
    },
    {
        "id": "ju02",
        "grupo": "Videojuego",
        "corta": "Qué está en juego",
        "completa": "¿Qué está en juego si no ganas este videojuego? ¿Qué ocurre si vuelves "
        "a vivir como hasta ahora? ¿Qué es exactamente lo que estás intentando evitar?",
    },
    {
        "id": "ju03",
        "grupo": "Videojuego",
        "corta": "Misión 12 meses",
        "completa": "¿Cuál es la gran misión que quieres completar durante los próximos "
        "12 meses? Una misión que, si la cumplieras, significara que te alejaste de la "
        "vida que evitas y te acercaste a la que quieres construir.",
    },
    {
        "id": "ju04",
        "grupo": "Videojuego",
        "corta": "Proyecto del mes",
        "completa": "¿Cuál es el proyecto concreto que vas a completar durante este mes? "
        "El “boss fight” de este mes: algo que puedas construir, aprender o desarrollar "
        "y que haga avanzar tu misión.",
    },
    {
        "id": "ju05",
        "grupo": "Videojuego",
        "corta": "Palancas diarias",
        "completa": "¿Cuáles son las 2–3 acciones diarias que realmente mueven la aguja "
        "hacia tu misión? Solo las que, hechas de forma constante, hacen avanzar tu vida "
        "aunque no tengas motivación.",
    },
    {
        "id": "ju06",
        "grupo": "Videojuego",
        "corta": "Reglas (qué no sacrificar)",
        "completa": "¿Qué no estás dispuesto a sacrificar para ganar este juego? ¿Qué cosas "
        "deben mantenerse protegidas mientras construyes esta vida?",
    },
]

POR_ID: dict[str, dict] = {p["id"]: p for p in PREGUNTAS}

GRUPOS: list[str] = ["Excavación", "Piloto automático", "Síntesis", "Videojuego"]


def siguiente(pregunta_id: str) -> dict | None:
    """Siguiente pregunta en orden del catálogo (para el popup)."""
    ids = [p["id"] for p in PREGUNTAS]
    try:
        pos = ids.index(pregunta_id)
    except ValueError:
        return None
    return PREGUNTAS[pos + 1] if pos + 1 < len(ids) else None


def anterior(pregunta_id: str) -> dict | None:
    """Pregunta anterior en orden del catálogo (para el popup)."""
    ids = [p["id"] for p in PREGUNTAS]
    try:
        pos = ids.index(pregunta_id)
    except ValueError:
        return None
    return PREGUNTAS[pos - 1] if pos > 0 else None
