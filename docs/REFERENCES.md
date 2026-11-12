# 📚 Referencias — SpeechToTextAuxPy

> Fuentes consultadas y documentación externa, anotadas con **para qué sirve cada una** en este proyecto. No es una bibliografía decorativa: cada entrada se usó para resolver una duda concreta del código.

---

## Índice

1. [Cómo leer esta lista](#1-cómo-leer-esta-lista)
2. [System.Speech (.NET Framework)](#2-systemspeech-net-framework)
3. [SAPI 5.4 (API nativa)](#3-sapi-54-api-nativa)
4. [pythonnet y el runtime de .NET](#4-pythonnet-y-el-runtime-de-net)
5. [Windows: audio, voces e idioma](#5-windows-audio-voces-e-idioma)
6. [Python estándar](#6-python-estándar)
7. [colorama y salida de consola](#7-colorama-y-salida-de-consola)
8. [Estándares y metadatos del repositorio](#8-estándares-y-metadatos-del-repositorio)
9. [Contexto teórico: reconocimiento de voz](#9-contexto-teórico-reconocimiento-de-voz)
10. [Fuentes descartadas y por qué](#10-fuentes-descartadas-y-por-qué)

---

## 1. Cómo leer esta lista

Cada referencia lleva:

- **Enlace** y **tipo** (documentación oficial, repositorio, estándar).
- **Qué se consultó**: el punto concreto, no el tema general.
- **Estado**: ✅ vigente y usado · ⚠️ útil con matices · 📖 lectura de contexto.

Las URLs de Microsoft cambian de dominio con frecuencia (`docs.microsoft.com` → `learn.microsoft.com`). Si un enlace devuelve 404, busca el título exacto del artículo: el contenido sigue existiendo, solo se movió.

---

## 2. System.Speech (.NET Framework)

Es la API que el programa usa realmente. Todo lo demás es envoltorio.

### 2.1 `SpeechRecognitionEngine`

- **Enlace:** <https://learn.microsoft.com/dotnet/api/system.speech.recognition.speechrecognitionengine>
- **Tipo:** documentación oficial de API.
- **Qué se consultó:**
  - Constructores: `SpeechRecognitionEngine()` (reconocedor por defecto del sistema) frente a `SpeechRecognitionEngine(CultureInfo)` (reconocedor de una cultura concreta). El proyecto usa el segundo.
  - `SetInputToDefaultAudioDevice()` y sus alternativas (`SetInputToAudioStream`, `SetInputToWaveFile`).
  - `RecognizeAsync(RecognizeMode)` frente a `Recognize()` síncrono.
  - `RecognizeAsyncCancel()` frente a `RecognizeAsyncStop()`: el primero descarta lo pendiente, el segundo espera.
  - Propiedades de temporización: `InitialSilenceTimeout`, `EndSilenceTimeout`, `EndSilenceTimeoutAmbiguous`, `BabbleTimeout`.
  - Eventos: `SpeechDetected`, `SpeechHypothesized`, `SpeechRecognized`, `SpeechRecognitionRejected`, `RecognizeCompleted`.
- **Estado:** ✅ Referencia principal del módulo `sapi_engine.py`.

### 2.2 `DictationGrammar`

- **Enlace:** <https://learn.microsoft.com/dotnet/api/system.speech.recognition.dictationgrammar>
- **Qué se consultó:** diferencia entre dictado libre y gramáticas cerradas; el constructor sin parámetros carga el tema de dictado por defecto del reconocedor.
- **Estado:** ✅ Es la gramática que usa el programa. La alternativa (`Grammar` + `GrammarBuilder`) está documentada en [`desarrollador.md`](desarrollador.md#88-gramática-de-comandos-en-vez-de-dictado).

### 2.3 `RecognizeMode`

- **Enlace:** <https://learn.microsoft.com/dotnet/api/system.speech.recognition.recognizemode>
- **Qué se consultó:** semántica de `Single` (una frase y se detiene) frente a `Multiple` (continúa hasta cancelar).
- **Estado:** ✅ El programa depende de `Multiple` para la escucha indefinida.

### 2.4 `RecognitionResult`

- **Enlace:** <https://learn.microsoft.com/dotnet/api/system.speech.recognition.recognitionresult>
- **Qué se consultó:** propiedades `Text`, `Confidence`, `Alternates`, `Grammar`, `Audio`; y el hecho de que implementa `IDisposable`.
- **Estado:** ✅ De aquí sale la decisión de llamar a `Dispose()` después de leer `Text`, y la receta de filtrado por `Confidence`.

### 2.5 `SpeechRecognitionEngine.InstalledRecognizers()`

- **Enlace:** <https://learn.microsoft.com/dotnet/api/system.speech.recognition.speechrecognitionengine.installedrecognizers>
- **Qué se consultó:** cómo enumerar los reconocedores del sistema (`RecognizerInfo`: `Id`, `Culture`, `Name`, `Description`).
- **Estado:** ✅ Es la base del diagnóstico de la [sección 5.4 del manual](datasheet.md#54-verificar-qué-reconocedores-hay-instalados). Es la forma correcta de comprobar si el paquete de voz está instalado, en lugar de deducirlo de un mensaje de error.

### 2.6 `System.Speech.Recognition` (espacio de nombres completo)

- **Enlace:** <https://learn.microsoft.com/dotnet/api/system.speech.recognition>
- **Qué se consultó:** inventario de clases disponibles (`Choices`, `GrammarBuilder`, `SemanticResultValue`, `SpeechAudioFormatInfo`) para valorar extensiones.
- **Estado:** 📖 Contexto para las recetas de extensión.

---

## 3. SAPI 5.4 (API nativa)

`System.Speech` no implementa reconocimiento: es una capa administrada sobre el motor SAPI que vive en Windows desde hace dos décadas. Entender esto explica los límites del programa (calidad del reconocedor, formatos de audio soportados, comportamiento de la gramática).

### 3.1 Microsoft Speech API — portal de documentación

- **Enlace:** <https://learn.microsoft.com/previous-versions/windows/desktop/ms723627(v=vs.85)>
- **Tipo:** documentación oficial (archivada en "previous-versions").
- **Qué se consultó:** arquitectura general (aplicación → SAPI runtime → motor de reconocimiento → driver de audio), y la noción de que el reconocedor se carga **in-process** vía COM.
- **Estado:** ✅ Explica por qué el proceso de Python incluye el motor en su propio espacio de memoria y por qué `Dispose()` es obligatorio.

### 3.2 `ISpRecognizer` y la interfaz COM

- **Enlace:** <https://learn.microsoft.com/previous-versions/windows/desktop/ee125663(v=vs.85)>
- **Qué se consultó:** modelo de objetos COM (`ISpRecognizer`, `ISpRecoContext`, `ISpRecoGrammar`), para entender qué hace `System.Speech` por debajo y qué se pierde al no usarlo directamente (control fino de formato de audio, selección de dispositivo por `ISpObjectToken`).
- **Estado:** 📖 Contexto. No se usa directamente: hacerlo desde Python exigiría `comtypes` o `win32com` y mucho más código.

### 3.3 Formato de audio del reconocedor

- **Enlace:** <https://learn.microsoft.com/dotnet/api/system.speech.audioformat.speechaudioformatinfo>
- **Qué se consultó:** el formato que espera el motor cuando se le entrega un stream: típicamente **16 kHz, 16 bits, mono, PCM**. Es la razón por la que el manual recomienda fijar ese formato en el dispositivo si es posible, y por la que el remuestreo del sistema funciona igual pero con coste.
- **Estado:** ✅ Usado en las recomendaciones de configuración de audio.

---

## 4. pythonnet y el runtime de .NET

### 4.1 Documentación oficial de pythonnet

- **Enlace:** <https://pythonnet.github.io/>
- **Tipo:** documentación del proyecto.
- **Qué se consultó:** modelo de interoperabilidad (objetos .NET expuestos como objetos Python), conversión de tipos, delegados y eventos.
- **Estado:** ✅ Base del módulo `sapi_engine.py`.

### 4.2 Repositorio y wiki de pythonnet

- **Enlace:** <https://github.com/pythonnet/pythonnet>
- **Enlace (wiki):** <https://github.com/pythonnet/pythonnet/wiki>
- **Qué se consultó:**
  - Compatibilidad de versiones: pythonnet 3.x frente a 2.x (`requirements.txt` fija `>=3.0.0` por esto).
  - Carga de ensamblados con `clr.AddReference("System.Speech")` y resolución desde la GAC.
  - Suscripción a eventos .NET con `+=` y firma esperada del delegado (`object sender, EventArgs args`).
- **Estado:** ✅ Referencia para cualquier cambio en el puente.

### 4.3 Selección de runtime (`PYTHONNET_RUNTIME`)

- **Enlace:** <https://github.com/pythonnet/pythonnet/wiki/Configuring-Python.NET>
- **Qué se consultó:** cómo pythonnet elige entre **.NET Framework** (`netfx`) y **.NET Core / 5+** (`coreclr`), y el papel de la variable de entorno `PYTHONNET_RUNTIME`.
- **Estado:** ⚠️ Importante y frágil. En Windows el valor por defecto es `netfx`, que es lo que permite encontrar `System.Speech` en la GAC. Si alguien define `PYTHONNET_RUNTIME=coreclr` en el sistema, el programa deja de encontrar el ensamblado y el error resultante (`FileNotFoundException`) no menciona la variable. Documentado como trampa en [`desarrollador.md`](desarrollador.md#31-un-proceso-dos-runtimes).

### 4.4 `clr-loader`

- **Enlace:** <https://github.com/pythonnet/clr-loader>
- **Qué se consultó:** cómo se localiza e inicializa el runtime (rutas, arquitecturas, mensajes de error cuando no hay runtime compatible).
- **Estado:** 📖 Útil para diagnosticar fallos de arranque que ocurren antes de que se ejecute código del proyecto.

### 4.5 Versiones y dependencias de .NET Framework

- **Enlace:** <https://learn.microsoft.com/dotnet/framework/migration-guide/versions-and-dependencies>
- **Qué se consultó:** qué versión de .NET Framework trae cada versión de Windows 10, para poder afirmar que 4.7.2+ está incluido y no hay que instalar nada.
- **Estado:** ✅ Sustenta la sección de requisitos.

### 4.6 `System.Speech` en .NET moderno

- **Enlace:** <https://www.nuget.org/packages/System.Speech>
- **Qué se consultó:** existe un paquete NuGet con el mismo espacio de nombres para .NET Core 3.1+ en Windows. Aclaración importante: **no es el camino que usa este proyecto** (que va por .NET Framework y la GAC), y usarlo requeriría cambiar el runtime de pythonnet y distribuir el ensamblado junto a la aplicación.
- **Estado:** ⚠️ Referencia para entender por qué el programa es "Windows + .NET Framework" y no "Windows + .NET 8".

---

## 5. Windows: audio, voces e idioma

### 5.1 Reconocimiento de voz en Windows (soporte oficial)

- **Enlace:** <https://support.microsoft.com/windows>
- **Qué se consultó:** rutas de configuración citadas en el manual: *Configuración → Hora e idioma → Voz*, *Configuración → Sistema → Sonido*, *Panel de control de sonido → Grabar*.
- **Estado:** ⚠️ Los artículos de soporte se reorganizan a menudo. Las rutas descritas en [`datasheet.md`](datasheet.md) corresponden a Windows 10 22H2 y Windows 11; en otras versiones los nombres cambian ligeramente ("Voz" puede aparecer como "Voz e idioma").

### 5.2 Paquetes de voz e idioma

- **Enlace:** <https://support.microsoft.com/windows/language-packs-for-windows-installed-languages-and-language-packs-in-windows-7-and-windows-8-1-0d5a2b0f-9b7d-4b0b-8b0f-0f7b8f5f5c2a>
- **Qué se consultó:** diferencia entre paquete de idioma de interfaz, voz TTS y reconocedor SR; por qué instalar "Español" en Windows no garantiza que exista el reconocedor.
- **Estado:** ⚠️ El artículo original está orientado a Windows 7/8.1. La conclusión operativa —verificar con `InstalledRecognizers()` en lugar de suponer— sigue siendo válida y es la que se documenta.

### 5.3 Dispositivos de audio y exclusividad

- **Enlace:** <https://learn.microsoft.com/windows/win32/coreaudio/device-roles>
- **Qué se consultó:** el concepto de *dispositivo predeterminado* y sus roles (comunicaciones frente a multimedia), que explica por qué el programa "toma" lo que el sistema marque y por qué cambiar de dispositivo en caliente no afecta a una sesión ya iniciada.
- **Estado:** 📖 Contexto técnico para la sección de audio del manual.

### 5.4 Códec y página de códigos de la consola

- **Enlace:** <https://learn.microsoft.com/windows/console/setconsoleoutputcp>
- **Qué se consultó:** qué hace exactamente `chcp 65001` (cambia la página de códigos de salida de la consola) y por qué no basta con `sys.stdout.reconfigure`.
- **Estado:** ✅ Justifica la doble capa de configuración UTF-8 descrita en [`desarrollador.md`](desarrollador.md#34-codificación-de-la-consola).

---

## 6. Python estándar

### 6.1 `signal`

- **Enlace:** <https://docs.python.org/3/library/signal.html>
- **Qué se consultó:** disponibilidad de `signal.pause()` por plataforma (no existe en Windows), comportamiento de los manejadores (se ejecutan en el hilo principal) y disponibilidad de `SIGTERM`.
- **Estado:** ✅ Explica el fallback `try/except AttributeError` + `time.sleep(0.5)`.

### 6.2 `sys`

- **Enlace:** <https://docs.python.org/3/library/sys.html>
- **Qué se consultó:** `sys.stdout.reconfigure()`, `sys.platform`, `sys.exit()` y el comportamiento de los flujos estándar al redirigir.
- **Estado:** ✅ Usado en `main.py`.

### 6.3 `datetime`

- **Enlace:** <https://docs.python.org/3/library/datetime.html>
- **Qué se consultó:** `strftime("%H:%M:%S")` y su dependencia de la zona horaria local.
- **Estado:** ✅ Usado en `console_utils.py`.

### 6.4 PEP 8 — guía de estilo

- **Enlace:** <https://peps.python.org/pep-0008/>
- **Qué se consultó:** convenciones de indentación, longitud de línea, nombres y orden de importaciones.
- **Estado:** ✅ Aplicado en los tres módulos.

### 6.5 PEP 257 — docstrings

- **Enlace:** <https://peps.python.org/pep-0257/>
- **Qué se consultó:** formato de docstrings de módulo, clase y función.
- **Estado:** ✅ Todos los docstrings del proyecto siguen esta convención, con secciones `Args`/`Raises` al estilo Google.

### 6.6 PEP 484 — type hints

- **Enlace:** <https://peps.python.org/pep-0484/>
- **Qué se consultó:** uso de `Optional[...]` y `Any`, y por qué no se pueden anotar tipos .NET.
- **Estado:** ✅ Las firmas están anotadas de forma parcial y deliberada.

---

## 7. colorama y salida de consola

### 7.1 Repositorio de colorama

- **Enlace:** <https://github.com/tartley/colorama>
- **Qué se consultó:** efecto de `init()` sobre `sys.stdout`/`sys.stderr`, constantes `Fore`/`Style`, y comportamiento al redirigir (los códigos ANSI se eliminan si el flujo no es una terminal).
- **Estado:** ✅ Base del diseño de degradación elegante.

### 7.2 colorama en PyPI

- **Enlace:** <https://pypi.org/project/colorama/>
- **Qué se consultó:** versiones publicadas y compatibilidad con Python 3.10+.
- **Estado:** ✅ Origen de la cota `>=0.4.6`.

---

## 8. Estándares y metadatos del repositorio

| Referencia | Enlace | Uso en el proyecto |
|---|---|---|
| **Licencia MIT** | <https://opensource.org/license/mit> | Texto de `LICENSE`, con titularía de 2026. |
| **Semantic Versioning** | <https://semver.org/lang/es/> | La versión del manual (1.0.0) sigue este esquema. |
| **Keep a Changelog** | <https://keepachangelog.com/es-ES/> | Formato recomendado si en el futuro se añade un `CHANGELOG.md`. |
| **Shields.io** | <https://shields.io/> | Badges estáticos del README. Son las únicas imágenes externas del proyecto. |
| **GitHub Flavored Markdown** | <https://github.github.com/gfm/> | Tablas, bloques de código y anclas del README. |
| **REUSE / SPDX** | <https://spdx.dev/learn/handling-license-info/> | Referencia para declarar la licencia por archivo, si algún día se adopta. |

---

## 9. Contexto teórico: reconocimiento de voz

No son fuentes que el código use, pero explican por qué el programa se comporta como se comporta (latencia de cola, errores en palabras raras, sensibilidad al ruido).

### 9.1 Jurafsky & Martin — *Speech and Language Processing*

- **Enlace:** <https://web.stanford.edu/~jurafsky/slp3/>
- **Qué se consultó:** capítulo de reconocimiento automático del habla: modelo acústico, modelo de lenguaje, decodificación con Viterbi, y por qué el resultado se emite al cerrar la frase.
- **Estado:** 📖 Lectura de contexto. Explica la diferencia entre un decodificador clásico (SAPI) y los modelos neuronales actuales.

### 9.2 Reconocimiento automático del habla (visión general)

- **Enlace:** <https://es.wikipedia.org/wiki/Reconocimiento_autom%C3%A1tico_del_habla>
- **Qué se consultó:** terminología en español (dictado, hablante independiente, vocabulario) para redactar la documentación de usuario sin jerga innecesaria.
- **Estado:** 📖 Contexto.

### 9.3 *Speech recognition* (visión general en inglés)

- **Enlace:** <https://en.wikipedia.org/wiki/Speech_recognition>
- **Qué se consultó:** historia de SAPI y su relación con los motores comerciales de los años 90-2000; útil para situar expectation management ("no es Whisper").
- **Estado:** 📖 Contexto.

---

## 10. Fuentes descartadas y por qué

Documentar lo que **no** se usó evita que el próximo que toque el proyecto repita la búsqueda.

| Fuente / enfoque | Por qué se descartó |
|---|---|
| **`SpeechRecognition` (paquete de PyPI)** | Añade una capa propia sobre SAPI o sobre servicios en la nube, y arrastra `PyAudio` (binario nativo) para el micrófono. El objetivo era usar SAPI directamente con dos dependencias puras. |
| **Vosk / Whisper / faster-whisper** | Excelente calidad, pero requieren descargar modelos de cientos de MB, consumen CPU/GPU de forma sostenida y no son "el reconocedor de Windows". Otro proyecto, no este. |
| **`winsdk` / WinRT `Windows.Media.SpeechRecognition`** | API moderna, asíncrona y orientada a UWP. Con pythonnet las tareas asíncronas (`IAsyncOperation`) son incómodas de consumir, y el objetivo explícito era `System.Speech`. |
| **`pywin32` + COM directo a SAPI** | Control total (selección de dispositivo por token, formato de audio), pero muchísimo más código y una dependencia con binarios por arquitectura. Se documenta como receta, no se implementa. |
| **`pyaudio` / `sounddevice` para captura propia** | Habría permitido elegir dispositivo y guardar WAV, pero obliga a implementar el bombeo de audio hacia el motor y a pelear con formatos. `SetInputToDefaultAudioDevice()` resuelve el 95 % de los casos con una línea. |
| **Tutoriales de "speech to text en Python" que usan Google Web Speech** | Envían audio a un servicio externo. Contradice el requisito de privacidad y de funcionamiento offline. |
| **Artículos que llaman `Recognize()` síncrono en un bucle** | Bloquea el hilo y añade un ciclo de espera por frase. `RecognizeAsync(Multiple)` es el patrón correcto para escucha continua. |
| **Ejemplos que no liberan el motor** | Dejan el dispositivo de audio tomado y el proceso colgado al cerrar. El proyecto libera con `RecognizeAsyncCancel()` + `Dispose()`. |

---

## Verificación de enlaces

Los enlaces se comprobaron al redactar esta documentación. Si alguno falla:

1. Busca el **título exacto** del artículo en el motor de búsqueda que prefieras; Microsoft conserva el contenido bajo `learn.microsoft.com` aunque cambie la ruta.
2. Para las API de .NET, navega desde el índice del espacio de nombres: <https://learn.microsoft.com/dotnet/api/system.speech.recognition>.
3. Para pythonnet, el `README` del repositorio suele estar más actualizado que la web del proyecto.

---

*Referencias de SpeechToTextAuxPy · Licencia MIT · Copyright (c) 2026 wanderc137*
