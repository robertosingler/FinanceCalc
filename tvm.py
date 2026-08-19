"""
Motor de calculo financiero TVM (Time Value of Money).

Ecuacion estandar (misma convencion que HP12C / BA II Plus):

    PV*(1+i)^n + PMT*(1+i*type)*((1+i)^n - 1)/i + FV = 0      (i != 0)
    PV + PMT*n + FV = 0                                        (i == 0)

Donde:
    PV   = Valor presente
    PMT  = Pago periodico
    FV   = Valor futuro
    i    = tasa periodica (decimal, no porcentaje)
    n    = numero de periodos
    type = 0 (fin de periodo / ordinaria) o 1 (inicio de periodo / anticipada)

Convencion de signos: el dinero que "sale" del bolsillo del usuario es
negativo, el que "entra" es positivo (igual que en cualquier calculadora
financiera real).
"""

from dataclasses import dataclass, asdict
from typing import Optional

FREQ_LABELS = {
    1: "Anual",
    2: "Semestral",
    4: "Trimestral",
    12: "Mensual",
    24: "Quincenal",
    26: "Bisemanal",
    52: "Semanal",
    365: "Diaria",
}


class TVMError(ValueError):
    pass


def periodic_rate(annual_rate_pct: float, freq: int, rate_type: str) -> float:
    """Convierte una tasa anual (nominal o efectiva) en tasa periodica decimal."""
    r = annual_rate_pct / 100.0
    if freq <= 0:
        raise TVMError("La frecuencia de capitalizacion debe ser mayor a 0")
    if rate_type == "nominal":
        return r / freq
    elif rate_type == "effective":
        return (1.0 + r) ** (1.0 / freq) - 1.0
    raise TVMError("rate_type debe ser 'nominal' o 'effective'")


def annual_rate_from_periodic(i: float, freq: int, rate_type: str) -> float:
    """Inversa de periodic_rate: de tasa periodica decimal a tasa anual %."""
    if rate_type == "nominal":
        return i * freq * 100.0
    elif rate_type == "effective":
        return ((1.0 + i) ** freq - 1.0) * 100.0
    raise TVMError("rate_type debe ser 'nominal' o 'effective'")


def _annuity_factor(i: float, n: float, type_: int) -> float:
    """((1+i)^n - 1) / i * (1 + i*type), con manejo de i == 0."""
    if i == 0:
        return n * (1 + 0 * type_)
    return ((1.0 + i) ** n - 1.0) / i * (1.0 + i * type_)


def solve_pv(pmt: float, fv: float, i: float, n: float, type_: int) -> float:
    if i == 0:
        return -(fv + pmt * n)
    factor = _annuity_factor(i, n, type_)
    return -(fv + pmt * factor) / ((1.0 + i) ** n)


def solve_fv(pv: float, pmt: float, i: float, n: float, type_: int) -> float:
    if i == 0:
        return -(pv + pmt * n)
    factor = _annuity_factor(i, n, type_)
    return -(pv * (1.0 + i) ** n + pmt * factor)


def solve_pmt(pv: float, fv: float, i: float, n: float, type_: int) -> float:
    if i == 0:
        if n == 0:
            raise TVMError("El numero de periodos no puede ser 0")
        return -(pv + fv) / n
    factor = _annuity_factor(i, n, type_)
    if factor == 0:
        raise TVMError("No se puede resolver PMT con estos parametros (factor = 0)")
    return -(pv * (1.0 + i) ** n + fv) / factor


def solve_n(pv: float, pmt: float, fv: float, i: float) -> float:
    if i == 0:
        if pmt == 0:
            raise TVMError("No se puede resolver N: PMT es 0 y la tasa es 0")
        return -(pv + fv) / pmt
    # A = (1+i)^n  =>  n = ln(A) / ln(1+i)
    denom = pv + pmt / i
    numer = pmt / i - fv
    if denom == 0:
        raise TVMError("No se puede resolver N con estos parametros")
    a = numer / denom
    if a <= 0:
        raise TVMError("No existe una solucion real para N con estos valores")
    import math
    return math.log(a) / math.log(1.0 + i)


