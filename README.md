<p align="center">
  <img src="images/banner.jpg" alt="PokéOnline" width="100%">
</p>

<h1 align="center">PokéOnline</h1>

<p align="center">
  <strong>El multijugador de Pokémon Añil, de vuelta.</strong><br>
  Parchea el juego, comprueba el servidor y lánzalo, todo desde una ventana.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/versión-0.1.0-3ddc84?style=flat-square" alt="versión 0.1.0">
  <img src="https://img.shields.io/badge/plataforma-Windows-2b3040?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/python-3.10%2B-2b3040?style=flat-square" alt="Python 3.10+">
</p>

---

## Qué es esto

Pokémon Añil **descontinuó su modo multijugador**. Sus servidores se apagaron y,
con ellos, las batallas y los intercambios online: el juego sigue instalado en tu
disco, pero la parte online quedó muerta.

Este proyecto la devuelve a la vida. Se ha hecho **ingeniería inversa** sobre el
protocolo del servidor original para levantar uno nuevo, **auto-hospedado por mí**,
que habla el mismo idioma que el juego. El resultado es que **las batallas y los
intercambios vuelven a funcionar** — solo que el tráfico ya no pasa por los
servidores de Pokémon Añil, sino por el mío.

> El servidor está pensado para estar encendido **24/7**. Aun así es una máquina
> doméstica: puede haber cortes puntuales. La app te dice en todo momento si está
> disponible.

## Qué hace la app

**PokéOnline** es el lanzador que conecta tu copia del juego con el servidor nuevo.
Hace tres cosas:

| | |
|---|---|
| **Parchea el juego** | Crea el archivo de configuración que redirige el juego al servidor nuevo, en lugar del original (que ya no responde). Un botón, y listo. |
| **Comprueba el servidor** | Sondea el servidor multijugador en segundo plano y te dice si está online antes de que te sientes a jugar. |
| **Lanza el juego** | Botón de *Jugar!* y a jugar. La app se cierra sola para no estorbar. |

Al abrirla verás dos indicadores:

- **Conexión** — si el servidor multijugador está encendido y aceptando partidas.
- **Configuración local** — si tu copia del juego ya está apuntando al servidor nuevo.

Si el juego todavía no está parcheado, aparece un botón **Parchear juego**. Púlsalo,
las dos luces se ponen en verde y ya puedes darle a **Jugar!**.

## ⚠️ Compatibilidad: comprueba tu versión antes de nada

Esto **no funciona con cualquier versión del juego**. Solo sirve en las versiones
donde el modo multijugador se activa mediante **dos NPC dentro del Centro Pokémon**.

Cómo saberlo: entra en un Centro Pokémon y mira si hay **dos NPC** que dan acceso al
online (batallas e intercambios). Si están ahí, vas bien. Si tu versión gestiona el
multijugador por otra vía —a través de librerías, sin esos NPC— **la app no te va a
servir de momento**: puedes parchearla y aun así el juego no conectará.

> Se trabajará en el futuro para poder parchear también esas versiones. Por ahora,
> la compatibilidad se limita a las de los dos NPC.

## Instalación

0. Asegúrate de que tu versión es compatible (los **dos NPC** del Centro Pokémon,
   ver arriba).
1. Descarga `PokeOnline.exe` desde la [última release](https://github.com/Anghios/pokeonline/releases).
2. **Cópialo dentro de la carpeta del juego**, junto a `Game.exe`. Esto es
   importante: la app busca el juego y escribe la configuración en su propia
   carpeta, así que desde el Escritorio o la carpeta de Descargas no funcionará.
3. Ejecútalo.
4. Si sale **Parchear juego**, púlsalo.
5. **Jugar!**

La carpeta debería quedarte más o menos así:

```
Pokemon Añil/
├── Game.exe
├── PokeOnline.exe     <-- aquí
└── Data/
    └── serverinfo.ini  <-- lo crea la app al parchear
```

No hace falta instalar Python ni nada más: el `.exe` lo lleva todo dentro.

## Cómo funciona el parcheo

El juego lee la dirección del servidor de un archivo de configuración. Parchear
consiste, simplemente, en escribir `Data\serverinfo.ini` con los datos del servidor
nuevo:

```ini
HOST=<dirección del servidor>
PORT=<puerto>
```

Nada más. No se modifica ningún ejecutable ni archivo del juego, así que **es
reversible**: borra `Data\serverinfo.ini` y todo vuelve a estar como estaba.

La app comprueba de forma continua que ese archivo exista y que su contenido sea el
correcto. Si lo borras, lo editas mal o el juego lo sobrescribe, te avisa y te
vuelve a ofrecer el botón de parchear.

## Compilar desde el código

Si prefieres compilarlo tú:

```bash
pip install pyinstaller pillow
python build.py
```

El ejecutable queda en `dist\PokeOnline.exe`.

También puedes ejecutarlo sin compilar, con `python server_checker.py` (necesita
Pillow para el banner).

## Preguntas frecuentes

**¿Esto es legal / me van a banear?**
No hay nada que banear: los servidores originales están apagados. La app no toca
los archivos del juego, solo añade un archivo de configuración.

**¿Necesito que mis amigos usen esto también?**
Sí. Para batallar o intercambiar, ambos tenéis que estar apuntando al mismo
servidor, así que los dos necesitáis parchear el juego.

**El servidor sale como offline, ¿qué hago?**
Puede estar caído puntualmente. La app reintenta sola cada pocos segundos, así que
déjala abierta un momento. Si sigue así un buen rato, abre una
[issue](https://github.com/Anghios/pokeonline/issues).

**La app está todo en verde, pero dentro del juego no puedo conectar.**
Lo más probable es que tu versión no sea de las compatibles. La app solo comprueba
que el servidor responda y que la configuración esté escrita; no puede saber si tu
versión del juego usa el sistema de los **dos NPC** del Centro Pokémon. Si el
multijugador de tu copia va por librerías, todavía no está soportado.

**¿Puedo volver atrás?**
Borra `Data\serverinfo.ini`.

## Aviso

Proyecto de fans, sin ánimo de lucro y **sin relación alguna con Pokémon Añil,
Nintendo, Game Freak ni The Pokémon Company**. Aquí no se distribuye el juego:
necesitas tu propia copia. El único objetivo es que un modo multijugador
abandonado siga siendo jugable para quien todavía lo disfruta.

---

<p align="center">
  Hecho por <a href="https://github.com/Anghios">Anghios</a>
</p>
