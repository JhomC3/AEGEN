"""v024 — Rumbo: histórico de respuestas del ejercicio (spec 020).

`rumbo_respuestas` apila respuestas por pregunta (vigente = última).
Precarga las respuestas del chat del ejercicio (`origen='chat'`) solo si la
tabla está vacía (re-ejecuciones seguras). Textos fieles al chat.
"""

VERSION = 24
NAME = "rumbo_respuestas"

VERSION = 24
NAME = "rumbo_respuestas"

# (pregunta, respuesta) transcritas del ejercicio. Revisadas contra el chat.
SEED: list[tuple[str, str]] = [
    (
        "ex01",
        (
            "Lo que he aprendido a tolerar en estos tres años es mi falta de ingresos "
            "económicos. Creo que me acostumbré a sentirme seguro, aunque esté muy incómodo. "
            "Seguro sin trabajo, por así decirlo."
        ),
    ),
    (
        "ex02",
        (
            "Me quejo de que caigo constantemente y siempre me caigo en el mismo lugar y no "
            "estoy avanzando. Estoy en un bucle de mierda del que no logro salirme: busco algo "
            "nuevo para salir, termino cayendo y me digo que no pasa nada, volvemos a levantar."
        ),
    ),
    (
        "ex03",
        (
            "Si alguien me viera desde lejos diría que no quiero trabajar, que soy un vago y "
            "que solo busco excusas. Pero si yo mismo me digo esas palabras, genero rechazo."
        ),
    ),
    (
        "ex04",
        (
            "Estoy realmente cómodo en este lodazal de lamentaciones, de frustraciones, de "
            "fallos. Me mantengo en este lodazal de justificaciones porque realmente me siento "
            "cómodo, aunque lo deteste. Disfrazo la realidad con acciones sin impacto que me "
            "sirven para decir que lo estoy intentando."
        ),
    ),
    (
        "ex05",
        (
            "Despierto donde mi mamá, apegado a que ella me mantenga. Frustrado, hecho una "
            "mierda, cansado, débil por lo que hay en mi cabeza. Primer pensamiento: otro día "
            "más de mierda. Entre las 9 y las 6 intento algo sabiendo que llevo ocho años "
            "haciendo lo mismo. A las 10 me siento una mierda diciéndome 'al menos lo intenté'."
        ),
    ),
    (
        "ex06",
        (
            "Cabe la posibilidad de que ni siquiera exista, porque no sé si pueda soportar "
            "esto mucho tiempo más. Cero conciencia, evasión profunda. Tal vez hasta mi mamá "
            "se haya rendido conmigo. La gente ni me recordará."
        ),
    ),
    (
        "ex07",
        (
            "Mi vida puede terminar mucho antes si sigo por este camino, y puede que ni "
            "siquiera tenga conciencia para plantearme preguntas."
        ),
    ),
    (
        "ex08",
        (
            "Un montón de tíos y primos presos de las adicciones, sin conciencia, refugiados "
            "en su miseria día a día para sobrevivir. Pensar en convertirme en eso me da ganas "
            "de vomitar. Tengo miedo de irme hacia ese futuro cómodamente y sin objeciones."
        ),
    ),
    (
        "ex09",
        (
            "Tendría que abandonar la identidad del que dice 'está bien, lo volvemos a "
            "intentar' aceptando que va a caer sin avance real. La identidad que me hace caer "
            "es rendirme en luchar, no dominar mis impulsos y justificarme con que estoy "
            "agotado o sin un marco de trabajo."
        ),
    ),
    (
        "ex10",
        (
            "Intenté hacerlo todo perfecto, ser el que sabe todo y hace todo bien. No me "
            "atrevo a hacer algo diferente porque voy a fallar y no quiero hacerlo imperfecto. "
            "Miedo a que digan que hago las cosas mal, a que me vean débil, indeciso, tonto, "
            "perdedor."
        ),
    ),
    (
        "ex11",
        (
            "Me protejo de verme vulnerable. Me está costando vivir, expresarme, sentir, "
            "sentirme mejor. Estoy sumergido en la soledad. Me está costando todo."
        ),
    ),
    (
        "ex12",
        (
            "Casa entre las montañas con mi familia: oficina, biblioteca, gimnasio. Caminata "
            "matutina, café recién molido viendo las montañas, trading y proyectos, entrenar, "
            "almorzar en familia, leer, sentir que avanzo y construyo algo, rodeado de amor."
        ),
    ),
    (
        "ex13",
        (
            "Soy el tipo de persona que se conoce a sí mismo y se domina a sí mismo y hace lo "
            "que tiene que hacer. Para eso necesito plan, marco, seguimiento muy preciso y "
            "retroalimentación constante."
        ),
    ),
    (
        "ex14",
        (
            "Definir las tareas de esta semana y las siguientes para completar el objetivo del "
            "mes, con seguimiento preciso para saber si avanzo. Un sistema que me impida "
            "volver a perderme: si no cumplo hoy, voy camino a la perdición."
        ),
    ),
    (
        "pa01",
        (
            "Hoy evité ir a entrenar: primer incumplimiento de mi programa de fuerza. Hago "
            "esto para evitar seguir mañana en el mismo bucle. Necesito un sistema que no me "
            "permita volver a caer profundo."
        ),
    ),
    (
        "pa02",
        (
            "Mis últimas dos horas fueron desastrosas: el comportamiento que quiero evitar. "
            "Quien las viera diría que soy un flojo mantenido que se justifica y no tiene futuro."
        ),
    ),
    (
        "pa03",
        (
            "Hasta esta última semana me movía hacia la vida que odio. Ahora quiero moverme de "
            "forma constante hacia la vida que quiero."
        ),
    ),
    (
        "pa04",
        (
            "Que el tiempo pasa en intentos hasta que pasen tres o cinco años más y siga en el "
            "mismo punto, más hundido. Cada día, cada hora, cada minuto es muy importante."
        ),
    ),
    (
        "pa05",
        (
            "Busqué trabajo rápido y mandé una hoja de vida sin más, para decir que al menos "
            "mandé una. Revisé el correo esperando que me llamen, para sentir que avanzo aunque "
            "sé que no. Tal vez crear este framework también sea protegerme."
        ),
    ),
    ("pa06", "Hoy no me he sentido vivo. Me he sentido muerto todo el tiempo."),
    (
        "pa07",
        (
            "Si dejara de necesitar que me vean fuerte, inteligente, disciplinado… no sé qué "
            "cambiaría. Tal vez me iría a vender cosas en la calle para tener plata."
        ),
    ),
    (
        "pa08",
        (
            "En todas partes. No quiero conseguir trabajo para seguir encerrado en la casa, en "
            "esta seguridad, confiando en que mi mamá me mantendrá mientras me pudro encerrado."
        ),
    ),
    (
        "pa09",
        (
            "Analizar el mercado en la mañana y plantear escenarios. Tener metas completas y "
            "formas de medir el progreso. Cumplir mi plan de aprendizaje (DAX, segmentación), "
            "estudiar, entrenar, leer y dormir para repetir. Pero hoy no me creo capaz de nada."
        ),
    ),
    (
        "si01",
        (
            "Aunque no sea consciente, me siento seguro y cómodo en este ciclo y realmente no "
            "quiero salir. No quiero hacerme responsable del éxito; culpo a lo externo, al "
            "ciclo, a que me falta un sistema. Tal vez creo que no merezco ser feliz."
        ),
    ),
    (
        "si02",
        (
            "Creo que nunca podré ser feliz, que siempre seré un mediocre inferior a todos. Me "
            "veo como alguien que jamás obtendrá lo que desea aunque tenga el potencial: ni la "
            "mujer, ni la casa, ni el hogar. Siempre fracasaré o dejaré todo inconcluso."
        ),
    ),
    (
        "si03",
        (
            "Me niego a convertirme en quien tenía el potencial y no lo hizo; en quien cree "
            "que no nació para obtener lo bueno, que nació para ser infeliz sin poder "
            "cambiarlo, que solo alcanzará frustraciones y que lo bueno siempre es de otros."
        ),
    ),
    (
        "si04",
        (
            "Estoy construyendo para obtener lo bueno que sé que tengo el potencial de "
            "obtener: mi físico, mi mujer, mi hogar, mi familia. Cada acción concreta cuenta "
            "y la reconozco."
        ),
    ),
    (
        "si05",
        (
            "Vivir del trading de aquí a un año: sería rentable porque fui constante cada día, "
            "superé dudas, miedos e inseguridades y acepté que sí puedo obtener lo bueno. "
            "Racionalmente parece imposible porque necesito dinero ya."
        ),
    ),
    (
        "si06",
        (
            "Hacer operaciones recurrentes según la estrategia y confirmar que puedo operar de "
            "forma recurrente. Pero necesito dinero ya: debería conseguir trabajo, aunque eso "
            "no lo controlo."
        ),
    ),
    (
        "si07",
        (
            "Analizar el mercado cada mañana con seguimiento para ejecutar cuando haya "
            "condiciones, y cumplir un plan de aprendizaje para reforzar habilidades técnicas."
        ),
    ),
    (
        "ju01",
        (
            "Ganar es encontrar sentido en cada acción: hacer todo con intención, enfocarme en "
            "acciones concretas de forma recurrente. Los resultados se vuelven costumbre; lo que "
            "me llena es la actividad deliberada y enfocada. Sin intención me siento vacío."
        ),
    ),
    (
        "ju02",
        (
            "Una vida de arrepentimientos, frustraciones y lamentaciones: despertar vacío en un "
            "bucle interminable. Tal vez huyo de ser responsable, de ser feliz; me acostumbré a "
            "sentirme un fracaso y no quiero cambiarlo."
        ),
    ),
    (
        "ju03",
        (
            "Vivir cada día con intención y enfoque; en lo material, ser económicamente estable: "
            "idealmente con el trading, encontrar trabajo y desarrollar mi trading."
        ),
    ),
    (
        "ju04",
        (
            "Consolidar habilidades técnicas (DAX, SQL, Python) para entrevistas, ser constante "
            "en el trading analizando cada mañana, y seguir cumpliendo el entrenamiento físico."
        ),
    ),
    (
        "ju05",
        (
            "Analizar el mercado con visión clara del contexto y seguimiento para ejecutar; "
            "avanzar cada día en el aprendizaje; cumplir el plan de entrenamiento. Pero hay días "
            "en que me siento totalmente incapacitado de iniciar, aun teniendo claro qué hacer."
        ),
    ),
    (
        "ju06",
        (
            "No puedo comprometer mi salud, mi descanso y recuperación: sin esto soy un "
            "absoluto inútil e incompetente."
        ),
    ),
]


def migrate(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rumbo_respuestas (
          id INTEGER PRIMARY KEY,
          pregunta TEXT NOT NULL,
          respuesta TEXT NOT NULL,
          origen TEXT NOT NULL DEFAULT 'manual' CHECK (origen IN ('chat', 'manual')),
          created_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_rumbo_respuestas_pregunta ON rumbo_respuestas (pregunta, id)"
    )
    row = conn.execute("SELECT COUNT(*) FROM rumbo_respuestas").fetchone()
    if row and row[0] == 0:
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.executemany(
            "INSERT INTO rumbo_respuestas (pregunta, respuesta, origen, created_at) "
            "VALUES (?, ?, 'chat', ?)",
            [(pid, texto, now) for pid, texto in SEED],
        )
