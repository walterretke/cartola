"""
Constantes do Cartola FC usadas em todo o backend.

Posições: o banco guarda SEMPRE o nome da posição no padrão do Cartola
(Goleiro, Lateral, Zagueiro, Meia, Atacante, Tecnico). A API-Football só
distingue "Defender", então ele vira "Zagueiro" até o sync do Cartola
informar se o atleta é lateral.
"""
import re
from typing import Dict, Optional

# ================================================================
# POSIÇÕES
# ================================================================
GOLEIRO = "Goleiro"
LATERAL = "Lateral"
ZAGUEIRO = "Zagueiro"
MEIA = "Meia"
ATACANTE = "Atacante"
TECNICO = "Tecnico"

ALL_POSITIONS = (GOLEIRO, LATERAL, ZAGUEIRO, MEIA, ATACANTE, TECNICO)

# Posições que recebem SG (saldo de gols) no Cartola
DEFENSIVE_POSITIONS = frozenset({GOLEIRO, LATERAL, ZAGUEIRO})

# posicao_id da API oficial do Cartola
CARTOLA_POSITION_IDS: Dict[int, str] = {
    1: GOLEIRO,
    2: LATERAL,
    3: ZAGUEIRO,
    4: MEIA,
    5: ATACANTE,
    6: TECNICO,
}

_ALIASES: Dict[str, str] = {
    # API-Football (forma curta do endpoint de partidas)
    "g": GOLEIRO,
    "d": ZAGUEIRO,
    "m": MEIA,
    "f": ATACANTE,
    # API-Football (forma longa)
    "goalkeeper": GOLEIRO,
    "defender": ZAGUEIRO,
    "midfielder": MEIA,
    "attacker": ATACANTE,
    # Cartola, com e sem acento, e siglas
    "goleiro": GOLEIRO,
    "gol": GOLEIRO,
    "lateral": LATERAL,
    "lat": LATERAL,
    "zagueiro": ZAGUEIRO,
    "zag": ZAGUEIRO,
    "meia": MEIA,
    "mei": MEIA,
    "atacante": ATACANTE,
    "ata": ATACANTE,
    "tecnico": TECNICO,
    "técnico": TECNICO,
    "tec": TECNICO,
}


def normalize_position(raw: Optional[str]) -> str:
    """Converte qualquer nome de posição conhecido para o padrão do Cartola."""
    if not raw:
        return MEIA
    return _ALIASES.get(raw.strip().lower(), raw)


def merge_position(current: Optional[str], incoming: Optional[str]) -> str:
    """
    Decide a posição ao atualizar um atleta a partir da API-Football.
    A API-Football não distingue lateral de zagueiro, então um "Lateral"
    vindo do Cartola não é rebaixado para "Zagueiro".
    """
    current_norm = normalize_position(current) if current else None
    incoming_norm = normalize_position(incoming)
    if current_norm == LATERAL and incoming_norm == ZAGUEIRO:
        return LATERAL
    return incoming_norm


# ================================================================
# STATUS DO ATLETA NO CARTOLA
# ================================================================
CARTOLA_STATUS_LABELS: Dict[int, str] = {
    2: "Dúvida",
    3: "Suspenso",
    5: "Contundido",
    6: "Nulo",
    7: "Provável",
}

STATUS_PROVAVEL = 7
STATUS_DUVIDA = 2
PLAYABLE_STATUSES = frozenset({STATUS_PROVAVEL, STATUS_DUVIDA})


def status_label(status_id: Optional[int]) -> str:
    return CARTOLA_STATUS_LABELS.get(status_id or 6, "Nulo")


# ================================================================
# FORMAÇÕES (esquemas táticos aceitos pelo Cartola)
# A ordem das chaves importa: o montador escolhe do ataque para a defesa.
# ================================================================
FORMATIONS: Dict[str, Dict[str, int]] = {
    "3-4-3": {ATACANTE: 3, MEIA: 4, LATERAL: 0, ZAGUEIRO: 3, GOLEIRO: 1, TECNICO: 1},
    "3-5-2": {ATACANTE: 2, MEIA: 5, LATERAL: 0, ZAGUEIRO: 3, GOLEIRO: 1, TECNICO: 1},
    "4-3-3": {ATACANTE: 3, MEIA: 3, LATERAL: 2, ZAGUEIRO: 2, GOLEIRO: 1, TECNICO: 1},
    "4-4-2": {ATACANTE: 2, MEIA: 4, LATERAL: 2, ZAGUEIRO: 2, GOLEIRO: 1, TECNICO: 1},
    "4-5-1": {ATACANTE: 1, MEIA: 5, LATERAL: 2, ZAGUEIRO: 2, GOLEIRO: 1, TECNICO: 1},
    "5-3-2": {ATACANTE: 2, MEIA: 3, LATERAL: 2, ZAGUEIRO: 3, GOLEIRO: 1, TECNICO: 1},
    "5-4-1": {ATACANTE: 1, MEIA: 4, LATERAL: 2, ZAGUEIRO: 3, GOLEIRO: 1, TECNICO: 1},
}
DEFAULT_FORMATION = "4-3-3"


# ================================================================
# RODADAS
# ================================================================
FINISHED_FIXTURE_STATUSES = frozenset({"FT", "AET", "PEN"})
LIVE_FIXTURE_STATUSES = frozenset({"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"})

_ROUND_RE = re.compile(r"(\d+)\s*$")


def round_number_from_name(round_name: Optional[str]) -> Optional[int]:
    """'Regular Season - 12' -> 12"""
    if not round_name:
        return None
    match = _ROUND_RE.search(round_name)
    return int(match.group(1)) if match else None


def round_name_from_number(round_number: int) -> str:
    return f"Regular Season - {round_number}"


def team_logo_url(team_id: Optional[int]) -> Optional[str]:
    """Escudo do clube na CDN da API-Football (o id do TeamProfile é o da API-Football)."""
    if not team_id:
        return None
    return f"https://media.api-sports.io/football/teams/{team_id}.png"
