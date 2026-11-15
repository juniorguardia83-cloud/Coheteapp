# 🚀 Cohete Live

Juego para celular (APK) pensado para **TikTok Live**: cuando alguien entra a tu live aparece en el juego con una **skin y su nombre**, y se pone en una **cola para subir a un cohete**. Cuando el cohete se llena (o se acaba el tiempo) hace la cuenta regresiva y **despega**.

- Visual 2.5D (se ve en perspectiva, pero dibujado en 2D): suelo con perspectiva, plataforma, torre, cohete con sombreado y personajes que caminan.
- Cada espectador recibe un **astronauta** con color y accesorio según su nombre, su **foto de perfil** en el casco y su **nombre** encima.
- 🎁 Los que mandan regalo o te siguen **pasan al frente** de la cola. Los comentarios salen como globo de texto.
- Indicador **EN VIVO**: la app detecta si tu live está activo. El estado del servidor se ve en **⚙️ Ajustes**.
- **2 cohetes** y un mapa con base espacial, cristales, torres, antenas y un rover que patrulla.
- **Modo Demo** y botón **Simular** para probar sin estar en vivo.

## 1) Conseguir el APK

1. En GitHub abre la pestaña **Actions** → **Build Cohete Live APK**.
2. Si no corrió sola: **Run workflow**.
3. Cuando termine, entra a la ejecución y descarga el artefacto **Cohete-Live-APK** (es un .zip con `app-debug.apk`).
4. Instala el APK en el celular (permite "instalar apps desconocidas").

Puedes abrir la app y usar **🤖 Demo** o **➕ Simular** sin nada más.

## 2) Conectar tu TikTok (para el live real)

La conexión con TikTok Live usa Node.js, así que corre en **Termux** en el mismo celular:

```bash
pkg update
pkg install nodejs git
git clone https://github.com/juniorguardia83-cloud/Coheteapp
cd Coheteapp/server
bash iniciar.sh
```

La primera vez instala las dependencias solo. Déjalo abierto en Termux.

Luego, en la app: toca **⚙️**, escribe tu **usuario de TikTok** (sin @) y **Guardar**.
Cuando inicies tu live, el indicador cambia a **🔴 EN VIVO** y cada persona que entre aparecerá en la cola.

> No hace falta tu contraseña. Nunca se la des a ninguna app.

## Si sale "Failed to sign request" (403)

La librería necesita un servicio de firma (**Euler Stream**). Sin clave usa el cupo gratis compartido, y a veces lo rechaza. La solución es una **clave gratis**:

1. Crea una cuenta en https://www.eulerstream.com y genera una API key en su panel (dashboard).
2. En Termux, guárdala en un archivo (reemplaza TU_CLAVE):
   ```bash
   cd ~/Coheteapp/server
   echo "TU_CLAVE" > euler.key
   bash iniciar.sh
   ```
   Al arrancar debe decir `🔑 Usando tu clave de Euler Stream`.

El archivo `euler.key` no se sube a GitHub (está en `.gitignore`). No compartas tu clave con nadie.

## Ajustes (⚙️)

| Ajuste | Para qué sirve |
|---|---|
| Usuario de TikTok | La cuenta que está en vivo |
| Servidor / Puerto | Por defecto `127.0.0.1` y `8765` |
| Asientos por cohete | De 1 a 200. Hay 2 cohetes: se llena el 1 y luego el 2 |
| Tiempo para despegar | Minutos y segundos (hasta 60:00) desde que sube el primero |
| Sonidos | Pops y motor |

## Notas

- La librería de TikTok Live es **no oficial**: si TikTok cambia algo, puede dejar de funcionar hasta que se actualice (`npm install tiktok-live-connector@latest` dentro de `server/`).
- Si el live aún no empezó, el servidor reintenta cada 20 segundos.
- Si no hay foto de perfil, se usa la inicial del nombre.

## Estructura

```
app/        App Android (WebView) + juego en app/src/main/assets/index.html
server/     Puente TikTok Live → app (Node.js, para Termux)
.github/    Compilación automática del APK
```
