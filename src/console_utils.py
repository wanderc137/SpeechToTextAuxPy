"""
console_utils.py - Utilidades de impresión con color y timestamp para la consola.

Proporciona funciones para imprimir mensajes con formato:
- Timestamp encian
- Texto reconocido en blanco
- Información en verde
- Errores en rojo

Usa colorama cuando está disponible, con degradación elegante si no.
"""

import sys
from datetime import datetime

# Intentar importar colorama para colores en consola Windows
try:
    from colorama import init, Fore, Style

    init()  # Inicializa colorama para Windows
    COLORAMA_DISPONIBLE = True
except ImportError:
    COLORAMA_DISPONIBLE = False

    # Fallbacks para cuando colorama no está instalado
    class Fore:  # type: ignore
        """Fallback vacío para Fore cuando colorama no está disponible."""
        CYAN = ""
        GREEN = ""
        RED = ""
        WHITE = ""
        RESET = ""

    class Style:  # type: ignore
        """Fallback vacío para Style cuando colorama no está disponible."""
        BRIGHT = ""
        RESET_ALL = ""


def _formato_timestamp() -> str:
    """Devuelve el timestamp actual como string [HH:MM:SS]."""
    return datetime.now().strftime("%H:%M:%S")


def print_timestamp(color: str = Fore.CYAN, stream=sys.stdout) -> None:
    """
    Imprime el timestamp actual con formato [HH:MM:SS] en el color y
    flujo especificados.

    Args:
        color: Color de Fore (colorama) para el timestamp.
               Por defecto Fore.CYAN.
        stream: Flujo de salida (sys.stdout o sys.stderr).
                Por defecto sys.stdout.

    Si colorama no está disponible, imprime sin color.
    Realiza flush para garantizar salida en tiempo real.
    """
    reset = Style.RESET_ALL if COLORAMA_DISPONIBLE else ""
    ts = _formato_timestamp()
    stream.write(f"{color}[{ts}]{reset} ")
    stream.flush()


def print_recognized(text: str) -> None:
    """
    Imprime texto reconocido con timestamp y color.

    Formato: [HH:MM:SS] texto reconocido
    El timestamp aparece en cian y el texto en blanco brillante.

    Args:
        text: Texto reconocido por el motor SAPI.
    """
    reset = Style.RESET_ALL if COLORAMA_DISPONIBLE else ""
    bright = Style.BRIGHT if COLORAMA_DISPONIBLE else ""
    print_timestamp(color=Fore.CYAN, stream=sys.stdout)
    sys.stdout.write(f"{bright}{Fore.WHITE}{text}{reset}\n")
    sys.stdout.flush()


def print_info(message: str) -> None:
    """
    Imprime un mensaje informativo con timestamp en color verde.

    Args:
        message: Mensaje informativo a mostrar.
    """
    reset = Style.RESET_ALL if COLORAMA_DISPONIBLE else ""
    print_timestamp(color=Fore.GREEN, stream=sys.stdout)
    sys.stdout.write(f"{message}{reset}\n")
    sys.stdout.flush()


def print_error(message: str) -> None:
    """
    Imprime un mensaje de error con timestamp en color rojo.

    Tanto el timestamp como el mensaje se dirigen a stderr para
    mantener la coherencia cuando la salida está redirigida.

    Args:
        message: Mensaje de error a mostrar.
    """
    reset = Style.RESET_ALL if COLORAMA_DISPONIBLE else ""
    print_timestamp(color=Fore.RED, stream=sys.stderr)
    sys.stderr.write(f"ERROR: {message}{reset}\n")
    sys.stderr.flush()
