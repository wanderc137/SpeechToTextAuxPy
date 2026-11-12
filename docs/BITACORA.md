# 🧾 Bitácora de desarrollo — SpeechToTextAuxPy

> Registro de decisiones, problemas y callejones sin salida. Está escrito para el próximo que toque el proyecto —probablemente yo mismo dentro de seis meses— y para que no repita los errores que aquí se documentan.

---

## 1. Contexto de partida

**Objetivo:** transcribir en vivo, en español, audio que entra por la toma auxiliar (line-in) de un PC con Windows, mostrando el texto en consola con la hora de cada frase, de forma continua y sin depender de internet.

**Restricciones que moldearon todo lo demás:**

1. **Windows obligatorio.** El equipo de destino es Windows 10 y no hay ánimo de instalar servicios en la nube ni modelos de terceros.
2. **Sin modelos descargables.** El reconocedor tenía que ser el que ya trae (o instala) el sistema operativo.
3. **Dos dependencias como máximo.** Cada paquete añadido es un punto de fallo en un equipo que no administro.
4. **Consola, no interfaz gráfica.** El uso previsto es "dejar una ventana abierta y leer".
5. **Privacidad por diseño.** El audio no debe salir del equipo bajo ninguna circunstancia.

Ese quinto punto descartó de entrada cualquier solución basada en APIs web, que es lo que aparece primero al buscar "speech to text Python".

---

## 2. Decisiones técnicas

### D-01 · Usar SAPI a través de `System.Speech`, no COM directo

| Opción | Pros | Contras | Veredicto |
|---|---|---|---|
| COM directo (`pywin32`/`comtypes` → `ISpRecognizer`) | Control total: dispositivo por token, formato exacto | Cientos de líneas, tipos COM a mano, dependencia con binarios por arquitectura | ❌ |
| **`System.Speech` vía pythonnet** | API administrada, eventos, `Dispose()`, 40 líneas de envoltorio | Solo .NET Framework, Windows | ✅ |
| `SpeechRecognition` (PyPI) | Multi-backend | Arrastra `PyAudio`, capa extra, tentación de usar la nube | ❌ |

**Justificación:** `System.Speech` expone exactamente lo necesario (motor, gramática, evento de resultado) sin escribir interoperabilidad COM a mano. El coste es atarse a .NET Framework, algo irrelevante cuando el requisito ya es Windows.

### D-02 · `RecognizeAsync(Multiple)` en lugar de `Recognize()` en bucle

`Recognize()` bloquea el hilo hasta obtener una frase. Un bucle `while True: Recognize()` habría funcionado, pero:

- bloquea el hilo principal, que necesita atender `Ctrl+C`;
- reconstruye el ciclo de escucha en cada iteración;
- mezcla la lógica de espera con la de reconocimiento.

`RecognizeAsync(Multiple)` deja el motor escuchando en hilos de .NET y libera el hilo principal para las señales. Es el patrón documentado por Microsoft para dictado continuo.

### D-03 · `DictationGrammar` en lugar de una gramática cerrada

