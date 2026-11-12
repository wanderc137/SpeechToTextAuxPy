# 📘 Manual de usuario — SpeechToTextAuxPy

> **Ficha técnica y guía de operación** · versión 1.0.0 · Windows 10/11 · español (es-ES)

Este documento explica, sin asumir conocimientos de programación, qué hace el programa, cómo se instala, cómo se configura el audio y cómo se interpreta todo lo que aparece en pantalla. Si buscas detalles de implementación, consulta [`desarrollador.md`](desarrollador.md).

---

## Índice

1. [Qué es y qué no es](#1-qué-es-y-qué-no-es)
2. [Requisitos](#2-requisitos)
3. [Instalación paso a paso](#3-instalación-paso-a-paso)
4. [Dependencias del proyecto](#4-dependencias-del-proyecto)
5. [Configuración del audio](#5-configuración-del-audio)
6. [Operación](#6-operación)
7. [Cómo leer la pantalla](#7-cómo-leer-la-pantalla)
8. [Sesiones de ejemplo](#8-sesiones-de-ejemplo)
9. [Mensajes y su significado](#9-mensajes-y-su-significado)
10. [Códigos de salida](#10-códigos-de-salida)
11. [Cuidado y mantenimiento](#11-cuidado-y-mantenimiento)
12. [Preguntas frecuentes](#12-preguntas-frecuentes)
13. [Limitaciones declaradas](#13-limitaciones-declaradas)
14. [Glosario](#14-glosario)

---

## 1. Qué es y qué no es

**SpeechToTextAuxPy** es una herramienta de consola que escucha el **dispositivo de entrada de audio predeterminado de Windows** —un micrófono o una entrada auxiliar *line-in*— y escribe en pantalla, en español, cada frase que el motor de reconocimiento de Windows entiende. Cada línea lleva delante la hora exacta en que se cerró la frase, con formato `[HH:MM:SS]`.

El programa no tiene ventana propia, ni botones, ni icono de bandeja. Es una ventana de consola que se queda escuchando hasta que la cierras con `Ctrl+C`.

### Lo que sí hace

- Escucha de forma **continua e indefinida**: no hay límite de duración ni de número de frases.
- Transcribe **español de España** (`es-ES`) por defecto, con posibilidad de cambiar el idioma editando una línea.
- Muestra el texto **en el momento** en que el motor cierra cada frase, sin esperar al final de la sesión.
- Funciona **sin conexión a internet**. El reconocimiento ocurre dentro del equipo.
- **No guarda audio ni transcripciones** por sí mismo: si quieres un archivo, rediriges la salida (se explica más abajo).
- Termina de forma ordenada con `Ctrl+C`, liberando el dispositivo de audio.

### Lo que no hace

- **No graba audio a disco.** No hay archivo `.wav` en ningún momento.
- **No traduce ni resume.** Escribe lo que oye, no lo que significa.
- **No distingue hablantes.** Dos voces se convierten en un único flujo de texto.
- **No añade puntuación de forma fiable** ni mayúsculas sistemáticas: el motor de dictado de Windows devuelve texto plano.
- **No funciona en Linux ni en macOS.** Depende de un componente que solo existe en Windows.
- **No elige el dispositivo por nombre.** Usa el que el sistema tenga marcado como predeterminado; cambiarlo es tarea de Windows, no del programa.

---

## 2. Requisitos

| Componente | Mínimo | Notas |
|---|---|---|
| **Sistema operativo** | Windows 10 (build 10240 o superior) | Windows 11 conserva los mismos componentes. Probado en Windows 10. |
| **Arquitectura** | x86-64 | También funciona en x86 de 32 bits con Python de 32 bits. |
| **Python** | 3.10 | 3.11, 3.12 y 3.13 también sirven. |
| **.NET Framework** | 4.7.2 | Incluido en Windows 10 desde la versión 1803. No hay que instalarlo aparte. |
| **Paquete de voz** | Español (España) o Español (México) | **Imprescindible.** Es el requisito que más falla. |
| **Audio** | Micrófono o entrada line-in operativa | Cualquier dispositivo que Windows reconozca como entrada. |
| **Espacio en disco** | ~15 MB | Código, dependencias y caché de pip. |
| **Memoria** | ~60–120 MB de RAM en ejecución | El runtime de .NET se carga dentro del proceso de Python. |
| **Red** | Solo para instalar dependencias | Después, el programa funciona totalmente offline. |
| **Permisos** | Usuario estándar | No requiere administrador. |

### Sobre el paquete de voz

Windows separa dos cosas que suelen confundirse:

- **Voces de texto a voz (TTS)**: sirven para que el equipo *hable*.
- **Reconocedores de voz (SR)**: sirven para que el equipo *escuche*.

El programa necesita un **reconocedor**. En Windows 10 y 11 se instala desde **Configuración → Hora e idioma → Voz → Agregar voces**, eligiendo *Español (España)*. El mismo paquete suele traer voz TTS y reconocedor SR, pero la única forma fiable de comprobarlo es enumerar los reconocedores instalados (ver [sección 5.4](#54-verificar-qué-reconocedores-hay-instalados)).

> ⚠️ Sin reconocedor `es-ES`, el programa arranca, falla al crear el motor y termina con código `2` y un mensaje que indica cómo instalar el paquete. No hay forma de "forzar" el idioma: el motor debe existir en el sistema.

---

## 3. Instalación paso a paso

### 3.1 Copiar el proyecto

Descomprime o clona el proyecto en una carpeta local, por ejemplo:

```
C:\ruta\al\proyecto\SpeechToTextAuxPy
```

Evita rutas con caracteres poco habituales y no lo ejecutes desde una unidad de red: el arranque del runtime de .NET se vuelve lento y algunas instalaciones de Python no lo toleran bien.

### 3.2 Crear un entorno virtual

Un entorno virtual evita mezclar `pythonnet` con otras instalaciones de Python del equipo. Desde **CMD** o **PowerShell**, dentro de la carpeta del proyecto:

```bat
python -m venv venv
venv\Scripts\activate
```

En PowerShell, si la activación está bloqueada por la política de ejecución:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
venv\Scripts\Activate.ps1
```

Sabrás que está activo porque el prompt empieza por `(venv)`.

### 3.3 Instalar las dependencias

```bat
pip install -r requirements.txt
```

Tarda entre 10 y 40 segundos según la conexión: `pythonnet` trae una rueda ya compilada y `colorama` es un paquete pequeño. No se compila nada en C.

### 3.4 Verificar la instalación

```bat
python -c "import clr; print('pythonnet OK')"
```

Si imprime `pythonnet OK`, el puente con .NET está operativo. Si lanza `ModuleNotFoundError`, el entorno virtual no está activado o `pip` instaló en otro intérprete.

### 3.5 Ejecutar

```bat
python src\main.py
```

o, si prefieres el lanzador que instala dependencias y ajusta la codificación de la consola:

```bat
run.bat
```

---

## 4. Dependencias del proyecto

Todas las dependencias están declaradas en **`requirements.txt`**, en la raíz del proyecto:

```
pythonnet>=3.0.0
colorama>=0.4.6
```

| Paquete | Versión declarada | Rol | ¿Opcional? |
|---|---|---|---|
| **pythonnet** | `>= 3.0.0` | Carga el runtime de .NET en el proceso de Python y expone `System.Speech.Recognition` como si fuera un módulo Python. Sin él no hay reconocimiento. | No |
| **colorama** | `>= 0.4.6` | Traduce las secuencias ANSI a llamadas de consola de Windows para que los colores se vean. | Sí, con degradación automática: sin `colorama` el programa funciona igual, en blanco y negro. |

Instalación dentro del entorno virtual del proyecto (recomendado siempre):

```bat
venv\Scripts\activate
pip install -r requirements.txt
```

Comprobación de versiones instaladas:

```bat
pip show pythonnet colorama
```

> **Nota sobre versiones:** `pythonnet` 2.x no es compatible con este código: la API de interoperabilidad cambió y el manejo de delegados es distinto. Si tienes una versión antigua en el entorno global, el mensaje de error puede ser confuso; instala siempre dentro del `venv`.

---

## 5. Configuración del audio

El programa **no abre el micrófono directamente**: le pide a Windows "dame el dispositivo de entrada predeterminado". Por eso el 90 % de los problemas de "no reconoce nada" se resuelven en el panel de sonido, no en el código.

### 5.1 Elegir entrada: micrófono o line-in

**Micrófono** — para dictar cerca del equipo, reuniones pequeñas, pruebas.

1. Conecta el micrófono (jack rosa/rosa verdoso o USB).
2. **Configuración → Sistema → Sonido → Entrada**.
3. Selecciona el dispositivo y habla: la barra de nivel debe moverse.
4. Ajusta el volumen para que las palabras normales lleguen aproximadamente a la mitad de la barra.

**Line-in (entrada auxiliar)** — para capturar la salida de una mesa de mezclas, un grabador, un receptor o la salida de otro PC.

1. Conecta el cable a la toma **azul** del panel trasero (habitualmente `Line In`) o a la interfaz USB correspondiente.
2. Abre **Panel de control de sonido** (búscalo en el menú Inicio) → pestaña **Grabar**.
3. Localiza **Entrada auxiliar / Line-In**. Si no aparece, haz clic derecho en una zona vacía y activa **Mostrar dispositivos deshabilitados**; luego habilítalo.
4. Clic derecho → **Establecer como dispositivo predeterminado**.
5. **Propiedades → Niveles**: sube el volumen. En **Mejoras**, desactiva todo lo que no necesites (cancelación de eco, supresión de ruido) si el audio viene ya limpio de la mesa.
6. **Escuchar este dispositivo** debe estar **desactivado**: si lo activas, se produce realimentación y el reconocimiento empeora.

### 5.2 Niveles: cómo ajustarlos sin oído experto

- Si el nivel llega al máximo y se queda pegado (**clipping**), el motor recibe una señal deformada y transcribe peor. Baja el volumen de la fuente o del dispositivo.
- Si el nivel apenas se mueve, el motor no detecta voz: sube el volumen.
- Objetivo práctico: en habla normal, el pico debe quedar entre el 60 % y el 85 % de la barra.

### 5.3 Formato y exclusividad

En **Propiedades del dispositivo → Opciones avanzadas**:

- **Formato predeterminado**: el reconocedor de SAPI trabaja internamente a 16 kHz, 16 bits, mono. Si puedes fijar ese formato, Windows se ahorra remuestreo. Si no aparece, deja 44,1 kHz o 48 kHz: el motor remuestrea solo y funciona igual.
- **Permitir que las aplicaciones tomen control exclusivo**: desmárcalo si otra aplicación (una DAW, una web de videollamada) se queda con el dispositivo y el programa deja de recibir audio.

### 5.4 Verificar qué reconocedores hay instalados

Guarda esto como `check_recognizers.py` **fuera del proyecto** o ejecútalo con `python -c`. No modifica nada; solo enumera:

```python
import clr
clr.AddReference("System.Speech")
from System.Speech.Recognition import SpeechRecognitionEngine

for info in SpeechRecognitionEngine.InstalledRecognizers():
    print(f"{info.Culture.Name:8} | {info.Name} | {info.Description}")
```

Salida típica en un equipo con español instalado:

```
en-US    | MS-1033-80-DESK | Microsoft Speech Recognizer 8.0 for Windows (English - US)
es-ES    | MS-3082-80-DESK | Microsoft Speech Recognizer 8.0 for Windows (Spanish - Spain)
```

Si no aparece ninguna línea `es-ES`, el programa no podrá arrancar con el idioma por defecto. Instala el paquete de voz y repite.

---

## 6. Operación

### 6.1 Arrancar

```bat
run.bat
```

o, dentro del entorno virtual:

```bat
python src\main.py
```

### 6.2 Durante la sesión

- Habla con normalidad. No hace falta decir palabras clave ni comandos.
- Cada vez que el motor cierra una frase (porque detectas una pausa), aparece una línea nueva.
- No hay que pulsar nada entre frases.
- Puedes dejar la ventana minimizada: sigue funcionando.
- Puedes cambiar de dispositivo predeterminado **mientras corre**, pero el motor ya abrió el anterior; para que el cambio surta efecto, reinicia el programa.

### 6.3 Detener

`Ctrl+C` en la ventana de la consola. También funciona cerrar la ventana con la X, pero entonces no se ejecuta la secuencia de apagado ordenado y el mensaje final no aparece.

Secuencia correcta:

```
[10:15:52] Ctrl+C recibido. Deteniendo...
[10:15:52] Reconocimiento de voz detenido.
[10:15:52] Programa terminado.
```

### 6.4 Guardar la transcripción en un archivo

El programa escribe en la salida estándar, así que la redirección del sistema funciona:

```bat
python src\main.py > transcripcion.txt
```

Para ver el texto **y** guardarlo a la vez:

```powershell
python src\main.py | Tee-Object -FilePath transcripcion.txt
```

Ten en cuenta dos cosas:

1. Los mensajes de estado (`Motor SAPI inicializado`, `Ctrl+C recibido`…) también acaban en el archivo, porque van por la misma salida estándar. Los errores van por `stderr` y **no** se capturan con `>`; si quieres ambos: `> transcripcion.txt 2>&1`.
2. La marca de tiempo `[HH:MM:SS]` se guarda tal cual, lo que permite reconstruir después el ritmo de la sesión.

---

## 7. Cómo leer la pantalla

| Color | Elemento | Significado |
|---|---|---|
| **Cian** | `[HH:MM:SS]` + texto | Frase reconocida. Es el contenido útil. |
| **Verde** | `[HH:MM:SS]` + mensaje | Estado del programa: arranque, espera, parada. |
| **Rojo** | `[HH:MM:SS] ERROR: …` | Fallo. Va por `stderr`, por lo que no se mezcla con la transcripción al redirigir. |
| **Blanco brillante** | Texto tras el timestamp cian | La transcripción propiamente dicha. |

Sin `colorama`, todos los colores desaparecen y el formato se mantiene: `[HH:MM:SS] texto`.

La hora es la del **cierre de la frase**, no la del inicio. En una frase de diez segundos, el timestamp corresponde al momento en que el motor decidió que habías terminado.

---

## 8. Sesiones de ejemplo

### 8.1 Clase o conferencia por line-in

Escenario: la salida de la mesa de sonido del aula entra por `Line In`; quieres el texto en pantalla para tomar notas.

```
[09:02:11] === SpeechToTextAuxPy ===
[09:02:11] Reconocimiento de voz continuo mediante SAPI (System.Speech)
[09:02:11] Motor SAPI inicializado correctamente (idioma: es-ES)
[09:02:11] Iniciando reconocimiento de voz en español...
[09:02:11] Habla al micrófono/entrada auxiliar. Ctrl+C para salir.
[09:02:11] Esperando entrada de voz...
[09:03:04] buenos días vamos a comenzar la clase de hoy
[09:03:12] el tema es la arquitectura de los sistemas distribuidos
[09:03:27] recordad que el examen práctico es la semana que viene
[09:03:41] alguna pregunta sobre el temario anterior
^C
[09:14:58] Ctrl+C recibido. Deteniendo...
[09:14:58] Reconocimiento de voz detenido.
[09:14:58] Programa terminado.
```

Lo que muestra este ejemplo, y conviene interiorizar:

- Entre el inicio de una frase y su aparición pasan uno o dos segundos: es el silencio final que el motor espera.
- Las frases se cortan donde hay pausas, no donde termina la idea.
- No hay puntuación: si necesitas comas y puntos, hay que postprocesar el texto.

### 8.2 Dictado directo con micrófono USB

```
[18:40:05] Motor SAPI inicializado correctamente (idioma: es-ES)
[18:40:05] Iniciando reconocimiento de voz en español...
[18:40:09] nota para el lunes comprar dos cables hdmi
[18:40:16] llamar al proveedor y confirmar el presupuesto
[18:40:24] revisar la factura de marzo antes del viernes
```

En dictado corto la precisión es alta si hablas a velocidad normal y a 20–30 cm del micrófono. Gritar o susurrar empeora el resultado.

### 8.3 Guardar una sesión completa

```powershell
PS> python src\main.py | Tee-Object -FilePath sesion_2026-06-06.txt
```

Al terminar, el archivo contiene las mismas líneas que viste, incluidos los mensajes de estado. Si solo quieres frases reconocidas, filtra después:

```powershell
Get-Content sesion_2026-06-06.txt | Select-String -Pattern '^\[\d{2}:\d{2}:\d{2}\] (?!Motor|Iniciando|Habla|Esperando|Ctrl|Reconocimiento|Programa|===)'
```

---

## 9. Mensajes y su significado

| Mensaje | Cuándo aparece | Qué implica |
|---|---|---|
| `=== SpeechToTextAuxPy ===` | Al arrancar | Cabecera. Informativo. |
| `Reconocimiento de voz continuo mediante SAPI (System.Speech)` | Al arrancar | Describe el motor en uso. |
| `Motor SAPI inicializado correctamente (idioma: es-ES)` | Tras crear el motor | El reconocedor existe y el dispositivo de audio se abrió. |
| `Iniciando reconocimiento de voz en español...` | Tras `RecognizeAsync` | El motor ya escucha. |
| `Habla al micrófono/entrada auxiliar. Ctrl+C para salir.` | Justo después | Recordatorio de uso. |
| `Esperando entrada de voz...` | Antes del bucle de espera | El proceso está vivo esperando eventos. |
| `Ctrl+C recibido. Deteniendo...` | Al pulsar `Ctrl+C` | Comienza el apagado ordenado. |
| `Reconocimiento de voz detenido.` | Tras cancelar | Se llamó a `RecognizeAsyncCancel()`. |
| `Programa terminado.` | Al final | Salida limpia, código `0`. |
| `El motor ya estaba detenido.` | `stop()` sin motor activo | No es un error; protección contra doble parada. |
| `ERROR: El idioma 'es-ES' no está soportado. …` | No hay reconocedor es-ES | Instala el paquete de voz. Código `2`. |
| `ERROR: No se encontró dispositivo de entrada de audio disponible. …` | Sin entrada utilizable | Conecta/habilita un dispositivo. Código `2`. |
| `ERROR: Error al inicializar SAPI: …` | Fallo .NET no clasificado | El texto incluye el mensaje original. Código `2`. |
| `ERROR: Dependencia faltante: …` | `pythonnet` ausente | Activa el `venv` e instala `requirements.txt`. Código `1`. |
| `ERROR: Error de ejecución SAPI: …` | Fallo al iniciar la escucha | Suele ser dispositivo ocupado en exclusiva. Código `2`. |
| `ERROR: Error inesperado: …` | Cualquier otra excepción | Código `3`; adjunta el mensaje al reportar. |
| `ERROR: Error en callback de reconocimiento: …` | Fallo procesando una frase | La sesión **no** se interrumpe. |
| `ERROR: Error al cancelar reconocimiento: …` | Fallo en la parada | El proceso intenta liberar igualmente. |

Los mensajes de error se escriben íntegramente en `stderr`; los de estado y las frases, en `stdout`. Esa separación es deliberada: permite usar el programa como filtro (`python src\main.py | otra_herramienta`) sin que los avisos contaminen el flujo útil.

---

## 10. Códigos de salida

| Código | Cuándo | Qué hacer |
|---|---|---|
| `0` | `Ctrl+C` o cierre ordenado | Nada. Es el final esperado. |
| `1` | Falta `pythonnet` | `venv\Scripts\activate` y `pip install -r requirements.txt`. |
| `2` | Fallo al inicializar o iniciar SAPI | Revisa paquete de voz y dispositivo de audio. |
| `3` | Excepción no clasificada | Lee el mensaje; suele incluir la causa de .NET. |

Se pueden consultar desde un `.bat` con `echo %errorlevel%` o desde PowerShell con `$LASTEXITCODE`.

---

## 11. Cuidado y mantenimiento

- **No hay estado persistente.** Ni configuración, ni historial, ni caché: cada arranque es limpio. Actualizar el programa consiste en reemplazar los archivos.
- **El entorno virtual es desechable.** Si algo se rompe, borra `venv` y vuelve a crearlo. Es la reparación más rápida y no afecta al sistema.
- **No ejecutes dos instancias a la vez** esperando que ambas reciban audio: la primera que abra el dispositivo puede dejarlo en exclusiva y la segunda fallará al inicializar.
- **Sesiones largas:** el programa libera el resultado de cada frase, así que la memoria se mantiene estable en sesiones de horas. Aun así, para eventos de varias horas conviene reiniciar entre bloques y guardar por partes.
- **Portátiles:** con el equipo en batería, la administración de energía puede suspender el dispositivo USB de audio. Si notas cortes, revisa el plan de energía.

---

## 12. Preguntas frecuentes

**¿Necesito internet?**
No. La instalación de dependencias sí lo requiere; el reconocimiento es local. Windows tiene un ajuste llamado *Reconocimiento de voz en línea*, pero SAPI 5.4 —el que usa este programa— trabaja con el reconocedor instalado en el equipo y no abre conexiones.

**¿Funciona en Windows 11?**
Sí, en la medida en que Windows 11 mantiene SAPI 5.4 y .NET Framework 4.8. El proyecto se probó en Windows 10; en Windows 11 el comportamiento es el mismo, aunque esa combinación no está verificada en este repositorio.

**¿Puedo cambiar el idioma?**
Sí, si el reconocedor de ese idioma está instalado. En `src/main.py` cambia `SapiEngine(language="es-ES")` por `es-MX`, `en-US`, etc. El mensaje de error del programa te indica cuándo falta el paquete.

**¿Por qué no aparecen comas ni puntos?**
Porque la gramática de dictado devuelve la secuencia de palabras más probable, sin puntuación editorial. Añadirla exige postprocesar el texto o dictar los signos ("coma", "punto") y confiar en que el motor los transcriba; ninguna de las dos cosas está implementada.

**¿Puedo elegir otro micrófono sin cambiar el predeterminado de Windows?**
No con el código actual: el motor se ata al dispositivo predeterminado en el momento de arrancar. La alternativa es cambiar el predeterminado en Windows o modificar `sapi_engine.py` para seleccionar un dispositivo por índice.

**Se reconocen frases sueltas y otras desaparecen. ¿Es normal?**
Sí. El motor descarta lo que no supera su umbral de confianza y lo que interpreta como ruido. Frases muy cortas ("sí", "vale") o con ruido de fondo se pierden con frecuencia.

**¿Puedo usarlo para subtitular un vídeo en directo?**
Como apoyo, sí; como subtitulado profesional, no. La latencia de cola (0,2–0,8 s) y la ausencia de puntuación lo hacen poco apto para emisión.

**¿Consume mucha CPU?**
Poco y a ráfagas: la decodificación de una frase dura decenas de milisegundos. En reposo el proceso está casi siempre esperando. La memoria sí es notable al inicio (60–120 MB) porque carga el runtime de .NET.

**¿Qué pasa si hablo en otro idioma?**
El motor intentará ajustar los sonidos a palabras españolas y producirá texto sin sentido. No detecta el idioma automáticamente.

**¿Puedo lanzarlo al iniciar sesión?**
Sí, con el Programador de tareas apuntando a `run.bat`, pero ten en cuenta que `run.bat` ejecuta `pip install` en cada arranque: para uso desatendido, crea una tarea que llame directamente a `venv\Scripts\python.exe src\main.py`.

**¿Por qué `run.bat` tarda en arrancar?**
Porque comprueba e instala dependencias cada vez. Es comodidad para la primera ejecución, no una optimización. Ejecutando `python src\main.py` con el `venv` activo el arranque es inmediato.

---

## 13. Limitaciones declaradas

1. **Solo Windows.** `System.Speech.dll` es exclusivo de .NET Framework en Windows.
2. **Un único idioma por ejecución.** El motor se crea con una cultura fija.
3. **Sin streaming a archivo.** No escribe audio ni transcripción; para persistir hay que redirigir la salida.
4. **Sin texto parcial.** Solo se muestra la frase cerrada, no las hipótesis intermedias.
5. **Sin selección de dispositivo.** Siempre el predeterminado del sistema.
6. **Sin diarización.** No separa voces ni identifica hablantes.
7. **Sin control de confianza.** El programa imprime todo lo que el motor acepta, sin filtrar por `Confidence`.
8. **Sin pausa ni reanudación.** Solo arrancar y detener con `Ctrl+C`.
9. **Depende del paquete de voz del sistema.** La calidad no es la de un modelo neuronal moderno; es la del reconocedor de Windows.
10. **Pensado para una persona frente al equipo o una fuente de audio limpia.** Salas ruidosas, música de fondo y reverberación degradan mucho el resultado.

---

## 14. Glosario

| Término | Definición |
|---|---|
| **SAPI** | *Speech Application Programming Interface*. API de voz de Windows; la versión 5.4 es la que sigue viva en Windows 10/11. |
| **System.Speech** | Ensamblado de .NET Framework que envuelve SAPI 5.4 con clases administradas (`SpeechRecognitionEngine`, `DictationGrammar`). |
| **pythonnet / clr** | Puente que permite a Python cargar y usar ensamblados .NET dentro del mismo proceso. |
| **Reconocedor (SR)** | Componente de software que convierte audio en texto, instalado por idioma. |
| **Gramática de dictado** | Modo de reconocimiento de lenguaje libre, sin lista cerrada de comandos. |
| **Line-in** | Entrada de audio de nivel de línea, pensada para señales ya amplificadas (mesas, reproductores). |
| **Clipping** | Saturación de la señal por exceso de nivel; destruye información y arruina el reconocimiento. |
| **Latencia de cola** | Retardo entre el final de la frase hablada y su aparición en pantalla. |
| **stderr** | Canal de error estándar; separado de la salida normal para no contaminar la transcripción. |

---

*Documento de usuario de SpeechToTextAuxPy · Licencia MIT · Copyright (c) 2026 wanderc137*
