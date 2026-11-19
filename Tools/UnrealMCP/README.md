# MCP для Fruit_Example

Локальный сервер `unreal_fruit` связывает Codex с Unreal Editor 5.8 через
встроенный Python Remote Execution Epic. C++ и сторонний плагин движка не нужны.

В проекте включены `PythonScriptPlugin`, `EditorScriptingUtilities` и удалённое
выполнение Python. Транспорт ограничен этим компьютером: UDP multicast
`239.0.0.1:6766`, интерфейс `127.0.0.1`, TTL 0; TCP использует свободный локальный
порт. Сервер выбирает редактор по полному пути проекта. Remote Execution
доступен локальным процессам, а не только этому MCP-клиенту.

## Использование

1. Открыть `Fruit_Example.uproject` в Unreal Editor и дождаться загрузки.
2. Если `.codex/config.toml` отсутствует, скопировать `.codex/config.example.toml`
   в `.codex/config.toml` и указать локальные абсолютные пути. Личная конфигурация
   исключена из Git. Codex читает проектную конфигурацию `.codex/config.toml`. После первого
   подключения может понадобиться перезапуск MCP в настройках Codex.
3. Проверить `editor_status`, затем работать с ассетами через MCP.

Инструменты: `editor_status`, `list_assets`, `list_level_actors`,
`execute_python`, `save_all`. Python выполняется в редакторе и может изменять
проект. `execute_python` возвращает вывод `print()` и ошибки Unreal;
сохранение выполняется отдельно через `save_all`. Доступны операции,
предоставленные Unreal Python API; произвольное редактирование графов Blueprint
этот адаптер не добавляет.

Проверка без перезапуска Codex, через настоящий MCP stdio-клиент:

```powershell
.\Tools\UnrealMCP\.venv\Scripts\python.exe .\Tools\UnrealMCP\client.py
.\Tools\UnrealMCP\.venv\Scripts\python.exe .\Tools\UnrealMCP\client.py list_assets
```

## Повторная установка

Из корня проекта:

```powershell
python -m venv Tools\UnrealMCP\.venv
.\Tools\UnrealMCP\.venv\Scripts\python.exe -m pip install -r Tools\UnrealMCP\requirements.txt
```

При переносе проекта обновить абсолютные пути в `.codex/config.toml`.
`UNREAL_ENGINE_ROOT` указывает на каталог UE, содержащий папку `Engine`.
Используется поставляемый с движком `remote_execution.py`.

Если редактор закрыт, инструмент вернёт ошибку после поиска в течение 8 секунд.
Если Python-команда не ответила в течение 60 секунд, её выполнение в редакторе
могло продолжиться: проверить состояние перед повторной отправкой изменений.
Для больших списков использовать `offset` и `limit`.
