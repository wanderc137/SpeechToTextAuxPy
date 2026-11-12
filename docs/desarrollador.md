# 🧑‍💻 Documentación para desarrolladores — SpeechToTextAuxPy

> Referencia técnica del código: arquitectura, contrato de cada función, modelo de hilos, trampas de pythonnet y recetas de extensión.

---

## Índice

- [1. Vista general](#1-vista-general)
- [2. Estructura del repositorio](#2-estructura-del-repositorio)
- [3. Modelo de ejecución](#3-modelo-de-ejecución)
- [4. API de referencia](#4-api-de-referencia)
  - [4.1 `SapiEngine`](#41-sapiengine)
  - [4.2 `console_utils`](#42-console_utils)
  - [4.3 `main`](#43-main)
- [5. Ciclo de vida y diagrama de secuencia](#5-ciclo-de-vida-y-diagrama-de-secuencia)
- [6. Taxonomía de errores](#6-taxonomía-de-errores)
- [7. Trampas de implementación](#7-trampas-de-implementación)
- [8. Recetas de extensión](#8-recetas-de-extensión)
- [9. Pruebas](#9-pruebas)
- [10. Rendimiento](#10-rendimiento)
- [11. Convenciones y estilo](#11-convenciones-y-estilo)
- [12. Distribución](#12-distribución)
- [13. Matriz de compatibilidad](#13-matriz-de-compatibilidad)
- [14. Referencias](#14-referencias)

---

## 1. Vista general

SpeechToTextAuxPy es un programa de ~250 líneas repartidas en tres módulos. Su interés técnico no está en el volumen de código sino en **el puente**: Python no accede al micrófono ni implementa un decodificador acústico; carga el runtime de .NET dentro de su propio proceso y delega todo el trabajo de voz en `System.Speech`, que a su vez es una fachada administrada sobre **SAPI 5.4**.

```
audio del sistema
      │
      ▼
SAPI 5.4 (reconocedor es-ES, COM in-proc)
      │
      ▼
System.Speech.Recognition  ── eventos ──▶  delegado Python
      ▲                                        │
      │                                     pythonnet (clr)
      │                                        ▼
      └──────────────────────────────  SapiEngine → console_utils → consola
```

### Principios de diseño

| Principio | Cómo se materializa |
|---|---|
| **Una sola responsabilidad por módulo** | `sapi_engine` habla con .NET; `console_utils` formatea; `main` orquesta y gestiona señales. |
| **Degradación elegante** | Sin `colorama` el programa pierde color, no funcionalidad. |
| **Fallo explicado, no silencioso** | Toda excepción de inicialización se traduce a un mensaje accionable antes de propagarse. |
| **Ciclo de vida explícito** | `start()` / `stop()` con liberación de COM (`Dispose`) y atributos puestos a `None`. |
| **Superficie mínima** | Dos dependencias, sin binarios nativos, sin servicio, sin configuración externa. |

### Qué NO hay aquí (decisiones conscientes)

- No hay captura de audio propia (nada de `pyaudio`, `sounddevice` ni `soundcard`).
- No hay hilo de trabajo en Python: el reconocimiento asíncrono vive en hilos de .NET.
- No hay persistencia ni base de datos.
- No hay CLI con argumentos (`argparse`): el idioma es una constante en `main()`.

Estas ausencias son parte del diseño, no deuda pendiente: cada una habría añadido dependencias o superficie de fallo sin mejorar el objetivo (transcribir en vivo, en consola, en Windows).

---

## 2. Estructura del repositorio

```
SpeechToTextAuxPy/
├── README.md                 ← presentación, uso y troubleshooting
├── LICENSE                   ← MIT, Copyright (c) 2026 wanderc137
├── requirements.txt          ← pythonnet>=3.0.0, colorama>=0.4.6
├── run.bat                   ← lanzador Windows (chcp 65001 + pip + python)
├── src/
│   ├── main.py               ← entrada, señales, bucle de espera
│   ├── sapi_engine.py        ← SapiEngine: wrapper de System.Speech
│   └── console_utils.py      ← impresión con timestamp y color
└── docs/
    ├── datasheet.md          ← manual de usuario
    ├── desarrollador.md      ← este documento
    ├── REFERENCES.md         ← fuentes y documentación externa
    ├── BITACORA.md           ← decisiones, problemas y descartes
    └── assets/
        ├── architecture.svg  ← mapa de componentes
        ├── sapi-flow.svg     ← flujo de una frase, paso a paso
        └── setup.svg         ← puesta en marcha
```

### Dependencias entre módulos

```
main.py ──▶ sapi_engine.py ──▶ console_utils.py
   │                              ▲
   └──────────────────────────────┘
```

`sapi_engine` importa `console_utils` con **import absoluto** (`import console_utils`), no relativo. Eso obliga a ejecutar desde `src/` o a tener `src/` en `sys.path`. Es una decisión heredada del diseño original: funciona con `python src\main.py` porque Python añade el directorio del script a `sys.path`, pero **rompe** si intentas `python -m src.main` o empaquetar como módulo. La corrección, si algún día se necesita, es convertir `src/` en paquete (`__init__.py`) y usar imports relativos o un `pyproject.toml` con layout `src/`.

---

## 3. Modelo de ejecución

### 3.1 Un proceso, dos runtimes

`python.exe` arranca el intérprete de CPython y, en la primera instrucción `import clr`, pythonnet inicializa el runtime de .NET **dentro del mismo proceso**. No hay comunicación entre procesos ni serialización: los objetos .NET son objetos Python desde el punto de vista del código.

Consecuencias prácticas:

- El consumo de memoria incluye el CLR: 60–120 MB de RSS es normal.
- Un fallo del runtime de .NET (por ejemplo, un `AccessViolation` en el reconocedor) mata el proceso de Python sin excepción capturable.
- El arranque paga el coste de inicializar el CLR: 0,5–1,5 s antes del primer mensaje.

Con `pythonnet` 3.x, en Windows el runtime por defecto es **.NET Framework** —el que expone `System.Speech` en la GAC—. Si en el entorno se define `PYTHONNET_RUNTIME=coreclr`, `clr.AddReference("System.Speech")` dejará de resolver salvo que el ensamblado esté disponible junto a la aplicación. Es la causa número uno de "en mi máquina funciona y en la del compañero no".

### 3.2 Hilos

| Hilo | Origen | Qué ejecuta |
|---|---|---|
| **Principal** | CPython | `main()`, registro de señales, bucle de espera, manejador de `Ctrl+C`. |
| **Hilos de .NET** | `SpeechRecognitionEngine` | Captura de audio, detección de voz, decodificación. |
| **Hilo del delegado** | .NET, al disparar `SpeechRecognized` | `_on_speech_recognized` → `console_utils`. |

El callback de reconocimiento **no corre en el hilo principal**. Pythonnet adquiere el GIL para ejecutar código Python desde un hilo de .NET; mientras el callback está en ejecución, ese hilo de .NET queda bloqueado. Si el callback tardase (por ejemplo, escribiendo en un socket lento), SAPI acumularía eventos y aumentaría la latencia percibida.

Reglas prácticas:

- El callback debe hacer trabajo O(1): leer el texto, imprimirlo, liberar el resultado.
- No llamar a `time.sleep`, ni a `input()`, ni a servicios de red desde el callback.
- No modificar el motor (cargar gramáticas, cambiar configuración) desde el callback: hazlo antes de `RecognizeAsync`.

### 3.3 Señales en Windows

Windows no tiene el modelo POSIX de señales, pero CPython emula `SIGINT` a partir del evento de consola `CTRL_C_EVENT` y ejecuta el manejador **en el hilo principal**, entre bytecodes. El detalle importante es el bucle de espera:

```python
while True:
    try:
        signal.pause()          # bloquea hasta recibir una señal — no existe en Windows
    except AttributeError:
        import time
        time.sleep(0.5)         # fallback: despierta cada 500 ms
```

En Windows, `signal.pause` **no está definido como función**: el acceso al atributo lanza `AttributeError` en cada iteración, se captura y se duerme 500 ms. El efecto neto es un bucle de sondeo de 2 Hz que:

- mantiene vivo el proceso sin consumir CPU apreciable;
- permite que el manejador de `Ctrl+C` se ejecute en cuanto el hilo principal vuelve a bytecode;
- introduce hasta ~500 ms de retardo en la reacción al `Ctrl+C`.

Es correcto pero poco elegante. Alternativas evaluadas y descartadas en [`BITACORA.md`](BITACORA.md): `threading.Event().wait()` (equivalente y más limpio), `input()` (rompe el uso no interactivo y consume stdin), bucle con `sleep(0.05)` (más CPU sin beneficio).

> **Detalle sutil:** el `try/except AttributeError` está *dentro* del `while`, así que en un sistema donde `signal.pause()` sí existe (Linux/macOS) el programa se bloquearía ahí; pero en esos sistemas falla antes, al no poder cargar `System.Speech`. La rama solo se ejercita en Windows.

### 3.4 Codificación de la consola

Dos capas independientes, ambas necesarias:

1. **`run.bat` ejecuta `chcp 65001`**: cambia la página de códigos de la consola a UTF-8. Sin esto, la consola interpreta los bytes UTF-8 de Python como CP850/CP1252 y los acentos salen corruptos.
2. **`main.py` reconfigura los flujos**: `sys.stdout.reconfigure(encoding="utf-8")` fuerza la codificación del stream de Python, independientemente de la consola. Se envuelve en `try/except AttributeError` porque `reconfigure` no existe en Python < 3.7.

Si solo se aplica una de las dos, el resultado depende de cómo se lance el programa: por eso están ambas.

---

## 4. API de referencia

Convención de firmas: se usa la anotación real del código (PEP 484 parcial). Los tipos .NET se anotan como `Any` porque no existen en el sistema de tipos de Python.

### 4.1 `SapiEngine`

**Módulo:** `src/sapi_engine.py`
**Responsabilidad:** encapsular el ciclo de vida de `System.Speech.Recognition.SpeechRecognitionEngine`.

```python
class SapiEngine:
    def __init__(self, language: str = "es-ES") -> None: ...
    def _on_speech_recognized(self, sender: Any, args: Any) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

#### Atributos de instancia

| Atributo | Tipo | Descripción |
|---|---|---|
| `_language` | `str` | Código de cultura solicitado (`"es-ES"`, `"es-MX"`, `"en-US"`). |
| `_engine` | `Optional[Any]` | Instancia de `SpeechRecognitionEngine` o `None` si aún no se creó / ya se liberó. |
| `_grammar` | `Optional[Any]` | `DictationGrammar` cargada; se mantiene para que el GC no la recolecte antes que el motor. |
| `_RecognizeMode` | `type` | Referencia al enum .NET `RecognizeMode`, guardada en `__init__` para no reimportar en `start()`. |

#### `__init__(language: str = "es-ES") -> None`

Construye el motor y lo deja listo, pero **sin escuchar**.

Secuencia exacta:

1. `import clr` — si falla, lanza `ImportError` con el comando de instalación en el mensaje.
2. `clr.AddReference("System.Speech")` — resuelve el ensamblado en la GAC.
3. Importa `DictationGrammar`, `RecognizeMode`, `SpeechRecognitionEngine` y `System.Globalization.CultureInfo`.
4. `CultureInfo(language)` — valida el formato de la cultura.
5. `SpeechRecognitionEngine(cultura)` — selecciona el reconocedor instalado para esa cultura. Si no hay ninguno, el constructor .NET lanza `ArgumentException`.
6. `SetInputToDefaultAudioDevice()` — abre el dispositivo de entrada predeterminado; si no hay, `InvalidOperationException`.
7. `DictationGrammar()` + `LoadGrammar(...)` — gramática de lenguaje libre.
8. `SpeechRecognized += self._on_speech_recognized` — suscripción al evento.
9. `console_utils.print_info(...)` — confirma el éxito.

**Excepciones**

| Tipo | Condición | Efecto en el mensaje |
|---|---|---|
| `ImportError` | `clr` no importable | Se relanza tal cual; `main()` la mapea a código `1`. |
| `RuntimeError` | Cualquier fallo .NET | Se envuelve con `raise ... from e`, conservando la causa. |

**Heurística de diagnóstico:** el `except Exception` inspecciona el texto del error buscando subcadenas:

| Subcadena | Interpretación | Mensaje que se muestra |
|---|---|---|
| `culture`, `language` | Cultura sin reconocedor | Instrucciones para agregar la voz en Configuración |
| `device`, `audio` | Sin dispositivo de entrada | Instrucciones para conectar micrófono/line-in |
| (otra) | Fallo no clasificado | `Error al inicializar SAPI: <mensaje original>` |

Es una heurística, no una clasificación por tipo de excepción. Ver [sección 6](#6-taxonomía-de-errores) para la crítica y la alternativa robusta.

#### `start() -> None`

```python
if self._engine is None:
    console_utils.print_error("El motor SAPI no está inicializado.")
    return
self._engine.RecognizeAsync(self._RecognizeMode.Multiple)
console_utils.print_info("Iniciando reconocimiento de voz en español...")
console_utils.print_info("Habla al micrófono/entrada auxiliar. Ctrl+C para salir.")
```

- `RecognizeMode.Multiple` mantiene la escucha tras cada frase; `Single` habría detenido el motor al primer resultado.
- La llamada **retorna inmediatamente**: el trabajo ocurre en hilos de .NET.
- Si el motor ya estaba escuchando, .NET lanza `InvalidOperationException`; el código la captura y la convierte en `RuntimeError`.
- Llamar a `start()` tras `stop()` falla, porque `stop()` deja `_engine = None`. El motor no es reutilizable a propósito.

#### `_on_speech_recognized(sender, args) -> None`

```python
if args and args.Result and args.Result.Text:
    texto = args.Result.Text.strip()
    if texto:
        console_utils.print_recognized(texto)
if args and args.Result:
    try:
        args.Result.Dispose()
    except Exception:
        pass
```

- Triple comprobación de nulos antes de tocar `Text`. En pythonnet, acceder a un objeto .NET ya liberado lanza, no devuelve `None`, así que las guardas evitan excepciones en cascada.
- `strip()` elimina el espacio inicial que SAPI suele anteponer a la frase.
- El `if texto` descarta resultados compuestos solo por espacios (pasan el filtro de `Text` no vacío pero no aportan nada).
- `Dispose()` del resultado libera memoria no administrada asociada a la hipótesis. Se hace **después** de leer el texto, nunca antes.
- Todo va dentro de un `try/except` externo: un fallo procesando una frase no debe tumbar la sesión.
- `sender` no se usa; existe porque la firma del delegado .NET lo exige.

#### `stop() -> None`

```python
if self._engine is not None:
    self._engine.RecognizeAsyncCancel()
    self._engine.Dispose()
    self._engine = None
    self._grammar = None
else:
    console_utils.print_info("El motor ya estaba detenido.")
```

- **Idempotente**: la segunda llamada entra por el `else`.
- `RecognizeAsyncCancel()` descarta la frase en curso; no espera a que termine. Para esperar, existiría `RecognizeAsyncStop()`, que el código no usa a propósito (podría tardar).
- `Dispose()` libera el motor y, con él, el dispositivo de audio. Sin esta llamada, el dispositivo puede quedar tomado hasta que muera el proceso.
- Cada operación tiene su propio `try/except` para que un fallo en la cancelación no impida el `Dispose`.

**Orden importante:** cancelar primero, liberar después, anular atributos al final (`finally`). Si se anulara antes de `Dispose()`, se perdería la referencia y el objeto quedaría vivo hasta el próximo GC del CLR.

---

### 4.2 `console_utils`

**Módulo:** `src/console_utils.py`
**Responsabilidad:** todo lo que se imprime pasa por aquí. Centralizar el formato es lo que permite cambiar el esquema de salida en un solo sitio.

```python
COLORAMA_DISPONIBLE: bool

def _formato_timestamp() -> str: ...
def print_timestamp(color: str = Fore.CYAN, stream=sys.stdout) -> None: ...
def print_recognized(text: str) -> None: ...
def print_info(message: str) -> None: ...
def print_error(message: str) -> None: ...
```

#### `COLORAMA_DISPONIBLE` y los fallbacks

En tiempo de importación:

```python
try:
    from colorama import init, Fore, Style
    init()
    COLORAMA_DISPONIBLE = True
except ImportError:
    COLORAMA_DISPONIBLE = False
    class Fore:  CYAN = GREEN = RED = WHITE = RESET = ""
    class Style: BRIGHT = RESET_ALL = ""
```

El truco es que los *fallbacks* exponen los mismos atributos con cadena vacía. Así el resto del módulo escribe `Fore.CYAN` sin comprobar nada, y sin `colorama` simplemente no se emite ningún código de escape. No hay ramas condicionales dispersas.

`init()` de colorama se llama al importar el módulo, lo que envuelve `sys.stdout`/`sys.stderr` para traducir ANSI a llamadas Win32. Es un efecto secundario global: si algún día se importa `console_utils` desde una biblioteca, conviene mover `init()` a `main()`.

#### `_formato_timestamp() -> str`

Devuelve `datetime.now().strftime("%H:%M:%S")`. Sin corchetes: los añade quien imprime. Es privada por convención; no forma parte del contrato público.

#### `print_timestamp(color=Fore.CYAN, stream=sys.stdout) -> None`

Escribe `[HH:MM:SS] ` (con espacio final) en el color y flujo indicados, y hace `flush()`. Es la pieza reutilizada por las otras tres funciones, de modo que el formato del timestamp se define **una sola vez**.

Nota: el valor por defecto `stream=sys.stdout` se evalúa en tiempo de definición. Si alguien reemplaza `sys.stdout` después de importar el módulo, el default seguirá apuntando al objeto antiguo. Para redirigir de verdad hay que pasar el stream explícitamente o reconfigurar el objeto (que es lo que hace `main.py` con `reconfigure`, sin sustituirlo).

#### `print_recognized(text: str) -> None`

Formato final en `stdout`:

```
[HH:MM:SS] texto reconocido
```

Timestamp en cian, texto en blanco brillante, `flush()` al final de la línea. Es la única función que produce la salida "de negocio".

#### `print_info(message: str) -> None`

Timestamp en verde + mensaje, en `stdout`. Se usa para estado (arranque, espera, parada).

#### `print_error(message: str) -> None`

Timestamp en rojo + `ERROR: ` + mensaje, **todo en `stderr`**, con `flush()`. La línea completa va al mismo flujo para que no se parta al redirigir: si el timestamp fuera a `stdout` y el texto a `stderr`, un `> archivo` dejaría líneas huérfanas.

---

### 4.3 `main`

**Módulo:** `src/main.py`

```python
_engine: SapiEngine = None

def signal_handler(signal_num: int, frame) -> None: ...
def main() -> None: ...
```

#### Código de módulo

Antes de importar nada del proyecto y solo si `sys.platform == "win32"`, reconfigura `stdin`, `stdout` y `stderr` a UTF-8, con `try/except AttributeError` para versiones antiguas. Se hace a nivel de módulo —no dentro de `main()`— porque el `import` de `console_utils` ejecuta `colorama.init()`, y el orden importa: primero la codificación, después el wrapper de color.

#### `signal_handler(signal_num: int, frame) -> None`

Registrado para `SIGINT` y, si existe, `SIGTERM`.

1. `print_info("Ctrl+C recibido. Deteniendo...")`
2. `_engine.stop()` dentro de `try/except` (un fallo al parar no debe impedir la salida)
3. `print_info("Programa terminado.")`
4. `sys.exit(0)` → lanza `SystemExit`, que desenrolla la pila y ejecuta los `finally`.

Usa la variable global `_engine` porque el manejador de señales no recibe contexto. Es el único uso legítimo de estado global en el proyecto.

`SIGTERM` se registra dentro de `try/except AttributeError` porque en algunas configuraciones de Windows la constante no existe. En la práctica `SIGTERM` solo llega desde herramientas que lo emulan (WSL, Cygwin, gestores de procesos).

#### `main() -> None`

1. Registra señales.
2. Imprime cabecera (`=== SpeechToTextAuxPy ===` + descripción).
3. `_engine = SapiEngine(language="es-ES")`.
4. `_engine.start()`.
5. `print_info("Esperando entrada de voz...")` y bucle de espera.
6. Captura de errores por tipo:

| Excepción | Mensaje adicional | `sys.exit` |
|---|---|---|
| `ImportError` | "Ejecuta: pip install -r requirements.txt" | `1` |
| `RuntimeError` | "Verifica que el paquete de voz español esté instalado" | `2` |
| `Exception` | "Error inesperado: …" | `3` |

El `except Exception` final es la red de seguridad: cualquier cosa no prevista sale con código distinto de cero y un mensaje, nunca con un traceback sin contexto.

---

## 5. Ciclo de vida y diagrama de secuencia

```
main.py                    SapiEngine                  System.Speech / SAPI
  │                            │                              │
  ├─ signal(SIGINT)            │                              │
  ├─ SapiEngine("es-ES") ─────▶│                              │
  │                            ├─ clr.AddReference ──────────▶│
  │                            ├─ CultureInfo("es-ES")        │
  │                            ├─ SpeechRecognitionEngine ───▶│ (elige reconocedor)
  │                            ├─ SetInputToDefaultAudioDevice│ (abre el dispositivo)
  │                            ├─ LoadGrammar(Dictation) ────▶│
  │                            ├─ SpeechRecognized += cb      │
  │                            │◀── "inicializado" ───────────│
  ├─ start() ─────────────────▶│                              │
  │                            ├─ RecognizeAsync(Multiple) ──▶│
  │                            │◀── escuchando (hilos .NET) ──│
  ├─ print "Esperando..."      │                              │
  ├─ while True: pause/sleep   │                              │
  │                            │        (usuario habla)       │
  │                            │◀── SpeechRecognized ─────────│
  │                            ├─ _on_speech_recognized()      │
  │                            │   ├─ args.Result.Text        │
  │                            │   ├─ print_recognized()      │
  │                            │   └─ Result.Dispose()        │
  │        (Ctrl+C)            │                              │
  ├─ signal_handler()          │                              │
  │   ├─ stop() ──────────────▶│                              │
  │   │                        ├─ RecognizeAsyncCancel() ────▶│
  │   │                        ├─ Dispose() ─────────────────▶│ (libera COM y audio)
  │   │                        └─ _engine = None              │
  │   └─ sys.exit(0)           │                              │
```

Diagrama visual: [`assets/sapi-flow.svg`](assets/sapi-flow.svg).

### Máquina de estados del motor

```
        ┌──────────┐  __init__   ┌───────────┐  start()  ┌────────────┐
        │  creado  │────────────▶│  listo    │──────────▶│ escuchando │
        └──────────┘             └───────────┘           └─────┬──────┘
                                       ▲                       │ stop()
                                       │                       ▼
                                       │                 ┌───────────┐
                                       └─────────────────│ detenido  │
                                          (no se puede   └───────────┘
                                           reutilizar)     _engine=None
```

No hay transición de "detenido" a "listo": instanciar de nuevo es la única forma de volver a escuchar.

---

## 6. Taxonomía de errores

### 6.1 Cómo se propaga un error

```
.NET lanza ArgumentException
        │
        ▼
__init__ captura Exception
        ├─ inspecciona el texto → elige mensaje para el usuario
        └─ raise RuntimeError(...) from e
                │
                ▼
main() captura RuntimeError → print_error + sys.exit(2)
```

La causa original se conserva en `__cause__`, así que un `traceback` completo (si se imprime) muestra la excepción .NET. El programa, en uso normal, no imprime traceback: solo el mensaje traducido.

### 6.2 Crítica honesta de la heurística

Buscar `"culture"` o `"device"` en `str(e)` funciona con los mensajes en inglés del runtime, y falla si:

- el sistema tiene el runtime localizado (mensajes en español, alemán…);
- el mensaje cambia entre versiones de .NET;
- el texto del error contiene la palabra por casualidad.

Alternativa robusta, no implementada:

```python
from System import ArgumentException, InvalidOperationException

try:
    ...
except ArgumentException as e:
    # cultura sin reconocedor instalado
    ...
except InvalidOperationException as e:
    # sin dispositivo de audio
    ...
```

pythonnet permite capturar excepciones .NET por tipo. El cambio es pequeño y elimina la dependencia del idioma del runtime; se deja como mejora para quien quiera endurecerlo.

### 6.3 Tabla de escenarios

| Escenario | Excepción origen | Mensaje al usuario | Código |
|---|---|---|---|
| `pythonnet` ausente | `ImportError` (Python) | "pythonnet no está instalado…" | 1 |
| Cultura sin reconocedor | `ArgumentException` (.NET) | "El idioma 'es-ES' no está soportado…" | 2 |
| Sin dispositivo de entrada | `InvalidOperationException` (.NET) | "No se encontró dispositivo de entrada…" | 2 |
| Dispositivo tomado en exclusiva | `InvalidOperationException` (.NET) | "Error al iniciar reconocimiento…" | 2 |
| Ensamblado no encontrado | `FileNotFoundException` (.NET) | "Error al inicializar SAPI…" | 2 |
| Error en una frase | Cualquiera | "Error en callback de reconocimiento…" | sesión continúa |
| Error al parar | Cualquiera | "Error al cancelar reconocimiento…" | sesión termina igual |

---

## 7. Trampas de implementación

Errores que este código ya evita y que conviene no reintroducir al modificarlo.

### 7.1 Liberar antes de leer

`RecognitionResult` es `IDisposable`. Llamar `Dispose()` y **después** leer `.Text` devuelve basura o lanza. El orden correcto es: leer → imprimir → liberar.

### 7.2 Reutilizar el motor tras `Dispose()`

`SpeechRecognitionEngine.Dispose()` deja el objeto inutilizable. Volver a llamar a `RecognizeAsync` sobre él lanza `ObjectDisposedException`. Por eso `stop()` pone `_engine = None` y `start()` no comprueba si hay que "reiniciar": hay que crear una instancia nueva.

### 7.3 Reimportar dentro del bucle

La primera versión importaba `RecognizeMode` dentro de `start()`. No es caro (el módulo ya está en caché) pero sí ruidoso y repetido en cada llamada. Ahora se guarda como `self._RecognizeMode` en `__init__`.

### 7.4 Mezclar `stdout` y `stderr` en una misma línea

Si el timestamp va a `stdout` y el mensaje a `stderr`, al redirigir aparecen líneas partidas y desordenadas. La regla del proyecto: **una línea completa, un solo flujo**.

### 7.5 Confiar en que el callback corre en el hilo principal

No. Cualquier operación que toque estado compartido sin sincronización es una carrera. En este programa el único estado compartido es `_engine`, y solo lo toca el manejador de señales (hilo principal). El callback no lo lee.

### 7.6 `print()` en lugar de escritura con `flush()`

Al redirigir a archivo o canalizar, `print()` puede quedar retenido en el búfer y dar la impresión de que el programa no funciona. `console_utils` siempre hace `flush()` explícito.

### 7.7 Suponer que `signal.pause()` existe

Detalle explicado en [3.3](#33-señales-en-windows). Si se refactoriza el bucle de espera, conservar el fallback o sustituirlo por `threading.Event().wait()`.

### 7.8 Instalar dependencias en cada arranque

`run.bat` ejecuta `pip install -r requirements.txt` siempre. Es cómodo para la primera vez y perjudicial para uso repetido: añade segundos de arranque y consulta el índice de paquetes. Para uso diario, `python src\main.py` dentro del `venv`.

### 7.9 `__pycache__` en el repositorio

El `.gitignore` actual solo excluye la documentación interna del pipeline. Si aparece `src/__pycache__/`, añadirlo al `.gitignore` en el próximo commit: son artefactos de la versión de Python local y no deben versionarse.

### 7.10 Versiones de pythonnet

`pythonnet` 2.x usaba `clr.AddReference` igual, pero el manejo de delegados y la carga del runtime cambiaron en 3.x. Un `requirements.txt` con `pythonnet>=3.0.0` es deliberado. No bajar esa cota.

---

## 8. Recetas de extensión

Cada receta indica **qué archivo** tocar y **qué se rompe** si se hace mal. Ninguna está implementada en el código actual.

### 8.1 Cambiar el idioma

```python
# src/main.py
_engine = SapiEngine(language="es-MX")
```

Requisito: reconocedor `es-MX` instalado. Comprobación previa:

```python
from System.Speech.Recognition import SpeechRecognitionEngine
print([i.Culture.Name for i in SpeechRecognitionEngine.InstalledRecognizers()])
```

Si se elige un idioma sin reconocedor, el programa sale con código `2` y un mensaje que lo explica.

### 8.2 Volver el idioma configurable por argumentos

```python
# src/main.py
import argparse

parser = argparse.ArgumentParser(description="Transcripción continua con SAPI")
parser.add_argument("--lang", default="es-ES", help="Cultura, p. ej. es-ES")
parser.add_argument("--quiet", action="store_true", help="Sin mensajes de estado")
args = parser.parse_args()
_engine = SapiEngine(language=args.lang)
```

Cuidado: `--quiet` exige que `console_utils` acepte un flag global o que `main` no llame a `print_info`. La forma menos invasiva es una variable de módulo en `console_utils` consultada por `print_info`.

### 8.3 Filtrar por confianza

`SpeechRecognitionResult.Confidence` es un `float` entre 0 y 1.

```python
# src/sapi_engine.py, dentro de _on_speech_recognized
if args and args.Result and args.Result.Text:
    texto = args.Result.Text.strip()
    confianza = float(args.Result.Confidence)
    if texto and confianza >= 0.6:
        console_utils.print_recognized(texto)
```

Advertencia: el umbral es empírico y depende del hablante. Con 0,6 se pierden frases dichas bajito; con 0,3 se cuelan disparates. Documenta el valor elegido en el README.

### 8.4 Registrar también los rechazos

```python
# en __init__, tras suscribir SpeechRecognized
self._engine.SpeechRecognitionRejected += self._on_rejected

def _on_rejected(self, sender, args):
    console_utils.print_info("[audio descartado: confianza insuficiente]")
```

Sirve para diagnosticar "hablo y no aparece nada": si hay rechazos, el audio llega y el problema es acústico, no de dispositivo.

### 8.5 Texto parcial en vivo

`SpeechHypothesized` entrega hipótesis inestables mientras se habla.

```python
self._engine.SpeechHypothesized += self._on_hypothesis

def _on_hypothesis(self, sender, args):
    if args and args.Result and args.Result.Text:
        sys.stdout.write("\r\x1b[K~ " + args.Result.Text)
        sys.stdout.flush()
```

Se actualiza la misma línea con `\r` (retorno de carro) y se borra con la secuencia ANSI `\x1b[K`. Consecuencia: la salida deja de ser una lista limpia de líneas y se vuelve difícil de redirigir a archivo. Si se implementa, conviene activarlo solo cuando `stdout.isatty()` sea `True`.

### 8.6 Ajustar el silencio de fin de frase

```python
from System import TimeSpan
# tras crear el motor
self._engine.EndSilenceTimeout = TimeSpan.FromMilliseconds(600)
self._engine.EndSilenceTimeoutAmbiguous = TimeSpan.FromMilliseconds(900)
```

Efecto: frases más largas (menos cortes a mitad de idea) a costa de más latencia. `EndSilenceTimeoutAmbiguous` se aplica cuando la última palabra es ambigua (por ejemplo, termina en vocal átona).

### 8.7 Escribir a archivo desde el propio programa

```python
# src/main.py
from datetime import datetime
from sapi_engine import SapiEngine
import console_utils

class EngineConLog(SapiEngine):
    def __init__(self, ruta, **kw):
        super().__init__(**kw)
        self._f = open(ruta, "a", encoding="utf-8", buffering=1)  # line-buffered

    def _on_speech_recognized(self, sender, args):
        if args and args.Result and args.Result.Text:
            texto = args.Result.Text.strip()
            if texto:
                self._f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{texto}\n")
        super()._on_speech_recognized(sender, args)

    def stop(self):
        try:
            self._f.close()
        finally:
            super().stop()
```

Detalles que importan: `buffering=1` fuerza escritura por línea, `encoding="utf-8"` evita depender de la página de códigos, y el archivo se cierra en `stop()`. TSV (`\t`) es más fácil de procesar después que texto con corchetes.

### 8.8 Gramática de comandos en vez de dictado

```python
from System.Speech.Recognition import Choices, GrammarBuilder, Grammar

choices = Choices()
for frase in ("iniciar grabación", "detener grabación", "pausar", "continuar"):
    choices.Add(frase)

grammar = Grammar(GrammarBuilder(choices))
self._engine.LoadGrammar(grammar)   # en lugar de DictationGrammar
```

Ventaja: precisión altísima y cero falsos positivos. Desventaja: solo reconoce esas frases; cualquier otra cosa se rechaza. Es el modo adecuado para control por voz, no para transcribir.

### 8.9 Registrar con `logging`

```python
import logging
logging.basicConfig(
    filename="speechtotext.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
```

Y en `console_utils.print_error`, añadir `logging.error(message)`. Así los errores quedan auditables sin depender de que alguien mirara la consola.

### 8.10 Ejecución desatendida

Para arrancar al iniciar sesión sin ventana visible ni `pip` de por medio:

- **Programador de tareas** → acción: `C:\ruta\al\proyecto\venv\Scripts\pythonw.exe` con argumento `src\main.py`; directorio de inicio: `src`.
- Ojo: `pythonw.exe` no tiene consola, así que `print()` escribe en un stream nulo. Si necesitas la transcripción, redirige a archivo explícitamente en lugar de confiar en `stdout`.

### 8.11 Empaquetar con PyInstaller

Funciona, con matices:

- Añadir `--hidden-import clr` (pythonnet se carga dinámicamente y el análisis estático no lo detecta).
- `--onefile` extrae el runtime a `%TEMP%` en cada arranque: 2–5 s de latencia inicial. Preferible `--onedir`.
- El ejecutable debe ser de la misma arquitectura que el Python usado (x64 con x64).
- No incluye el paquete de voz: sigue siendo requisito del sistema.

---

## 9. Pruebas

### 9.1 Lo que se puede verificar sin audio

```bat
python -m compileall src
```

Detecta errores de sintaxis en los tres módulos. Es el mínimo verificable sin Windows ni audio.

```python
# prueba de humo de console_utils (sin .NET)
import io, sys
sys.path.insert(0, "src")
import console_utils

buf = io.StringIO()
console_utils.print_timestamp(color="", stream=buf)
assert buf.getvalue().startswith("[") and buf.getvalue().endswith("] ")
print("formato de timestamp OK")
```

### 9.2 Matriz manual (requiere Windows y audio)

| ID | Escenario | Preparación | Resultado esperado | Código |
|---|---|---|---|---|
| CP-01 | Arranque normal | Voz es-ES instalada, dispositivo conectado | Cabecera + "Iniciando reconocimiento…" | — |
| CP-02 | Reconocimiento | Hablar 3 frases separadas | 3 líneas con timestamp | — |
| CP-03 | Salida limpia | `Ctrl+C` | 3 mensajes de cierre, sin traceback | 0 |
| CP-04 | Sin dispositivo | Deshabilitar todas las entradas | Mensaje sobre dispositivo | 2 |
| CP-05 | Sin voz es-ES | `--lang en-GB` sin paquete | Mensaje sobre idioma | 2 |
| CP-06 | Sin pythonnet | `pip uninstall pythonnet` en el venv | Mensaje de dependencia | 1 |
| CP-07 | Dispositivo en exclusiva | Abrir una DAW que tome el dispositivo | Error al iniciar, mensaje claro | 2 |
| CP-08 | Redirección | `python src\main.py > out.txt` | Archivo con líneas completas | 0 |
| CP-09 | Sin colorama | `pip uninstall colorama` | Misma salida, sin colores | 0 |
| CP-10 | Acentos | Frase con "ñ", "á", "ü" | Caracteres correctos en consola | — |
| CP-11 | Sesión larga | 30 min continuos | Memoria estable, sin cortes | — |
| CP-12 | Doble instancia | Dos programas a la vez | La segunda falla con mensaje | 2 |

### 9.3 Simular una fuente de audio

Para probar sin hablar (por ejemplo, con un archivo de clase):

1. Instala un dispositivo de audio virtual de bucle (VB-CABLE u similar) **si el equipo lo permite**; no forma parte del proyecto.
2. Envía el audio del reproductor al dispositivo virtual.
3. Marca el dispositivo virtual como entrada predeterminada.
4. Ejecuta el programa: transcribirá lo que se reproduzca.

Ventaja: reproducible. Desventaja: el reconocedor está entrenado con voz humana en vivo; la reproducción comprimida (MP3 a 128 kbps) degrada el resultado. Sirve para verificar el flujo, no la calidad.

### 9.4 Qué no es testeable de forma automática

- La precisión del reconocimiento (depende del reconocedor de Windows, no del código).
- El comportamiento del dispositivo de audio (depende del driver).
- El timing de `Ctrl+C` (depende del planificador).

Por eso no hay suite de tests: la lógica propia es de 250 líneas y casi toda es integración con el sistema operativo. Un `pytest` con mocks de `clr` verificaría que se llaman los métodos en orden, lo cual aporta poco frente a la matriz manual.

---

## 10. Rendimiento

### 10.1 Modelo de coste

| Fase | Coste típico | Comentario |
|---|---|---|
| Arranque del intérprete | 50–150 ms | Python 3.12 con pocas importaciones. |
| `import clr` + carga del CLR | 400–1200 ms | Se paga una vez. Depende del disco y del antivirus. |
| Creación del motor + `SetInputToDefaultAudioDevice` | 100–400 ms | Abre el dispositivo. |
| Decodificación de una frase de 5 s | 20–80 ms de CPU | A ráfagas, un núcleo. |
| Impresión con `flush()` | < 1 ms | Dominado por la consola. |
| Memoria residente | 60–120 MB | CLR + ensamblados + búferes. |

En reposo, el proceso no consume CPU medible: espera en `sleep(0.5)` y en los hilos de audio del sistema.

### 10.2 Latencia percibida

```
última sílaba ──[silencio final 0,2–0,8 s]──[decodificación 0,02–0,08 s]──▶ línea en pantalla
```

Es latencia de **cola**, no de streaming. Si la frase se corta por una pausa interna, aparecen dos líneas con timestamps distintos: es el comportamiento esperado, no un fallo.

Formas de reducirla, en orden de impacto:

1. Bajar `EndSilenceTimeout` (por ejemplo a 300 ms): más líneas, más fragmentadas.
2. Asegurar que el reconocedor trabaja a 16 kHz mono (evita remuestreo).
3. Reducir el ruido de fondo: el motor tarda más en decidir cuando la señal es ambigua.

Formas de empeorarla sin darse cuenta: consola en red, antivirus con escaneo de cada escritura, sesión RDP (redirección de audio comprimida).

### 10.3 Medición

```powershell
Measure-Command { python src\main.py }
```

Mide el arranque y el tiempo total hasta `Ctrl+C`. Para aislar el arranque, añade marcas temporales en `main()` con `time.perf_counter()` alrededor de `SapiEngine(...)`.

---

## 11. Convenciones y estilo

- **PEP 8** sin excepciones: 4 espacios, líneas ≤ 92 caracteres (el código existente las respeta), dos líneas en blanco entre funciones de nivel superior.
- **Docstrings en español**, estilo Google (`Args:`, `Returns:`, `Raises:`). Todas las funciones públicas las llevan.
- **Tipos**: anotaciones en firmas; `Any` para objetos .NET; `Optional[...]` cuando el atributo puede ser `None`.
- **Nombres**: `snake_case` para funciones y variables, `PascalCase` para clases, `_prefijo` para uso interno. Los identificadores están en español (`cultura`, `texto`, `error_msg`) y las API externas conservan su nombre en inglés.
- **Manejo de excepciones**: nunca `except:` desnudo; siempre `except Exception` o un tipo concreto, y siempre con una razón (mensaje, re-raise o comentario).
- **Sin prints fuera de `console_utils`**: si necesitas depurar, usa el módulo o `logging`, no `print()` suelto.

---

## 12. Distribución

El proyecto se distribuye como código fuente. No hay `setup.py` ni `pyproject.toml` porque no es una biblioteca: es una aplicación que se ejecuta desde su carpeta.

Si se quisiera publicar en PyPI:

```toml
# pyproject.toml (no incluido)
[project]
name = "speechtotextauxpy"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = ["pythonnet>=3.0.0", "colorama>=0.4.6"]
```

Requisito previo: convertir `src/` en paquete con `__init__.py` y arreglar los imports absolutos descritos en la [sección 2](#2-estructura-del-repositorio).

---

## 13. Matriz de compatibilidad

| Componente | Soportado | Notas |
|---|---|---|
| Windows 10 1803+ | ✅ Probado | .NET 4.7.2 incluido. |
| Windows 11 | ✅ Esperado | Mismos componentes; no verificado en este repositorio. |
| Windows 8.1 / 7 | ⚠️ Probable | Requiere .NET Framework 4.7.2 instalado aparte. |
| Python 3.10 – 3.13 | ✅ | `reconfigure` disponible; typing moderno. |
| Python 3.9 | ⚠️ | `sys.stdin.reconfigure` existe desde 3.7; el código debería funcionar, pero no se prueba. |
| Python 3.6 y anteriores | ❌ | Sin `reconfigure`; `Optional[Any]` con `from __future__` sería necesario. |
| pythonnet 3.x | ✅ | Versión objetivo. |
| pythonnet 2.5 | ❌ | API de delegados distinta. |
| .NET Framework 4.7.2 / 4.8 | ✅ | Donde vive `System.Speech`. |
| .NET 6/7/8 (CoreCLR) | ❌ | `System.Speech` no forma parte del runtime base; requiere el paquete NuGet y no es el camino soportado aquí. |
| Linux / macOS | ❌ | No existe `System.Speech`; pythonnet con Mono no lo expone. |

---

## 14. Referencias

Lista anotada completa en [`REFERENCES.md`](REFERENCES.md). Las imprescindibles:

- [`System.Speech.Recognition.SpeechRecognitionEngine`](https://learn.microsoft.com/dotnet/api/system.speech.recognition.speechrecognitionengine) — clase central; consultar `EndSilenceTimeout`, `MaxAlternates` y los eventos.
- [`DictationGrammar`](https://learn.microsoft.com/dotnet/api/system.speech.recognition.dictationgrammar) — gramática usada.
- [pythonnet](https://pythonnet.github.io/) — interoperabilidad y selección de runtime.
- [SAPI 5.4](https://learn.microsoft.com/previous-versions/windows/desktop/ms723627(v=vs.85)) — la API nativa que hay debajo.

---

*Documentación técnica de SpeechToTextAuxPy · Licencia MIT · Copyright (c) 2026 wanderc137*