Una gramática de comandos (`Choices` + `GrammarBuilder`) da precisión casi perfecta, pero solo reconoce las frases listadas. El requisito es transcribir lenguaje libre, así que se usa la gramática de dictado. La receta para cambiar a comandos quedó documentada en [`desarrollador.md`](desarrollador.md#88-gramática-de-comandos-en-vez-de-dictado) por si el proyecto deriva hacia control por voz.

### D-04 · `colorama` opcional, con degradación elegante

Se podría haber exigido `colorama` y ya está. Se prefirió que el programa funcione sin él por dos razones:

1. Si alguien copia solo `src/` a otro equipo, el programa sigue siendo útil.
2. Al redirigir a archivo, los códigos ANSI son ruido; el fallback los elimina de raíz.

El mecanismo —clases `Fore`/`Style` con atributos vacíos— evita llenar el código de `if COLORAMA_DISPONIBLE`. Coste: dos clases de relleno, ocho líneas.

### D-05 · Timestamp centralizado en `print_timestamp()`

La primera versión construía el timestamp dentro de cada función. Eso hizo que, tras un refactor, los colores quedaran inconsistentes (timestamp en verde dentro de un mensaje de error, por ejemplo). Se extrajo `_formato_timestamp()` y `print_timestamp(color, stream)` para que el formato se defina en un solo lugar. Lección aplicada: **si un formato se repite tres veces, es una función**.

### D-06 · Errores siempre por `stderr`

Un mensaje de error partido entre `stdout` (timestamp) y `stderr` (texto) se desordena al redirigir. Se unificó: cada función escribe su línea completa en un único flujo. Los errores van a `stderr`; el estado y las frases, a `stdout`. Esto habilita el uso como filtro (`programa | otra_cosa`) sin contaminar.

### D-07 · UTF-8 por partida doble

`chcp 65001` en `run.bat` **y** `reconfigure(encoding="utf-8")` en `main.py`. Parece redundante y no lo es:

- `chcp` cambia cómo la consola interpreta los bytes.
- `reconfigure` cambia cómo Python codifica los `str` al escribirlos.

Si solo se aplica una, el resultado depende de cómo se lance el programa (doble clic, PowerShell, tarea programada). Con ambas, los acentos salen bien en los tres casos.

### D-08 · Idioma como constante, no como argumento

Se evaluó `argparse` con `--lang`. Se descartó porque el caso de uso es una instalación fija en español: añadir argumentos obliga a documentar flags, a manejar errores de parseo y a decidir precedencias. Cambiar una línea es suficiente y el error es evidente. Si el proyecto crece, la receta está en [`desarrollador.md`](desarrollador.md#82-volver-el-idioma-configurable-por-argumentos).

---

## 3. Problemas encontrados y cómo se resolvieron

### P-01 · `signal.pause()` no existe en Windows

**Síntoma:** el bucle principal lanzaba `AttributeError: module 'signal' has no attribute 'pause'` al arrancar en Windows.

**Causa:** `signal.pause()` es POSIX. En Windows el módulo `signal` no lo define.

**Solución aplicada:** `try: signal.pause() / except AttributeError: time.sleep(0.5)` dentro del bucle.

**Coste:** hasta 500 ms de retardo al reaccionar a `Ctrl+C`. Aceptable para una herramienta de consola.

**Mejor solución conocida (no aplicada):** `threading.Event().wait()` —bloquea sin consumir CPU y sin depender de `pause()`—. No se cambió porque el bucle actual funciona y el cambio no aporta nada visible al usuario. Queda anotado como mejora de una línea.

### P-02 · Colores inconsistentes tras centralizar el timestamp

**Síntoma:** `print_info` mostraba el timestamp en cian y `print_error` en verde; el color del texto no coincidía con el del mensaje.

**Causa:** cada función construía su propio prefijo y, al refactorizar, se copió el color equivocado.

**Solución:** `print_timestamp(color=..., stream=...)` recibe el color como parámetro; cada función pasa el suyo (cian para frases, verde para estado, rojo para errores). Tabla de colores documentada en el manual para que no vuelva a desincronizarse.

### P-03 · Salida partida entre `stdout` y `stderr`

**Síntoma:** al redirigir con `>`, las líneas de error aparecían sin timestamp y las de estado con timestamp huérfano.

**Causa:** el timestamp se escribía en `stdout` y el mensaje en `stderr`.

**Solución:** `print_timestamp` acepta `stream`; `print_error` escribe timestamp, prefijo `ERROR: ` y mensaje —todo— en `stderr`, con un único `flush()`.

### P-04 · Reimportación de `RecognizeMode` en cada `start()`

**Síntoma:** ninguna falla funcional; código repetido y una importación dentro de un método.

**Causa:** el enum se necesitaba en `start()` y se importó localmente para no ampliar el alcance del módulo.

**Solución:** se guarda en `__init__` como `self._RecognizeMode`. Una importación, un atributo, cero duplicación.

### P-05 · Falta de manejo de `SIGTERM`

**Síntoma:** al cerrar desde un gestor de procesos (o desde WSL), el programa moría sin liberar el audio.

**Solución:** segundo `signal.signal(signal.SIGTERM, signal_handler)` envuelto en `try/except AttributeError`, porque en algunas configuraciones de Windows la constante no existe. Barato y evita un caso raro pero real.

### P-06 · El motor quedaba tomado al salir

**Síntoma:** tras cerrar el programa, otro programa no podía usar el micrófono hasta que expiraba el proceso.

**Causa:** faltaba `Dispose()`; el objeto .NET sobrevivía al `sys.exit` hasta que el CLR lo recolectaba, y con él el dispositivo.

**Solución:** `stop()` hace `RecognizeAsyncCancel()` → `Dispose()` → atributos a `None`, cada paso con su `try/except`. Es idempotente: llamarlo dos veces imprime "El motor ya estaba detenido." y no falla.

### P-07 · `AttributeError` en el callback al acceder a `Result`

**Síntoma:** ocasionalmente, una excepción en `_on_speech_recognized` durante frases con ruido.

**Causa:** `args.Result` puede ser `None` cuando el evento llega sin resultado válido; acceder a `.Text` sin comprobar lanzaba.

**Solución:** triple guarda `args and args.Result and args.Result.Text`, más `strip()` y comprobación de cadena no vacía. Todo el callback va dentro de un `try/except` que reporta pero no interrumpe la sesión.

### P-08 · Acentos corruptos en consola

**Síntoma:** "reconocimiento" aparecía como "reconocÃmiento".

**Causa:** la consola usaba CP850/CP1252 mientras Python escribía UTF-8.

**Solución:** `chcp 65001` en el lanzador + `reconfigure` en los tres flujos. Ver D-07.

### P-09 · Mensajes de error poco útiles

**Síntoma:** con el paquete de voz sin instalar, el usuario veía `ArgumentException: No recognizer of the required ID found.` y no sabía qué hacer.

**Solución:** el `except` inspecciona el texto del error y traduce a instrucciones concretas ("Configuración → Hora e idioma → Voz → Agregar voces"). Limitación asumida: depende del idioma del runtime. Ver la crítica en [`desarrollador.md`](desarrollador.md#62-crítica-honesta-de-la-heurística).

### P-10 · `run.bat` instalaba dependencias en cada arranque

**Síntoma:** el programa tardaba entre 3 y 15 segundos en arrancar, incluso con todo instalado.

**Causa:** el lanzador ejecuta `pip install -r requirements.txt` siempre, como red de seguridad para la primera ejecución.

**Decisión:** se mantiene. Es un lanzador de conveniencia para quien abre el proyecto por primera vez; el uso diario documentado es `python src\main.py` con el `venv` activo. Cambiarlo habría roto el caso "descomprimo y hago doble clic".

### P-11 · `__pycache__` fuera del control de versiones

Al compilar para verificar sintaxis se generan `.pyc` en `src/__pycache__/`. El `.gitignore` actual solo excluye la documentación interna del pipeline, así que conviene añadir `__pycache__/` y `*.pyc` en el próximo commit. No se tocó en esta pasada para no alterar archivos de control de versiones.

---

## 4. Vías descartadas (y por qué no volver a intentarlas)

| Enfoque | Por qué se descartó | ¿Volvería a intentarlo? |
|---|---|---|
| **Google Web Speech API** (la que aparece en todos los tutoriales) | Envía el audio a un servidor. Viola el requisito de privacidad y no funciona offline. | No. |
| **`speech_recognition` + `PyAudio`** | `PyAudio` requiere binario nativo; la capa añade un backend propio que acaba llamando a SAPI de forma menos controlable. | No para este objetivo. |
| **Vosk** | Modelo de 50 MB a 1,5 GB, inicialización lenta, CPU sostenida. Gran opción offline, pero es otro producto. | No. |
| **Whisper / faster-whisper** | Precisión muy superior, pero modelos de cientos de MB y dependencia de `torch`/`ctranslate2`. Contradice "dos dependencias" y "sin descargas". | No, salvo cambio de requisito. |
| **WinRT `Windows.Media.SpeechRecognition`** | API moderna, pero asíncrona con `IAsyncOperation`, incómoda desde pythonnet, y requiere `winsdk`. Además no es `System.Speech`, que era el requisito explícito. | No. |
| **`pywin32` + COM directo** | Control fino real (elegir dispositivo, fijar formato), pero multiplica el código por diez y añade binarios. | Solo si hiciera falta selección de dispositivo por nombre. |
| **Captura propia con `sounddevice` + `SetInputToAudioStream`** | Permitiría elegir dispositivo y guardar WAV, pero hay que bombear audio a un `Stream` de .NET compatible, con formato exacto y sin bloquear el hilo. Complejidad alta para un requisito que no estaba. | Solo con requisito explícito de selección de dispositivo. |
| **Guardar WAV en paralelo** | Implica duplicar la captura o interceptar el flujo de SAPI (`SpeechRecognitionEngine` no expone el audio). Se resolvió documentando la redirección de texto. | No. |
| **Interfaz gráfica (tkinter)** | El uso previsto es consola; una GUI añade estado, eventos y pruebas. | No. |
| **Servicio de Windows** | El programa necesita una consola visible y un usuario que lea. Como servicio no tiene stdout útil. | No. |
| **Hilo propio de Python para "mantener vivo"** | Innecesario: `RecognizeAsync` ya usa hilos de .NET. Un hilo extra solo añadiría sincronización. | No. |
| **Cola `queue.Queue` entre callback y hilo principal** | Se evaluó para desacoplar la impresión. Se descartó porque la impresión es O(1) y la cola añadía un hilo consumidor y una condición de parada. Si el consumidor se hiciera lento (red, disco), entonces sí valdría la pena. | Solo si el destino de la salida se vuelve lento. |

---

## 5. Lecciones aprendidas

### L-01 · El reconocedor no es el paquete de idioma

Instalar "Español" en Windows no garantiza que exista un reconocedor `es-ES`: puede haber solo voz TTS. La comprobación correcta es enumerar `InstalledRecognizers()`, no interpretar un mensaje de error. Se documentó como paso de verificación en el manual.

### L-02 · La latencia es de cola, no de streaming

SAPI no emite texto mientras hablas: espera a detectar silencio final. Cualquier expectativa de "subtítulos palabra a palabra" es irreal con esta tecnología. Documentarlo desde el principio evita reportes de bug que no son bugs.

### L-03 · `System.Speech` es .NET Framework, no .NET moderno

Es la confusión más común al buscar documentación: hay un paquete NuGet `System.Speech` para .NET 6+, pero el proyecto carga el ensamblado de la GAC con el runtime `netfx` de pythonnet. Mezclar ambos caminos produce `FileNotFoundException` sin mensaje claro.

### L-04 · Un `Dispose()` a tiempo evita "el micrófono está ocupado"

Los objetos .NET que envuelven recursos del sistema no se liberan por salir del ámbito en Python. `SpeechRecognitionEngine` toma el dispositivo de audio: sin `Dispose()` explícito, el recurso queda retenido hasta que el CLR recolecte, y el CLR no tiene prisa.

### L-05 · Los callbacks de .NET no corren donde uno cree

Asumir que el manejador de `SpeechRecognized` se ejecuta en el hilo principal es la receta para una carrera. En este proyecto no importa porque el callback no toca estado compartido, pero es la primera trampa al añadir funcionalidad (por ejemplo, escribir en un archivo compartido con el hilo principal).

### L-06 · Redirigir la salida es más barato que implementar logging

El requisito "guardar la transcripción" se resolvió con `>` y `Tee-Object`. Escribir un subsistema de archivos (rotación, rutas, cierre ordenado) habría costado más código que el resto del programa. La solución de plataforma casi siempre gana a la solución propia.

### L-07 · Los mensajes de error son parte del producto

La primera versión decía "Error al inicializar SAPI". La versión final dice qué instalar y dónde. En una herramienta que depende de un componente del sistema operativo que el usuario no sabe que existe, la calidad del mensaje es la diferencia entre "funciona" y "no funciona".

### L-08 · Dos capas de UTF-8 no son redundancia

`chcp` y `reconfigure` actúan en puntos distintos del camino (consola y proceso). Confiar en una sola funciona "en mi máquina" y falla en la del compañero. Ver D-07.

### L-09 · El `pip install` automático es comodidad, no best practice

Meter `pip install` en el lanzador hace feliz al primer uso y castiga al uso diario. Lo correcto es documentar las dos rutas: lanzador para empezar, `venv` + `python src\main.py` para trabajar.

### L-10 · 250 líneas también necesitan documentación

La tentación con un programa pequeño es "se entiende leyéndolo". No es cierto: lo que no se entiende es *por qué* se eligió `Multiple`, por qué hay `sleep(0.5)`, por qué se hace `Dispose` después de imprimir. Esa información no está en el código, está aquí.

---

## 6. Deuda técnica conocida

Ordenada por relación coste/beneficio. Nada de esto bloquea el uso actual.

| # | Deuda | Impacto | Esfuerzo | Comentario |
|---|---|---|---|---|
| 1 | Heurística de errores por subcadena | Medio | Bajo | Capturar `ArgumentException` e `InvalidOperationException` por tipo, tal como se describe en `desarrollador.md`. |
| 2 | `signal.pause()` + `sleep(0.5)` | Bajo | Muy bajo | Sustituir por `threading.Event().wait()`. |
| 3 | Imports absolutos que impiden `python -m src.main` | Bajo | Bajo | `__init__.py` + imports relativos, o `pyproject.toml`. |
| 4 | Sin selección de dispositivo | Medio | Alto | Requiere captura propia o cambiar el predeterminado del sistema. |
| 5 | Sin `Confidence` ni `SpeechRecognitionRejected` | Medio | Bajo | Dos recetas ya escritas, sin implementar. |
| 6 | `__pycache__` no ignorado | Muy bajo | Muy bajo | Añadir al `.gitignore` en el próximo commit. |
| 7 | Sin suite de tests | Bajo | Medio | Solo tiene sentido con mocks de `clr`; aporta poco frente a la matriz manual. |
| 8 | Sin `CHANGELOG.md` | Bajo | Bajo | Adoptar Keep a Changelog si hay releases. |

---

## 7. Cómo se verificó

- **Sintaxis:** `python -m compileall src` sobre los tres módulos, sin errores.
- **Revisión estática manual:** recorrido de los caminos de error (sin `pythonnet`, sin reconocedor, sin dispositivo), comprobando que cada uno produce un mensaje y un código de salida distintos.
- **Pruebas de ejecución:** en Windows 10 con reconocedor `es-ES` instalado, con micrófono USB y con line-in; sesiones de 10–40 minutos; `Ctrl+C` repetido; redirección a archivo; ejecución sin `colorama`.
- **Lo que no se verificó:** Windows 11, Python 3.13 en producción, sesiones de más de 8 horas, y equipos sin `.NET Framework` 4.7.2 (no se encontró ninguno).

---

## 8. Si empezara hoy

1. Empezaría por enumerar `InstalledRecognizers()` en un script de diagnóstico antes de escribir una línea de envoltorio: ahorra la mitad de las pruebas de error.
2. Usaría `threading.Event()` para el bucle principal desde el minuto uno.
3. Capturaría las excepciones .NET por tipo, no por texto.
4. Escribiría el `console_utils` con `stream` parametrizado desde el principio: la separación `stdout`/`stderr` es fácil de hacer bien y molesta de arreglar después.
5. Documentaría la latencia de cola en el README antes que cualquier otra cosa: es la expectativa que más decepciona al usuario nuevo.

---

*Bitácora de SpeechToTextAuxPy · Licencia MIT · Copyright (c) 2026 wanderc137*
