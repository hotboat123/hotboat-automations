# Link de WhatsApp en Email de Nueva Reserva

## Funcionalidad

Cuando se detecta una nueva reserva, el email automático incluye un **link directo a WhatsApp** que te permite contactar al cliente con un mensaje pre-escrito.

## Mensaje Pre-configurado

El link de WhatsApp abre una conversación con el cliente con este mensaje:

```
Hola! como estas? Tomás de HotBoat por aquí, me aparece que intentaste hacer una reserva para el día [FECHA] y tuviste problemas para realizar el pago, te ayudo por aquí?
```

Donde `[FECHA]` se reemplaza automáticamente con la fecha de la reserva.

## Ejemplo de Email

```
🎉 Nueva Reserva HotBoat

👤 Cliente: Claudia Araneda
📞 Contacto: +56927707240 | claudiaes@gmail.com
💬 WhatsApp: https://wa.me/56927707240?text=Hola!%20como%20estas%3F...
📅 Fecha: 21/03/2028 a las 00:00
🛥️ Servicio: HotBoat Trip 2 people (80.990 per person)
...
```

## Cómo Funciona

1. **Detección automática**: El monitor de reservas (`AppointmentsMonitor`) detecta nuevas reservas cada X minutos
2. **Extracción de datos**: Se obtiene el número de teléfono y la fecha de la reserva
3. **Generación del link**: Se crea un link de WhatsApp con:
   - El número del cliente (formato internacional)
   - El mensaje personalizado con la fecha de la reserva
4. **Envío del email**: Se envía el email con el link clickeable

## Formato del Link

El link tiene este formato:

```
https://wa.me/56927707240?text=Hola!%20como%20estas%3F%20Tom%C3%A1s%20de%20HotBoat%20por%20aqu%C3%AD%2C%20me%20aparece%20que%20intentaste%20hacer%20una%20reserva%20para%20el%20d%C3%ADa%2021%2F03%2F2028%20y%20tuviste%20problemas%20para%20realizar%20el%20pago%2C%20te%20ayudo%20por%20aqu%C3%AD%3F
```

- `wa.me/[NUMERO]` es el servicio de WhatsApp para iniciar conversaciones
- `?text=...` es el mensaje pre-escrito (URL encoded)

## Personalización

Si necesitas cambiar el mensaje, edita el archivo:

**`app/monitors/appointments_monitor.py`**

Busca la línea ~320:

```python
whatsapp_message = f"Hola! como estas? Tomás de HotBoat por aquí, me aparece que intentaste hacer una reserva para el día {date_str} y tuviste problemas para realizar el pago, te ayudo por aquí?"
```

Y modifica el texto según tus necesidades. Mantén `{date_str}` para que se incluya la fecha automáticamente.

## Probar la Funcionalidad

Para enviar un email de prueba con el link de WhatsApp:

```bash
python scripts/test_new_appointment_email.py
```

Esto enviará un email de prueba a tu bandeja de entrada configurada en `EMAIL_TO`.

## Notas Importantes

- ✅ El link solo aparece si hay un número de teléfono válido
- ✅ El número se formatea automáticamente (agrega +56 si es necesario)
- ✅ El mensaje se codifica correctamente para URLs (espacios, acentos, etc.)
- ✅ Funciona en cualquier dispositivo (móvil o desktop con WhatsApp instalado)
- ⚠️ Si el cliente no tiene WhatsApp, el link no funcionará

## Mantenimiento

Esta funcionalidad se mantiene automáticamente. No requiere configuración adicional más allá de la configuración estándar del monitor de reservas en `config.yaml`:

```yaml
monitors:
  appointments:
    enabled: true
    check_interval: 300  # cada 5 minutos
```
