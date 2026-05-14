# Gestor de Menus Familiares

Proyecto base en Python para gestionar menus familiares con CLI, interfaz web integrada, API REST, capa MCP local y sugerencias de IA.

## Estructura

- `app/main.py`: CLI con Typer
- `app/api.py`: API REST con FastAPI
- `app/web/`: vistas HTML, templates Jinja y estaticos
- `app/core/`: logica de negocio
- `app/mcp/`: servidor MCP local, tools y resources
- `app/ai/`: agente IA, asistente y prompts
- `app/models/`: modelos SQLModel y esquemas Pydantic
- `data/`: SQLite y cache local

## Requisitos

- Python 3.11+

## Instalacion

```bash
cd menu_familiar
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Uso CLI

Ejecutando desde la raiz del proyecto:

```bash
uv run -m app.main init-db
uv run -m app.main seed-demo
uv run -m app.main week
uv run -m app.main suggest-week
uv run -m app.main shopping-list
```

Ejecutando desde el directorio padre:

```bash
uv run --directory menu_familiar -m app.main init-db
uv run --directory menu_familiar -m app.main seed-demo
uv run --directory menu_familiar -m app.main week
uv run --directory menu_familiar -m app.main suggest-week
uv run --directory menu_familiar -m app.main shopping-list
```

## Uso API

```bash
uv run -m app.main serve-api
```

Interfaz web: `http://127.0.0.1:8010/web`

Abrir `http://127.0.0.1:8010/docs`.

El comando lee `host` y `port` desde [config.yaml](/home/asuarez/claude/comidas/menu_familiar/config.yaml).

La web reutiliza la misma Basic Auth que la API.

## Variables de entorno

Editar `.env` para configurar proveedor IA y claves si se quiere salir del modo mock.

## Estado actual

El proyecto deja un flujo funcional de base:

1. Carga configuracion y crea la BD SQLite.
2. Permite gestionar recetas, perfil familiar y menu semanal.
3. Genera sugerencias semanales en modo mock o usando un proveedor real.
4. Expone recursos y tools mediante una capa MCP local simplificada.
5. Incluye una interfaz web server-rendered para operar toda la funcionalidad actual.
