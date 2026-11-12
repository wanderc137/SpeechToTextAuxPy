"""
main.py - Punto de entrada de SpeechToTextAuxPy.

Reconocimiento de voz continuo en español usando SAPI de Windows
(System.Speech.Recognition) vía pythonnet.

Flujo:
    1. Configurar codificación UTF-8 para la consola
    2. Registrar manejador de Ctrl+C (signal.SIGINT)
    3. Instanciar SapiEngine con idioma "es-ES"
    4. Llamar engine.start()
    5. Mantener el programa vivo (bucle de espera con signal.pause())
    6. Al recibir Ctrl+C, llamar engine.stop() y salir limpiamente
"""

import signal
import sys

# Configurar codificación UTF-8 para la consola en Windows
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 no tiene reconfigure, pero intentamos setdefaultencoding
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Importar módulos del proyecto
import console_utils
from sapi_engine import SapiEngine


# Variable global para el motor (necesaria desde el manejador de señal)
_engine: SapiEngine = None  # type: ignore


def signal_handler(signal_num: int, frame) -> None:
    """
    Manejador de señales para Ctrl+C (SIGINT).

    Detiene el motor SAPI y termina el programa de forma limpia.

    Args:
        signal_num: Número de señal recibida.
        frame: Frame de ejecución actual (no usado).
    """
    global _engine

    console_utils.print_info("Ctrl+C recibido. Deteniendo...")

    if _engine is not None:
        try:
            _engine.stop()
        except Exception as e:
            console_utils.print_error(f"Error al detener el motor: {e}")

    console_utils.print_info("Programa terminado.")
    sys.exit(0)


def main() -> None:
    """
    Función principal del programa.

    Realiza las siguientes operaciones:
        1. Registra el manejador de Ctrl+C
        2. Crea la instancia de SapiEngine con idioma español
        3. Inicia el reconocimiento de voz
        4. Mantiene el programa ejecutándose hasta Ctrl+C
    """
    global _engine

    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    # SIGTERM no es común en Windows nativo, pero mejora compatibilidad
    # con entornos como WSL, Cygwin o gestores de procesos
    try:
        signal.signal(signal.SIGTERM, signal_handler)
    except AttributeError:
        pass  # SIGTERM no disponible en algunas versiones de Windows

    console_utils.print_info("=== SpeechToTextAuxPy ===")
    console_utils.print_info(
        "Reconocimiento de voz continuo mediante SAPI (System.Speech)"
    )

    try:
        # Crear instancia del motor SAPI con idioma español
        _engine = SapiEngine(language="es-ES")

        # Iniciar reconocimiento
        _engine.start()

        # Mantener el programa vivo esperando señales
        # signal.pause() no está disponible en Windows,
        # así que usamos un bucle simple con espera
        console_utils.print_info("Esperando entrada de voz...")
        while True:
            try:
                # Esperar indefinidamente hasta Ctrl+C
                signal.pause()
            except AttributeError:
                # signal.pause() no está en Windows, usamos bucle con sleep
                import time
                time.sleep(0.5)

    except ImportError as e:
        console_utils.print_error(
            f"Dependencia faltante: {e}\n"
            f"   -> Ejecuta: pip install -r requirements.txt"
        )
        sys.exit(1)
    except RuntimeError as e:
        console_utils.print_error(
            f"Error de ejecución SAPI: {e}\n"
            f"   -> Verifica que el paquete de voz español esté instalado.\n"
            f"   -> Configuración > Hora e idioma > Voz > Agregar voz"
        )
        sys.exit(2)
    except Exception as e:
        console_utils.print_error(
            f"Error inesperado: {e}"
        )
        sys.exit(3)


if __name__ == "__main__":
    main()