def solve_rate(pv: float, pmt: float, fv: float, n: float, type_: int,
               guess: float = 0.01) -> float:
    """Resuelve la tasa periodica i por Newton-Raphson con fallback a biseccion."""
    import math

    def f(i: float) -> float:
        if i == 0:
            return pv + pmt * n + fv
        return pv * (1.0 + i) ** n + pmt * _annuity_factor(i, n, type_) + fv

    def fprime(i: float, h: float = 1e-7) -> float:
        return (f(i + h) - f(i - h)) / (2 * h)

    i = guess
    for _ in range(100):
        fi = f(i)
        dfi = fprime(i)
        if dfi == 0:
            break
        i_new = i - fi / dfi
        if i_new <= -0.999999:
            i_new = (i - 0.999999) / 2
        if abs(i_new - i) < 1e-12:
            return i_new
        i = i_new

    if abs(f(i)) < 1e-6:
        return i

    # Fallback: biseccion en un rango amplio
    lo, hi = -0.999999, 10.0
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        raise TVMError("No se encontro una tasa que resuelva la ecuacion (revisa los signos de PV/PMT/FV)")
    for _ in range(200):
        mid = (lo + hi) / 2
        fmid = f(mid)
        if abs(fmid) < 1e-10:
            return mid
        if flo * fmid < 0:
            hi, fhi = mid, fmid
        else:
            lo, flo = mid, fmid
    return (lo + hi) / 2


@dataclass
class AmortizationRow:
    period: int
    payment: float
    principal: float
    interest: float
    balance: float


def amortization_schedule(pv: float, pmt: float, i: float, n: int, type_: int,
                           decimals: int = 2) -> list:
    """Genera la tabla de amortizacion. pv = monto del prestamo (positivo),
    pmt = pago periodico (se usa en valor absoluto, se asume que se paga)."""
    n = int(round(n))
    if n <= 0:
        raise TVMError("El numero de periodos debe ser mayor a 0")

    balance = pv
    rows = []
    payment = -pmt  # pmt suele venir negativo (sale del bolsillo)

    for period in range(1, n + 1):
        if type_ == 1 and period == 1:
            interest = 0.0
        else:
            interest = balance * i
        principal = payment - interest
        balance = balance - principal
        rows.append(AmortizationRow(
            period=period,
            payment=round(payment, decimals),
            principal=round(principal, decimals),
            interest=round(interest, decimals),
            balance=round(balance, decimals),
        ))
    return [asdict(r) for r in rows]


def calculate(data: dict) -> dict:
    """Punto de entrada principal. Recibe el estado completo y la variable a
    resolver, devuelve el estado actualizado."""
    solve_for = data.get("solve_for")
    freq = int(data.get("freq", 12))
    rate_type = data.get("rate_type", "effective")
    mode = data.get("mode", "end")
    type_ = 1 if mode == "begin" else 0
    decimals = int(data.get("decimals", 2))

    pv = data.get("pv")
    pmt = data.get("pmt")
    fv = data.get("fv")
    rate = data.get("rate")
    n = data.get("n")

    if solve_for != "rate":
        if rate is None:
            raise TVMError("Falta la tasa anual")
        i = periodic_rate(float(rate), freq, rate_type)

    result = {}

    if solve_for == "pv":
        if pmt is None or fv is None or n is None:
            raise TVMError("Faltan datos para resolver PV (PMT, FV, N)")
        pv = solve_pv(float(pmt), float(fv), i, float(n), type_)
        result["pv"] = round(pv, decimals)

    elif solve_for == "pmt":
        if pv is None or fv is None or n is None:
            raise TVMError("Faltan datos para resolver PMT (PV, FV, N)")
        pmt = solve_pmt(float(pv), float(fv), i, float(n), type_)
        result["pmt"] = round(pmt, decimals)

    elif solve_for == "fv":
        if pv is None or pmt is None or n is None:
            raise TVMError("Faltan datos para resolver FV (PV, PMT, N)")
        fv = solve_fv(float(pv), float(pmt), i, float(n), type_)
        result["fv"] = round(fv, decimals)

    elif solve_for == "n":
        if pv is None or pmt is None or fv is None:
            raise TVMError("Faltan datos para resolver N (PV, PMT, FV)")
        n = solve_n(float(pv), float(pmt), float(fv), i)
        result["n"] = round(n, decimals)

    elif solve_for == "rate":
        if pv is None or pmt is None or fv is None or n is None:
            raise TVMError("Faltan datos para resolver RATE (PV, PMT, FV, N)")
        i = solve_rate(float(pv), float(pmt), float(fv), float(n), type_)
        rate = annual_rate_from_periodic(i, freq, rate_type)
        result["rate"] = round(rate, decimals + 2)

    else:
        raise TVMError("solve_for invalido. Debe ser: pv, pmt, fv, n o rate")

    result["periodic_rate_pct"] = round(i * 100, 6)
    return result
