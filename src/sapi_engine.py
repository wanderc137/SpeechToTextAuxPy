"""
sapi_engine.py - Envoltura para System.Speech.Recognition de .NET Framework.

Proporciona la clase SapiEngine que utiliza pythonnet para acceder
a la API de reconocimiento de voz SAPI de Windows (System.Speech).

Dependencias:
    - pythonnet >= 3.0.0  (pip install pythonnet)
    - .NET Framework 4.7.2+ (incluido en Windows 10)
    - Paquete de voz en español instalado en Windows
"""

import sys
from typing import Any, Optional

import console_utils


class SapiEngine:
    """
    Envoltura para System.Speech.Recognition.SpeechRecognitionEngine de .NET.

    Gestiona el ciclo de vida del motor de reconocimiento de voz SAPI:
    inicialización, inicio de escucha asíncrona, detención y liberación
    de recursos COM/.NET.

    Args:
        language: Código de idioma ISO (ej: "es-ES", "en-US").
                  Por defecto "es-ES" (español de España).
    """

    def __init__(self, language: str = "es-ES") -> None:
        """
        Inicializa el motor de reconocimiento de voz SAPI.

        Pasos:
            1. Importa clr de pythonnet
            2. Agrega referencia a System.Speech.dll
            3. Crea SpeechRecognitionEngine con CultureInfo del idioma
            4. Configura entrada desde dispositivo de audio predeterminado
            5. Carga gramática de dictado (DictationGrammar)
            6. Registra el evento SpeechRecognized

        Args:
            language: Código de idioma para el reconocimiento (ej: "es-ES").

        Raises:
            ImportError: Si pythonnet (clr) no está instalado.
            Exception: Propagación de errores de .NET SAPI.
        """
        self._language = language
        self._engine: Optional[Any] = None
        self._grammar: Optional[Any] = None

        try:
            # Importar pythonnet
            import clr
        except ImportError:
            raise ImportError(
                "pythonnet no está instalado. Ejecuta: pip install pythonnet>=3.0.0"
            )

        try:
            # Agregar referencia a System.Speech de .NET Framework
            clr.AddReference("System.Speech")

            from System.Speech.Recognition import (  # type: ignore
                DictationGrammar,
                RecognizeMode,
                SpeechRecognitionEngine,
            )
            from System.Globalization import CultureInfo  # type: ignore

            # Guardar RecognizeMode como atributo de clase para evitar
            # reimportaciones redundantes en start()
            self._RecognizeMode = RecognizeMode

            # Crear CultureInfo para el idioma solicitado
            cultura = CultureInfo(language)

            # Crear el motor de reconocimiento
            self._engine = SpeechRecognitionEngine(cultura)

            # Configurar entrada desde el dispositivo de audio predeterminado
            self._engine.SetInputToDefaultAudioDevice()

            # Cargar gramática de dictado (reconocimiento de texto libre)
            self._grammar = DictationGrammar()
            self._engine.LoadGrammar(self._grammar)

            # Registrar el evento de reconocimiento
            self._engine.SpeechRecognized += self._on_speech_recognized

            console_utils.print_info(
                f"Motor SAPI inicializado correctamente (idioma: {language})"
            )

        except Exception as e:
            error_msg = str(e)
            # Detectar errores comunes y dar mensajes útiles
            if "culture" in error_msg.lower() or "language" in error_msg.lower():
                console_utils.print_error(
                    f"El idioma '{language}' no está soportado. "
                    f"Asegúrate de tener instalado el paquete de voz en español.\n"
                    f"   -> Configuración > Hora e idioma > Voz > Agregar voz"
                )
            elif "device" in error_msg.lower() or "audio" in error_msg.lower():
                console_utils.print_error(
                    "No se encontró dispositivo de entrada de audio disponible.\n"
                    "   -> Conecta un micrófono o entrada auxiliar (line-in).\n"
                    "   -> Verifica Configuración > Sonido > Administrar dispositivos de audio."
                )
            else:
                console_utils.print_error(
                    f"Error al inicializar SAPI: {error_msg}"
                )
            raise RuntimeError(
                f"Fallo al inicializar SpeechRecognitionEngine: {error_msg}"
            ) from e

    def _on_speech_recognized(self, sender: Any, args: Any) -> None:
        """
        Callback ejecutado cuando SAPI reconoce una frase.

        Este método es registrado como delegado del evento SpeechRecognized.
        Obtiene el texto reconocido y lo envía a la consola.

        Args:
            sender: Objeto que disparó el evento (SpeechRecognitionEngine).
            args: Argumentos del evento (SpeechRecognizedEventArgs).
        """
        try:
            if args and args.Result and args.Result.Text:
                texto = args.Result.Text.strip()
                if texto:
                    console_utils.print_recognized(texto)

            # Liberar recursos del resultado
            if args and args.Result:
                try:
                    args.Result.Dispose()
                except Exception:
                    pass  # Ignorar errores en dispose
        except Exception as e:
            console_utils.print_error(f"Error en callback de reconocimiento: {e}")

    def start(self) -> None:
        """
        Inicia el reconocimiento de voz asíncrono continuo.

        El motor comienza a escuchar el dispositivo de entrada predeterminado
        y dispara eventos SpeechRecognized cuando detecta voz.

        Reconoce múltiples frases de forma continua (RecognizeMode.Multiple)
        hasta que se llame a stop() o se cancele explícitamente.
        """
        if self._engine is None:
            console_utils.print_error("El motor SAPI no está inicializado.")
            return

        try:
            self._engine.RecognizeAsync(self._RecognizeMode.Multiple)
            console_utils.print_info(
                "Iniciando reconocimiento de voz en español..."
            )
            console_utils.print_info(
                "Habla al micrófono/entrada auxiliar. Ctrl+C para salir."
            )
        except Exception as e:
            console_utils.print_error(f"Error al iniciar reconocimiento: {e}")
            raise RuntimeError(f"No se pudo iniciar RecognizeAsync: {e}") from e

    def stop(self) -> None:
        """
        Detiene el reconocimiento de voz y libera recursos.

        Cancela el reconocimiento asíncrono y libera el motor SAPI
        y la gramática asociada. Es seguro llamarlo múltiples veces.
        """
        if self._engine is not None:
            try:
                # Cancelar reconocimiento asíncrono
                self._engine.RecognizeAsyncCancel()
                console_utils.print_info("Reconocimiento de voz detenido.")
            except Exception as e:
                console_utils.print_error(
                    f"Error al cancelar reconocimiento: {e}"
                )

            try:
                # Liberar recursos del motor
                self._engine.Dispose()
            except Exception as e:
                console_utils.print_error(
                    f"Error al liberar recursos del motor: {e}"
                )
            finally:
                self._engine = None
                self._grammar = None
        else:
            console_utils.print_info("El motor ya estaba detenido.")
