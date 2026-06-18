@echo off
REM Docker Helper Script for PDF Agent
REM Usage: docker-helper.bat [command]

if "%1"=="" (
    echo.
    echo PDF Agent Docker Helper
    echo =======================
    echo Usage: docker-helper.bat [command]
    echo.
    echo Commands:
    echo   build       - Build the Docker image
    echo   up          - Start the application
    echo   down        - Stop the application
    echo   logs        - View application logs
    echo   restart     - Restart the application
    echo   shell       - Open a shell in the running container
    echo   clean       - Remove containers and volumes
    echo   setup       - Setup environment file
    echo   status      - Check container status
    echo.
    exit /b 0
)

if "%1"=="build" (
    echo Building Docker image...
    docker-compose build
    exit /b 0
)

if "%1"=="up" (
    echo Starting PDF Agent...
    docker-compose up -d
    timeout /t 5
    echo.
    echo ✓ PDF Agent is running at http://localhost:8501
    exit /b 0
)

if "%1"=="down" (
    echo Stopping PDF Agent...
    docker-compose down
    echo ✓ Stopped
    exit /b 0
)

if "%1"=="logs" (
    echo Showing application logs (Ctrl+C to exit)...
    docker-compose logs -f pdf-agent
    exit /b 0
)

if "%1"=="restart" (
    echo Restarting PDF Agent...
    docker-compose restart pdf-agent
    echo ✓ Restarted
    exit /b 0
)

if "%1"=="shell" (
    echo Opening shell in container...
    docker-compose exec pdf-agent /bin/bash
    exit /b 0
)

if "%1"=="clean" (
    echo Cleaning up Docker resources...
    docker-compose down -v
    echo ✓ Cleaned
    exit /b 0
)

if "%1"=="setup" (
    if exist .env (
        echo .env file already exists
    ) else (
        echo Creating .env from example...
        copy .env.example .env
        echo ✓ .env created. Edit it and add your GROQ_API_KEY
    )
    exit /b 0
)

if "%1"=="status" (
    echo Checking container status...
    docker-compose ps
    exit /b 0
)

echo Unknown command: %1
echo Run 'docker-helper.bat' without arguments for help
exit /b 1
