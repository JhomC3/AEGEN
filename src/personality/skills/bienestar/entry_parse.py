"""Parseo de entradas del dominio (fusión SDD 001)."""

from __future__ import annotations

import re


def num(texto: str) -> float | None:
    """Número con coma decimal española o None."""
    m = re.search(r"(\d+(?:[.,]\d+)?)", texto.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_serie(texto: str) -> dict | None:
    """«Press 80x8 rir1» / «80 kg 8 reps». Requiere ejercicio + kg + reps."""
    t = texto.lower()
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:kg|kilos?)?\s*[x×]\s*(\d+)", t)
    if not m:
        return None
    kg = float(m.group(1).replace(",", "."))
    reps = float(m.group(2).replace(",", "."))
    rir_m = re.search(r"rir\s*(-?\d+(?:[.,]\d+)?)", t)
    rir = float(rir_m.group(1).replace(",", ".")) if rir_m else None
    d_m = re.search(r"descanso\s*(\d+)", t)
    nombre = " ".join(
        w
        for w in re.sub(r"[^a-záéíóúñü ]", " ", t).split()
        if w
        not in {
            "guarda",
            "guardar",
            "registra",
            "registrar",
            "añade",
            "agrega",
            "suma",
            "hoy",
            "ayer",
            "serie",
            "series",
            "sesion",
            "sesión",
            "con",
            "de",
            "el",
            "la",
            "una",
            "mi",
            "que",
        }
        and not re.fullmatch(r"\d+(?:[.,]\d+)?|kg|x|rir|rir\d.*|descanso", w)
    ).strip()
    if not nombre:
        return None
    serie: dict = {"ejercicio": nombre.title(), "kg": kg, "reps": reps}
    if rir is not None:
        serie["rir"] = rir
    if d_m:
        serie["descanso_seg"] = int(d_m.group(1))
    return serie


def parse_diario(texto: str) -> dict | None:
    """«50 g de avena» / «avena 50g». Requiere alimento + gramos."""
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:g(?:r(?:amos?)?)?\.?)\s+de\s+([a-záéíóúñü ]+)",
        texto.lower(),
    )
    if not m:
        m = re.search(r"([a-záéíóúñü ]+?)\s+(\d+(?:[.,]\d+)?)\s*g\b", texto.lower())
        if not m:
            return None
        alimento, gramos = m.group(1).strip(), float(m.group(2).replace(",", "."))
    else:
        gramos = float(m.group(1).replace(",", "."))
        alimento = m.group(2).strip()
    alimento = " ".join(
        w
        for w in alimento.split()
        if w
        not in {
            "registra",
            "registrar",
            "guarda",
            "guardar",
            "hoy",
            "ayer",
            "comi",
            "comí",
            "de",
            "el",
            "la",
            "mi",
            "que",
        }
    ).strip()
    if not alimento or gramos <= 0:
        return None
    return {"alimento": alimento.title(), "cantidad_g": gramos}


def parse_respiracion(texto: str) -> dict | None:
    """«4/0/6/0 2 minutos» / «inhala 4 exhala 6 durante 120 segundos»."""
    t = texto.lower()
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*/\s*"
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)",
        t,
    )
    if m:
        fases = [float(x.replace(",", ".")) for x in m.groups()]
    else:
        inh = re.search(r"inhala?\s*(\d+(?:[.,]\d+)?)", t)
        exh = re.search(r"exhala?\s*(\d+(?:[.,]\d+)?)", t)
        if not (inh and exh):
            return None
        fases = [
            float(inh.group(1).replace(",", ".")),
            0.0,
            float(exh.group(1).replace(",", ".")),
            0.0,
        ]
    d = re.search(r"(\d+(?:[.,]\d+)?)\s*(min(?:utos?)?|seg(?:undos?)?|s)\b", t)
    if not d:
        return None
    dur = float(d.group(1).replace(",", "."))
    if d.group(2).startswith("min"):
        dur *= 60
    return {
        "inhale_s": fases[0],
        "hold_in_s": fases[1],
        "exhale_s": fases[2],
        "hold_out_s": fases[3],
        "duracion_sec": dur,
    }


def parse_rumbo_dia(texto: str) -> dict | None:
    """«t1=8 t2=7 t3=9» / «8 7 9» junto a rumbo."""
    nums = [
        (f"t{k}", int(v))
        for k, v in re.findall(r"\bt([123])\s*=\s*(\d{1,2})", texto.lower())
    ]
    vals = dict(nums)
    if len(vals) == 3:
        return {"t1": vals["t1"], "t2": vals["t2"], "t3": vals["t3"]}
    solos = re.findall(r"\b(\d|10)\b", texto)
    if len(solos) == 3 and "rumbo" in texto.lower():
        return {"t1": int(solos[0]), "t2": int(solos[1]), "t3": int(solos[2])}
    return None
