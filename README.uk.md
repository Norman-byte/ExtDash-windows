# ExtDash Windows

**Українська** | [English](README.md)

Автор: [Norman-byte](https://github.com/Norman-byte)

Створено разом у співпраці з [Claude](https://claude.ai) (Anthropic).

Дашборд для моніторингу ПК на Windows, зручний для телефона. Невеликий сервер на Flask
об'єднує дані з Glances (навантаження CPU, GPU, RAM, мережа) та LibreHardwareMonitor
(температура CPU, вентилятори, температури материнської плати) в один JSON і віддає
односторінковий дашборд (`index.html`).

## Вимоги

- Windows 10/11
- Python 3 з Flask і Glances (веб-режим): `pip install flask "glances[web]"`
- LibreHardwareMonitor (LHM): `winget install LibreHardwareMonitor.LibreHardwareMonitor`

## Налаштування LibreHardwareMonitor

1. Запустіть LHM (від імені адміністратора, інакше датчики плати можуть не читатися).
2. Options -> Remote Web Server -> увімкніть (порт 8085).
3. Options -> Run On Windows Startup.

Сервер читає `http://127.0.0.1:8085/data.json`.

## Конфіг датчиків

Скопіюйте `sensor_config.example.json` у `sensor_config.json` і відредагуйте його. Файл
лежить у `.gitignore`, бо залежить від конкретного ПК. Кожен датчик це посилання на листок
дерева LHM: `chip` / `group` / `label` мають точно збігатися з назвами, які показує LHM.

- `cpu_fan`, `case_fans`: датчики вентиляторів, показуються у відсотках
- `cpu_temp`, `vrm_temp`, `pch_temp`: датчики температури
- `gpu_temp`: необов'язково, замінює температуру GPU з Glances (наприклад, GPU Hot Spot)
- `network_interface`: назва інтерфейсу, як її показує Glances

Вентилятори: `label` це назва датчика в LHM, `display_label` це текст на дашборді.
Відсоток обертів рахується як `(RPM - min_rpm) / (max_rpm - min_rpm) * 100`, тому задайте
`min_rpm` і `max_rpm` за реальним діапазоном кожного вентилятора.

## Запуск

Спочатку Glances, потім сервер:

    glances -w --disable-plugin smart
    cd C:\path\to\ExtDash-windows
    python pc_dashboard_server.py

Відкрийте `http://127.0.0.1:8080` на ПК або `http://<IP-ПК>:8080` на телефоні.
Сирий JSON за адресою `/data`. Одразу після старту деякі значення можуть кілька секунд
бути `null`. Після зміни коду сервера або `sensor_config.json` перезапустіть сервер.

## Автозапуск

Запускайте обидві команди при вході в Windows через Планувальник завдань (скрипт із двома
викликами Start-Process: спочатку Glances, через 5 секунд сервер), із затримкою входу 30 секунд.

## Безпека

Glances, LHM і сервер слухають на всіх інтерфейсах без автентифікації, тому метрики
видно всім у локальній мережі.

## Ліцензія

Дивіться `LICENSE`.