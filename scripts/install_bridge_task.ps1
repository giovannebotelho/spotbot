# Script PowerShell para instalar a Tarefa Agendada no Windows (Antigravity Mobile Telegram Bridge)
# Executa a ponte em segundo plano mesmo com a tela do PC bloqueada (Win + L)

$taskName = "AntigravityTelegramBridge"
$pythonExecutable = (Get-Command python.exe).Source
$scriptPath = "C:\Py\spotbot\services\telegram_bridge.py"
$workingDir = "C:\Py\spotbot"

Write-Host "🚀 Instalando a tarefa agendada: $taskName..." -ForegroundColor Green

# Ação: Executar Python sem janela de terminal
$action = New-ScheduledTaskAction -Execute $pythonExecutable -Argument "`"$scriptPath`"" -WorkingDirectory $workingDir

# Disparador: Ao iniciar o sistema / fazer logon
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Configurações: Reiniciar em caso de falha, não suspender se estiver em bateria
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Registrar a Tarefa
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Ponte remota do Antigravity via Telegram Bot" -User $env:USERNAME

Write-Host "✅ Tarefa '$taskName' instalada com sucesso!" -ForegroundColor Green
Write-Host "📌 Ela iniciará automaticamente ao fazer logon e continuará rodando com a tela bloqueada." -ForegroundColor Yellow
