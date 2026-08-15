---
name: git-commit-push
description: >-
  Ejecuta el flujo completo de 3 pasos de Git: sube todas las modificaciones a Staged (git add .),
  genera un mensaje de commit expresivo y adecuado según los cambios realizados (git commit), 
  y finalmente realiza el push a la rama remota (git push).
  Utiliza esta skill siempre que el usuario pida guardar, hacer commit y push, o subir sus cambios al repositorio.
---

# Skill: Git Commit & Push Workflow

Esta skill permite al agente ejecutar de manera automatizada y segura el flujo de 3 pasos para preparar, empaquetar y subir cambios a un repositorio de Git.

---

## Workflow de 3 Pasos

### Paso 1: Mover modificaciones de "Changes" a "Staged"
1. Verificar el estado actual del repositorio:
   ```bash
   git status
   ```
2. Pasar todas las modificaciones (archivos modificados, creados y eliminados) al área de preparación (Staged):
   ```bash
   git add .
   ```
3. Confirmar que los cambios estén listos para commit mediante `git status`.

---

### Paso 2: Generar mensaje y realizar Commit
1. Analizar brevemente el contenido de los cambios staged para comprender su propósito:
   ```bash
   git diff --staged --stat
   ```
2. Determinar un mensaje de commit claro y significativo. Se recomienda utilizar el formato **Conventional Commits**:
   - `feat:` para nuevas funcionalidades.
   - `fix:` para solución de errores.
   - `docs:` para cambios en documentación.
   - `refactor:` para refactorización de código sin cambio de comportamiento.
   - `style:` para formateo o cambios estéticos.
   - `chore:` para mantenimiento, herramientas o configuración.
3. Ejecutar el commit con el mensaje seleccionado:
   ```bash
   git commit -m "<tipo>: <descripción breve y concisa de los cambios>"
   ```

---

### Paso 3: Realizar el Push a la rama remota
1. Detectar la rama actual en uso:
   ```bash
   git branch --show-current
   ```
2. Enviar los cambios al repositorio remoto:
   ```bash
   git push origin <nombre-de-rama>
   ```
   *Nota: Si la rama actual no tiene un tracking remoto configurado, usar `git push -u origin <nombre-de-rama>`.*

---

## Verificación Final
1. Ejecutar `git status` para comprobar que el directorio de trabajo quedó limpio (`working tree clean`).
2. Informar al usuario el hash y mensaje del commit realizado, confirmando que la rama remota ha sido actualizada exitosamente.
