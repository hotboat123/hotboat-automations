# 📱 Configuración de Telegram Bot

Guía paso a paso para configurar las notificaciones por Telegram.

## Paso 1: Crear el Bot

1. **Abre Telegram** en tu teléfono o computadora

2. **Busca @BotFather**
   - Es el bot oficial de Telegram para crear bots
   - Tiene una marca de verificación azul ✓

3. **Inicia conversación**: Envía `/start`

4. **Crea un nuevo bot**: Envía `/newbot`

5. **Sigue las instrucciones:**

```
BotFather: Alright, a new bot. How are we going to call it? 
           Please choose a name for your bot.

Tú: HotBoat Automations

BotFather: Good. Now let's choose a username for your bot. 
           It must end in `bot`. Like this, for example: TetrisBot or tetris_bot.

Tú: hotboat_automations_bot

BotFather: Done! Congratulations on your new bot. 
           You will find it at t.me/hotboat_automations_bot
           
           Use this token to access the HTTP API:
           123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567
           
           Keep your token secure and store it safely...
```

6. **Guarda el token** que te da BotFather
   - Ejemplo: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567`
   - ⚠️ **NO compartas este token con nadie**

## Paso 2: Obtener tu Chat ID

### Opción A: Usando @userinfobot (Más Fácil)

1. Busca **@userinfobot** en Telegram
2. Envía `/start`
3. El bot te responderá con tu información:
```
Id: 987654321
First name: Juan
Username: @juanperez
```
4. Copia el número del `Id` (ejemplo: `987654321`)

### Opción B: Usando @getmyid_bot

1. Busca **@getmyid_bot**
2. Envía cualquier mensaje
3. Te responderá con tu Chat ID

### Opción C: Manualmente

1. Busca tu bot (el que creaste): `@hotboat_automations_bot`
2. Envía `/start` al bot
3. Abre en tu navegador:
```
https://api.telegram.org/bot<TU_TOKEN>/getUpdates
```
Reemplaza `<TU_TOKEN>` con tu token real.

4. Busca tu chat_id en el JSON:
```json
{
  "message": {
    "chat": {
      "id": 987654321,  ← Este es tu CHAT_ID
      "first_name": "Juan",
      ...
    }
  }
}
```

## Paso 3: Configurar en el Proyecto

1. **Abre el archivo `.env`** en tu editor

2. **Agrega las variables:**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567
TELEGRAM_CHAT_IDS=987654321
```

3. **Para múltiples destinatarios:**
```env
TELEGRAM_CHAT_IDS=987654321,456789123,789456123
```
(Separados por comas, sin espacios)

## Paso 4: Probar

1. **Inicia el sistema:**
```bash
python main.py
```

2. **Deberías recibir en Telegram:**
```
ℹ️ ✅ Sistema de automatizaciones iniciado correctamente
```

Si no recibes el mensaje, revisa:
- Que el token sea correcto (sin espacios extras)
- Que el chat_id sea correcto
- Que hayas iniciado conversación con tu bot (envíale /start)
- Los logs en `logs/automation.log`

## Paso 5: Grupos de Telegram (Opcional)

Si quieres recibir notificaciones en un grupo:

1. **Crea un grupo** en Telegram

2. **Agrega tu bot al grupo:**
   - Busca tu bot
   - Agrégalo como miembro al grupo

3. **Haz al bot administrador** (opcional pero recomendado):
   - Info del grupo > Editar > Administradores
   - Agrega tu bot

4. **Obtén el Chat ID del grupo:**
   - Envía un mensaje en el grupo
   - Abre: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Busca el chat con `"type": "group"` o `"type": "supergroup"`
   - El chat_id será negativo: ejemplo `-1001234567890`

5. **Actualiza `.env`:**
```env
TELEGRAM_CHAT_IDS=-1001234567890,987654321
```

## Personalización Avanzada

### Cambiar el nombre y foto del bot

1. Habla con @BotFather
2. `/mybots` > Selecciona tu bot

**Cambiar nombre:**
- Edit Bot > Name > Escribe el nuevo nombre

**Cambiar descripción:**
- Edit Bot > Description > Escribe la descripción

**Cambiar foto:**
- Edit Bot > Edit Botpic > Sube una imagen

**Comandos personalizados:**
- Edit Bot > Edit Commands
- Ejemplo:
```
start - Iniciar el bot
help - Obtener ayuda
status - Ver estado del sistema
```

### Respuestas del bot (Futuro)

Puedes extender el sistema para que el bot responda comandos:

Crea `app/bot_commands.py`:
```python
from telegram import Update
from telegram.ext import Application, CommandHandler

async def status_command(update: Update, context):
    """Responde al comando /status"""
    await update.message.reply_text(
        "🟢 Sistema operando correctamente\n"
        "📅 Monitores activos: 2\n"
        "⏰ Última verificación: hace 30s"
    )

def setup_bot_commands(bot_token):
    """Configura comandos del bot"""
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("status", status_command))
    return application
```

## Solución de Problemas

### Error: "Unauthorized"
- El token es incorrecto
- Verifica que no tenga espacios al inicio/final
- Genera un nuevo token con @BotFather: `/token`

### No recibo mensajes
1. Asegúrate de haber iniciado conversación con el bot
2. El chat_id debe ser un número (positivo para chats privados, negativo para grupos)
3. Revisa los logs: `logs/automation.log`

### Error: "Chat not found"
- El chat_id es incorrecto
- Si es un grupo, debe tener el bot como miembro
- Verifica con `/getUpdates` que el chat_id sea correcto

### Mensajes duplicados
- No ejecutes el script múltiples veces simultáneamente
- Usa solo una instancia del sistema

## Recursos

- [Documentación oficial de Telegram Bots](https://core.telegram.org/bots)
- [BotFather](https://t.me/BotFather)
- [python-telegram-bot Documentación](https://docs.python-telegram-bot.org/)

¡Listo! Ya tienes tu bot de Telegram configurado 🎉

